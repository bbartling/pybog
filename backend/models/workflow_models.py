"""
Workflow state management models for PyBOG backend.
Defines models for review and approval workflow states and transitions.
"""

from datetime import datetime
from enum import Enum
from typing import Dict, Any, Optional, List, Union
from pydantic import BaseModel, Field, field_validator


class WorkflowState(str, Enum):
    """Workflow state machine for review and approval process."""
    IDLE = "idle"                           # No active workflow
    EXTRACTING_TEXT = "extracting_text"     # Extracting text from uploaded files
    AWAITING_TEXT_REVIEW = "awaiting_text_review"  # Waiting for user to review extracted text
    ANALYZING = "analyzing"                 # AI analysis in progress
    AWAITING_ANALYSIS_REVIEW = "awaiting_analysis_review"  # Waiting for user to review analysis
    GENERATING_BOG = "generating_bog"       # Generating BOG file
    COMPLETE = "complete"                   # Workflow completed successfully
    FAILED = "failed"                       # Workflow failed with error


class ReviewType(str, Enum):
    """Types of review in the workflow."""
    TEXT_EXTRACTION = "text_extraction"
    ANALYSIS_RESULT = "analysis_result"
    BOG_GENERATION = "bog_generation"


class ReviewDecision(str, Enum):
    """User decisions for review items."""
    APPROVE = "approve"
    REQUEST_CHANGES = "request_changes"
    REJECT = "reject"
    RETRY = "retry"


class TextExtractionReview(BaseModel):
    """Text extraction review data."""
    
    file_id: int
    extracted_text: str
    quality_score: float = Field(ge=0.0, le=1.0)
    quality_issues: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    hvac_terms_found: int = 0
    character_count: int
    estimated_tokens: Optional[int] = None
    
    @field_validator('extracted_text')
    @classmethod
    def validate_extracted_text(cls, v):
        if not v or not v.strip():
            raise ValueError('Extracted text cannot be empty')
        return v.strip()
    
    @field_validator('character_count')
    @classmethod
    def validate_character_count(cls, v):
        if v < 0:
            raise ValueError('Character count must be non-negative')
        return v


class AnalysisReview(BaseModel):
    """Analysis result review data."""
    
    analysis_id: int
    quality_score: float = Field(ge=0.0, le=1.0)
    io_points_count: int = 0
    control_blocks_count: int = 0
    pseudocode_steps_count: int = 0
    issues: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    confidence_level: float = Field(ge=0.0, le=1.0, default=0.0)
    completeness_score: float = Field(ge=0.0, le=1.0, default=0.0)
    
    @field_validator('analysis_id')
    @classmethod
    def validate_analysis_id(cls, v):
        if v <= 0:
            raise ValueError('Analysis ID must be positive')
        return v


class ReviewItem(BaseModel):
    """Generic review item for workflow."""
    
    id: str  # Unique identifier for this review item
    session_id: str
    review_type: ReviewType
    state: WorkflowState
    data: Union[TextExtractionReview, AnalysisReview]
    user_feedback: Optional[str] = None
    decision: Optional[ReviewDecision] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    reviewed_at: Optional[datetime] = None
    
    @field_validator('id', 'session_id')
    @classmethod
    def validate_non_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('ID and session_id cannot be empty')
        return v.strip()


class WorkflowTransition(BaseModel):
    """Workflow state transition."""
    
    from_state: WorkflowState
    to_state: WorkflowState
    trigger: str  # What triggered the transition
    metadata: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class SessionWorkflow(BaseModel):
    """Complete workflow state for a session."""
    
    session_id: str
    current_state: WorkflowState = WorkflowState.IDLE
    pending_reviews: List[ReviewItem] = Field(default_factory=list)
    completed_reviews: List[ReviewItem] = Field(default_factory=list)
    state_history: List[WorkflowTransition] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    @field_validator('session_id')
    @classmethod
    def validate_session_id(cls, v):
        if not v or not v.strip():
            raise ValueError('Session ID cannot be empty')
        return v.strip()
    
    def add_transition(self, to_state: WorkflowState, trigger: str, metadata: Optional[Dict[str, Any]] = None):
        """Add a state transition to the workflow."""
        transition = WorkflowTransition(
            from_state=self.current_state,
            to_state=to_state,
            trigger=trigger,
            metadata=metadata or {}
        )
        self.state_history.append(transition)
        self.current_state = to_state
        self.updated_at = datetime.utcnow()
    
    def add_review_item(self, review_item: ReviewItem):
        """Add a review item to pending reviews."""
        self.pending_reviews.append(review_item)
        self.updated_at = datetime.utcnow()
    
    def complete_review(self, review_id: str, decision: ReviewDecision, feedback: Optional[str] = None):
        """Complete a review item."""
        for i, review in enumerate(self.pending_reviews):
            if review.id == review_id:
                review.decision = decision
                review.user_feedback = feedback
                review.reviewed_at = datetime.utcnow()
                completed_review = self.pending_reviews.pop(i)
                self.completed_reviews.append(completed_review)
                self.updated_at = datetime.utcnow()
                return completed_review
        return None


class ReviewRequest(BaseModel):
    """Request to submit a review decision."""
    
    session_id: str
    review_id: str
    decision: ReviewDecision
    feedback: Optional[str] = None
    modified_data: Optional[Dict[str, Any]] = None  # For edited text or analysis data
    
    @field_validator('session_id', 'review_id')
    @classmethod
    def validate_non_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('Session ID and review ID cannot be empty')
        return v.strip()


class ReviewResponse(BaseModel):
    """Response after submitting a review."""
    
    review_id: str
    decision: ReviewDecision
    next_state: WorkflowState
    message: str
    actions_available: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class WorkflowStatusResponse(BaseModel):
    """Current workflow status response."""
    
    session_id: str
    current_state: WorkflowState
    pending_reviews_count: int
    completed_reviews_count: int
    next_actions: List[str] = Field(default_factory=list)
    current_review: Optional[ReviewItem] = None
    progress_percent: Optional[float] = None
    estimated_completion: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


# Workflow state transition rules
WORKFLOW_TRANSITIONS = {
    WorkflowState.IDLE: [
        WorkflowState.EXTRACTING_TEXT,
        WorkflowState.FAILED
    ],
    WorkflowState.EXTRACTING_TEXT: [
        WorkflowState.AWAITING_TEXT_REVIEW,
        WorkflowState.FAILED
    ],
    WorkflowState.AWAITING_TEXT_REVIEW: [
        WorkflowState.ANALYZING,
        WorkflowState.EXTRACTING_TEXT,  # Retry extraction
        WorkflowState.FAILED
    ],
    WorkflowState.ANALYZING: [
        WorkflowState.AWAITING_ANALYSIS_REVIEW,
        WorkflowState.FAILED
    ],
    WorkflowState.AWAITING_ANALYSIS_REVIEW: [
        WorkflowState.GENERATING_BOG,
        WorkflowState.ANALYZING,  # Retry analysis
        WorkflowState.FAILED
    ],
    WorkflowState.GENERATING_BOG: [
        WorkflowState.COMPLETE,
        WorkflowState.FAILED
    ],
    WorkflowState.COMPLETE: [
        WorkflowState.IDLE  # Start new workflow
    ],
    WorkflowState.FAILED: [
        WorkflowState.IDLE  # Reset and start over
    ]
}


def is_valid_transition(from_state: WorkflowState, to_state: WorkflowState) -> bool:
    """Check if a state transition is valid."""
    return to_state in WORKFLOW_TRANSITIONS.get(from_state, [])


def get_next_actions(current_state: WorkflowState) -> List[str]:
    """Get available actions for current workflow state."""
    actions = {
        WorkflowState.IDLE: ["upload_file", "start_workflow"],
        WorkflowState.EXTRACTING_TEXT: ["cancel_extraction"],
        WorkflowState.AWAITING_TEXT_REVIEW: ["approve_text", "edit_text", "retry_extraction"],
        WorkflowState.ANALYZING: ["cancel_analysis"],
        WorkflowState.AWAITING_ANALYSIS_REVIEW: ["approve_analysis", "request_changes", "retry_analysis"],
        WorkflowState.GENERATING_BOG: ["cancel_generation"],
        WorkflowState.COMPLETE: ["download_bog", "start_new_workflow"],
        WorkflowState.FAILED: ["retry_workflow", "start_new_workflow"]
    }
    return actions.get(current_state, [])