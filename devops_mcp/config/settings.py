# devops_mcp/config/settings.py

"""
MCP Settings
Centralized configuration for all MCP servers
Loads from environment variables with sensible defaults
"""

from pydantic_settings import BaseSettings
from typing import Optional
from pathlib import Path
import os


class MCPSettings(BaseSettings):
    """MCP Server Settings"""
    
    # ========== FastAPI Connection ==========
    FASTAPI_URL: str = "http://localhost:8000"
    API_TOKEN: Optional[str] = None
    
    # ========== Kubernetes ==========
    DEFAULT_CONTEXT: str = "dev"
    KUBECONFIG_PATH: str = str(Path.home() / ".kube" / "config")
    
    # ========== Logging ==========
    LOG_LEVEL: str = "INFO"
    LOG_DIR: Path = Path(__file__).parent.parent.parent / "logs" / "mcp"
    LOG_FILE: str = "devops_automation.log"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # ========== Token Management ==========
    TOKEN_REFRESH_ENABLED: bool = True
    TOKEN_REFRESH_INTERVAL: int = 43200  # 12 hours in seconds
    TOKEN_FILE: Path = Path.home() / ".mcp_tokens.env"
    
    # ========== Server Configuration ==========
    SERVER_NAME: str = "devops-automation"
    SERVER_VERSION: str = "1.0.0"
    TIMEOUT: int = 600  # Default timeout for API calls (10 minutes)
    
    # ========== Feature Flags ==========
    ENABLE_DRY_RUN: bool = True
    ENABLE_ROLLBACK: bool = True
    REQUIRE_APPROVAL_PRODUCTION: bool = True  # Require confirmation for prod

    # ========== Quick Deploy Defaults ==========
    # Used by quick_deploy_microservice to derive parameters
    GITHUB_BASE_URL: str = "https://github.com/tehvault"
    GITOPS_REPO_NAME: str = "git-ops"
    DOMAIN_SUFFIX: str = "vaultfy.ai"
    DEFAULT_CONTAINER_PORT: int = 3000
    
    # ========== Cluster Mappings ==========
    # Override these with environment variables if needed
    CLUSTER_DEV: str = "dev"
    CLUSTER_STAGING: str = "staging"
    CLUSTER_PRODUCTION: str = "production"
    CLUSTER_QA: str = "qa"
    
    class Config:
        """Pydantic settings configuration"""
        env_file = ".env"
        env_prefix = "MCP_"  # All env vars should start with MCP_
        case_sensitive = False
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # Create log directory if it doesn't exist
        self.LOG_DIR.mkdir(parents=True, exist_ok=True)
    
    @property
    def log_file_path(self) -> Path:
        """Get full path to log file"""
        return self.LOG_DIR / self.LOG_FILE
    
    @property
    def cluster_contexts(self) -> dict[str, str]:
        """
        Get cluster context mappings
        
        Returns:
            Dict mapping environment names to kubectl contexts
        """
        return {
            "dev": self.CLUSTER_DEV,
            "development": self.CLUSTER_DEV,
            "staging": self.CLUSTER_STAGING,
            "stage": self.CLUSTER_STAGING,
            "production": self.CLUSTER_PRODUCTION,
            "prod": self.CLUSTER_PRODUCTION,
            "qa": self.CLUSTER_QA,
            "uat": self.CLUSTER_QA
        }
    
    def get_cluster_context(self, environment: str) -> str:
        """
        Get kubectl context for an environment
        
        Args:
            environment: Environment name (e.g., 'dev', 'staging', 'production')
            
        Returns:
            Kubectl context name
        """
        return self.cluster_contexts.get(environment.lower(), self.DEFAULT_CONTEXT)


# Global settings instance
settings = MCPSettings()


# Logging configuration helper
def setup_logging():
    """
    Setup logging configuration for MCP servers
    
    Call this at the start of each MCP server
    """
    import logging
    
    # Create logger
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper()))
    
    # File handler
    file_handler = logging.FileHandler(settings.log_file_path)
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(settings.LOG_FORMAT)
    file_handler.setFormatter(file_formatter)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, settings.LOG_LEVEL.upper()))
    console_formatter = logging.Formatter('%(levelname)s - %(message)s')
    console_handler.setFormatter(console_formatter)
    
    # Add handlers
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger


# Example .env file content
"""
# MCP Configuration
# Save this as .env in your project root

# FastAPI Connection
MCP_FASTAPI_URL=http://localhost:8000
MCP_API_TOKEN=your_api_token_here

# Kubernetes Contexts
MCP_CLUSTER_DEV=dev
MCP_CLUSTER_STAGING=staging
MCP_CLUSTER_PRODUCTION=production
MCP_CLUSTER_QA=qa

# Logging
MCP_LOG_LEVEL=INFO
MCP_LOG_DIR=logs/mcp

# Features
MCP_ENABLE_DRY_RUN=true
MCP_REQUIRE_APPROVAL_PRODUCTION=true

# Token Management
MCP_TOKEN_REFRESH_ENABLED=true
MCP_TOKEN_REFRESH_INTERVAL=43200
"""