/**
 * Unified ChatMessage interface for PyBOG
 * Consolidates all message types used across the application
 */

export interface ChatMessage {
  id: string;
  type: 'user' | 'assistant' | 'system';
  messageType?:
    | 'status'
    | 'analysis'
    | 'artifact'
    | 'user'
    | 'processing'
    | 'error'
    | 'progress'
    | 'analysis_summary'
    | 'result_files'
    | 'analysis_progress'
    | 'analysis_review'
    | 'bog_progress'
    | 'bog_download'
    | 'text_review';
  content: string;
  timestamp: Date;
  sessionId?: string;
  files?: File[];
  status?: 'sending' | 'sent' | 'failed';
  persisted?: boolean;
  metadata?: {
    status?: 'error' | 'success' | 'warning' | 'info' | 'complete' | 'approved' | 'awaiting_analysis_review';
    kind?: string;
    [key: string]: any;
  };
  // Analysis-specific fields
  analysis?: {
    io_points?: any[];
    control_blocks?: any[];
    pseudocode?: any[];
    quality_score?: number;
    issues?: string[];
    recommendations?: string[];
  };
  // File-specific fields
  fileData?: {
    file_id?: string;
    filename?: string;
    file_type?: string;
    file_size?: number;
    preview_url?: string;
  };
  // Progress-specific fields
  progress?: {
    operation?: string;
    state?: string;
    progress_percent?: number;
    message?: string;
  };
}

export interface Session {
  id: string;
  name: string;
  createdAt: Date;
  messages: ChatMessage[];
  currentAnalysis: any | null;
  analysisMessageId?: string;
  persisted?: boolean;
}

export interface WorkflowState {
  state: 'idle' | 'analyzing' | 'awaiting_approval' | 'generating' | 'complete' | 'awaiting_analysis_review';
  currentOperation?: string;
  progress_percent?: number;
  resumeUrl?: string;
  metadata?: Record<string, any>;
}