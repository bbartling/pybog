"""
Session management data models for PyBOG backend.
Defines models for sessions, session operations, and session responses.
"""

from datetime import datetime
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field, field_validator


class Session(BaseModel):
    """Session model matching the database schema."""
    
    session_id: str
    name: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    @field_validator('session_id')
    @classmethod
    def validate_session_id(cls, v):
        if not v or not v.strip():
            raise ValueError('Session ID cannot be empty')
        return v.strip()
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        if not v or not v.strip():
            raise ValueError('Session name cannot be empty')
        return v.strip()
    
    class Config:
        from_attributes = True


class SessionCreateRequest(BaseModel):
    """Request model for creating a new session."""
    
    session_id: str
    name: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    @field_validator('session_id')
    @classmethod
    def validate_session_id(cls, v):
        if not v or not v.strip():
            raise ValueError('Session ID cannot be empty')
        return v.strip()
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        if not v or not v.strip():
            raise ValueError('Session name cannot be empty')
        return v.strip()


class SessionUpdateRequest(BaseModel):
    """Request model for updating an existing session."""
    
    name: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        if v is not None and (not v or not v.strip()):
            raise ValueError('Session name cannot be empty')
        return v.strip() if v else v


class SessionWithFiles(BaseModel):
    """Session model with associated file information."""
    
    session_id: str
    name: str
    metadata: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    message_count: int = 0
    file_count: int = 0
    upload_count: int = 0
    bog_count: int = 0
    analysis_count: int = 0
    completed_analysis_count: int = 0
    active_analysis_count: int = 0
    
    class Config:
        from_attributes = True


class SessionListResponse(BaseModel):
    """Response model for session listing."""
    
    sessions: List[SessionWithFiles]
    total_count: int


class SessionResponse(BaseModel):
    """Standard response model for session operations."""
    
    success: bool
    session: Optional[Session] = None
    message: Optional[str] = None
    error: Optional[str] = None


class SessionStatsResponse(BaseModel):
    """Response model for session statistics."""
    
    total_sessions: int
    active_sessions: int
    total_messages: int
    total_files: int
    total_analyses: int