"""
GitHub Webhook Routes
FastAPI endpoints for receiving GitHub webhook events and querying
Terraform PR status.

Endpoints:
  POST /github/webhook          — Receive GitHub webhook events
  GET  /terraform/pr-status/{pr_number} — Query Terraform plan/apply status
"""

from typing import Optional

from fastapi import APIRouter, Query, Request, status

from pydantic import BaseModel, Field

from app.controllers.github_webhook_controller import github_webhook_controller
from app.core.logging_config import logger
from app.models.github_webhook import PRStatusResponse
from app.models.common import ErrorResponse
from app.services.git_service import git_service

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


# ---------------------------------------------------------------------------
# GitHub comment lookup
# ---------------------------------------------------------------------------


@github_router.get(
    "/comments/{comment_id}",
    status_code=status.HTTP_200_OK,
    summary="Get GitHub Comment by ID",
    description=(
        "Retrieves a specific GitHub issue comment by its numeric ID. "
        "Optionally accepts a repo_name query parameter (owner/repo); "
        "falls back to the GITOPS_REPO_URL setting when omitted."
    ),
    responses={
        400: {"model": ErrorResponse, "description": "Missing repo_name"},
        404: {"model": ErrorResponse, "description": "Comment not found"},
        502: {"model": ErrorResponse, "description": "GitHub API error"},
    },
)
async def get_comment_by_id(
    comment_id: int,
    repo_name: Optional[str] = Query(
        None, description="Full repository name (owner/repo)"
    ),
) -> dict:
    """
    **Get GitHub Comment**

    Fetches a single issue comment from the GitHub API using the
    comment's numeric ID.
    """
    logger.info(f"get_comment_by_id | comment_id={comment_id} | repo_name={repo_name!r}")
    return await git_service.get_comment_by_id(comment_id, repo_name)


# ---------------------------------------------------------------------------
# Post PR comment
# ---------------------------------------------------------------------------


class PostCommentRequest(BaseModel):
    pr_number: int = Field(..., description="Pull request number")
    comment: str = Field(..., description="Comment body text")
    repo_name: Optional[str] = Field(
        None, description="Full repository name (owner/repo)"
    )


@github_router.post(
    "/comments",
    status_code=status.HTTP_201_CREATED,
    summary="Post a Comment on a Pull Request",
    description=(
        "Posts a new comment on a GitHub pull request. "
        "Optionally accepts repo_name in the body; "
        "falls back to the GITOPS_REPO_URL setting when omitted."
    ),
    responses={
        400: {"model": ErrorResponse, "description": "Missing repo_name"},
        404: {"model": ErrorResponse, "description": "PR not found"},
        502: {"model": ErrorResponse, "description": "GitHub API error"},
    },
)
async def post_pr_comment(request: PostCommentRequest) -> dict:
    """
    **Post PR Comment**

    Creates a new comment on the specified pull request via the GitHub API.
    """
    return await git_service.post_pr_comment(
        request.pr_number, request.comment, request.repo_name
    )


# ---------------------------------------------------------------------------
# Merge Pull Request
# ---------------------------------------------------------------------------


class MergePRRequest(BaseModel):
    commit_title: str = Field(
        ..., description="Title for the merge commit"
    )
    commit_message: str = Field(
        "", description="Extra detail appended to the merge commit message"
    )
    merge_method: str = Field(
        "squash", description="Merge strategy: 'merge', 'squash', or 'rebase'"
    )
    repo_name: Optional[str] = Field(
        None, description="Full repository name (owner/repo). Falls back to GITOPS_REPO_URL when omitted."
    )


@github_router.post(
    "/pulls/{pull_number}/merge",
    status_code=status.HTTP_200_OK,
    summary="Merge a Pull Request",
    description=(
        "Merges the specified GitHub Pull Request using the GitHub REST API "
        "(PUT /repos/{owner}/{repo}/pulls/{pull_number}/merge). "
        "Supports merge, squash, and rebase strategies."
    ),
    responses={
        400: {"model": ErrorResponse, "description": "Invalid merge_method or missing repo_name"},
        404: {"model": ErrorResponse, "description": "PR not found"},
        405: {"model": ErrorResponse, "description": "PR is not mergeable"},
        409: {"model": ErrorResponse, "description": "Merge conflict"},
        422: {"model": ErrorResponse, "description": "GitHub validation error"},
        502: {"model": ErrorResponse, "description": "GitHub API error"},
    },
)
async def merge_pull_request(
    pull_number: int,
    request: MergePRRequest,
) -> dict:
    """
    **Merge Pull Request**

    Calls the GitHub API to merge the given PR. The ``merge_method`` controls
    how commits are combined:

    - ``squash`` — squashes all commits into one (default)
    - ``merge``  — creates a merge commit
    - ``rebase`` — rebases commits onto the base branch
    """
    return await github_webhook_controller.merge_pull_request(
        pull_number=pull_number,
        commit_title=request.commit_title,
        commit_message=request.commit_message,
        merge_method=request.merge_method,
        repo_name=request.repo_name,
    )


# ---------------------------------------------------------------------------
# Delete Branch
# ---------------------------------------------------------------------------


@github_router.delete(
    "/branches/{branch_name:path}",
    status_code=status.HTTP_200_OK,
    summary="Delete a GitHub Branch",
    description=(
        "Deletes a branch from a GitHub repository using the GitHub REST API "
        "(DELETE /repos/{owner}/{repo}/git/refs/heads/{branch}). "
        "Branch names containing slashes (e.g. tf/client/dev/gcs/202501011200) "
        "are fully supported via path parameter."
    ),
    responses={
        400: {"model": ErrorResponse, "description": "Missing repo_name"},
        404: {"model": ErrorResponse, "description": "Branch not found"},
        502: {"model": ErrorResponse, "description": "GitHub API error"},
    },
)
async def delete_branch(
    branch_name: str,
    repo_name: Optional[str] = Query(
        None, description="Full repository name (owner/repo). Falls back to GITOPS_REPO_URL when omitted."
    ),
) -> dict:
    """
    **Delete GitHub Branch**

    Removes the specified branch ref from the repository. The branch name
    is captured as a path segment so forward slashes are preserved.

    Returns ``{"branch": "<name>", "deleted": true}`` on success.
    """
    return await github_webhook_controller.delete_branch(
        branch_name=branch_name,
        repo_name=repo_name,
    )


# ---------------------------------------------------------------------------
# Close Pull Request
# ---------------------------------------------------------------------------


@github_router.patch(
    "/pulls/{pull_number}/close",
    status_code=status.HTTP_200_OK,
    summary="Close a Pull Request",
    description=(
        "Closes the specified GitHub Pull Request without merging it, "
        "using the GitHub REST API "
        "(PATCH /repos/{owner}/{repo}/pulls/{pull_number} with state=closed). "
        "Optionally accepts repo_name as a query parameter; "
        "falls back to GITOPS_REPO_URL when omitted."
    ),
    responses={
        400: {"model": ErrorResponse, "description": "Missing repo_name"},
        404: {"model": ErrorResponse, "description": "PR not found"},
        422: {"model": ErrorResponse, "description": "GitHub validation error (e.g. already closed)"},
        502: {"model": ErrorResponse, "description": "GitHub API error"},
    },
)
async def close_pull_request(
    pull_number: int,
    repo_name: Optional[str] = Query(
        None, description="Full repository name (owner/repo). Falls back to GITOPS_REPO_URL when omitted."
    ),
) -> dict:
    """
    **Close Pull Request**

    Sets the PR state to ``closed`` without merging. Returns
    ``{"pull_number": N, "state": "closed", "closed": true}`` on success.
    """
    return await github_webhook_controller.close_pull_request(
        pull_number=pull_number,
        repo_name=repo_name,
    )
