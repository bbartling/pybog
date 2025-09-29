"""
File management data models for PyBOG backend.
Defines models for file records, progress states, and file operations.
"""

from datetime import datetime
from enum import Enum
from typing import Dict, Any, Optional, Literal
from pydantic import BaseModel, Field, field_validator


class ProgressState(str, Enum):
    """Progress state machine for file operations."""
    QUEUED = "queued"           # Task queued for processing
    PROCESSING = "processing"   # Active processing
    FINALIZING = "finalizing"   # Completing, generating outputs
    COMPLETE = "complete"       # Successfully finished
    FAILED = "failed"          # Error occurred


class FileType(str, Enum):
    """File type enumeration."""
    UPLOAD = "upload"
    BOG = "bog"
    ANALYSIS = "analysis"
    DOCUMENT = "document"


class StorageType(str, Enum):
    """Storage type for files."""
    BYTEA = "bytea"        # Stored in database as BYTEA
    FILE_PATH = "file_path"  # Stored on filesystem with path reference
    NONE = "none"          # No storage (error state)


class FileRecord(BaseModel):
    """File record model matching the database schema."""
    
    id: Optional[int] = None
    session_id: str
    filename: str
    original_name: str
    mime_type: Optional[str] = None
    file_type: FileType
    file_size: int
    state: ProgressState = ProgressState.QUEUED
    storage_type: Optional[StorageType] = None  # Computed field
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[datetime] = None
    archived_at: Optional[datetime] = None
    
    @field_validator('file_size')
    @classmethod
    def validate_file_size(cls, v):
        if v < 0:
            raise ValueError('File size must be non-negative')
        return v
    
    @field_validator('filename', 'original_name')
    @classmethod
    def validate_filename(cls, v):
        if not v or not v.strip():
            raise ValueError('Filename cannot be empty')
        return v.strip()
    
    class Config:
        from_attributes = True


class FileUploadRequest(BaseModel):
    """Request model for file uploads."""
    
    session_id: str
    file_type: FileType = FileType.UPLOAD
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    @field_validator('session_id')
    @classmethod
    def validate_session_id(cls, v):
        if not v or not v.strip():
            raise ValueError('Session ID cannot be empty')
        return v.strip()


class FileStateUpdate(BaseModel):
    """Model for updating file state."""
    
    state: ProgressState
    metadata: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    
    @field_validator('error_message')
    @classmethod
    def validate_error_message(cls, v, info):
        # Error message is required when state is FAILED
        if info.data.get('state') == ProgressState.FAILED and not v:
            raise ValueError('Error message is required when state is FAILED')
        return v


class FileMetadata(BaseModel):
    """File metadata response model."""
    
    id: int
    session_id: str
    filename: str
    original_name: str
    mime_type: Optional[str]
    file_type: FileType
    file_size: int
    state: ProgressState
    storage_type: StorageType
    metadata: Dict[str, Any]
    created_at: datetime
    archived_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class FileListResponse(BaseModel):
    """Response model for file listing."""
    
    files: list[FileMetadata]
    total_count: int
    session_id: str


class FileCleanupResult(BaseModel):
    """Result model for file cleanup operations."""
    
    archived_count: int
    purged_count: int
    total_processed: int
    
    @property
    def total_processed(self) -> int:
        return self.archived_count + self.purged_count


class TextExtractionResult(BaseModel):
    """Result model for text extraction operations."""
    
    file_id: int
    extracted_text: str
    page_count: Optional[int] = None
    word_count: int
    character_count: int
    extraction_method: str  # "pdf", "docx", "text", "fallback"
    metadata: Dict[str, Any] = Field(default_factory=dict)
    success: bool = True
    error_message: Optional[str] = None
    
    @field_validator('word_count', 'character_count')
    @classmethod
    def validate_counts(cls, v):
        if v < 0:
            raise ValueError('Counts must be non-negative')
        return v


class FilePreview(BaseModel):
    """File preview model with extracted content."""
    
    file_id: int
    filename: str
    mime_type: Optional[str]
    file_size: int
    preview_text: str  # First 500 characters
    full_text_available: bool
    page_count: Optional[int] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)