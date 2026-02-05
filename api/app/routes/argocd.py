"""
ArgoCD API Routes

All endpoints support an optional 'env' query parameter to target
environment-specific ArgoCD instances:
- env=dev: Uses DEV ArgoCD server and credentials
- env=uat: Uses UAT ArgoCD server and credentials
- env=staging: Uses STAGING ArgoCD server and credentials
- env=prod: Uses PROD ArgoCD server and credentials
- env=default (or omitted): Uses default ArgoCD configuration
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.controllers.argocd_controller import ArgoCDController
from app.core.dependencies import get_argocd_service_with_env
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
from app.services.argocd_service import ArgoCDService, EnvironmentConfigError
from app.core.exceptions import TokenRenewalFailedException

# Create the router instance - this MUST exist for main.py
router = APIRouter(prefix="/argocd", tags=["ArgoCD"])

@router.get("/version")
async def get_argocd_version(
    service: ArgoCDService = Depends(get_argocd_service_with_env)
):
    """
    Get ArgoCD server version

    Query Parameters:
    - **env**: Target environment (optional, e.g., 'uat', 'development')
    """
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
    service: ArgoCDService = Depends(get_argocd_service_with_env)
):
    """
    Get ArgoCD server settings

    Query Parameters:
    - **env**: Target environment (optional, e.g., 'uat', 'development')
    """
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


@router.get("/config")
async def get_environment_config(
    env: Optional[str] = Query(None, description="Target environment (e.g., 'dev', 'uat', 'staging', 'prod')")
):
    """
    Get ArgoCD configuration status for a specific environment.

    This endpoint checks what configuration is available without attempting to connect.
    Useful for verifying environment setup before making API calls.

    Query Parameters:
    - **env**: Target environment (optional). Supported values:
        - 'dev' or 'development': Uses _DEV suffix
        - 'uat': Uses _UAT suffix
        - 'staging': Uses _STAGING suffix
        - 'prod' or 'production': Uses _PROD suffix
        - None or 'default': Uses base configuration

    Returns:
    - **environment**: The resolved environment name
    - **suffix**: Configuration suffix used (e.g., '_DEV', '_UAT')
    - **server_url**: Configured ArgoCD server URL
    - **server_configured**: Whether server URL is set
    - **credentials_configured**: Whether token or username+password is available
    - **has_token**: Whether a pre-configured token exists
    - **has_username_password**: Whether username and password are configured
    """
    try:
        config = ArgoCDService.get_environment_config(env)
        return BaseResponse(
            status=ResponseStatus.SUCCESS,
            data=config
        )
    except Exception as e:
        return BaseResponse(
            status=ResponseStatus.ERROR,
            message=f"Failed to get environment config: {str(e)}"
        )


@router.post("/login")
async def login_to_argocd(
    env: Optional[str] = Query(None, description="Target environment (e.g., 'dev', 'uat', 'staging', 'prod')"),
    username: Optional[str] = Query(None, description="Override username (uses config if not provided)"),
    password: Optional[str] = Query(None, description="Override password (uses config if not provided)")
):
    """
    Authenticate with ArgoCD server for a specific environment.

    This endpoint performs a login to ArgoCD's `/api/v1/session` endpoint and returns
    a session token. The credentials are resolved based on the environment:

    Query Parameters:
    - **env**: Target environment. Determines which config suffix to use:
        - 'dev' or 'development': Uses ARGOCD_SERVER_DEV, ARGOCD_USERNAME_DEV, ARGOCD_PASSWORD_DEV
        - 'uat': Uses ARGOCD_SERVER_UAT, ARGOCD_USERNAME_UAT, ARGOCD_PASSWORD_UAT
        - 'staging': Uses ARGOCD_SERVER_STAGING, ARGOCD_USERNAME_STAGING, ARGOCD_PASSWORD_STAGING
        - 'prod' or 'production': Uses ARGOCD_SERVER_PROD, ARGOCD_USERNAME_PROD, ARGOCD_PASSWORD_PROD
        - None or 'default': Uses base config (ARGOCD_SERVER, ARGOCD_USERNAME, ARGOCD_PASSWORD)
    - **username**: Override username (optional, uses environment config if not provided)
    - **password**: Override password (optional, uses environment config if not provided)

    Returns:
    - **token**: The generated ArgoCD session token
    - **server_url**: The ArgoCD server URL used
    - **environment**: The resolved environment name

    Errors:
    - 400: Missing required configuration (server URL or credentials)
    - 401: Authentication failed (invalid credentials)
    - 503: Cannot connect to ArgoCD server
    """
    try:
        result = ArgoCDService.login_for_environment(
            env=env,
            username=username,
            password=password
        )
        return BaseResponse(
            status=ResponseStatus.SUCCESS,
            message=f"Successfully authenticated with ArgoCD ({result['environment']})",
            data=result
        )
    except EnvironmentConfigError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except TokenRenewalFailedException as e:
        error_msg = str(e)
        if "Invalid username or password" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=error_msg
            )
        elif "Cannot connect" in error_msg or "timed out" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=error_msg
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_msg
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Login failed: {str(e)}"
        )


@router.get("/projects", response_model=ProjectListResponse)
async def list_projects(
    service: ArgoCDService = Depends(get_argocd_service_with_env)
):
    """
    List all ArgoCD projects

    Query Parameters:
    - **env**: Target environment (optional, e.g., 'uat', 'development')
    """
    return await ArgoCDController.list_projects(service)


@router.get("/projects/{project_name}", response_model=ProjectResponse)
async def get_project(
    project_name: str,
    service: ArgoCDService = Depends(get_argocd_service_with_env)
):
    """
    Get project details by name

    Query Parameters:
    - **env**: Target environment (optional, e.g., 'uat', 'development')
    """
    return await ArgoCDController.get_project(service, project_name)


@router.post("/projects", response_model=BaseResponse, status_code=201)
async def create_project(
    request: CreateProjectRequest,
    service: ArgoCDService = Depends(get_argocd_service_with_env)
):
    """
    Create a new ArgoCD project

    Query Parameters:
    - **env**: Target environment (optional, e.g., 'uat', 'development')

    Body Parameters:
    - **name**: Project name (required)
    - **description**: Project description (optional)
    - **source_repos**: List of allowed source repositories
    - **destinations**: List of allowed destinations (server and namespace)
    """
    return await ArgoCDController.create_project(service, request)


@router.delete("/projects/{project_name}", response_model=BaseResponse)
async def delete_project(
    project_name: str,
    service: ArgoCDService = Depends(get_argocd_service_with_env)
):
    """
    Delete a project

    Query Parameters:
    - **env**: Target environment (optional, e.g., 'uat', 'development')
    """
    return await ArgoCDController.delete_project(service, project_name)

@router.get("/applications", response_model=ApplicationListResponse)
async def list_applications(
    project: Optional[str] = Query(None, description="Filter by project"),
    repo: Optional[str] = Query(None, description="Filter by repository"),
    sync_status: Optional[str] = Query(None, description="Filter by sync status"),
    health_status: Optional[str] = Query(None, description="Filter by health status"),
    service: ArgoCDService = Depends(get_argocd_service_with_env)
):
    """
    List all applications with optional filtering

    Query Parameters:
    - **env**: Target environment (optional, e.g., 'uat', 'development')
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
    service: ArgoCDService = Depends(get_argocd_service_with_env)
):
    """
    Get all out-of-sync applications

    Query Parameters:
    - **env**: Target environment (optional, e.g., 'uat', 'development')
    """
    return await ArgoCDController.get_out_of_sync_applications(service, project)


@router.get("/applications/unhealthy", response_model=ApplicationListResponse)
async def get_unhealthy_applications(
    project: Optional[str] = Query(None, description="Filter by project"),
    service: ArgoCDService = Depends(get_argocd_service_with_env)
):
    """
    Get all unhealthy applications

    Query Parameters:
    - **env**: Target environment (optional, e.g., 'uat', 'development')
    """
    return await ArgoCDController.get_unhealthy_applications(service, project)


@router.post("/applications/sync-all-out-of-sync", response_model=BaseResponse)
async def sync_all_out_of_sync(
    project: Optional[str] = Query(None, description="Filter by project"),
    prune: bool = Query(True, description="Prune resources"),
    service: ArgoCDService = Depends(get_argocd_service_with_env)
):
    """
    Sync all out-of-sync applications

    Query Parameters:
    - **env**: Target environment (optional, e.g., 'uat', 'development')
    """
    return await ArgoCDController.sync_all_out_of_sync(service, project, prune)


@router.get("/applications/{app_name}", response_model=ApplicationResponse)
async def get_application(
    app_name: str,
    service: ArgoCDService = Depends(get_argocd_service_with_env)
):
    """
    Get application details by name

    Query Parameters:
    - **env**: Target environment (optional, e.g., 'uat', 'development')
    """
    return await ArgoCDController.get_application(service, app_name)


@router.get("/applications/{app_name}/status", response_model=BaseResponse)
async def get_application_status(
    app_name: str,
    service: ArgoCDService = Depends(get_argocd_service_with_env)
):
    """
    Get application sync and health status

    Query Parameters:
    - **env**: Target environment (optional, e.g., 'uat', 'development')
    """
    return await ArgoCDController.get_application_status(service, app_name)


@router.post("/applications", response_model=BaseResponse, status_code=201)
async def create_application(
    request: CreateApplicationRequest,
    service: ArgoCDService = Depends(get_argocd_service_with_env)
):
    """
    Create a new ArgoCD application

    Query Parameters:
    - **env**: Target environment (optional, e.g., 'uat', 'development')

    Body Parameters:
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
    service: ArgoCDService = Depends(get_argocd_service_with_env)
):
    """
    Update an existing application

    Query Parameters:
    - **env**: Target environment (optional, e.g., 'uat', 'development')
    """
    return await ArgoCDController.update_application(service, app_name, request)


@router.delete("/applications/{app_name}", response_model=ApplicationDeleteResponse)
async def delete_application(
    app_name: str,
    cascade: bool = Query(False, description="Delete application resources"),
    service: ArgoCDService = Depends(get_argocd_service_with_env)
):
    """
    Delete an application

    Query Parameters:
    - **env**: Target environment (optional, e.g., 'uat', 'development')

    Path/Query Parameters:
    - **app_name**: Name of the application to delete
    - **cascade**: If true, delete all application resources from cluster
    """
    return await ArgoCDController.delete_application(service, app_name, cascade)


@router.post("/applications/{app_name}/sync", response_model=SyncOperationResponse)
async def sync_application(
    app_name: str,
    request: SyncApplicationRequest,
    service: ArgoCDService = Depends(get_argocd_service_with_env)
):
    """
    Sync an application

    Query Parameters:
    - **env**: Target environment (optional, e.g., 'uat', 'development')

    Body Parameters:
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
    service: ArgoCDService = Depends(get_argocd_service_with_env)
):
    """
    Rollback application to a specific revision

    Query Parameters:
    - **env**: Target environment (optional, e.g., 'uat', 'development')

    Body Parameters:
    - **app_name**: Name of the application to rollback
    - **revision**: Target revision to rollback to (required)
    """
    return await ArgoCDController.rollback_application(service, app_name, request)


@router.post("/applications/{app_name}/refresh", response_model=BaseResponse)
async def refresh_application(
    app_name: str,
    service: ArgoCDService = Depends(get_argocd_service_with_env)
):
    """
    Force refresh application from Git repository

    Query Parameters:
    - **env**: Target environment (optional, e.g., 'uat', 'development')
    """
    return await ArgoCDController.refresh_application(service, app_name)