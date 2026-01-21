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


import uuid
import json
import asyncio
from fastapi.responses import StreamingResponse
from app.core.log_stream import request_id_ctx, log_stream_handler

@router.post(
    "/micro-service",
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
    **Generate GitOps Manifests for Microservice** - Streaming Response
    """
    request_id = str(uuid.uuid4())
    
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
