"""
GitOps Routes
FastAPI endpoints for GitOps manifest generation

Automatically uses environment-specific ArgoCD configuration based on
the 'environment' field in the request body.
"""

import uuid
import json
import asyncio
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse

from app.controllers.gitops_manifest_controller import gitops_manifest_controller
from app.models.gitops import (
    CleanupRequest,
    GitOpsManifestRequest
)
from app.models.common import ErrorResponse
from app.core.logging_config import logger
from app.core.dependencies import create_argocd_service_for_env, get_argocd_service
from app.services.argocd_service import ArgoCDService
from app.core.log_stream import request_id_ctx, log_stream_handler

router = APIRouter(prefix="/gitops", tags=["GitOps Manifest Generation"])


@router.post(
    "/micro-service",
    status_code=status.HTTP_200_OK,
    summary="Generate GitOps Manifests",
    description="Generate Kubernetes manifests from templates with variable substitution. "
                "Automatically uses environment-specific ArgoCD configuration based on the "
                "'environment' field (e.g., 'uat' uses UAT ArgoCD server and credentials).",
    responses={
        400: {"model": ErrorResponse, "description": "Invalid request or validation error"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    }
)
async def generate_microservice_manifests(
    request: GitOpsManifestRequest
):
    """
    **Generate GitOps Manifests for Microservice** - Streaming Response

    The ArgoCD service is automatically configured based on the 'environment'
    field in the request:
    - environment='uat': Uses UAT ArgoCD server and credentials
    - Other environments: Uses default ArgoCD configuration
    """
    request_id = str(uuid.uuid4())

    # Get environment value from request for ArgoCD service configuration
    env_value = request.environment.value if hasattr(request.environment, 'value') else str(request.environment)

    # Create environment-specific ArgoCD service
    argocd_service = create_argocd_service_for_env(env=env_value)
    logger.info(f"Created ArgoCD service for environment: {env_value}")

    async def event_generator():
        # Set context and register handler
        token = request_id_ctx.set(request_id)
        queue = log_stream_handler.register(request_id)
        
        try:
            logger.info(f"Received manifest generation request for {request.microservice_name}")
            
            # Start the actual processing in a background task
            # We wrap it to capture the result or exception
            process_task = asyncio.create_task(
                gitops_manifest_controller.generate_manifests(request, argocd_service)
            )
            
            # Loop to yield logs while task is running
            while not process_task.done():
                try:
                    # Wait for new log with a timeout to check task status
                    log_json = await asyncio.wait_for(queue.get(), timeout=0.1)
                    yield log_json + "\n"
                except asyncio.TimeoutError:
                    continue
            
            # Flush remaining logs
            while not queue.empty():
                log_json = await queue.get()
                yield log_json + "\n"
                
            # Check result
            try:
                result = await process_task
                logger.info(f"Manifest generation completed for {request.microservice_name}")
                
                # Verify result is a Pydantic model and dump it to JSON
                # Use mode='json' to convert datetime objects to ISO format strings
                result_dict = result.model_dump(mode='json') if hasattr(result, 'model_dump') else result.dict()

                # Send final result
                yield json.dumps({
                    "type": "result",
                    "data": result_dict
                }) + "\n"
                
            except Exception as e:
                logger.error(f"Processing failed: {str(e)}", exc_info=True)
                yield json.dumps({
                    "type": "error",
                    "message": str(e)
                }) + "\n"
                
        except Exception as e:
             logger.error(f"Stream handler error: {str(e)}")
             yield json.dumps({
                "type": "error", 
                "message": f"Stream error: {str(e)}"
             }) + "\n"
        finally:
            log_stream_handler.unregister(request_id)
            request_id_ctx.reset(token)

    return StreamingResponse(event_generator(), media_type="application/x-ndjson")

@router.post(
    "/cleanup",
    status_code=status.HTTP_200_OK,
    summary="Cleanup Deployment Resources",
    description="""
    Safely removes all resources created during deployment:
    - Cloudflare DNS records
    - ArgoCD applications
    - GitOps repository manifests
    - Microservice repository workflows
    - GitHub secrets (explicit opt-in only)
    
    ⚠️ **SAFETY PROTOCOLS:**
    - All operations are idempotent and verified before execution
    - GitHub secrets require explicit naming (no wildcards)
    - Full audit trail recorded for all operations
    """,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid request or validation error"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    }
)
async def cleanup_deployment(
    request: CleanupRequest,
    argocd_service: ArgoCDService = Depends(get_argocd_service)
):
    """
    **Cleanup Deployment Resources** - Streaming Response
    
    Safely removes all infrastructure created during deployment workflow.
    Follows the same streaming pattern as manifest generation for consistent UX.
    """
    request_id = str(uuid.uuid4())
    
    async def event_generator():
        # Set context and register handler
        token = request_id_ctx.set(request_id)
        queue = log_stream_handler.register(request_id)
        
        try:
            logger.info(
                f"Received cleanup request | "
                f"microservice={request.microservice_name} | "
                f"environment={request.environment} | "
                f"domain={request.domain_name} | "
                f"force={request.force}"
            )
            
            # Safety validation before starting cleanup
            if request.environment.lower() == "prod" and not request.audit_comment:
                error_msg = "audit_comment is REQUIRED for production environment cleanup"
                logger.error(error_msg)
                yield json.dumps({
                    "type": "error",
                    "message": error_msg
                }) + "\n"
                return
            
            if request.force and not request.audit_comment:
                error_msg = "audit_comment is REQUIRED when using force flag"
                logger.error(error_msg)
                yield json.dumps({
                    "type": "error",
                    "message": error_msg
                }) + "\n"
                return
            
            # Convert CleanupRequest to GitOpsManifestRequest format
            # (reusing existing schema for consistency)
            from app.models.gitops import EnvironmentType
            
            try:
                env_enum = EnvironmentType(request.environment.lower())
            except ValueError:
                valid_envs = [e.value for e in EnvironmentType]
                error_msg = f"Invalid environment: {request.environment}. Must be one of: {', '.join(valid_envs)}"
                logger.error(error_msg)
                yield json.dumps({
                    "type": "error",
                    "message": error_msg
                }) + "\n"
                return
            
            # Create minimal GitOpsManifestRequest (only fields used in cleanup)
            cleanup_manifest_request = GitOpsManifestRequest(
                microservice_name=request.microservice_name,
                environment=env_enum,
                domain_name=request.domain_name,
                argocd_app_name=request.argocd_app_name,
                gitops_repo_url=request.gitops_repo_url,
                microservice_url=request.microservice_repo_url,
                # Minimal required fields (unused in cleanup but required by schema)
                container_port=8080,
                git_repo_name=request.microservice_repo_url.rstrip("/").split("/")[-1].removesuffix(".git"),
                git_branch="main",
                # Other required fields with safe defaults
                env_content=None,
                cronjobs=None,
                worker=None
            )
            
            # Start cleanup in background task
            cleanup_task = asyncio.create_task(
                gitops_manifest_controller.cleanup_deployment(
                    request=cleanup_manifest_request,
                    argocd_service=argocd_service,
                    github_secret_names=request.github_secret_names,
                    force=request.force
                )
            )
            
            # Stream logs while cleanup is running
            while not cleanup_task.done():
                try:
                    log_json = await asyncio.wait_for(queue.get(), timeout=0.1)
                    yield log_json + "\n"
                except asyncio.TimeoutError:
                    continue
            
            # Flush remaining logs
            while not queue.empty():
                log_json = await queue.get()
                yield log_json + "\n"
                
            # Check cleanup result
            try:
                result = await cleanup_task
                logger.info(
                    f"Cleanup completed | "
                    f"microservice={request.microservice_name} | "
                    f"environment={request.environment} | "
                    f"success={result.get('success', False)}"
                )
                
                # Send final result
                yield json.dumps({
                    "type": "result",
                    "data": result
                }) + "\n"
                
            except Exception as e:
                logger.error(f"Cleanup failed: {str(e)}", exc_info=True)
                yield json.dumps({
                    "type": "error",
                    "message": str(e)
                }) + "\n"
                
        except Exception as e:
            logger.error(f"Cleanup stream handler error: {str(e)}", exc_info=True)
            yield json.dumps({
                "type": "error",
                "message": f"Stream error: {str(e)}"
            }) + "\n"
        finally:
            log_stream_handler.unregister(request_id)
            request_id_ctx.reset(token)

    return StreamingResponse(event_generator(), media_type="application/x-ndjson")