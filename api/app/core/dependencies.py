
# API Key security
from typing import Optional
from fastapi import Depends, HTTPException, Query, Security, status
from fastapi.security import APIKeyHeader

from app.core.config import Settings, get_settings
from app.services.argocd_service import ArgoCDService, EnvironmentConfigError


api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def get_api_key(api_key: Optional[str] = Security(api_key_header)) -> str:
    """Validate API key if configured"""
    settings = get_settings()

    # If no API key is configured, skip validation
    if not settings.API_KEY:
        return None

    # Validate API key
    if not api_key or api_key != settings.API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key"
        )

    return api_key


def get_argocd_service(
    settings: Settings = Depends(get_settings),
    api_key: Optional[str] = Depends(get_api_key)
) -> ArgoCDService:
    """
    Get ArgoCD service instance (default environment)
    This creates a new service instance for each request
    """

    return ArgoCDService(
        server_url=settings.ARGOCD_SERVER,
        auth_token=settings.ARGOCD_TOKEN,
        username=settings.ARGOCD_USERNAME,
        password=settings.ARGOCD_PASSWORD,
        verify_ssl=settings.VERIFY_SSL,
        auto_renew_token=settings.AUTO_RENEW_TOKEN
    )


def get_argocd_service_with_env(
    env: Optional[str] = Query(None, description="Target environment (e.g., 'dev', 'uat', 'staging', 'prod')"),
    settings: Settings = Depends(get_settings),
    api_key: Optional[str] = Depends(get_api_key)
) -> ArgoCDService:
    """
    Get ArgoCD service instance with environment-specific configuration.

    This creates a new service instance for each request, with the URL and
    credentials resolved based on the target environment.

    Supported environments:
    - dev/development: Uses ARGOCD_SERVER_DEV, ARGOCD_USERNAME_DEV, etc.
    - uat: Uses ARGOCD_SERVER_UAT, ARGOCD_USERNAME_UAT, etc.
    - staging: Uses ARGOCD_SERVER_STAGING, ARGOCD_USERNAME_STAGING, etc.
    - prod/production: Uses ARGOCD_SERVER_PROD, ARGOCD_USERNAME_PROD, etc.
    - None/default: Uses base config (ARGOCD_SERVER, ARGOCD_USERNAME, etc.)

    Args:
        env: Target environment

    Returns:
        ArgoCDService instance configured for the specified environment

    Raises:
        HTTPException 400: If required environment configuration is missing
        HTTPException 503: If cannot connect to ArgoCD server
    """
    try:
        return ArgoCDService(
            server_url=settings.ARGOCD_SERVER,
            auth_token=settings.ARGOCD_TOKEN,
            username=settings.ARGOCD_USERNAME,
            password=settings.ARGOCD_PASSWORD,
            verify_ssl=settings.VERIFY_SSL,
            auto_renew_token=settings.AUTO_RENEW_TOKEN,
            env=env
        )
    except EnvironmentConfigError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        error_msg = str(e)
        if "Cannot connect" in error_msg or "Connection" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"ArgoCD service unavailable for environment '{env or 'default'}': {error_msg}"
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initialize ArgoCD service: {error_msg}"
        )


def create_argocd_service_for_env(env: Optional[str] = None) -> ArgoCDService:
    """
    Factory function to create an ArgoCD service for a specific environment.

    This is useful when you need to create a service outside of the FastAPI
    dependency injection context (e.g., in background tasks or other services).

    Supported environments:
    - dev/development: Uses ARGOCD_SERVER_DEV, ARGOCD_USERNAME_DEV, etc.
    - uat: Uses ARGOCD_SERVER_UAT, ARGOCD_USERNAME_UAT, etc.
    - staging: Uses ARGOCD_SERVER_STAGING, ARGOCD_USERNAME_STAGING, etc.
    - prod/production: Uses ARGOCD_SERVER_PROD, ARGOCD_USERNAME_PROD, etc.
    - None/default: Uses base config (ARGOCD_SERVER, ARGOCD_USERNAME, etc.)

    Args:
        env: Target environment

    Returns:
        ArgoCDService instance configured for the specified environment

    Raises:
        EnvironmentConfigError: If required environment configuration is missing
    """
    settings = get_settings()

    return ArgoCDService(
        server_url=settings.ARGOCD_SERVER,
        auth_token=settings.ARGOCD_TOKEN,
        username=settings.ARGOCD_USERNAME,
        password=settings.ARGOCD_PASSWORD,
        verify_ssl=settings.VERIFY_SSL,
        auto_renew_token=settings.AUTO_RENEW_TOKEN,
        env=env
    )


def is_argocd_available(env: Optional[str] = None) -> bool:
    """Check if ArgoCD service is available for the given environment"""
    service = create_argocd_service_for_env(env)
    return service is not None and service.is_available


def get_settings_dependency() -> Settings:
    """Dependency to get settings"""
    return get_settings()