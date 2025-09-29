"""
Data models for PyBOG backend.
Contains Pydantic models for API requests/responses and database records.
"""

from .file_models import (
    FileRecord, FileType, ProgressState, StorageType,
    FileUploadRequest, FileStateUpdate, FileMetadata,
    FileListResponse, FileCleanupResult
)

from .session_models import (
    Session, SessionCreateRequest, SessionUpdateRequest,
    SessionWithFiles, SessionListResponse, SessionResponse,
    SessionStatsResponse
)

from .websocket_models import (
    WebSocketMessage, MessageType, ErrorCode,
    ChatMessageData, ProgressMessageData, BOGGeneratedMessageData,
    ErrorMessageData, WebSocketConnectionInfo, SessionResumeInfo,
    create_chat_message, create_progress_message,
    create_bog_generated_message, create_error_message
)

__all__ = [
    # File models
    "FileRecord",
    "FileType", 
    "ProgressState",
    "StorageType",
    "FileUploadRequest",
    "FileStateUpdate", 
    "FileMetadata",
    "FileListResponse",
    "FileCleanupResult",
    
    # Session models
    "Session",
    "SessionCreateRequest",
    "SessionUpdateRequest",
    "SessionWithFiles",
    "SessionListResponse",
    "SessionResponse",
    "SessionStatsResponse",
    
    # WebSocket models
    "WebSocketMessage",
    "MessageType",
    "ErrorCode",
    "ChatMessageData",
    "ProgressMessageData",
    "BOGGeneratedMessageData",
    "ErrorMessageData",
    "WebSocketConnectionInfo",
    "SessionResumeInfo",
    "create_chat_message",
    "create_progress_message",
    "create_bog_generated_message",
    "create_error_message",
]