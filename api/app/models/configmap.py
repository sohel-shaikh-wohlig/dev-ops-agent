from pydantic import BaseModel, Field, validator
from typing import Dict, List, Optional
from datetime import datetime
from enum import Enum
from .common import ChangeType, EnvironmentType

class ConfigMapChange(BaseModel):
    """
    Model for a single configuration change
    Used in both preview and update responses
    """
    file: str = Field(
        ...,
        description="File being modified (values.yaml or configmap.yaml)",
        example="values.yaml"
    )
    type: ChangeType = Field(
        ...,
        description="Type of change (ADD or UPDATE)",
        example="UPDATE"
    )
    key: str = Field(
        ...,
        description="Configuration key being changed",
        example="APP_NAME"
    )
    old_value: Optional[str] = Field(
        None,
        description="Previous value (null for new keys)",
        example="OldAppName"
    )
    new_value: str = Field(
        ...,
        description="New value being set",
        example="NewAppName"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "file": "values.yaml",
                "type": "UPDATE",
                "key": "APP_NAME",
                "old_value": "OldAppName",
                "new_value": "NewAppName"
            }
        }

# ========================================
# Request Models
# ========================================

class ConfigMapUpdateRequest(BaseModel):
    """
    Request model for complete ConfigMap configuration update workflow
    
    This executes the entire workflow:
    1. Clone GitOps repository
    2. Update values.yaml and configmap.yaml
    3. Optionally commit and push to Git
    4. Optionally sync ArgoCD application
    """
    environment_name: EnvironmentType = Field(
        ...,
        description="Target environment for deployment"
    )
    
    microservice_name: str = Field(
        ...,
        description="Name of the microservice (must match folder name in GitOps repo)",
        min_length=1,
        max_length=100,
        example="intelligent-chatbot-adapter-api"
    )
    
    gitops_url: str = Field(
        ...,
        description="Full URL to GitOps repository (supports https:// or git@)",
        example="https://github.com/organization/gitops-repo.git"
    )
    
    argocd_app_name: str = Field(
        ...,
        description="ArgoCD application name for synchronization",
        min_length=1,
        max_length=100,
        example="chatbot-api-dev"
    )
    
    env_content: str = Field(
        ...,
        description="Content of .env file with KEY=VALUE pairs (one per line)",
        min_length=1,
        example="APP_NAME=ChatbotAPI\nDEBUG=true\nPORT=8000\nLOG_LEVEL=info"
    )
    
    auto_commit: bool = Field(
        default=False,
        description="Automatically commit and push changes to Git repository"
    )
    
    auto_sync_argocd: bool = Field(
        default=False,
        description="Automatically sync ArgoCD application after Git push (requires auto_commit=true)"
    )
    
    git_branch: Optional[str] = Field(
        default="main",
        description="Git branch to use (default: main)",
        example="main"
    )
    
    commit_message: Optional[str] = Field(
        None,
        description="Custom commit message (auto-generated if not provided)",
        max_length=200,
        example="Updated configuration for chatbot-api in staging"
    )
    
    @validator('microservice_name')
    def validate_microservice_name(cls, v):
        """Validate microservice name is not empty and clean"""
        if not v or not v.strip():
            raise ValueError("Microservice name cannot be empty")
        
        # Check for invalid characters
        if any(char in v for char in ['/', '\\', '..', ' ']):
            raise ValueError("Microservice name cannot contain slashes, spaces, or '..'")
        
        return v.strip()
    
    @validator('gitops_url')
    def validate_gitops_url(cls, v):
        """Validate GitOps URL format"""
        if not v or not v.strip():
            raise ValueError("GitOps URL cannot be empty")
        
        v = v.strip()
        
        # Check for valid URL format
        if not (v.startswith('http://') or v.startswith('https://') or v.startswith('git@')):
            raise ValueError(
                "GitOps URL must start with http://, https://, or git@. "
                f"Got: {v[:20]}..."
            )
        
        # Basic validation for GitHub/GitLab URLs
        if 'github.com' in v or 'gitlab.com' in v:
            if not v.endswith('.git'):
                # Allow URLs without .git but warn
                pass
        
        return v
    
    @validator('argocd_app_name')
    def validate_argocd_app_name(cls, v):
        """Validate ArgoCD application name"""
        if not v or not v.strip():
            raise ValueError("ArgoCD application name cannot be empty")
        
        # ArgoCD app names should follow DNS naming conventions
        if not v.replace('-', '').replace('_', '').isalnum():
            raise ValueError(
                "ArgoCD application name should contain only alphanumeric characters, hyphens, and underscores"
            )
        
        return v.strip()
    
    @validator('env_content')
    def validate_env_content(cls, v):
        """Validate environment content is not empty and has valid format"""
        if not v or not v.strip():
            raise ValueError("Environment content cannot be empty")
        
        # Check that at least one KEY=VALUE pair exists
        lines = [line.strip() for line in v.strip().split('\n')]
        valid_lines = [line for line in lines if line and not line.startswith('#') and '=' in line]
        
        if not valid_lines:
            raise ValueError(
                "Environment content must contain at least one valid KEY=VALUE pair. "
                "Lines should be in format: KEY=VALUE"
            )
        
        return v.strip()
    
    @validator('auto_sync_argocd')
    def validate_auto_sync_requires_commit(cls, v, values):
        """Validate that auto_sync_argocd requires auto_commit"""
        if v and not values.get('auto_commit'):
            raise ValueError(
                "auto_sync_argocd=true requires auto_commit=true. "
                "Cannot sync ArgoCD without committing changes to Git."
            )
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "environment_name": "staging",
                "microservice_name": "intelligent-chatbot-adapter-api",
                "gitops_url": "https://github.com/myorg/gitops-repo.git",
                "argocd_app_name": "chatbot-api-staging",
                "env_content": "APP_NAME=ChatbotAPI\nDEBUG=true\nPORT=8000\nLOG_LEVEL=info\nDATABASE_URL=postgresql://db:5432/chatbot",
                "auto_commit": True,
                "auto_sync_argocd": True,
                "git_branch": "main",
                "commit_message": "Updated chatbot configuration for staging"
            }
        }


class ConfigMapPreviewRequest(BaseModel):
    """
    Request model for previewing configuration changes
    
    Shows what changes would be made without actually applying them.
    Creates a preview session that can be applied later.
    """
    environment_name: EnvironmentType = Field(
        ...,
        description="Target environment"
    )
    
    microservice_name: str = Field(
        ...,
        description="Name of the microservice",
        min_length=1,
        max_length=100,
        example="payment-service"
    )
    
    gitops_url: str = Field(
        ...,
        description="GitOps repository URL",
        example="https://github.com/myorg/gitops-repo.git"
    )
    
    env_content: str = Field(
        ...,
        description="Environment variables content (KEY=VALUE format)",
        min_length=1,
        example="PAYMENT_GATEWAY=stripe\nAPI_KEY=sk_test_xxx\nWEBHOOK_URL=https://api.example.com/webhook"
    )
    
    git_branch: Optional[str] = Field(
        default="main",
        description="Git branch to clone (default: main)"
    )
    
    @validator('microservice_name')
    def validate_microservice_name(cls, v):
        if not v or not v.strip():
            raise ValueError("Microservice name cannot be empty")
        return v.strip()
    
    @validator('gitops_url')
    def validate_gitops_url(cls, v):
        if not v or not v.strip():
            raise ValueError("GitOps URL cannot be empty")
        
        v = v.strip()
        if not (v.startswith('http://') or v.startswith('https://') or v.startswith('git@')):
            raise ValueError("GitOps URL must be a valid URL (http://, https://, or git@)")
        
        return v
    
    @validator('env_content')
    def validate_env_content(cls, v):
        if not v or not v.strip():
            raise ValueError("Environment content cannot be empty")
        
        # Validate at least one KEY=VALUE pair
        lines = [line.strip() for line in v.strip().split('\n')]
        valid_lines = [line for line in lines if line and not line.startswith('#') and '=' in line]
        
        if not valid_lines:
            raise ValueError("Environment content must contain at least one KEY=VALUE pair")
        
        return v.strip()
    
    class Config:
        json_schema_extra = {
            "example": {
                "environment_name": "production",
                "microservice_name": "payment-service",
                "gitops_url": "https://github.com/myorg/gitops-repo.git",
                "env_content": "PAYMENT_GATEWAY=stripe\nAPI_KEY=sk_live_xxx\nWEBHOOK_URL=https://api.example.com/webhook",
                "git_branch": "main"
            }
        }


class ConfigMapApplyChangesRequest(BaseModel):
    """
    Request model for applying previewed changes
    
    Uses a session ID from a previous preview to apply changes,
    with options for Git commit and ArgoCD sync.
    """
    session_id: str = Field(
        ...,
        description="Session ID from preview response",
        min_length=1,
        example="550e8400-e29b-41d4-a716-446655440000"
    )
    
    auto_commit: bool = Field(
        default=False,
        description="Commit and push changes to Git"
    )
    
    auto_sync_argocd: bool = Field(
        default=False,
        description="Sync ArgoCD application after commit"
    )
    
    argocd_app_name: Optional[str] = Field(
        None,
        description="ArgoCD application name (required if auto_sync_argocd=true)",
        example="payment-service-prod"
    )
    
    commit_message: Optional[str] = Field(
        None,
        description="Custom commit message (auto-generated if not provided)",
        max_length=200,
        example="Applied configuration changes for payment service"
    )
    
    @validator('session_id')
    def validate_session_id(cls, v):
        """Validate session ID is not empty"""
        if not v or not v.strip():
            raise ValueError("Session ID cannot be empty")
        return v.strip()
    
    @validator('argocd_app_name')
    def validate_argocd_app_name_if_sync(cls, v, values):
        """Validate ArgoCD app name is provided if auto_sync is enabled"""
        if values.get('auto_sync_argocd') and not v:
            raise ValueError(
                "argocd_app_name is required when auto_sync_argocd=true"
            )
        return v
    
    @validator('auto_sync_argocd')
    def validate_auto_sync_requires_commit(cls, v, values):
        """Validate that auto_sync requires auto_commit"""
        if v and not values.get('auto_commit'):
            raise ValueError(
                "auto_sync_argocd=true requires auto_commit=true"
            )
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "550e8400-e29b-41d4-a716-446655440000",
                "auto_commit": True,
                "auto_sync_argocd": True,
                "argocd_app_name": "payment-service-prod",
                "commit_message": "Applied reviewed configuration changes"
            }
        }


# ========================================
# Response Models
# ========================================

class ConfigMapUpdateResponse(BaseModel):
    """
    Response model for GitOps configuration update
    
    Returns detailed information about changes made,
    Git commit status, and ArgoCD sync status.
    """
    status: str = Field(
        ...,
        description="Operation status",
        example="success"
    )
    
    message: str = Field(
        ...,
        description="Human-readable status message",
        example="Configuration updated successfully"
    )
    
    environment: str = Field(
        ...,
        description="Target environment",
        example="staging"
    )
    
    microservice: str = Field(
        ...,
        description="Microservice name",
        example="intelligent-chatbot-adapter-api"
    )
    
    changes: List[ConfigMapChange] = Field(
        ...,
        description="List of all configuration changes made"
    )
    
    summary: Dict[str, int] = Field(
        ...,
        description="Summary statistics of changes"
    )
    
    git_committed: bool = Field(
        default=False,
        description="Whether changes were committed to Git"
    )
    
    git_commit_hash: Optional[str] = Field(
        None,
        description="Git commit hash (if committed)",
        example="a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0"
    )
    
    git_branch: Optional[str] = Field(
        None,
        description="Git branch used",
        example="main"
    )
    
    argocd_synced: bool = Field(
        default=False,
        description="Whether ArgoCD application was synced"
    )
    
    argocd_app_name: Optional[str] = Field(
        None,
        description="ArgoCD application name (if synced)",
        example="chatbot-api-staging"
    )
    
    repository_url: Optional[str] = Field(
        None,
        description="GitOps repository URL used",
        example="https://github.com/myorg/gitops-repo.git"
    )
    
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp of operation completion"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "success",
                "message": "Configuration updated successfully",
                "environment": "staging",
                "microservice": "intelligent-chatbot-adapter-api",
                "changes": [
                    {
                        "file": "values.yaml",
                        "type": "UPDATE",
                        "key": "APP_NAME",
                        "old_value": "OldName",
                        "new_value": "ChatbotAPI"
                    },
                    {
                        "file": "values.yaml",
                        "type": "ADD",
                        "key": "NEW_FEATURE_FLAG",
                        "old_value": None,
                        "new_value": "true"
                    },
                    {
                        "file": "configmap.yaml",
                        "type": "UPDATE",
                        "key": "APP_NAME",
                        "old_value": "{{ .Values.config.APP_NAME | quote }}",
                        "new_value": "{{ .Values.config.APP_NAME | quote }}"
                    }
                ],
                "summary": {
                    "total_changes": 8,
                    "values_yaml_changes": 4,
                    "configmap_yaml_changes": 4,
                    "additions": 2,
                    "updates": 6
                },
                "git_committed": True,
                "git_commit_hash": "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0",
                "git_branch": "main",
                "argocd_synced": True,
                "argocd_app_name": "chatbot-api-staging",
                "repository_url": "https://github.com/myorg/gitops-repo.git",
                "timestamp": "2026-01-19T10:30:00.000000"
            }
        }


class ConfigMapPreviewResponse(BaseModel):
    """
    Response model for configuration preview
    
    Returns proposed changes without applying them,
    and provides a session ID for later application.
    """
    status: str = Field(
        ...,
        description="Preview status",
        example="success"
    )
    
    message: str = Field(
        ...,
        description="Status message",
        example="Preview generated successfully"
    )
    
    session_id: str = Field(
        ...,
        description="Session ID for applying changes later (use with /apply endpoint)",
        example="550e8400-e29b-41d4-a716-446655440000"
    )
    
    environment: str = Field(
        ...,
        description="Target environment",
        example="production"
    )
    
    microservice: str = Field(
        ...,
        description="Microservice name",
        example="payment-service"
    )
    
    changes: List[ConfigMapChange] = Field(
        ...,
        description="List of proposed changes"
    )
    
    env_variables: Dict[str, str] = Field(
        ...,
        description="Parsed environment variables from .env content"
    )
    
    summary: Dict[str, int] = Field(
        ...,
        description="Summary statistics of proposed changes"
    )
    
    repository_url: str = Field(
        ...,
        description="GitOps repository URL",
        example="https://github.com/myorg/gitops-repo.git"
    )
    
    repository_cloned: bool = Field(
        default=True,
        description="Whether repository was successfully cloned"
    )
    
    microservice_path: Optional[str] = Field(
        None,
        description="Path to microservice in repository",
        example="/tmp/preview-session/repo/payment-service"
    )
    
    session_expires_at: Optional[datetime] = Field(
        None,
        description="When preview session expires (typically 1 hour)"
    )
    
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp of preview generation"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "success",
                "message": "Preview generated successfully",
                "session_id": "550e8400-e29b-41d4-a716-446655440000",
                "environment": "production",
                "microservice": "payment-service",
                "changes": [
                    {
                        "file": "values.yaml",
                        "type": "UPDATE",
                        "key": "PAYMENT_GATEWAY",
                        "old_value": "paypal",
                        "new_value": "stripe"
                    },
                    {
                        "file": "values.yaml",
                        "type": "ADD",
                        "key": "WEBHOOK_URL",
                        "old_value": None,
                        "new_value": "https://api.example.com/webhook"
                    }
                ],
                "env_variables": {
                    "PAYMENT_GATEWAY": "stripe",
                    "API_KEY": "sk_live_xxx",
                    "WEBHOOK_URL": "https://api.example.com/webhook"
                },
                "summary": {
                    "total_changes": 6,
                    "values_yaml_changes": 3,
                    "configmap_yaml_changes": 3,
                    "additions": 1,
                    "updates": 5
                },
                "repository_url": "https://github.com/myorg/gitops-repo.git",
                "repository_cloned": True,
                "microservice_path": "/tmp/preview-550e8400/repo/payment-service",
                "session_expires_at": "2026-01-19T11:30:00.000000",
                "timestamp": "2026-01-19T10:30:00.000000"
            }
        }


class ConfigValuesResponse(BaseModel):
    """
    Response model for retrieving config values from GitOps repository
    """
    status: str = Field(
        ...,
        description="Operation status",
        example="success"
    )

    microservice: str = Field(
        ...,
        description="Microservice name",
        example="payment-service"
    )

    environment: str = Field(
        ...,
        description="Environment (branch) name",
        example="production"
    )

    config: Dict[str, str] = Field(
        ...,
        description="Configuration values from the 'config' block in values.yaml"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "status": "success",
                "microservice": "payment-service",
                "environment": "production",
                "config": {
                    "NODE_ENV": "production",
                    "API_URL": "https://api.example.com",
                    "LOG_LEVEL": "info"
                }
            }
        }