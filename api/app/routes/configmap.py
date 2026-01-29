"""
GitOps Routes
FastAPI endpoints for GitOps configuration updates
Based on original terminal script functionality
"""


from app.controllers.configmap_controller import configmap_controller
from app.core.dependencies import get_argocd_service
from fastapi import APIRouter, HTTPException, status, Depends
from app.models.configmap import (
    ConfigMapUpdateRequest,
    ConfigMapUpdateResponse,
    ConfigMapPreviewRequest,
    ConfigMapPreviewResponse,
    ConfigMapApplyChangesRequest,
    ConfigValuesResponse,
)
from app.services.configmap_service import get_values_from_gitops, mask_sensitive_values

from app.models.common import ErrorResponse
from app.services.argocd_service import ArgoCDService
from app.core.logging_config import logger

router = APIRouter(prefix="/configmap", tags=["ConfigMap Configuration"])
gitops_router = APIRouter(prefix="/gitops", tags=["GitOps Configuration"])


@router.post(
    "/update",
    response_model=ConfigMapUpdateResponse,
    status_code=status.HTTP_200_OK,
    summary="Complete GitOps Configuration Update",
    description="Execute complete workflow: Clone → Update → Commit → Sync ArgoCD",
    responses={
        400: {"model": ErrorResponse, "description": "Invalid request or validation error"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    }
)
async def update_gitops_configuration(
        request: ConfigMapUpdateRequest,
        argocd_servie : ArgoCDService = Depends(get_argocd_service)
):
    """
    **Complete ConfigMap Configuration Update Workflow**
    
    Replicates your terminal script's complete functionality via REST API.
    
    **Workflow Steps:**
    1. Clone GitOps repository from provided URL
    2. Locate microservice directory
    3. Parse environment variables from .env content
    4. Update values.yaml (config section)
    5. Update configmap.yaml (template references)
    6. Commit and push to Git (if auto_commit=true)
    7. Sync ArgoCD application (if auto_sync_argocd=true)
    8. Cleanup temporary files
    """
    try:
        logger.info(f"Received ConfigMap update request for {request.microservice_name} in {request.environment_name}")
        
        result = configmap_controller.execute_update(request, argocd_servie)
        
        logger.info(f"ConfigMap update completed successfully for {request.microservice_name}")
        return result
        
    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"ConfigMap update failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"ConfigMap configuration update failed: {str(e)}"
        )


@router.post(
    "/preview",
    response_model=ConfigMapPreviewResponse,
    status_code=status.HTTP_200_OK,
    summary="Preview Configuration Changes",
    description="Preview what changes would be made without applying them"
)
async def preview_configuration_changes(request: ConfigMapPreviewRequest):
    """
    **Preview Configuration Changes (Dry Run)**
    
    Shows what changes would be made without modifying files.
    Creates a preview session for later apply.
    """
    try:
        logger.info(f"Received preview request for {request.microservice_name}")
        
        result = configmap_controller.preview_changes(request)
        
        logger.info(f"Preview completed for {request.microservice_name}")
        return result
        
    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Preview failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to preview changes: {str(e)}"
        )


@router.post(
    "/apply",
    response_model=ConfigMapUpdateResponse,
    status_code=status.HTTP_200_OK,
    summary="Apply Previewed Changes",
    description="Apply changes from a preview session"
)
async def apply_previewed_changes(request: ConfigMapApplyChangesRequest):
    """
    **Apply Previously Previewed Changes**

    Applies changes from a preview session.
    """
    try:
        logger.info(f"Received apply request for session: {request.session_id}")

        result = configmap_controller.apply_previewed_changes(request)

        logger.info(f"Changes applied successfully for session: {request.session_id}")
        return result
        
    except ValueError as e:
        logger.error(f"Preview session error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Apply failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to apply changes: {str(e)}"
        )


@gitops_router.get(
    "/config-values",
    response_model=ConfigValuesResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Configuration Values from GitOps Repository",
    description="Retrieve the 'config' block from values.yaml for a microservice in a specific environment",
    responses={
        404: {"model": ErrorResponse, "description": "Branch or values.yaml file not found"},
        500: {"model": ErrorResponse, "description": "Git authentication or connection error"}
    }
)
async def get_config_values(
    microservice_name: str,
    env: str
):
    """
    **Get Configuration Values from GitOps Repository**

    Fetches the 'config' block from the values.yaml file for a specified microservice.

    **Parameters:**
    - **microservice_name**: Name of the microservice (matches directory name in GitOps repo)
    - **env**: Environment name, used as the Git branch (e.g., 'development', 'staging', 'production')

    **Returns:**
    - The 'config' block from `{microservice_name}/values.yaml`
    - Empty dict if the 'config' block doesn't exist

    **Errors:**
    - 404: Branch doesn't exist or values.yaml not found
    - 500: Git authentication or connection errors
    """
    try:
        logger.info(f"Fetching config values for {microservice_name} from branch {env}")

        config = get_values_from_gitops(microservice_name, env)

        logger.info(f"Successfully retrieved config for {microservice_name} ({len(config)} keys)")

        # Mask sensitive values before returning (SECRET, KEY, TOKEN, PASSWORD, CREDENTIAL)
        masked_config = mask_sensitive_values(config)

        return ConfigValuesResponse(
            status="success",
            microservice=microservice_name,
            environment=env,
            config=masked_config
        )

    except ValueError as e:
        # Branch or file not found - return 404
        logger.warning(f"Not found error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        # Git authentication/connection errors or other internal errors - return 500
        logger.error(f"Failed to get config values: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve configuration values: {str(e)}"
        )


async def gitops_service_health(
    argocd_service: ArgoCDService = Depends(get_argocd_service)
):
    """Check availability of Git and ArgoCD utilities"""
    import subprocess

    git_available = False
    git_version = None
    try:
        result = subprocess.run(
            ['git', '--version'],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            git_available = True
            git_version = result.stdout.strip()
    except Exception as e:
        logger.warning(f"Git health check failed: {e}")

    argocd_available = argocd_service.is_available  # is_available is an attribute, not a method

    return {
        "status": "healthy" if git_available else "degraded",
        "git_available": git_available,
        "git_version": git_version,
        "argocd_available": argocd_available
    }