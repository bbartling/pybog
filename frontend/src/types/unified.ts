/**
 * Unified Data Models for PyBOG
 * Clean interfaces that align with n8n workflows and backend data structures
 */

// Core Session Management
export interface Session {
  id: string;
  sessionId: string;
  name: string;
  createdAt: string;
  updatedAt: string;
  lastActivity: string;
  state: SessionState;
  metadata: SessionMetadata;
}

export interface SessionMetadata {
  workflowId?: string;
  executionId?: string;
  resumeUrl?: string;
  waitNodeId?: string;
  analysisComplete?: boolean;
  bogGenerated?: boolean;
  documentCount?: number;
  messageCount?: number;
  [key: string]: any;
}

export enum SessionState {
  IDLE = 'idle',
  PROCESSING = 'processing',
  WAITING_APPROVAL = 'waiting_approval',
  ANALYZING = 'analyzing',
  GENERATING = 'generating',
  COMPLETE = 'complete',
  ERROR = 'error'
}

// Message System
export interface Message {
  id: string;
  messageId: string;
  sessionId: string;
  type: MessageType;
  messageType?: MessageCategory;
  messageCategory?: MessageCategory;  // Added for compatibility
  content: string | MessageContent;
  timestamp: string;
  metadata: MessageMetadata;
  files?: FileReference[];
  analysis?: AnalysisData;
  waitNode?: WaitNodeData;
}

export enum MessageType {
  USER = 'user',
  ASSISTANT = 'assistant',
  SYSTEM = 'system'
}

export enum MessageCategory {
  STATUS = 'status',
  ANALYSIS = 'analysis',
  ARTIFACT = 'artifact',
  PROCESSING = 'processing',
  ERROR = 'error',
  APPROVAL = 'approval',
  WORKFLOW = 'workflow'
}

export interface MessageContent {
  text?: string;
  html?: string;
  markdown?: string;
  json?: any;
  components?: UIComponent[];
}

export interface MessageMetadata {
  workflowNode?: string;
  executionId?: string;
  stepNumber?: number;
  progress?: number;
  isStreaming?: boolean;
  requiresAction?: boolean;
  actionType?: 'approve' | 'reject' | 'modify';
  [key: string]: any;
}

// File Management
export interface FileReference {
  id: string;
  fileId: string;
  filename: string;
  fileType: string;
  fileSize: number;
  uploadTime: string;
  storagePath?: string;
  downloadUrl?: string;
  metadata: FileMetadata;
}

export interface FileMetadata {
  mimeType?: string;
  extractedText?: boolean;
  pageCount?: number;
  processingStatus?: 'pending' | 'processing' | 'complete' | 'error';
  [key: string]: any;
}

// Analysis System
export interface AnalysisData {
  id: string;
  analysisId: string;
  sessionId: string;
  status: AnalysisStatus;
  hvacComponents?: HVACComponent[];
  documentQuality?: DocumentQuality;
  recommendations?: Recommendation[];
  validationResults?: ValidationResult[];
  createdAt: string;
  updatedAt: string;
}

export enum AnalysisStatus {
  PENDING = 'pending',
  IN_PROGRESS = 'in_progress',
  AWAITING_REVIEW = 'awaiting_review',
  APPROVED = 'approved',
  REJECTED = 'rejected',
  COMPLETE = 'complete'
}

export interface HVACComponent {
  id: string;
  type: string;
  name: string;
  model?: string;
  specifications?: Record<string, any>;
  confidence: number;
  location?: string;
  relationships?: string[];
}

export interface DocumentQuality {
  score: number;
  completeness: number;
  clarity: number;
  issues: string[];
  suggestions: string[];
}

export interface Recommendation {
  type: 'warning' | 'suggestion' | 'requirement';
  message: string;
  severity: 'low' | 'medium' | 'high';
  affectedComponents?: string[];
}

export interface ValidationResult {
  field: string;
  valid: boolean;
  message?: string;
  suggestion?: string;
}

// Workflow Integration
export interface WaitNodeData {
  nodeId: string;
  nodeName: string;
  executionId: string;
  resumeUrl: string;
  waitType: 'approval' | 'input' | 'confirmation';
  requiredData?: WaitNodeRequirements;
  displayData?: WaitNodeDisplay;
  timeoutAt?: string;
}

export interface WaitNodeRequirements {
  action: string[];  // e.g., ['approve', 'reject', 'modify']
  fields?: WaitNodeField[];
  validation?: Record<string, any>;
}

export interface WaitNodeField {
  name: string;
  type: 'text' | 'boolean' | 'number' | 'select' | 'textarea';
  label: string;
  required: boolean;
  options?: string[];
  defaultValue?: any;
  validation?: any;
}

export interface WaitNodeDisplay {
  title: string;
  description?: string;
  data: Record<string, any>;
  actions: WaitNodeAction[];
}

export interface WaitNodeAction {
  id: string;
  label: string;
  type: 'primary' | 'secondary' | 'danger';
  payload: Record<string, any>;
  requiresInput?: boolean;
  inputFields?: WaitNodeField[];
}

// BOG Generation
export interface BOGFile {
  id: string;
  bogId: string;
  sessionId: string;
  filename: string;
  filePath?: string;
  downloadUrl?: string;
  content?: BOGContent;
  createdAt: string;
  metadata: BOGMetadata;
}

export interface BOGContent {
  format: 'bog' | 'json' | 'xml';
  data: Record<string, any>;
  validation?: ValidationResult[];
}

export interface BOGMetadata {
  version?: string;
  generatedBy?: string;
  components?: number;
  points?: number;
  status?: 'draft' | 'final' | 'approved';
  [key: string]: any;
}

// UI Components for Rich Messages
export interface UIComponent {
  type: 'card' | 'button' | 'progress' | 'alert' | 'form' | 'chart' | 'table';
  props: Record<string, any>;
  children?: UIComponent[];
  actions?: ComponentAction[];
}

export interface ComponentAction {
  type: 'click' | 'submit' | 'change';
  handler: string;
  payload?: any;
}

// Workflow Events (SSE/WebSocket)
export interface WorkflowEvent {
  type: WorkflowEventType;
  sessionId: string;
  timestamp: string;
  data: any;
}

export enum WorkflowEventType {
  STARTED = 'workflow_started',
  NODE_STARTED = 'node_started',
  NODE_COMPLETED = 'node_completed',
  WAITING = 'waiting',
  RESUMED = 'resumed',
  COMPLETED = 'workflow_completed',
  ERROR = 'workflow_error',
  MESSAGE = 'message',
  ANALYSIS_UPDATE = 'analysis_update',
  BOG_GENERATED = 'bog_generated'
}

// API Request/Response Types
export interface SessionCreateRequest {
  name: string;
  metadata?: Record<string, any>;
}

export interface SessionResponse {
  session: Session;
  messages: Message[];
  files: FileReference[];
  analysis?: AnalysisData;
  bogFiles?: BOGFile[];
}

export interface FileUploadRequest {
  sessionId: string;
  files: File[];
  message?: string;
  metadata?: Record<string, any>;
}

export interface ChatMessageRequest {
  sessionId: string;
  message: string;
  includeContext?: boolean;
}

export interface AnalysisRequest {
  sessionId: string;
  text?: string;
  extractedText?: string;
  files?: string[];  // file IDs
  conversationHistory?: Message[];
}

export interface ApprovalRequest {
  sessionId: string;
  action: 'approve' | 'reject' | 'modify';
  feedback?: string;
  modifications?: Record<string, any>;
  resumeUrl?: string;
}

export interface StreamResponse {
  type: 'chunk' | 'complete' | 'error';
  data: any;
  done: boolean;
}

// WebSocket Message Types
export interface WSMessage {
  type: WSMessageType;
  sessionId: string;
  data: any;
}

export enum WSMessageType {
  CONNECT = 'connect',
  DISCONNECT = 'disconnect',
  MESSAGE = 'message',
  PROGRESS = 'progress',
  STATUS = 'status',
  ERROR = 'error',
  PING = 'ping',
  PONG = 'pong'
}

// Error Handling
export interface APIError {
  code: string;
  message: string;
  details?: Record<string, any>;
  timestamp: string;
  traceId?: string;
}

// Helper Type Guards
export const isAnalysisMessage = (msg: Message): boolean => {
  return (msg.messageCategory === MessageCategory.ANALYSIS || msg.messageType === MessageCategory.ANALYSIS) && !!msg.analysis;
};

export const isWaitingMessage = (msg: Message): boolean => {
  return (msg.messageCategory === MessageCategory.APPROVAL || msg.messageType === MessageCategory.APPROVAL) && !!msg.waitNode;
};

export const requiresUserAction = (msg: Message): boolean => {
  return !!msg.metadata?.requiresAction || !!msg.waitNode;
};

export const isCompleteAnalysis = (analysis?: AnalysisData): boolean => {
  return analysis?.status === AnalysisStatus.COMPLETE || 
         analysis?.status === AnalysisStatus.APPROVED;
};
