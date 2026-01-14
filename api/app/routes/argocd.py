"""
API Routes - Dummy/Template File
"""
from typing import Optional
from fastapi import APIRouter, Depends, Query

from app.controllers.argocd_controller import ArgoCDController
from app.core.dependencies import get_argocd_service
from app.models.argocd import (
    ApplicationDeleteResponse,
    ApplicationListResponse,
    ApplicationQueryParams,
    ApplicationResponse,
    CreateApplicationRequest,
    CreateProjectRequest,
    ProjectListResponse,
    ProjectResponse,
    RollbackApplicationRequest,
    SyncApplicationRequest,
    SyncOperationResponse,
    UpdateApplicationRequest
)
from app.models.common import BaseResponse, ResponseStatus
from app.services.argocd_service import ArgoCDService

# Create the router instance - this MUST exist for main.py
router = APIRouter(prefix="/argocd", tags=["ArgoCD"])

@router.get("/version")
async def get_argocd_version(
    service: ArgoCDService = Depends(get_argocd_service)
):
    """Get ArgoCD server version"""
    try:
        version = service.get_version()
        return BaseResponse(
            status=ResponseStatus.SUCCESS,
            data=version
        )
    except Exception as e:
        return BaseResponse(
            status=ResponseStatus.ERROR,
            message=f"Failed to get ArgoCD version: {str(e)}"
        )


@router.get("/settings")
async def get_argocd_settings(
    service: ArgoCDService = Depends(get_argocd_service)
):
    """Get ArgoCD server settings"""
    try:
        settings = service.get_settings()
        return BaseResponse(
            status=ResponseStatus.SUCCESS,
            data=settings
        )
    except Exception as e:
        return BaseResponse(
            status=ResponseStatus.ERROR,
            message=f"Failed to get ArgoCD settings: {str(e)}"
        )

@router.get("/projects", response_model=ProjectListResponse)
async def list_projects(
    service: ArgoCDService = Depends(get_argocd_service)
):
    """List all ArgoCD projects"""
    return await ArgoCDController.list_projects(service)


@router.get("/projects/{project_name}", response_model=ProjectResponse)
async def get_project(
    project_name: str,
    service: ArgoCDService = Depends(get_argocd_service)
):
    """Get project details by name"""
    return await ArgoCDController.get_project(service, project_name)


@router.post("/projects", response_model=BaseResponse, status_code=201)
async def create_project(
    request: CreateProjectRequest,
    service: ArgoCDService = Depends(get_argocd_service)
):
    """
    Create a new ArgoCD project
    
    - **name**: Project name (required)
    - **description**: Project description (optional)
    - **source_repos**: List of allowed source repositories
    - **destinations**: List of allowed destinations (server and namespace)
    """
    return await ArgoCDController.create_project(service, request)


@router.delete("/projects/{project_name}", response_model=BaseResponse)
async def delete_project(
    project_name: str,
    service: ArgoCDService = Depends(get_argocd_service)
):
    """Delete a project"""
    return await ArgoCDController.delete_project(service, project_name)

@router.get("/applications", response_model=ApplicationListResponse)
async def list_applications(
    project: Optional[str] = Query(None, description="Filter by project"),
    repo: Optional[str] = Query(None, description="Filter by repository"),
    sync_status: Optional[str] = Query(None, description="Filter by sync status"),
    health_status: Optional[str] = Query(None, description="Filter by health status"),
    service: ArgoCDService = Depends(get_argocd_service)
):
    """
    List all applications with optional filtering
    
    - **project**: Filter applications by project name
    - **repo**: Filter applications by repository URL (partial match)
    - **sync_status**: Filter by sync status (Synced, OutOfSync, Unknown)
    - **health_status**: Filter by health status (Healthy, Progressing, Degraded, etc.)
    """
    query_params = ApplicationQueryParams(
        project=project,
        repo=repo,
        sync_status=sync_status,
        health_status=health_status
    )
    return await ArgoCDController.list_applications(service, query_params)


@router.get("/applications/out-of-sync", response_model=ApplicationListResponse)
async def get_out_of_sync_applications(
    project: Optional[str] = Query(None, description="Filter by project"),
    service: ArgoCDService = Depends(get_argocd_service)
):
    """Get all out-of-sync applications"""
    return await ArgoCDController.get_out_of_sync_applications(service, project)


@router.get("/applications/unhealthy", response_model=ApplicationListResponse)
async def get_unhealthy_applications(
    project: Optional[str] = Query(None, description="Filter by project"),
    service: ArgoCDService = Depends(get_argocd_service)
):
    """Get all unhealthy applications"""
    return await ArgoCDController.get_unhealthy_applications(service, project)


@router.post("/applications/sync-all-out-of-sync", response_model=BaseResponse)
async def sync_all_out_of_sync(
    project: Optional[str] = Query(None, description="Filter by project"),
    prune: bool = Query(True, description="Prune resources"),
    service: ArgoCDService = Depends(get_argocd_service)
):
    """Sync all out-of-sync applications"""
    return await ArgoCDController.sync_all_out_of_sync(service, project, prune)


@router.get("/applications/{app_name}", response_model=ApplicationResponse)
async def get_application(
    app_name: str,
    service: ArgoCDService = Depends(get_argocd_service)
):
    """Get application details by name"""
    return await ArgoCDController.get_application(service, app_name)


@router.get("/applications/{app_name}/status", response_model=BaseResponse)
async def get_application_status(
    app_name: str,
    service: ArgoCDService = Depends(get_argocd_service)
):
    """Get application sync and health status"""
    return await ArgoCDController.get_application_status(service, app_name)


@router.post("/applications", response_model=BaseResponse, status_code=201)
async def create_application(
    request: CreateApplicationRequest,
    service: ArgoCDService = Depends(get_argocd_service)
):
    """
    Create a new ArgoCD application
    
    - **name**: Application name (required)
    - **project**: ArgoCD project (default: "default")
    - **repo_url**: Git repository URL (required)
    - **path**: Path within repository (default: ".")
    - **target_revision**: Target revision/branch (default: "HEAD")
    - **destination_namespace**: Target Kubernetes namespace (default: "default")
    - **auto_sync**: Enable automated sync (default: false)
    - **auto_prune**: Enable auto-prune (default: false)
    - **self_heal**: Enable self-heal (default: false)
    """
    return await ArgoCDController.create_application(service, request)


@router.put("/applications/{app_name}", response_model=BaseResponse)
async def update_application(
    app_name: str,
    request: UpdateApplicationRequest,
    service: ArgoCDService = Depends(get_argocd_service)
):
    """Update an existing application"""
    return await ArgoCDController.update_application(service, app_name, request)


@router.delete("/applications/{app_name}", response_model=ApplicationDeleteResponse)
async def delete_application(
    app_name: str,
    cascade: bool = Query(False, description="Delete application resources"),
    service: ArgoCDService = Depends(get_argocd_service)
):
    """
    Delete an application
    
    - **app_name**: Name of the application to delete
    - **cascade**: If true, delete all application resources from cluster
    """
    return await ArgoCDController.delete_application(service, app_name, cascade)


@router.post("/applications/{app_name}/sync", response_model=SyncOperationResponse)
async def sync_application(
    app_name: str,
    request: SyncApplicationRequest,
    service: ArgoCDService = Depends(get_argocd_service)
):
    """
    Sync an application
    
    - **app_name**: Name of the application to sync
    - **revision**: Specific revision to sync (optional)
    - **prune**: Prune resources (default: false)
    - **dry_run**: Perform dry run without applying changes (default: false)
    """
    return await ArgoCDController.sync_application(service, app_name, request)


@router.post("/applications/{app_name}/rollback", response_model=BaseResponse)
async def rollback_application(
    app_name: str,
    request: RollbackApplicationRequest,
    service: ArgoCDService = Depends(get_argocd_service)
):
    """
    Rollback application to a specific revision
    
    - **app_name**: Name of the application to rollback
    - **revision**: Target revision to rollback to (required)
    """
    return await ArgoCDController.rollback_application(service, app_name, request)


@router.post("/applications/{app_name}/refresh", response_model=BaseResponse)
async def refresh_application(
    app_name: str,
    service: ArgoCDService = Depends(get_argocd_service)
):
    """Force refresh application from Git repository"""
    return await ArgoCDController.refresh_application(service, app_name)