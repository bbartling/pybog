"""
LangChain agent data models for PyBOG backend.
Defines models for chat messages, analysis results, and agent responses.
"""

from datetime import datetime
from enum import Enum
from typing import Dict, Any, Optional, List, Literal
from pydantic import BaseModel, Field, field_validator


class MessageType(str, Enum):
    """Chat message type enumeration."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class ChatMessage(BaseModel):
    """Chat message model matching the database schema."""
    
    id: Optional[int] = None
    session_id: str
    message_type: MessageType
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[datetime] = None
    
    @field_validator('content')
    @classmethod
    def validate_content(cls, v):
        if not v or not v.strip():
            raise ValueError('Message content cannot be empty')
        return v.strip()
    
    @field_validator('session_id')
    @classmethod
    def validate_session_id(cls, v):
        if not v or not v.strip():
            raise ValueError('Session ID cannot be empty')
        return v.strip()
    
    class Config:
        from_attributes = True


class IOPoint(BaseModel):
    """Input/Output point for PyBOG analysis."""
    
    name: str
    type: Literal["input", "output"]
    data_type: Literal["boolean", "numeric", "string"]
    units: Optional[str] = None
    description: str
    
    @field_validator('name', 'description')
    @classmethod
    def validate_non_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('Field cannot be empty')
        return v.strip()


class ControlBlock(BaseModel):
    """Control block for PyBOG analysis."""
    
    name: str
    type: str
    description: str
    logic: List[str]
    complexity: int = Field(ge=1, le=10)
    
    @field_validator('name', 'type', 'description')
    @classmethod
    def validate_non_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('Field cannot be empty')
        return v.strip()
    
    @field_validator('logic')
    @classmethod
    def validate_logic(cls, v):
        if not v:
            raise ValueError('Logic cannot be empty')
        return [item.strip() for item in v if item.strip()]


class DocumentAnalysis(BaseModel):
    """Structured analysis result for documents."""
    
    io_points: List[IOPoint]
    control_blocks: List[ControlBlock]
    pseudocode: List[Dict[str, Any]]
    quality_score: float = Field(ge=0.0, le=1.0)
    issues: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    @field_validator('quality_score')
    @classmethod
    def validate_quality_score(cls, v):
        if not 0.0 <= v <= 1.0:
            raise ValueError('Quality score must be between 0.0 and 1.0')
        return v


class ChatResponse(BaseModel):
    """Response model for chat interactions."""
    
    content: str
    is_complete: bool = True
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    @field_validator('content')
    @classmethod
    def validate_content(cls, v):
        if not isinstance(v, str):
            raise ValueError('Content must be a string')
        return v


class AgentError(BaseModel):
    """Error model for agent operations."""
    
    error_code: Literal["AGENT_INIT", "CHAT_PROCESSING", "DOCUMENT_ANALYSIS", "LLM_ERROR"]
    message: str
    operation: str
    session_id: str
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    @field_validator('message', 'operation', 'session_id')
    @classmethod
    def validate_non_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('Field cannot be empty')
        return v.strip()