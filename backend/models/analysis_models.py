"""
Analysis engine data models for PyBOG backend.
Defines models for document analysis, BOG generation, and analysis results.
"""

from datetime import datetime
from enum import Enum
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field, field_validator

from .file_models import ProgressState


class AnalysisState(str, Enum):
    """Analysis state machine for document processing."""
    QUEUED = "queued"           # Analysis queued for processing
    PROCESSING = "processing"   # Active analysis in progress
    FINALIZING = "finalizing"   # Completing analysis, generating BOG file
    COMPLETE = "complete"       # Successfully finished
    FAILED = "failed"          # Error occurred


class IOPointType(str, Enum):
    """Input/Output point types."""
    INPUT = "input"
    OUTPUT = "output"


class DataType(str, Enum):
    """Data types for IO points."""
    BOOLEAN = "boolean"
    NUMERIC = "numeric"
    STRING = "string"


class IOPoint(BaseModel):
    """Input/Output point definition."""
    
    name: str
    type: IOPointType
    data_type: DataType
    units: Optional[str] = None
    description: str
    
    @field_validator('name', 'description')
    @classmethod
    def validate_non_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('Name and description cannot be empty')
        return v.strip()


class ControlBlock(BaseModel):
    """Control block definition."""
    
    name: str
    type: str
    description: str
    logic: List[str]
    complexity: int = Field(ge=1, le=10)
    
    @field_validator('name', 'type', 'description')
    @classmethod
    def validate_non_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('Name, type, and description cannot be empty')
        return v.strip()
    
    @field_validator('logic')
    @classmethod
    def validate_logic(cls, v):
        if not v:
            raise ValueError('Logic steps cannot be empty')
        return [step.strip() for step in v if step.strip()]


class PseudocodeStep(BaseModel):
    """Pseudocode step definition."""
    
    step: int = Field(ge=1)
    description: str
    code: str
    
    @field_validator('description', 'code')
    @classmethod
    def validate_non_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('Description and code cannot be empty')
        return v.strip()


class AnalysisMetadata(BaseModel):
    """Analysis metadata."""
    
    document_type: str = "unknown"
    confidence: float = Field(ge=0.0, le=1.0, default=0.0)
    recommendations: List[str] = Field(default_factory=list)
    processing_time_seconds: Optional[float] = None
    model_version: Optional[str] = None


class DocumentAnalysis(BaseModel):
    """Complete document analysis result."""
    
    io_points: List[IOPoint] = Field(default_factory=list)
    control_blocks: List[ControlBlock] = Field(default_factory=list)
    pseudocode: List[PseudocodeStep] = Field(default_factory=list)
    quality_score: float = Field(ge=0.0, le=1.0, default=0.0)
    issues: List[str] = Field(default_factory=list)
    metadata: AnalysisMetadata = Field(default_factory=AnalysisMetadata)
    
    @field_validator('quality_score')
    @classmethod
    def validate_quality_score(cls, v):
        return max(0.0, min(1.0, v))


class AnalysisResult(BaseModel):
    """Analysis result database model."""
    
    id: Optional[int] = None
    session_id: str
    input_file_id: int
    bog_file_id: Optional[int] = None
    state: AnalysisState = AnalysisState.QUEUED
    analysis_data: DocumentAnalysis
    error_message: Optional[str] = None
    created_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    @field_validator('session_id')
    @classmethod
    def validate_session_id(cls, v):
        if not v or not v.strip():
            raise ValueError('Session ID cannot be empty')
        return v.strip()
    
    @field_validator('error_message')
    @classmethod
    def validate_error_message(cls, v, info):
        # Error message is required when state is FAILED
        if info.data.get('state') == AnalysisState.FAILED and not v:
            raise ValueError('Error message is required when state is FAILED')
        return v
    
    class Config:
        from_attributes = True


class AnalysisRequest(BaseModel):
    """Request model for document analysis."""
    
    session_id: str
    file_id: int
    options: Dict[str, Any] = Field(default_factory=dict)
    
    @field_validator('session_id')
    @classmethod
    def validate_session_id(cls, v):
        if not v or not v.strip():
            raise ValueError('Session ID cannot be empty')
        return v.strip()
    
    @field_validator('file_id')
    @classmethod
    def validate_file_id(cls, v):
        if v <= 0:
            raise ValueError('File ID must be positive')
        return v


class BOGGenerationRequest(BaseModel):
    """Request model for BOG file generation."""
    
    session_id: str
    analysis_id: int
    filename: Optional[str] = None
    options: Dict[str, Any] = Field(default_factory=dict)
    
    @field_validator('session_id')
    @classmethod
    def validate_session_id(cls, v):
        if not v or not v.strip():
            raise ValueError('Session ID cannot be empty')
        return v.strip()
    
    @field_validator('analysis_id')
    @classmethod
    def validate_analysis_id(cls, v):
        if v <= 0:
            raise ValueError('Analysis ID must be positive')
        return v


class AnalysisStateUpdate(BaseModel):
    """Model for updating analysis state."""
    
    state: AnalysisState
    error_message: Optional[str] = None
    bog_file_id: Optional[int] = None
    
    @field_validator('error_message')
    @classmethod
    def validate_error_message(cls, v, info):
        # Error message is required when state is FAILED
        if info.data.get('state') == AnalysisState.FAILED and not v:
            raise ValueError('Error message is required when state is FAILED')
        return v


class AnalysisProgress(BaseModel):
    """Progress update for analysis operations."""
    
    session_id: str
    analysis_id: Optional[int] = None
    operation: str  # 'analyze', 'generate_bog', 'cancel'
    state: AnalysisState
    message: str
    progress_percent: Optional[float] = Field(None, ge=0.0, le=100.0)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    @field_validator('session_id', 'operation', 'message')
    @classmethod
    def validate_non_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('Session ID, operation, and message cannot be empty')
        return v.strip()


class AnalysisListResponse(BaseModel):
    """Response model for analysis listing."""
    
    analyses: List[AnalysisResult]
    total_count: int
    session_id: str
    
    class Config:
        from_attributes = True


class CancellationRequest(BaseModel):
    """Request model for cancelling analysis."""
    
    session_id: str
    analysis_id: Optional[int] = None  # If None, cancel all active analyses for session
    reason: Optional[str] = "User requested cancellation"
    
    @field_validator('session_id')
    @classmethod
    def validate_session_id(cls, v):
        if not v or not v.strip():
            raise ValueError('Session ID cannot be empty')
        return v.strip()


class CancellationResult(BaseModel):
    """Result model for cancellation operations."""
    
    cancelled_count: int
    cancelled_analysis_ids: List[int]
    session_id: str
    message: str