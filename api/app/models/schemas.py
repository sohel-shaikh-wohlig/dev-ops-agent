"""
Pydantic Schemas for Request/Response validation
"""
from pydantic import BaseModel, Field, validator
from typing import Dict, List, Optional
from datetime import datetime
from enum import Enum


class ChangeType(str, Enum):
    """Type of configuration change"""
    ADD = "ADD"
    UPDATE = "UPDATE"


class FileType(str, Enum):
    """Configuration file type"""
    VALUES_YAML = "values.yaml"
    CONFIGMAP_YAML = "configmap.yaml"


class ConfigChange(BaseModel):
    """
    Schema for a single configuration change
    """
    file: FileType
    type: ChangeType
    key: str
    old_value: Optional[str] = None
    new_value: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "file": "values.yaml",
                "type": "UPDATE",
                "key": "APP_NAME",
                "old_value": "OldApp",
                "new_value": "NewApp"
            }
        }


class PreviewRequest(BaseModel):
    """
    Schema for preview request
    Note: Files are handled separately as multipart/form-data
    """
    env_content: str = Field(..., description="Content of .env file")
    
    @validator('env_content')
    def validate_env_content(cls, v):
        if not v or not v.strip():
            raise ValueError("Environment content cannot be empty")
        return v


class PreviewResponse(BaseModel):
    """
    Schema for preview response
    """
    session_id: str = Field(..., description="Unique session identifier")
    changes: List[ConfigChange] = Field(..., description="List of configuration changes")
    env_variables: Dict[str, str] = Field(..., description="Parsed environment variables")
    summary: Dict[str, int] = Field(..., description="Summary of changes")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "123e4567-e89b-12d3-a456-426614174000",
                "changes": [
                    {
                        "file": "values.yaml",
                        "type": "UPDATE",
                        "key": "APP_NAME",
                        "old_value": "OldApp",
                        "new_value": "NewApp"
                    }
                ],
                "env_variables": {
                    "APP_NAME": "NewApp",
                    "DEBUG": "true"
                },
                "summary": {
                    "total_changes": 2,
                    "additions": 1,
                    "updates": 1
                },
                "created_at": "2026-01-13T10:00:00"
            }
        }


class ApplyRequest(BaseModel):
    """
    Schema for apply request
    """
    session_id: str = Field(..., description="Session ID from preview")
    
    @validator('session_id')
    def validate_session_id(cls, v):
        if not v or not v.strip():
            raise ValueError("Session ID cannot be empty")
        return v


class ApplyResponse(BaseModel):
    """
    Schema for apply response
    """
    status: str = Field(..., description="Operation status")
    message: str = Field(..., description="Status message")
    session_id: str = Field(..., description="Session identifier")
    applied_changes: int = Field(..., description="Number of changes applied")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "success",
                "message": "Changes applied successfully",
                "session_id": "123e4567-e89b-12d3-a456-426614174000",
                "applied_changes": 5,
                "timestamp": "2026-01-13T10:05:00"
            }
        }


class ErrorResponse(BaseModel):
    """
    Schema for error response
    """
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Detailed error information")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_schema_extra = {
            "example": {
                "error": "ValidationError",
                "message": "Invalid file format",
                "detail": "values.yaml not found in uploaded files",
                "timestamp": "2026-01-13T10:00:00"
            }
        }


class HealthResponse(BaseModel):
    """
    Schema for health check response
    """
    status: str
    version: str
    environment: str
    uptime: Optional[float] = None


class SessionInfo(BaseModel):
    """
    Schema for session information
    """
    session_id: str
    created_at: datetime
    expires_at: datetime
    changes_count: int
    status: str