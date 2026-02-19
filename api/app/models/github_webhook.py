"""
GitHub Webhook Models
Request/Response models for GitHub webhook events and Terraform PR status
"""

from typing import Optional
from pydantic import BaseModel, Field


class PRStatusResponse(BaseModel):
    """Response model for Terraform PR status lookup."""

    pr_number: int = Field(
        ...,
        description="Pull request number",
    )
    plan_status: str = Field(
        default="pending",
        description="Terraform plan status (pending|running|success|failed)",
    )
    plan_summary: str = Field(
        default="",
        description="Human-readable plan summary (e.g. Add: 2, Change: 0, Destroy: 0)",
    )
    apply_status: str = Field(
        default="pending",
        description="Terraform apply status (pending|running|success|failed)",
    )
    approved: bool = Field(
        default=False,
        description="Whether the PR has been approved",
    )
    state: str = Field(
        default="open",
        description="PR state (open|closed|merged)",
    )
    last_comment: str = Field(
        default="",
        description="Last Atlantis comment body (truncated)",
    )
    comment_id: Optional[int] = Field(
        default=None,
        description="GitHub comment ID of the last Atlantis comment",
    )
    repo_name: str = Field(
        default="",
        description="Full repository name (owner/repo) from the webhook event",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "pr_number": 123,
                "plan_status": "success",
                "plan_summary": "Add: 2, Change: 0, Destroy: 0",
                "apply_status": "pending",
                "approved": False,
                "state": "open",
                "last_comment": "",
                "comment_id": 987654321,
                "repo_name": "org/repo",
            }
        }
