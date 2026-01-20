"""
GitOps Routes
FastAPI endpoints for GitOps manifest generation
"""

from fastapi import APIRouter, HTTPException, status, Depends

from app.controllers.gitops_manifest_controller import gitops_manifest_controller
from app.models.gitops import (
    GitOpsManifestRequest,
    GitOpsManifestResponse
)
from app.models.common import ErrorResponse
from app.core.logging_config import logger
from app.core.dependencies import get_argocd_service
from app.services.argocd_service import ArgoCDService

router = APIRouter(prefix="/gitops", tags=["GitOps Manifest Generation"])


@router.post(
    "/micro-service",
    response_model=GitOpsManifestResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate GitOps Manifests",
    description="Generate Kubernetes manifests from templates with variable substitution",
    responses={
        400: {"model": ErrorResponse, "description": "Invalid request or validation error"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    }
)
async def generate_microservice_manifests(
    request: GitOpsManifestRequest,
    argocd_service: ArgoCDService = Depends(get_argocd_service)
):
    """
    **Generate GitOps Manifests for Microservice**

    Processes template files from `template/git-ops` directory and generates
    Kubernetes manifests with variable substitution.

    **Workflow:**
    1. Read all files from template/git-ops directory
    2. Create temporary output directory
    3. Perform variable substitutions:
       - `{{MICRO_SERVICE_NAME}}` → microserviceName
       - `{{MICRO_SERVICE_URL}}` → microserviceUrl
       - `{{CONTAINER_PORT}}` → containerPort
       - `{{DOMAIN_NAME}}` → domainName
       - `{{ENVIRONMENT}}` → environment
       - `{{GIT_REPO_NAME}}` → gitRepoName
       - `{{GIT_BRANCH}}` → gitBranch
       - `{{ARGOCD_APP_NAME}}` → argoCdAppName
       - `{{GITOPS_REPO_URL}}` → gitOpsRepoUrl
       - `{{ENVIRONMENT_VARIABLES_YAML}}` → formatted env vars for values.yaml
       - `{{ENVIRONMENT_VARIABLES_CONFIGMAP}}` → formatted env vars for ConfigMap
       - `{{KEY}}` → individual env var values (e.g., `{{LOG_LEVEL}}`)
    4. Save processed files maintaining original folder structure

    **Environment Variables (envContent):**
    Pass environment variables as KEY=VALUE pairs (same format as /configmap/update):
    ```
    LOG_LEVEL=debug
    NODE_ENV=development
    DATABASE_URL=postgresql://localhost:5432/db
    ```

    **Returns:**
    - List of processed files with replacement counts
    - Output directory path
    - Template variables used
    - Parsed environment variables
    """
    try:
        logger.info(f"Received manifest generation request for {request.microservice_name}")

        result = await gitops_manifest_controller.generate_manifests(request, argocd_service)

        logger.info(f"Manifest generation completed for {request.microservice_name}")
        return result

    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except FileNotFoundError as e:
        logger.error(f"Template not found: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Template directory not found: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Manifest generation failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate manifests: {str(e)}"
        )
