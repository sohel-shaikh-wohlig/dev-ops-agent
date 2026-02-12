"""
GitHub Webhook Service
Handles GitHub webhook event routing and Atlantis comment parsing.
Maintains an in-memory PR store for Terraform plan/apply status tracking.
"""

import re
from typing import Any, Dict, Optional

from app.core.logging_config import logger


# ---------------------------------------------------------------------------
# In-memory PR store (replace with a database later)
# ---------------------------------------------------------------------------
# Structure:
#   pr_store[pr_number] = {
#       "plan_status":   "pending|running|success|failed",
#       "apply_status":  "pending|running|success|failed",
#       "plan_summary":  "",
#       "approved":      False,
#       "state":         "open|closed|merged",
#       "last_comment":  "",
#   }
# ---------------------------------------------------------------------------
pr_store: Dict[int, Dict[str, Any]] = {}

# Regex for Atlantis plan output
PLAN_REGEX = re.compile(
    r"Plan:\s*(\d+) to add,\s*(\d+) to change,\s*(\d+) to destroy"
)


def _ensure_pr(pr_number: int) -> Dict[str, Any]:
    """Return the store entry for *pr_number*, creating it if missing."""
    if pr_number not in pr_store:
        pr_store[pr_number] = {
            "plan_status": "pending",
            "apply_status": "pending",
            "plan_summary": "",
            "approved": False,
            "state": "open",
            "last_comment": "",
        }
    return pr_store[pr_number]


class GitHubWebhookService:
    """
    Service for processing GitHub webhook events.

    Responsibilities:
      - Route events to the correct handler based on X-GitHub-Event
      - Parse Atlantis plan/apply comments
      - Track PR plan_status, apply_status, approval, and state
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
        except Exception:
            logger.error(
                f"Error processing GitHub event '{event_type}'", exc_info=True
            )

    # ------------------------------------------------------------------
    # Public — query helpers
    # ------------------------------------------------------------------

    def get_pr_status(self, pr_number: int) -> Optional[Dict[str, Any]]:
        """Return the stored status dict for *pr_number*, or None."""
        return pr_store.get(pr_number)

    # ------------------------------------------------------------------
    # Private — event handlers
    # ------------------------------------------------------------------

    async def _handle_issue_comment(self, payload: Dict[str, Any]) -> None:
        """
        Handle an ``issue_comment`` event.

        Only processes comments on pull requests made by the ``atlantis`` user.
        Parses Atlantis plan/apply output and updates the PR store.
        """
        issue = payload.get("issue", {})

        # Only care about comments on PRs
        if "pull_request" not in issue:
            return

        pr_number: int = issue.get("number", 0)
        comment = payload.get("comment", {})
        author: str = comment.get("user", {}).get("login", "")
        body: str = comment.get("body", "")
        repo_name: str = payload.get("repository", {}).get("full_name", "")

        # Only process Atlantis comments
        if author.lower() != "atlantis":
            return

        logger.info(
            f"Processing Atlantis comment | repo={repo_name} | pr=#{pr_number}"
        )

        entry = _ensure_pr(pr_number)
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
            return

        # --- Detect apply result ---
        if "Apply complete!" in body:
            entry["apply_status"] = "success"
            logger.info(f"Atlantis apply success | pr=#{pr_number}")
            return

        # --- Detect errors ---
        if "Error:" in body:
            # Determine which phase failed based on current state
            if entry["plan_status"] in ("pending", "running"):
                entry["plan_status"] = "failed"
                logger.warning(f"Atlantis plan failed | pr=#{pr_number}")
            else:
                entry["apply_status"] = "failed"
                logger.warning(f"Atlantis apply failed | pr=#{pr_number}")
            return

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
            entry = _ensure_pr(pr_number)
            logger.info(f"PR opened | pr=#{pr_number}")
            return

        if action == "closed":
            entry = _ensure_pr(pr_number)
            merged: bool = pr.get("merged", False)
            entry["state"] = "merged" if merged else "closed"
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
            entry = _ensure_pr(pr_number)
            entry["approved"] = True
            logger.info(f"PR approved | pr=#{pr_number}")


# Singleton instance
github_webhook_service = GitHubWebhookService()
