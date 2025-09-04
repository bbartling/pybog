"""
Shared constants for consistent state management across all PyBOG services.
This file should be referenced by API, frontend (via TypeScript version), and N8N workflows.
"""

# Session States - Used across API, Database, and N8N
class SessionState:
    NEW = "new"                          # Initial state when session created
    DOCUMENT_UPLOADED = "document_uploaded"  # File uploaded, awaiting processing
    ANALYZING = "analyzing"               # N8N workflow processing document
    ANALYSIS_COMPLETE = "analysis_complete"  # Analysis done, awaiting review
    PENDING_APPROVAL = "pending_approval"    # User needs to approve analysis
    APPROVED = "approved"                 # User approved, ready for BOG generation
    GENERATING = "generating"             # BOG file being generated
    COMPLETE = "complete"                 # BOG generation complete
    ERROR = "error"                       # Error occurred in workflow
    FEEDBACK_REQUESTED = "feedback_requested"  # User requested changes

# Valid state transitions
STATE_TRANSITIONS = {
    SessionState.NEW: [SessionState.DOCUMENT_UPLOADED, SessionState.ANALYZING],
    SessionState.DOCUMENT_UPLOADED: [SessionState.ANALYZING, SessionState.ERROR],
    SessionState.ANALYZING: [SessionState.ANALYSIS_COMPLETE, SessionState.ERROR],
    SessionState.ANALYSIS_COMPLETE: [SessionState.PENDING_APPROVAL],
    SessionState.PENDING_APPROVAL: [SessionState.APPROVED, SessionState.FEEDBACK_REQUESTED],
    SessionState.APPROVED: [SessionState.GENERATING],
    SessionState.GENERATING: [SessionState.COMPLETE, SessionState.ERROR],
    SessionState.FEEDBACK_REQUESTED: [SessionState.ANALYZING],
    SessionState.ERROR: [SessionState.NEW, SessionState.ANALYZING],  # Can retry
    SessionState.COMPLETE: []  # Terminal state
}

# WebSocket Message Types
class WebSocketMessageType:
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    STATE_CHANGED = "state_changed"
    ANALYSIS_COMPLETE = "analysis_complete"
    BOG_GENERATED = "bog_generated"
    ERROR = "error"
    PROGRESS_UPDATE = "progress_update"
    PING = "ping"
    PONG = "pong"

# File Types Supported
SUPPORTED_FILE_TYPES = {
    "application/pdf": ".pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "application/msword": ".doc",
    "text/plain": ".txt",
    "text/csv": ".csv"
}

# API Response Status
class ResponseStatus:
    SUCCESS = "success"
    ERROR = "error"
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
