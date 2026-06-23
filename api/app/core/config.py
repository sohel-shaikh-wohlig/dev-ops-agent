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
    
    # ==========================================================================
    # ArgoCD Configuration (Environment-Specific)
    # ==========================================================================
    # The ArgoCD service supports dynamic environment selection. For each
    # environment, add the corresponding _SUFFIX settings:
    #   - Default: ARGOCD_SERVER, ARGOCD_USERNAME, ARGOCD_PASSWORD, ARGOCD_TOKEN
    #   - DEV:     ARGOCD_SERVER_DEV, ARGOCD_USERNAME_DEV, etc.
    #   - TEST:    ARGOCD_SERVER_TEST, ARGOCD_USERNAME_TEST, etc.
    #   - UAT:     ARGOCD_SERVER_UAT, ARGOCD_USERNAME_UAT, etc.
    #   - STAGING: ARGOCD_SERVER_STAGING, ARGOCD_USERNAME_STAGING, etc.
    #   - PROD:    ARGOCD_SERVER_PROD, ARGOCD_USERNAME_PROD, etc.
    # ==========================================================================

    # Default ArgoCD Configuration (used when env is None or 'default')
    # Optional: If not set, environment-specific servers (ARGOCD_SERVER_DEV, etc.) must be used
    ARGOCD_SERVER: Optional[str] = Field(None, description="ArgoCD server URL (default)")
    ARGOCD_TOKEN: Optional[str] = Field(None, description="ArgoCD authentication token")
    ARGOCD_USERNAME: Optional[str] = Field(None, description="ArgoCD username")
    ARGOCD_PASSWORD: Optional[str] = Field(None, description="ArgoCD password")

    # DEV Environment ArgoCD Configuration
    ARGOCD_SERVER_DEV: Optional[str] = Field(None, description="ArgoCD server URL for DEV")
    ARGOCD_TOKEN_DEV: Optional[str] = Field(None, description="ArgoCD token for DEV")
    ARGOCD_USERNAME_DEV: Optional[str] = Field(None, description="ArgoCD username for DEV")
    ARGOCD_PASSWORD_DEV: Optional[str] = Field(None, description="ArgoCD password for DEV")

    # TEST Environment ArgoCD Configuration
    ARGOCD_SERVER_TEST: Optional[str] = Field(None, description="ArgoCD server URL for TEST")
    ARGOCD_TOKEN_TEST: Optional[str] = Field(None, description="ArgoCD token for TEST")
    ARGOCD_USERNAME_TEST: Optional[str] = Field(None, description="ArgoCD username for TEST")
    ARGOCD_PASSWORD_TEST: Optional[str] = Field(None, description="ArgoCD password for TEST")

    # UAT Environment ArgoCD Configuration
    ARGOCD_SERVER_UAT: Optional[str] = Field(None, description="ArgoCD server URL for UAT")
    ARGOCD_TOKEN_UAT: Optional[str] = Field(None, description="ArgoCD token for UAT")
    ARGOCD_USERNAME_UAT: Optional[str] = Field(None, description="ArgoCD username for UAT")
    ARGOCD_PASSWORD_UAT: Optional[str] = Field(None, description="ArgoCD password for UAT")

    # STAGING Environment ArgoCD Configuration
    ARGOCD_SERVER_STAGING: Optional[str] = Field(None, description="ArgoCD server URL for STAGING")
    ARGOCD_TOKEN_STAGING: Optional[str] = Field(None, description="ArgoCD token for STAGING")
    ARGOCD_USERNAME_STAGING: Optional[str] = Field(None, description="ArgoCD username for STAGING")
    ARGOCD_PASSWORD_STAGING: Optional[str] = Field(None, description="ArgoCD password for STAGING")

    # PROD Environment ArgoCD Configuration
    ARGOCD_SERVER_PROD: Optional[str] = Field(None, description="ArgoCD server URL for PROD")
    ARGOCD_TOKEN_PROD: Optional[str] = Field(None, description="ArgoCD token for PROD")
    ARGOCD_USERNAME_PROD: Optional[str] = Field(None, description="ArgoCD username for PROD")
    ARGOCD_PASSWORD_PROD: Optional[str] = Field(None, description="ArgoCD password for PROD")
    
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
    GITHUB_WEBHOOK_SECRET: str = Field("", description="Secret for validating GitHub webhook signatures")
    GITOPS_REPO_URL: Optional[str] = Field(None, description="GitOps repository URL for fetching values")

    # Preview Session Configuration
    PREVIEW_SESSION_TTL_MINUTES: int = Field(60, description="Preview session time-to-live in minutes")

    # ==========================================================================
    # Redis Configuration
    # ==========================================================================
    REDIS_HOST: str = Field("localhost", description="Redis server host")
    REDIS_PORT: int = Field(6379, description="Redis server port")
    REDIS_DB: int = Field(0, description="Redis database number")
    REDIS_PASSWORD: Optional[str] = Field(None, description="Redis password")
    REDIS_MAX_CONNECTIONS: int = Field(10, description="Redis connection pool max connections")
    REDIS_SOCKET_TIMEOUT: int = Field(5, description="Redis socket timeout in seconds")
    REDIS_CACHE_URL: Optional[str] = Field(None, description="Full Redis URL (overrides host/port/db)")
    REDIS_PUBSUB_CHANNEL_PREFIX: str = Field("pr_updates", description="Redis Pub/Sub channel prefix for PR status events")

    @property
    def redis_url(self) -> str:
        """Construct Redis URL from config, or return REDIS_CACHE_URL if set."""
        if self.REDIS_CACHE_URL:
            return self.REDIS_CACHE_URL
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    # Cloudflare
    CLOUDFLARE_TOKEN: str = Field("CLOUDFLARE_TOKEN", description="Cloudflare Token")
    CLOUDFLARE_ZONE_ID: str = Field("CLOUDFLARE_ZONE_ID", description="Cloudflare Zone ID")

    # ==========================================================================
    # Infrastructure - Load Balancer IPs (Environment-Specific)
    # ==========================================================================
    # The Cloudflare service supports dynamic environment selection for LB IPs.
    # For each environment, add the corresponding _SUFFIX settings:
    #   - Default: LOAD_BALANCER_IP
    #   - DEV:     LOAD_BALANCER_IP_DEV
    #   - TEST:    LOAD_BALANCER_IP_TEST
    #   - UAT:     LOAD_BALANCER_IP_UAT
    #   - STAGING: LOAD_BALANCER_IP_STAGING
    #   - PROD:    LOAD_BALANCER_IP_PROD
    # ==========================================================================

    # Default Load Balancer IP (used when env is None or 'default')
    LOAD_BALANCER_IP: str = Field("34.180.18.42", description="Load balancer IP for DNS records (default)")

    # DEV Environment Load Balancer IP
    LOAD_BALANCER_IP_DEV: Optional[str] = Field(None, description="Load balancer IP for DEV environment")

    # TEST Environment Load Balancer IP
    LOAD_BALANCER_IP_TEST: Optional[str] = Field(None, description="Load balancer IP for TEST environment")

    # UAT Environment Load Balancer IP
    LOAD_BALANCER_IP_UAT: Optional[str] = Field(None, description="Load balancer IP for UAT environment")

    # STAGING Environment Load Balancer IP
    LOAD_BALANCER_IP_STAGING: Optional[str] = Field(None, description="Load balancer IP for STAGING environment")

    # PROD Environment Load Balancer IP
    LOAD_BALANCER_IP_PROD: Optional[str] = Field(None, description="Load balancer IP for PROD environment")
    
    @validator("ARGOCD_SERVER", pre=True)
    def validate_server_url(cls, v):
        """Ensure server URL doesn't end with / (if provided)"""
        if v is None:
            return v
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
