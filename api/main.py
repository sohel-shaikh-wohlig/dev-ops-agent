"""
Main FastAPI Application
"""

import uvicorn
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager

from app.core.config import get_settings
from app.core.logging_config import setup_logging
from app.routes import argocd, routes, configmap, gitops, terraform
from app.routes.configmap import gitops_router
from app.routes.github_webhook import github_router, terraform_pr_router
from app.core.pubsub import pubsub_subscriber
from app.core.redis import redis_manager
from app.core.websocket_manager import ws_manager
from app.routes.websocket import ws_router
from app.utils.cleanup import cleanup_old_sessions
from app.utils.gh_cli import check_gh_cli, check_gh_auth


# Setup logging
logger = setup_logging()

# Get settings
settings = get_settings()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events
    """
    # Startup
    logger.info("Starting DevOps Automation API")
    logger.info(f"Environment: {settings.ENVIRONMENT}")

    settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    await redis_manager.connect()
    await pubsub_subscriber.start()

    # Verify gh CLI is installed and authenticated
    if not check_gh_cli():
        logger.warning("⚠ gh CLI not found — GitHub operations (comments, merges, workflow monitoring) will fail")
    elif not check_gh_auth():
        logger.warning("⚠ gh CLI not authenticated — set GH_TOKEN env var or run `gh auth login`")

    yield

    # Shutdown
    logger.info("Shutting DevOps Automation API")
    await pubsub_subscriber.stop()
    await ws_manager.disconnect_all()
    await redis_manager.close()
    await cleanup_old_sessions()


# Create FastAPI app
app = FastAPI(
    title=settings.API_TITLE,
    description=settings.API_DESCRIPTION,
    version=settings.API_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Exception handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors"""
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "status": "error",
            "message": "Validation error",
            "detail": exc.errors()
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "status": "error",
            "message": "Internal server error",
            "detail": str(exc) if settings.DEBUG else "An unexpected error occurred"
        }
    )

# Add GZip middleware
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Include routers
app.include_router(routes.router, prefix="/api")
app.include_router(argocd.router, prefix="/api")
app.include_router(configmap.router, prefix="/api")
app.include_router(gitops.router, prefix="/api")
app.include_router(gitops_router, prefix="/api")
app.include_router(terraform.router, prefix="/api")
app.include_router(github_router, prefix="/api")
app.include_router(terraform_pr_router, prefix="/api")
app.include_router(ws_router, prefix="/api")

@app.on_event("startup")
async def startup_event():
    """Startup event handler"""
    logger.info("="*80)
    logger.info(f"Starting {settings.API_TITLE} v{settings.API_VERSION}")
    logger.info(f"ArgoCD Server: {settings.ARGOCD_SERVER}")
    logger.info(f"Documentation: http://localhost:8000/docs")
    logger.info("="*80)


@app.on_event("shutdown")
async def shutdown_event():
    """Shutdown event handler"""
    logger.info("Shutting down ArgoCD FastAPI...")



@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "version": settings.API_VERSION,
        "environment": settings.ENVIRONMENT
    }


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": settings.API_DESCRIPTION,
        "version": settings.API_VERSION,
        "docs": {
            "swagger": "/docs",
            "redoc": "/redoc",
            "openapi": "/openapi.json"
        },
        "endpoints": {
            "health": "/health",
            "api": "/api"
        }
    }

if __name__ == "__main__":

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level="info"
    )
