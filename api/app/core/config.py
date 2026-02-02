"""
Core Configuration
Loads configuration from .env file using pydantic-settings
"""

from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import Field, validator
from typing import Optional, Union
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # API Settings
    API_TITLE: str = "DevOps Automation API"
    API_VERSION: str = "1.0.0"
    API_DESCRIPTION: str = "FastAPI wrapper for DevOps operations"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "DEBUG"
    LOG_FORMAT: str = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    LOG_FILE: str = ''
    UPLOAD_DIR: Path = Field(Path("/tmp/uploads"), env="UPLOAD_DIR")
    MAX_FILE_SIZE: int = Field(20_971_520, env="MAX_FILE_SIZE")

    @validator("UPLOAD_DIR", pre=True)
    def parse_upload_dir(cls, v):
        """Convert string to Path if needed"""
        return Path(v) if isinstance(v, str) else v
    
    # ArgoCD Server Configuration
    ARGOCD_SERVER: str = Field(..., description="ArgoCD server URL")
    
    # Authentication - Use either token or username/password
    ARGOCD_TOKEN: Optional[str] = Field(None, description="ArgoCD authentication token")
    ARGOCD_USERNAME: Optional[str] = Field(None, description="ArgoCD username")
    ARGOCD_PASSWORD: Optional[str] = Field(None, description="ArgoCD password")
    
    # SSL Configuration
    VERIFY_SSL: bool = Field(True, description="Verify SSL certificates")
    
    # Default Settings
    DEFAULT_PROJECT: str = Field("default", description="Default ArgoCD project")
    DEFAULT_SERVER: str = Field("https://kubernetes.default.svc", description="Default k8s server")
    DEFAULT_NAMESPACE: str = Field("default", description="Default namespace")
    DEFAULT_SYNC_TIMEOUT: int = Field(300, description="Default sync timeout in seconds")
    
    # Sync Options
    AUTO_SYNC: bool = Field(False, description="Enable auto-sync by default")
    AUTO_PRUNE: bool = Field(False, description="Enable auto-prune by default")
    SELF_HEAL: bool = Field(False, description="Enable self-heal by default")
    
    # API Security
    API_KEY: Optional[str] = Field(None, description="API key for securing endpoints")
    ALLOWED_ORIGINS: str = Field("*", description="CORS allowed origins")
    
    # Token Auto-Renewal
    AUTO_RENEW_TOKEN: bool = Field(True, description="Automatically renew expired tokens")

    # GitHub Configuration
    GIT_USER_NAME: str = Field("DevOps Automation", description="Git author name for commits")
    GIT_USER_EMAIL: str = Field("devops@automation.local", description="Git author email for commits")
    GITHUB_TOKEN: str = Field("GITHUB_TOKEN", description="GitHub secret token")
    GITOPS_REPO_URL: Optional[str] = Field(None, description="GitOps repository URL for fetching values")

    # Preview Session Configuration
    PREVIEW_SESSION_TTL_MINUTES: int = Field(60, description="Preview session time-to-live in minutes")

    # Cloudflare
    CLOUDFLARE_TOKEN: str = Field("CLOUDFLARE_TOKEN", description="Cloudflare Token")
    CLOUDFLARE_ZONE_ID: str = Field("CLOUDFLARE_ZONE_ID", description="Cloudflare Zone ID")

    LOAD_BALANCER_IP: str = Field("LOAD_BALANCER_IP", description="Load Balancer IP")
    
    @validator("ARGOCD_SERVER")
    def validate_server_url(cls, v):
        """Ensure server URL doesn't end with /"""
        return v.rstrip("/")
    
    @validator("ALLOWED_ORIGINS")
    def parse_origins(cls, v):
        """Parse comma-separated origins"""
        if v == "*":
            return ["*"]
        return [origin.strip() for origin in v.split(",")]
    
    class Config:
        env_file = ".env.development"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()
