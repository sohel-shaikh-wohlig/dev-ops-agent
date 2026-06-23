from enum import Enum
from typing import Any, Dict, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field


class SyncStatus(str, Enum):
    """Application sync status"""
    SYNCED = "Synced"
    OUT_OF_SYNC = "OutOfSync"
    UNKNOWN = "Unknown"


class HealthStatus(str, Enum):
    """Application health status"""
    HEALTHY = "Healthy"
    PROGRESSING = "Progressing"
    DEGRADED = "Degraded"
    SUSPENDED = "Suspended"
    MISSING = "Missing"
    UNKNOWN = "Unknown"


class ResponseStatus(str, Enum):
    """API response status"""
    SUCCESS = "success"
    ERROR = "error"
    WARNING = "warning"


class BaseResponse(BaseModel):
    """Base response model"""
    status: ResponseStatus = ResponseStatus.SUCCESS
    message: Optional[str] = None
    data: Optional[Any] = None


class ErrorResponse(BaseModel):
    """
    Response model for errors
    
    Provides detailed error information for debugging and user feedback.
    """
    status: str = Field(
        default="error",
        description="Error status",
        example="error"
    )
    
    error: str = Field(
        ...,
        description="Error type/category",
        example="ValidationError"
    )
    
    message: str = Field(
        ...,
        description="Human-readable error message",
        example="Invalid GitOps repository URL"
    )
    
    detail: Optional[str] = Field(
        None,
        description="Detailed error information",
        example="GitOps URL must start with http://, https://, or git@"
    )
    
    field: Optional[str] = Field(
        None,
        description="Field that caused the error (for validation errors)",
        example="gitops_url"
    )
    
    code: Optional[str] = Field(
        None,
        description="Error code for programmatic handling",
        example="INVALID_URL_FORMAT"
    )
    
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp when error occurred"
    )
    
    request_id: Optional[str] = Field(
        None,
        description="Request ID for tracking",
        example="req_abc123"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "error",
                "error": "ValidationError",
                "message": "Invalid GitOps repository URL",
                "detail": "GitOps URL must start with http://, https://, or git@. Got: invalid-url",
                "field": "gitops_url",
                "code": "INVALID_URL_FORMAT",
                "timestamp": "2026-01-19T10:30:00.000000",
                "request_id": "req_abc123def456"
            }
        }    


class PaginationParams(BaseModel):
    """Pagination parameters"""
    page: int = Field(1, ge=1, description="Page number")
    page_size: int = Field(20, ge=1, le=100, description="Items per page")


class MetadataModel(BaseModel):
    """Kubernetes metadata"""
    name: str
    namespace: Optional[str] = None
    labels: Optional[Dict[str, str]] = None
    annotations: Optional[Dict[str, str]] = None


class SourceModel(BaseModel):
    """ArgoCD application source"""
    repo_url: str = Field(..., alias="repoURL")
    path: str = "."
    target_revision: str = Field("HEAD", alias="targetRevision")
    chart: Optional[str] = None
    
    class Config:
        populate_by_name = True


class DestinationModel(BaseModel):
    """ArgoCD application destination"""
    server: str = "https://kubernetes.default.svc"
    namespace: str = "default"


class SyncPolicyModel(BaseModel):
    """Sync policy configuration"""
    automated: Optional[Dict[str, Any]] = None
    sync_options: Optional[List[str]] = Field(None, alias="syncOptions")
    retry: Optional[Dict[str, Any]] = None
    
    class Config:
        populate_by_name = True

# ========================================
# Enums
# ========================================
class RepositoryType(str, Enum):
    """Repository type"""
    GIT = "git"
    HELM = "helm"

class EnvironmentType(str, Enum):
    """Supported environment types"""
    DEVELOPMENT = "dev"
    TEST = "test"
    STAGING = "staging"
    PRODUCTION = "production"
    PROD = "prod"
    QA = "qa"
    UAT = "uat"


class ChangeType(str, Enum):
    """Type of configuration change"""
    ADD = "ADD"
    UPDATE = "UPDATE"
    UNCHANGED = "UNCHANGED"
