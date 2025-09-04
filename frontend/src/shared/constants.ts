/**
 * Shared constants for consistent state management across all PyBOG services.
 * This TypeScript version mirrors the Python constants.py file.
 */

// Session States - Used across API, Database, and N8N
export enum SessionState {
  NEW = "new",                          // Initial state when session created
  DOCUMENT_UPLOADED = "document_uploaded",  // File uploaded, awaiting processing
  ANALYZING = "analyzing",               // N8N workflow processing document
  ANALYSIS_COMPLETE = "analysis_complete",  // Analysis done, awaiting review
  PENDING_APPROVAL = "pending_approval",    // User needs to approve analysis
  APPROVED = "approved",                 // User approved, ready for BOG generation
  GENERATING = "generating",             // BOG file being generated
  COMPLETE = "complete",                 // BOG generation complete
  ERROR = "error",                       // Error occurred in workflow
  FEEDBACK_REQUESTED = "feedback_requested"  // User requested changes
}

// Valid state transitions
export const STATE_TRANSITIONS: Record<SessionState, SessionState[]> = {
  [SessionState.NEW]: [SessionState.DOCUMENT_UPLOADED, SessionState.ANALYZING],
  [SessionState.DOCUMENT_UPLOADED]: [SessionState.ANALYZING, SessionState.ERROR],
  [SessionState.ANALYZING]: [SessionState.ANALYSIS_COMPLETE, SessionState.ERROR],
  [SessionState.ANALYSIS_COMPLETE]: [SessionState.PENDING_APPROVAL],
  [SessionState.PENDING_APPROVAL]: [SessionState.APPROVED, SessionState.FEEDBACK_REQUESTED],
  [SessionState.APPROVED]: [SessionState.GENERATING],
  [SessionState.GENERATING]: [SessionState.COMPLETE, SessionState.ERROR],
  [SessionState.FEEDBACK_REQUESTED]: [SessionState.ANALYZING],
  [SessionState.ERROR]: [SessionState.NEW, SessionState.ANALYZING],  // Can retry
  [SessionState.COMPLETE]: []  // Terminal state
};

// WebSocket Message Types
export enum WebSocketMessageType {
  CONNECTED = "connected",
  DISCONNECTED = "disconnected",
  STATE_CHANGED = "state_changed",
  ANALYSIS_COMPLETE = "analysis_complete",
  BOG_GENERATED = "bog_generated",
  ERROR = "error",
  PROGRESS_UPDATE = "progress_update",
  PING = "ping",
  PONG = "pong"
}

// File Types Supported
export const SUPPORTED_FILE_TYPES: Record<string, string> = {
  "application/pdf": ".pdf",
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
  "application/msword": ".doc",
  "text/plain": ".txt",
  "text/csv": ".csv"
};

// API Response Status
export enum ResponseStatus {
  SUCCESS = "success",
  ERROR = "error",
  PENDING = "pending",
  IN_PROGRESS = "in_progress"
}

// Helper function to check if state transition is valid
export function isValidStateTransition(from: SessionState, to: SessionState): boolean {
  const validTransitions = STATE_TRANSITIONS[from];
  return validTransitions ? validTransitions.includes(to) : false;
}

// Helper function to get human-readable state label
export function getStateLabel(state: SessionState): string {
  const labels: Record<SessionState, string> = {
    [SessionState.NEW]: "New Session",
    [SessionState.DOCUMENT_UPLOADED]: "Document Uploaded",
    [SessionState.ANALYZING]: "Analyzing Document",
    [SessionState.ANALYSIS_COMPLETE]: "Analysis Complete",
    [SessionState.PENDING_APPROVAL]: "Awaiting Approval",
    [SessionState.APPROVED]: "Approved",
    [SessionState.GENERATING]: "Generating BOG File",
    [SessionState.COMPLETE]: "Complete",
    [SessionState.ERROR]: "Error",
    [SessionState.FEEDBACK_REQUESTED]: "Feedback Requested"
  };
  return labels[state] || state;
}
