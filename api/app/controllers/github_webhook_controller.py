"""
GitHub Webhook Controller
Validates webhook signatures, dispatches events to the service layer,
and exposes Terraform PR status lookups.
"""

import hashlib
import hmac

from fastapi import HTTPException, Request, status

from app.core.config import get_settings
from app.core.logging_config import logger
from app.models.github_webhook import PRStatusResponse
from app.services.github_webhook_service import github_webhook_service


class GitHubWebhookController:
    """Controller for GitHub webhook ingestion and PR status queries."""

    def __init__(self) -> None:
        self.service = github_webhook_service
        logger.info("GitHubWebhookController initialized")

    # ------------------------------------------------------------------
    # Webhook ingestion
    # ------------------------------------------------------------------

    async def handle_webhook(self, request: Request) -> dict:
        """
        Receive and process a GitHub webhook event.

        1. Read raw body and validate HMAC-SHA256 signature.
        2. Route the event to the appropriate service handler.
        3. Return 200 immediately after dispatching.

        Raises:
            HTTPException 401: Invalid or missing signature.
            HTTPException 400: Malformed JSON payload.
        """
        settings = get_settings()

        # --- Read raw body ---
        raw_body = await request.body()

        # --- Validate signature ---
        signature_header = request.headers.get("X-Hub-Signature-256", "")
        if not self._verify_signature(
            raw_body, signature_header, settings.GITHUB_WEBHOOK_SECRET
        ):
            logger.warning("GitHub webhook signature verification failed")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid webhook signature",
            )

        # --- Parse JSON ---
        try:
            payload = await request.json()
        except Exception:
            logger.warning("GitHub webhook — malformed JSON body")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid JSON payload",
            )

        event_type = request.headers.get("X-GitHub-Event", "")
        logger.info(f"GitHub webhook received | event={event_type}")

        # --- Dispatch to service ---
        await self.service.process_event(event_type, payload)

        return {"status": "ok"}

    # ------------------------------------------------------------------
    # PR status lookup
    # ------------------------------------------------------------------

    async def get_pr_status(self, pr_number: int) -> PRStatusResponse:
        """
        Return the current Terraform plan/apply status for a PR.

        Returns a default idle response when the PR has no stored status.
        """
        data = await self.service.get_pr_status(pr_number)
        if data is None:
            return PRStatusResponse(pr_number=pr_number, state="idle")

        return PRStatusResponse(
            pr_number=pr_number,
            plan_status=data["plan_status"],
            plan_summary=data["plan_summary"],
            apply_status=data["apply_status"],
            approved=data["approved"],
            state=data["state"],
            last_comment=data["last_comment"],
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _verify_signature(
        payload: bytes,
        signature_header: str,
        secret: str,
    ) -> bool:
        """
        Verify the HMAC-SHA256 signature sent by GitHub.

        Args:
            payload:          Raw request body bytes.
            signature_header: Value of X-Hub-Signature-256 (``sha256=<hex>``).
            secret:           Webhook secret configured in Settings.

        Returns:
            True if the signature is valid, False otherwise.
        """
        if not secret or not signature_header:
            return False

        if not signature_header.startswith("sha256="):
            return False

        expected = hmac.new(
            secret.encode("utf-8"),
            payload,
            hashlib.sha256,
        ).hexdigest()

        received = signature_header.removeprefix("sha256=")
        return hmac.compare_digest(expected, received)


# Singleton instance
github_webhook_controller = GitHubWebhookController()
