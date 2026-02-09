"""
GitOps Manifest Generation Models
Request/Response models for GitOps template processing
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
from pydantic import BaseModel, Field, validator

from app.models.common import EnvironmentType


class CronJobConfig(BaseModel):
    """
    Configuration model for CronJob settings

    Defines the schedule and command for a Kubernetes CronJob.
    """
    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Name of the cronjob",
        example="data-sync"
    )

    schedule: str = Field(
        default="0 * * * *",
        description="Cron schedule expression (e.g., '0 2 * * *' for daily at 2 AM)",
        example="0 2 * * *"
    )

    suspend: bool = Field(
        default=False,
        description="Whether to suspend the cronjob",
        example=False
    )

    cmd: List[str] = Field(
        default_factory=list,
        description="Command to execute as a list of strings",
        example=["npm", "run", "sync"]
    )

    class Config:
        json_schema_extra = {
            "example": {
                "name": "data-sync",
                "schedule": "0 2 * * *",
                "suspend": False,
                "cmd": ["npm", "run", "sync"]
            }
        }


class WorkerConfig(BaseModel):
    """
    Configuration model for Worker deployment settings

    Defines the worker deployment with conditional secrets for Vertex AI and BigQuery,
    plus additional environment variables.
    """
    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Name of the worker deployment",
        example="language-translation"
    )

    worker_type: str = Field(
        ...,
        alias="workerType",
        min_length=1,
        max_length=100,
        description="Type identifier for the worker (used in WORKER_TYPE env var)",
        example="languageTranslation"
    )

    secrets: Optional[List[str]] = Field(
        default=None,
        description="List of secrets to enable. Options: 'vertex_ai' for Vertex AI credentials, "
                    "'bq' for BigQuery credentials. If empty or null, no credential volumes are mounted.",
        example=["vertex_ai", "bq"]
    )

    vertex_ai_secret: str = Field(
        default="equity-api-ai",
        alias="vertexAiSecret",
        description="Name of the Kubernetes secret containing Vertex AI credentials (used if 'vertex_ai' is in secrets)",
        example="equity-api-ai"
    )

    bigquery_secret: str = Field(
        default="equity-api-cred",
        alias="bigquerySecret",
        description="Name of the Kubernetes secret containing BigQuery credentials (used if 'bq' is in secrets)",
        example="equity-api-cred"
    )

    additional_env: Optional[Dict[str, str]] = Field(
        default=None,
        alias="additionalEnv",
        description="Additional environment variables to pass to the worker as key-value pairs. "
                    "These will be added to the config section in values.yaml.",
        example={"BATCH_SIZE": "100", "MAX_RETRIES": "3"}
    )

    class Config:
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "name": "language-translation",
                "workerType": "languageTranslation",
                "secrets": ["vertex_ai", "bq"],
                "vertexAiSecret": "equity-api-ai",
                "bigquerySecret": "equity-api-cred",
                "additionalEnv": {
                    "BATCH_SIZE": "100",
                    "MAX_RETRIES": "3"
                }
            }
        }


class GitOpsManifestRequest(BaseModel):
    """
    Request model for GitOps manifest generation

    Generates Kubernetes manifests from templates with variable substitution.
    """
    environment: EnvironmentType = Field(
        ...,
        description="Target environment (development, staging, production, qa, uat)"
    )

    microservice_name: str = Field(
        ...,
        alias="microserviceName",
        min_length=1,
        max_length=100,
        description="Name of the microservice",
        example="user-service"
    )

    microservice_url: str = Field(
        ...,
        alias="microserviceUrl",
        description="URL/path for the microservice",
        example="/api/users"
    )

    container_port: int = Field(
        ...,
        alias="containerPort",
        ge=1,
        le=65535,
        description="Container port number",
        example=8080
    )

    gitops_repo_url: str = Field(
        ...,
        alias="gitOpsRepoUrl",
        description="GitOps repository URL",
        example="https://github.com/org/gitops-repo.git"
    )

    git_repo_name: str = Field(
        ...,
        alias="gitRepoName",
        min_length=1,
        max_length=100,
        description="Git repository name",
        example="gitops-repo"
    )

    git_branch: str = Field(
        default="main",
        alias="gitBranch",
        description="Git branch name",
        example="main"
    )

    argocd_app_name: str = Field(
        ...,
        alias="argoCdAppName",
        min_length=1,
        max_length=100,
        description="ArgoCD application name",
        example="user-service-dev"
    )

    domain_name: str = Field(
        ...,
        alias="domainName",
        description="Domain name for ingress",
        example="api.example.com"
    )

    env_content: str = Field(
        ...,
        alias="envContent",
        description="Content of .env file with KEY=VALUE pairs (one per line). "
                    "Same format as /configmap/update endpoint. Required for environment variable validation.",
        example="LOG_LEVEL=debug\nNODE_ENV=development\nDATABASE_URL=postgresql://localhost:5432/db"
    )

    cronjobs: Optional[List[CronJobConfig]] = Field(
        default=None,
        description="Optional list of CronJob configurations. If provided, cronjob resources will be included "
                    "in the generated manifests for each entry. If null or empty, no cronjobs will be configured.",
        example=[
            {
                "name": "data-sync",
                "schedule": "0 2 * * *",
                "suspend": False,
                "cmd": ["npm", "run", "sync"]
            },
            {
                "name": "cleanup",
                "schedule": "0 0 * * *",
                "suspend": False,
                "cmd": ["npm", "run", "cleanup"]
            }
        ]
    )

    worker: Optional[WorkerConfig] = Field(
        default=None,
        description="Optional Worker deployment configuration. If provided, a worker deployment will be included "
                    "with Vertex AI and BigQuery secret mounts. If null, no worker will be configured.",
        example={
            "name": "language-translation",
            "workerType": "LANGUAGE_TRANSLATION",
            "vertexAiSecret": "equity-api-ai",
            "bigquerySecret": "equity-api-cred",
            "additionalEnv": {
                "BATCH_SIZE": "100",
                "MAX_RETRIES": "3"
            }
        }
    )

    @validator('microservice_name')
    def validate_microservice_name(cls, v):
        """Validate microservice name format"""
        if not v or not v.strip():
            raise ValueError("Microservice name cannot be empty")
        # Check for invalid characters
        if any(char in v for char in ['/', '\\', '..', ' ']):
            raise ValueError("Microservice name cannot contain slashes, spaces, or '..'")
        return v.strip().lower()

    @validator('gitops_repo_url')
    def validate_gitops_url(cls, v):
        """Validate GitOps repository URL"""
        if not v or not v.strip():
            raise ValueError("GitOps repository URL cannot be empty")
        v = v.strip()
        if not (v.startswith('http://') or v.startswith('https://') or v.startswith('git@')):
            raise ValueError("GitOps URL must start with http://, https://, or git@")
        return v

    @validator('env_content')
    def validate_env_content(cls, v):
        """Validate environment content format (same as ConfigMap)"""
        if v is None or not v.strip():
            raise ValueError(
                "env_content is required and cannot be empty. "
                "Please provide environment variables in KEY=VALUE format."
            )

        # Check that at least one KEY=VALUE pair exists
        lines = [line.strip() for line in v.strip().split('\n')]
        valid_lines = [line for line in lines if line and not line.startswith('#') and '=' in line]

        if not valid_lines:
            raise ValueError(
                "Environment content must contain at least one valid KEY=VALUE pair. "
                "Lines should be in format: KEY=VALUE"
            )

        return v.strip()

    class Config:
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "environment": "development",
                "microserviceName": "user-service",
                "microserviceUrl": "/api/users",
                "containerPort": 8080,
                "gitOpsRepoUrl": "https://github.com/org/gitops-repo.git",
                "gitRepoName": "gitops-repo",
                "gitBranch": "main",
                "argoCdAppName": "user-service-dev",
                "domainName": "api.example.com",
                "envContent": "LOG_LEVEL=debug\nNODE_ENV=development\nDATABASE_URL=postgresql://localhost:5432/db",
                "cronjobs": [
                    {
                        "name": "data-sync",
                        "schedule": "0 2 * * *",
                        "suspend": False,
                        "cmd": ["npm", "run", "sync"]
                    }
                ]
            }
        }


class ProcessedFile(BaseModel):
    """Information about a processed template file"""
    source_path: str = Field(..., description="Original template file path")
    output_path: str = Field(..., description="Output file path")
    replacements_made: int = Field(..., description="Number of replacements made")


class GitOpsManifestResponse(BaseModel):
    """
    Response model for GitOps manifest generation
    """
    status: str = Field(
        default="success",
        description="Operation status"
    )

    message: str = Field(
        ...,
        description="Human-readable status message"
    )

    microservice_name: str = Field(
        ...,
        description="Microservice name"
    )

    environment: str = Field(
        ...,
        description="Target environment"
    )

    output_directory: str = Field(
        ...,
        description="Path to generated manifests"
    )

    processed_files: List[ProcessedFile] = Field(
        default_factory=list,
        description="List of processed template files"
    )

    total_files_processed: int = Field(
        ...,
        description="Total number of files processed"
    )

    template_variables: Dict[str, str] = Field(
        default_factory=dict,
        description="Variables used for substitution"
    )

    environment_variables: Dict[str, str] = Field(
        default_factory=dict,
        description="Parsed environment variables from env_content"
    )

    cronjobs: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="CronJobs configurations if provided in the request"
    )

    worker: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Worker configuration if provided in the request"
    )

    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp of operation"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "status": "success",
                "message": "GitOps manifests generated successfully",
                "microservice_name": "user-service",
                "environment": "development",
                "output_directory": "/tmp/git-ops/user-service",
                "processed_files": [
                    {
                        "source_path": "template/git-ops/deployment.yaml",
                        "output_path": "temp/git-ops/deployment.yaml",
                        "replacements_made": 4
                    }
                ],
                "total_files_processed": 5,
                "template_variables": {
                    "MICRO_SERVICE_NAME": "user-service",
                    "CONTAINER_PORT": "8080"
                },
                "cronjobs": [
                    {
                        "name": "data-sync",
                        "schedule": "0 2 * * *",
                        "suspend": False,
                        "cmd": ["npm", "run", "sync"]
                    }
                ],
                "timestamp": "2026-01-19T15:30:00.000000"
            }
        }

class CleanupRequest(BaseModel):
    """Request model for deployment cleanup"""
    microservice_name: str = Field(
        ...,
        description="Name of the microservice to cleanup"
    )
    environment: str = Field(
        ...,
        description="Target environment (dev/stage/prod)"
    )
    domain_name: str = Field(
        ...,
        description="Full domain name (e.g., app.dev.example.com)"
    )
    argocd_app_name: str = Field(
        ...,
        description="ArgoCD application name"
    )
    gitops_repo_url: str = Field(
        ...,
        description="GitOps repository URL"
    )
    microservice_repo_url: str = Field(
        ...,
        description="Microservice repository URL"
    )
    github_secret_names: Optional[List[str]] = Field(
        None,
        description="⚠️ EXPLICIT OPT-IN: GitHub secret names to delete",
        example=["DOCKER_USER", "GCP_SA_KEY"]
    )
    force: bool = Field(
        False,
        description="⚠️ DANGEROUS: Skip safety validations (use with caution)"
    )
    audit_comment: Optional[str] = Field(
        None,
        description="Required reason for cleanup operation",
        max_length=500
    )
