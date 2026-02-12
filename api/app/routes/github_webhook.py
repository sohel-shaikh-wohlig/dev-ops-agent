"""
GitHub Webhook Routes
FastAPI endpoints for receiving GitHub webhook events and querying
Terraform PR status.

Endpoints:
  POST /github/webhook          — Receive GitHub webhook events
  GET  /terraform/pr-status/{pr_number} — Query Terraform plan/apply status
"""

from fastapi import APIRouter, Request, status

from app.controllers.github_webhook_controller import github_webhook_controller
from app.models.github_webhook import PRStatusResponse
from app.models.common import ErrorResponse

# ---------------------------------------------------------------------------
# GitHub webhook router
# ---------------------------------------------------------------------------
github_router = APIRouter(prefix="/github", tags=["GitHub Webhooks"])


@github_router.post(
    "/webhook",
    status_code=status.HTTP_200_OK,
    summary="Receive GitHub Webhook Events",
    description=(
        "Receives GitHub webhook events (issue_comment, pull_request, "
        "pull_request_review), validates the HMAC-SHA256 signature, and "
        "dispatches the event for processing."
    ),
    responses={
        401: {"model": ErrorResponse, "description": "Invalid webhook signature"},
        400: {"model": ErrorResponse, "description": "Malformed JSON payload"},
    },
)
async def receive_webhook(request: Request) -> dict:
    """
    **GitHub Webhook Receiver**

    Validates the ``X-Hub-Signature-256`` header against the configured
    secret, then routes the event to the appropriate handler.
    """
    return await github_webhook_controller.handle_webhook(request)


# ---------------------------------------------------------------------------
# Terraform PR status router
# ---------------------------------------------------------------------------
terraform_pr_router = APIRouter(prefix="/terraform", tags=["Terraform Automation"])


@terraform_pr_router.get(
    "/pr-status/{pr_number}",
    response_model=PRStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Terraform PR Status",
    description=(
        "Returns the current Terraform plan/apply status for a given "
        "pull request number, as reported by Atlantis webhook events."
    ),
    responses={
        404: {"model": ErrorResponse, "description": "PR not found"},
    },
)
async def get_pr_status(pr_number: int) -> PRStatusResponse:
    """
    **Terraform PR Status**

    Looks up the plan/apply status, approval state, and PR state
    for the given pull request number.
    """
    return await github_webhook_controller.get_pr_status(pr_number)
