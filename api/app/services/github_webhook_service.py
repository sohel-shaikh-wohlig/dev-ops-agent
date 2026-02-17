"""
GitHub Webhook Service
Handles GitHub webhook event routing and Atlantis comment parsing.
Persists PR status in Redis via the global RedisManager.
"""

import json
import re
from typing import Any, Dict, Optional

import redis.asyncio as aioredis
from fastapi import HTTPException, status

from app.core.logging_config import logger
from app.core.redis import redis_manager

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
REDIS_KEY_PREFIX = "github:webhook"
REDIS_TTL = 7200  # 2 hours
PUBSUB_CHANNEL_PREFIX = "pr_updates"

PLAN_REGEX = re.compile(
    r"Plan:\s*(\d+) to add,\s*(\d+) to change,\s*(\d+) to destroy"
)

_DEFAULT_PR_ENTRY: Dict[str, Any] = {
    "plan_status": "pending",
    "apply_status": "pending",
    "plan_summary": "",
    "approved": False,
    "state": "open",
    "last_comment": "",
}


# ---------------------------------------------------------------------------
# Redis helpers
# ---------------------------------------------------------------------------

def _redis_key(pr_number: int) -> str:
    return f"{REDIS_KEY_PREFIX}:{pr_number}"


async def _get_pr_data(pr_number: int) -> Optional[Dict[str, Any]]:
    """Read PR data from Redis. Returns None if the key does not exist."""
    try:
        raw = await redis_manager.client.get(_redis_key(pr_number))
    except aioredis.RedisError as exc:
        logger.error(f"Redis read error for PR #{pr_number}: {exc}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Redis is unavailable",
        )

    if raw is None:
        return None

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        logger.warning(f"Corrupt JSON in Redis for PR #{pr_number}, resetting")
        return None


async def _save_pr_data(pr_number: int, data: Dict[str, Any]) -> None:
    """Persist PR data to Redis with TTL, then publish an update event."""
    payload = json.dumps(data)
    try:
        await redis_manager.client.set(
            _redis_key(pr_number),
            payload,
            ex=REDIS_TTL,
        )
    except aioredis.RedisError as exc:
        logger.error(f"Redis write error for PR #{pr_number}: {exc}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Redis is unavailable",
        )

    # Best-effort publish — data is already persisted, so a failed
    # notification is non-fatal.
    try:
        publish_data = {**data, "pr_number": pr_number}
        await redis_manager.client.publish(
            f"{PUBSUB_CHANNEL_PREFIX}:{pr_number}",
            json.dumps(publish_data),
        )
    except aioredis.RedisError as exc:
        logger.warning(f"Redis PUBLISH failed for PR #{pr_number}: {exc}")


async def _ensure_pr(pr_number: int) -> Dict[str, Any]:
    """Return the stored entry for *pr_number*, creating a default if missing."""
    data = await _get_pr_data(pr_number)
    if data is not None:
        return data
    data = {**_DEFAULT_PR_ENTRY}
    await _save_pr_data(pr_number, data)
    return data


class GitHubWebhookService:
    """
    Service for processing GitHub webhook events.

    Responsibilities:
      - Route events to the correct handler based on X-GitHub-Event
      - Parse Atlantis plan/apply comments
      - Track PR plan_status, apply_status, approval, and state in Redis
    """

    # ------------------------------------------------------------------
    # Public — event dispatcher
    # ------------------------------------------------------------------

    async def process_event(
        self,
        event_type: str,
        payload: Dict[str, Any],
    ) -> None:
        """
        Dispatch a GitHub event to the correct handler.

        Args:
            event_type: Value of the X-GitHub-Event header.
            payload:    Parsed JSON body of the webhook.
        """
        handler = {
            "issue_comment": self._handle_issue_comment,
            "pull_request": self._handle_pull_request,
            "pull_request_review": self._handle_pull_request_review,
        }.get(event_type)

        if handler is None:
            logger.debug(f"Ignoring unhandled GitHub event: {event_type}")
            return

        try:
            await handler(payload)
        except HTTPException:
            raise
        except Exception:
            logger.error(
                f"Error processing GitHub event '{event_type}'", exc_info=True
            )

    # ------------------------------------------------------------------
    # Public — query helpers
    # ------------------------------------------------------------------

    async def get_pr_status(self, pr_number: int) -> Optional[Dict[str, Any]]:
        """Return the stored status dict for *pr_number*, or None."""
        return await _get_pr_data(pr_number)

    # ------------------------------------------------------------------
    # Private — event handlers
    # ------------------------------------------------------------------

    async def _handle_issue_comment(self, payload: Dict[str, Any]) -> None:
        """
        Handle an ``issue_comment`` event.

        Only processes comments on pull requests.
        Parses Atlantis plan/apply output and updates the PR store in Redis.
        """
        issue = payload.get("issue", {})

        # Only care about comments on PRs
        if "pull_request" not in issue:
            return

        pr_number: int = issue.get("number", 0)
        comment = payload.get("comment", {})
        comment_id: int = comment.get("id", 0)
        body: str = comment.get("body", "")
        repo_name: str = payload.get("repository", {}).get("full_name", "")

        logger.info(
            f"Processing Atlantis comment | repo={repo_name} | pr=#{pr_number}"
        )

        entry = await _ensure_pr(pr_number)
        entry["comment_id"] = comment_id
        entry["last_comment"] = body[:500]  # truncate for safety

        # --- Detect plan result ---
        plan_match = PLAN_REGEX.search(body)
        if plan_match:
            add, change, destroy = plan_match.groups()
            entry["plan_status"] = "success"
            entry["plan_summary"] = (
                f"Add: {add}, Change: {change}, Destroy: {destroy}"
            )
            logger.info(
                f"Atlantis plan success | pr=#{pr_number} | {entry['plan_summary']}"
            )
            await _save_pr_data(pr_number, entry)
            return

        # --- Detect apply result ---
        if "Apply complete!" in body:
            entry["apply_status"] = "success"
            logger.info(f"Atlantis apply success | pr=#{pr_number}")
            await _save_pr_data(pr_number, entry)
            return

        # --- Detect errors ---
        if "Error:" in body:
            if entry["plan_status"] in ("pending", "running"):
                entry["plan_status"] = "failed"
                logger.warning(f"Atlantis plan failed | pr=#{pr_number}")
            else:
                entry["apply_status"] = "failed"
                logger.warning(f"Atlantis apply failed | pr=#{pr_number}")
            await _save_pr_data(pr_number, entry)
            return

        # Save the last_comment update even if no pattern matched
        await _save_pr_data(pr_number, entry)

    async def _handle_pull_request(self, payload: Dict[str, Any]) -> None:
        """
        Handle a ``pull_request`` event.

        - ``opened``: initialise the PR store entry.
        - ``closed``: mark as merged or closed.
        """
        action: str = payload.get("action", "")
        pr = payload.get("pull_request", {})
        pr_number: int = pr.get("number", 0)

        if action == "opened":
            await _ensure_pr(pr_number)
            logger.info(f"PR opened | pr=#{pr_number}")
            return

        if action == "closed":
            entry = await _ensure_pr(pr_number)
            merged: bool = pr.get("merged", False)
            entry["state"] = "merged" if merged else "closed"
            await _save_pr_data(pr_number, entry)
            logger.info(
                f"PR closed | pr=#{pr_number} | state={entry['state']}"
            )
            return

    async def _handle_pull_request_review(
        self, payload: Dict[str, Any]
    ) -> None:
        """
        Handle a ``pull_request_review`` event.

        Marks the PR as approved when the review state is ``approved``.
        """
        review = payload.get("review", {})
        state: str = review.get("state", "").lower()
        pr_number: int = payload.get("pull_request", {}).get("number", 0)

        if state == "approved":
            entry = await _ensure_pr(pr_number)
            entry["approved"] = True
            await _save_pr_data(pr_number, entry)
            logger.info(f"PR approved | pr=#{pr_number}")


# Singleton instance
github_webhook_service = GitHubWebhookService()
