from enum import Enum
from typing import Any, Dict, List, Optional

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
    """Error response model"""
    status: ResponseStatus = ResponseStatus.ERROR
    message: str
    detail: Optional[str] = None
    error_code: Optional[str] = None


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

class RepositoryType(str, Enum):
    """Repository type"""
    GIT = "git"
    HELM = "helm"