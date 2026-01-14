from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime

from app.models.common import HealthStatus, MetadataModel, RepositoryType, SyncStatus

# Request Models
class CreateApplicationRequest(BaseModel):
    """Request model for creating an application"""
    name: str = Field(..., min_length=1, max_length=253)
    project: str = Field("default", description="ArgoCD project name")
    repo_url: str = Field(..., description="Git repository URL")
    path: str = Field(".", description="Path within repository")
    target_revision: str = Field("HEAD", description="Target revision (branch/tag/commit)")
    destination_server: str = Field("https://kubernetes.default.svc", description="Kubernetes server")
    destination_namespace: str = Field("default", description="Target namespace")
    
    # Optional Helm configuration
    chart: Optional[str] = Field(None, description="Helm chart name")
    helm_values: Optional[Dict[str, Any]] = Field(None, description="Helm values")
    
    # Sync policy
    auto_sync: bool = Field(False, description="Enable automated sync")
    auto_prune: bool = Field(False, description="Enable auto-prune")
    self_heal: bool = Field(False, description="Enable self-heal")
    
    # Labels and annotations
    labels: Optional[Dict[str, str]] = None
    annotations: Optional[Dict[str, str]] = None


class UpdateApplicationRequest(BaseModel):
    """Request model for updating an application"""
    repo_url: Optional[str] = None
    path: Optional[str] = None
    target_revision: Optional[str] = None
    destination_namespace: Optional[str] = None
    auto_sync: Optional[bool] = None
    auto_prune: Optional[bool] = None
    self_heal: Optional[bool] = None


class SyncApplicationRequest(BaseModel):
    """Request model for syncing an application"""
    revision: Optional[str] = Field(None, description="Specific revision to sync")
    prune: bool = Field(False, description="Prune resources")
    dry_run: bool = Field(False, description="Perform dry run")
    resources: Optional[List[Dict[str, Any]]] = Field(None, description="Specific resources to sync")


class RollbackApplicationRequest(BaseModel):
    """Request model for rolling back an application"""
    revision: str = Field(..., description="Revision to rollback to")


# Response Models
class ApplicationSyncStatusResponse(BaseModel):
    """Application sync status"""
    status: SyncStatus
    revision: Optional[str] = None
    compared_to: Optional[Dict[str, Any]] = Field(None, alias="comparedTo")
    
    class Config:
        populate_by_name = True


class ApplicationHealthResponse(BaseModel):
    """Application health status"""
    status: HealthStatus
    message: Optional[str] = None


class ApplicationResourceResponse(BaseModel):
    """Application resource information"""
    group: Optional[str] = None
    version: str
    kind: str
    namespace: Optional[str] = None
    name: str
    status: Optional[str] = None
    health: Optional[Dict[str, Any]] = None
    sync_wave: Optional[int] = Field(None, alias="syncWave")
    
    class Config:
        populate_by_name = True


class ApplicationStatusResponse(BaseModel):
    """Application status"""
    sync: ApplicationSyncStatusResponse
    health: ApplicationHealthResponse
    resources: Optional[List[ApplicationResourceResponse]] = None
    operation_state: Optional[Dict[str, Any]] = Field(None, alias="operationState")
    
    class Config:
        populate_by_name = True


class ApplicationResponse(BaseModel):
    """Full application response"""
    metadata: MetadataModel
    spec: Dict[str, Any]
    status: ApplicationStatusResponse


class ApplicationSummaryResponse(BaseModel):
    """Application summary for list views"""
    name: str
    project: str
    sync_status: SyncStatus
    health_status: HealthStatus
    repo_url: str
    namespace: str
    created_at: Optional[datetime] = None


class ApplicationListResponse(BaseModel):
    """List of applications"""
    items: List[ApplicationSummaryResponse]
    total: int


class SyncOperationResponse(BaseModel):
    """Sync operation response"""
    application: str
    status: str
    message: Optional[str] = None
    started_at: Optional[datetime] = None


class ApplicationDeleteResponse(BaseModel):
    """Application deletion response"""
    application: str
    deleted: bool
    cascade: bool
    message: Optional[str] = None


# Query Parameters
class ApplicationQueryParams(BaseModel):
    """Query parameters for listing applications"""
    project: Optional[str] = Field(None, description="Filter by project")
    repo: Optional[str] = Field(None, description="Filter by repository")
    sync_status: Optional[SyncStatus] = Field(None, description="Filter by sync status")
    health_status: Optional[HealthStatus] = Field(None, description="Filter by health status")

# Request Models
class CreateProjectRequest(BaseModel):
    """Request model for creating a project"""
    name: str = Field(..., min_length=1, max_length=253)
    description: Optional[str] = Field(None, description="Project description")
    
    # Source repositories
    source_repos: List[str] = Field(default_factory=list, description="Allowed source repositories")
    
    # Destinations
    destinations: List[Dict[str, str]] = Field(
        default_factory=list,
        description="Allowed destinations (server and namespace)"
    )
    
    # Cluster resource whitelist/blacklist
    cluster_resource_whitelist: Optional[List[Dict[str, str]]] = Field(
        None,
        description="Cluster-scoped resources allowed"
    )
    namespace_resource_blacklist: Optional[List[Dict[str, str]]] = Field(
        None,
        description="Namespace-scoped resources denied"
    )
    
    # Roles
    roles: Optional[List[Dict[str, Any]]] = Field(None, description="Project roles")


class UpdateProjectRequest(BaseModel):
    """Request model for updating a project"""
    description: Optional[str] = None
    source_repos: Optional[List[str]] = None
    destinations: Optional[List[Dict[str, str]]] = None


# Response Models
class ProjectDestinationResponse(BaseModel):
    """Project destination"""
    server: str
    namespace: Optional[str] = None
    name: Optional[str] = None


class ProjectResponse(BaseModel):
    """Project response"""
    metadata: MetadataModel
    spec: Dict[str, Any]


class ProjectSummaryResponse(BaseModel):
    """Project summary for list views"""
    name: str
    description: Optional[str] = None
    source_repos_count: int
    destinations_count: int


class ProjectListResponse(BaseModel):
    """List of projects"""
    items: List[ProjectSummaryResponse]
    total: int

class CreateRepositoryRequest(BaseModel):
    """Request model for creating/adding a repository"""
    repo_url: str = Field(..., alias="repo", description="Repository URL")
    type: RepositoryType = Field(RepositoryType.GIT, description="Repository type")
    name: Optional[str] = Field(None, description="Repository name")
    
    # Authentication
    username: Optional[str] = Field(None, description="Username for authentication")
    password: Optional[str] = Field(None, description="Password for authentication")
    ssh_private_key: Optional[str] = Field(None, description="SSH private key")
    
    # TLS
    insecure: bool = Field(False, description="Skip TLS verification")
    tls_client_cert_data: Optional[str] = Field(None, description="TLS client certificate")
    tls_client_cert_key: Optional[str] = Field(None, description="TLS client certificate key")
    
    # Helm specific
    enable_oci: bool = Field(False, description="Enable OCI for Helm")
    
    class Config:
        populate_by_name = True


class UpdateRepositoryRequest(BaseModel):
    """Request model for updating a repository"""
    username: Optional[str] = None
    password: Optional[str] = None
    ssh_private_key: Optional[str] = None
    insecure: Optional[bool] = None


# Response Models
class RepositoryResponse(BaseModel):
    """Repository response"""
    repo: str
    type: str
    name: Optional[str] = None
    username: Optional[str] = None
    insecure: bool = False
    connection_state: Optional[Dict] = None


class RepositorySummaryResponse(BaseModel):
    """Repository summary for list views"""
    repo: str
    type: str
    name: Optional[str] = None
    connection_status: Optional[str] = None


class RepositoryListResponse(BaseModel):
    """List of repositories"""
    items: List[RepositorySummaryResponse]
    total: int


# Response Models (Clusters are typically read-only via API)
class ClusterInfoResponse(BaseModel):
    """Cluster information"""
    server_version: Optional[str] = Field(None, alias="serverVersion")
    connection_state: Optional[Dict[str, Any]] = Field(None, alias="connectionState")
    
    class Config:
        populate_by_name = True


class ClusterResponse(BaseModel):
    """Cluster response"""
    server: str
    name: str
    config: Optional[Dict[str, Any]] = None
    connection_state: Optional[Dict[str, Any]] = Field(None, alias="connectionState")
    server_version: Optional[str] = Field(None, alias="serverVersion")
    info: Optional[ClusterInfoResponse] = None
    
    class Config:
        populate_by_name = True


class ClusterSummaryResponse(BaseModel):
    """Cluster summary for list views"""
    server: str
    name: str
    status: Optional[str] = None


class ClusterListResponse(BaseModel):
    """List of clusters"""
    items: List[ClusterSummaryResponse]
    total: int