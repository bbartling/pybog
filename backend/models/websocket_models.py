"""
WebSocket message envelope models for PyBOG backend.
Defines models for WebSocket communication, message types, and event handling.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Dict, Any, Optional, Literal, Union
from pydantic import BaseModel, Field, field_validator

from .file_models import ProgressState


class MessageType(str, Enum):
    """WebSocket message types."""
    CHAT = "chat"
    PROGRESS = "progress"
    BOG_GENERATED = "bog_generated"
    ERROR = "error"


class ErrorCode(str, Enum):
    """Standardized error codes for WebSocket messages."""
    FILE = "FILE"                 # Upload failures, corrupted files, unsupported formats
    ANALYSIS = "ANALYSIS"         # LLM failures, parsing errors, insufficient content
    DATABASE = "DATABASE"         # Connection failures, constraint violations, transaction errors
    WEBSOCKET = "WEBSOCKET"       # WebSocket disconnections, connection timeouts
    AUTHENTICATION = "AUTH"       # Authentication, authorization, permissions
    VALIDATION = "VALIDATION"     # Input validation, data format, constraints
    NETWORK = "NETWORK"          # External API calls, network connectivity
    SYSTEM = "SYSTEM"            # System resources, memory, disk, configuration
    BUSINESS = "BUSINESS"        # Business logic, workflow, state transitions
    STREAM = "STREAM"            # Legacy alias for WEBSOCKET
    DB = "DB"                    # Legacy alias for DATABASE


class WebSocketMessage(BaseModel):
    """
    WebSocket message envelope with consistent format.
    
    Provides a standardized message structure for all WebSocket communications
    with type, session_id, data, and timestamp fields.
    """
    
    type: MessageType
    session_id: str
    data: Dict[str, Any]
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    @field_validator('session_id')
    @classmethod
    def validate_session_id(cls, v):
        if not v or not v.strip():
            raise ValueError('Session ID cannot be empty')
        return v.strip()
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ChatMessageData(BaseModel):
    """Data structure for chat message type."""

    content: str
    is_complete: bool = False
    message_id: Optional[str] = None
    buffer_content: Optional[str] = None
    final_content: Optional[str] = None
    message_type: Optional[str] = None


class ProgressMessageData(BaseModel):
    """Data structure for progress message type."""
    
    state: ProgressState
    message: str
    operation: str
    file_id: Optional[int] = None
    progress_percent: Optional[float] = None
    
    @field_validator('progress_percent')
    @classmethod
    def validate_progress_percent(cls, v):
        if v is not None and (v < 0 or v > 100):
            raise ValueError('Progress percent must be between 0 and 100')
        return v


class BOGGeneratedMessageData(BaseModel):
    """Data structure for BOG generated message type."""
    
    file_id: int
    filename: str
    analysis: Dict[str, Any]
    download_url: Optional[str] = None
    
    @field_validator('file_id')
    @classmethod
    def validate_file_id(cls, v):
        if v <= 0:
            raise ValueError('File ID must be positive')
        return v
    
    @field_validator('filename')
    @classmethod
    def validate_filename(cls, v):
        if not v or not v.strip():
            raise ValueError('Filename cannot be empty')
        return v.strip()


class ErrorMessageData(BaseModel):
    """Data structure for error message type."""
    
    error_code: ErrorCode
    message: str
    operation: str
    details: Optional[Dict[str, Any]] = None
    retry_possible: bool = False
    
    @field_validator('message')
    @classmethod
    def validate_message(cls, v):
        if not v or not v.strip():
            raise ValueError('Error message cannot be empty')
        return v.strip()
    
    @field_validator('operation')
    @classmethod
    def validate_operation(cls, v):
        if not v or not v.strip():
            raise ValueError('Operation cannot be empty')
        return v.strip()


class WebSocketConnectionInfo(BaseModel):
    """Information about WebSocket connection."""
    
    session_id: str
    connected_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_activity: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    message_count: int = 0
    
    def update_activity(self):
        """Update last activity timestamp."""
        self.last_activity = datetime.now(timezone.utc)
        self.message_count += 1


class SessionResumeInfo(BaseModel):
    """Information for session resume functionality."""
    
    session_id: str
    replay_events: list[WebSocketMessage] = Field(default_factory=list)
    current_state: Dict[str, Any] = Field(default_factory=dict)
    resume_timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# Type aliases for message data
MessageData = Union[
    ChatMessageData,
    ProgressMessageData, 
    BOGGeneratedMessageData,
    ErrorMessageData
]


def create_chat_message(session_id: str, content: str, is_complete: bool = False,
                       message_id: Optional[str] = None, buffer_content: Optional[str] = None,
                       final_content: Optional[str] = None, message_type: Optional[str] = None) -> WebSocketMessage:
    """Helper function to create a chat message."""
    return WebSocketMessage(
        type=MessageType.CHAT,
        session_id=session_id,
        data=ChatMessageData(
            content=content,
            is_complete=is_complete,
            message_id=message_id,
            buffer_content=buffer_content,
            final_content=final_content,
            message_type=message_type
        ).model_dump()
    )


def create_progress_message(session_id: str, state: ProgressState, message: str, 
                          operation: str, file_id: Optional[int] = None,
                          progress_percent: Optional[float] = None) -> WebSocketMessage:
    """Helper function to create a progress message."""
    return WebSocketMessage(
        type=MessageType.PROGRESS,
        session_id=session_id,
        data=ProgressMessageData(
            state=state,
            message=message,
            operation=operation,
            file_id=file_id,
            progress_percent=progress_percent
        ).model_dump()
    )


def create_bog_generated_message(session_id: str, file_id: int, filename: str, 
                                analysis: Dict[str, Any], 
                                download_url: Optional[str] = None) -> WebSocketMessage:
    """Helper function to create a BOG generated message."""
    return WebSocketMessage(
        type=MessageType.BOG_GENERATED,
        session_id=session_id,
        data=BOGGeneratedMessageData(
            file_id=file_id,
            filename=filename,
            analysis=analysis,
            download_url=download_url
        ).model_dump()
    )


def create_error_message(session_id: str, error_code: ErrorCode, message: str, 
                        operation: str, details: Optional[Dict[str, Any]] = None,
                        retry_possible: bool = False) -> WebSocketMessage:
    """Helper function to create an error message."""
    return WebSocketMessage(
        type=MessageType.ERROR,
        session_id=session_id,
        data=ErrorMessageData(
            error_code=error_code,
            message=message,
            operation=operation,
            details=details,
            retry_possible=retry_possible
        ).model_dump()
    )