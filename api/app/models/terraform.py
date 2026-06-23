"""
Terraform Automation Models
Request/Response models for Terraform resource provisioning
"""

from typing import Any, Dict, Optional
from pydantic import BaseModel, Field, validator


class TerraformProvisionRequest(BaseModel):
    """
    Request model for Terraform resource provisioning.

    Accepts client, environment, resource type, and a flexible
    resource_config dictionary whose shape depends on resource_type.

    Example request body:
    {
        "client_name": "acme-corp",
        "environment": "dev",
        "resource_type": "gcs",
        "resource_config": {
            "bucket_name": "acme-corp-data",
            "is_public": false
        }
    }
    """

    client_name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Client or project identifier",
        example="acme-corp",
    )

    environment: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Target environment (e.g. dev, staging, production)",
        example="dev",
    )

    resource_type: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Terraform resource type to provision (e.g. gcs, cloud_sql, gke)",
        example="gcs",
    )

    resource_config: Dict[str, Any] = Field(
        default_factory=dict,
        description="Resource-specific configuration variables. "
        "Shape depends on resource_type.",
        example={"bucket_name": "acme-corp-data", "is_public": False},
    )

    terraform_repo_url: str = Field(
        ...,
        min_length=1,
        description="Git repository URL (HTTPS or SSH)",
        example="git@github.com:tehvault/terraform_devops.git",
    )

    @validator("client_name")
    def validate_client_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("client_name cannot be blank")
        if any(ch in v for ch in ["/", "\\", "..", " "]):
            raise ValueError(
                "client_name cannot contain slashes, spaces, or '..'"
            )
        return v.lower()

    @validator("environment")
    def validate_environment(cls, v: str) -> str:
        v = v.strip().lower()
        allowed = {"dev", "test", "staging", "production", "qa", "uat"}
        if v not in allowed:
            raise ValueError(
                f"environment must be one of: {', '.join(sorted(allowed))}"
            )
        return v

    @validator("resource_type")
    def validate_resource_type(cls, v: str) -> str:
        v = v.strip().lower()
        if not v:
            raise ValueError("resource_type cannot be blank")
        return v

    @validator("terraform_repo_url")
    def validate_terraform_repo_url(cls, v: str) -> str:
        v = v.strip()
        if not (v.startswith("https://") or v.startswith("git@")):
            raise ValueError(
                "terraform_repo_url must be an HTTPS or SSH URL"
            )
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "client_name": "acme-corp",
                "environment": "dev",
                "resource_type": "gcs",
                "resource_config": {
                    "bucket_name": "acme-corp-data",
                    "is_public": False,
                },
                "terraform_repo_url": "git@github.com:tehvault/terraform_devops.git",
            }
        }


class TerraformProvisionResponse(BaseModel):
    """Response model for a Terraform GitOps provisioning request."""

    status: str = Field(
        default="success",
        description="Request status",
    )
    message: str = Field(
        default="Terraform PR created successfully",
        description="Human-readable status message",
    )
    resource_type: str = Field(
        ...,
        description="Requested resource type",
    )
    environment: str = Field(
        ...,
        description="Target environment",
    )
    branch: Optional[str] = Field(
        None,
        description="Feature branch created for the PR",
    )
    pr_url: Optional[str] = Field(
        None,
        description="URL of the created Pull Request",
    )
