
# API Key security
from typing import Optional
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader

from app.core.config import Settings, get_settings
from app.services.argocd_service import ArgoCDService


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
    Get ArgoCD service instance
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


def get_settings_dependency() -> Settings:
    """Dependency to get settings"""
    return get_settings()