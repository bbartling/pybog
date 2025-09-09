// n8n Webhook Service for handling approval workflows
interface WebhookApprovalData {
  sessionId: string;
  extractedText?: string;
  analysis?: any;
  action:
    | 'approve_text'
    | 'edit_text'
    | 'retry_extraction'
    | 'approve_analysis'
    | 'refine_analysis'
    | 'confirm'
    | 'regenerate'
    | 'cancel';
  feedback?: string;
  userAction?: string;
  timestamp?: string;
}

interface WorkflowWaitingResponse {
  resumeUrl: string;
  status: string;
  step: string;
  currentStep?: number;
  totalSteps?: number;
  message: string;
  extractedText?: string;
  totalCharacters?: number;
  fileCount?: number;
  textQuality?: string;
  qualityScore?: number;
  qualityIssues?: string[];
  recommendations?: string[];
  hvacTermsFound?: number;
  analysis?: {
    inputs: string[];
    outputs: string[];
    control_blocks: string[];
    pseudocode: Array<{ block: string; logic: string[]; complexity?: number }>;
    issues: string[];
  };
  analysisQuality?: string;
  summary?: {
    totalInputs: number;
    totalOutputs: number;
    totalBlocks: number;
    totalLogicLines: number;
    issuesFound: number;
    complexity: string;
  };
  actions?: {
    [key: string]: {
      label: string;
      action: string;
      description?: string;
      recommended?: boolean;
      confidence?: number;
      primary?: boolean;
      color?: string;
    };
  };
  progress?: {
    percentage: number;
    phase: string;
    description?: string;
    eta?: string;
  };
  workflowStatus: string;
  interactionType: string;
  capabilities?: {
    canEdit: boolean;
    canCancel: boolean;
    canRetry: boolean;
    canDownload?: boolean;
  };
  timestamp: string;
  downloadUrl?: string;
  bogFilePath?: string;
  // Enhanced: approval type to drive UI
  approvalType?: 'text_review' | 'analysis_review' | 'generation_confirmation';
  data?: any;
}

class N8nWebhookService {
  private baseUrl: string;
  private activeResumeUrls: Map<string, string> = new Map();

  constructor(baseUrl = 'http://localhost:5678') {
    this.baseUrl = baseUrl;
  }

  /**
   * Store resume URL for a session
   */
  storeResumeUrl(sessionId: string, resumeUrl: string): void {
    if (!sessionId || sessionId === 'undefined' || !resumeUrl) {
      console.warn('[N8n Webhook] Skipping storeResumeUrl for invalid sessionId or resumeUrl', { sessionId, resumeUrl });
      return;
    }
    console.log('[N8n Webhook] Storing resume URL for session:', sessionId, resumeUrl);
    this.activeResumeUrls.set(sessionId, resumeUrl);
    // Also store in localStorage for persistence
    try {
      localStorage.setItem(`pybog_resume_${sessionId}`, resumeUrl);
    } catch (e) {
      console.warn('[N8n Webhook] Failed to persist resume URL:', e);
    }
  }

  /**
   * Get stored resume URL for a session
   */
  getResumeUrl(sessionId: string): string | null {
    if (!sessionId || sessionId === 'undefined') return null;
    let url = this.activeResumeUrls.get(sessionId);
    if (!url) {
      // Try to restore from localStorage
      try {
        const stored = localStorage.getItem(`pybog_resume_${sessionId}`);
        if (stored) {
          url = stored;
          this.activeResumeUrls.set(sessionId, url);
        }
      } catch (e) {
        console.warn('[N8n Webhook] Failed to restore resume URL:', e);
      }
    }
    return url || null;
  }

  /**
   * Clear resume URL after use
   */
  clearResumeUrl(sessionId: string): void {
    this.activeResumeUrls.delete(sessionId);
    try {
      localStorage.removeItem(`pybog_resume_${sessionId}`);
    } catch (e) {}
  }

  /**
   * Resume a waiting workflow with approval
   */
  async approveWorkflowStep(
    resumeUrl: string, 
    data: WebhookApprovalData
  ): Promise<any> {
    try {
      console.log('[N8n Webhook] Approving workflow step:', { 
        resumeUrl, 
        action: data.action,
        sessionId: data.sessionId 
      });
      
      // Send directly to the resume URL with proper structure
      const response = await fetch(resumeUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Session-ID': data.sessionId,
          'X-User-Action': data.action,
        },
        body: JSON.stringify({
          // n8n Wait node expects data in 'body' field
          body: {
            sessionId: data.sessionId,
            action: data.action,
            extractedText: data.extractedText,
            analysis: data.analysis,
            feedback: data.feedback,
            userAction: data.userAction,
            timestamp: data.timestamp || new Date().toISOString(),
          }
        }),
      });

      if (!response.ok) {
        throw new Error(`Webhook approval failed: ${response.status} ${response.statusText}`);
      }

      // Parse response robustly. Some n8n Respond to Webhook nodes may return
      // no body (204) or non-JSON content. Avoid throwing "Unexpected end of JSON input".
      let result: any = {};
      try {
        const contentType = response.headers.get('content-type') || '';
        const contentLength = response.headers.get('content-length');
        const isEmpty = response.status === 204 || contentLength === '0';
        if (!isEmpty) {
          if (contentType.includes('application/json')) {
            result = await response.json();
          } else {
            const text = await response.text();
            try {
              result = text ? JSON.parse(text) : {};
            } catch {
              result = { text };
            }
          }
        }
      } catch (e) {
        // Fall back to empty object – upstream may have already resumed without body
        result = {};
      }

      console.log('[N8n Webhook] Approval response:', result);
      
      // Store new resume URL if provided in response
      if (result && result.resumeUrl && data.sessionId) {
        this.storeResumeUrl(data.sessionId, result.resumeUrl);
      }
      
      return result;
    } catch (error) {
      console.error('[N8n Webhook] Approval error:', error);
      throw error;
    }
  }

  /**
   * Approve text extraction and continue to analysis
   */
  async approveTextExtraction(
    sessionId: string,
    extractedText: string,
    resumeUrl?: string
  ) {
    const url = resumeUrl || this.getResumeUrl(sessionId);
    if (!url) {
      throw new Error('No resume URL available for session');
    }

    const response = await this.approveWorkflowStep(url, {
      sessionId,
      extractedText,
      action: 'approve_text',
    });

    // Clear the used resume URL
    this.clearResumeUrl(sessionId);
    
    return response;
  }

  /**
   * Approve analysis and proceed to BOG generation
   */
  async approveAnalysis(
    sessionId: string,
    analysis: any,
    resumeUrl?: string
  ) {
    const url = resumeUrl || this.getResumeUrl(sessionId);
    if (!url) {
      throw new Error('No resume URL available for session');
    }

    const response = await this.approveWorkflowStep(url, {
      sessionId,
      analysis,
      action: 'approve_analysis',
      userAction: 'approve',
    });

    // Do not clear resume URL here; downstream generation may provide a new resume URL we should store on parse
    return response;
  }

  /**
   * Request changes to analysis
   */
  async requestAnalysisChanges(
    sessionId: string,
    analysis: any,
    feedback: string,
    resumeUrl?: string
  ) {
    const url = resumeUrl || this.getResumeUrl(sessionId);
    if (!url) {
      throw new Error('No resume URL available for session');
    }

    return this.approveWorkflowStep(url, {
      sessionId,
      analysis,
      action: 'refine_analysis',
      feedback,
    });
  }

  /**
   * Edit extracted text before analysis
   */
  async editExtractedText(
    sessionId: string,
    extractedText: string,
    resumeUrl?: string
  ) {
    const url = resumeUrl || this.getResumeUrl(sessionId);
    if (!url) {
      throw new Error('No resume URL available for session');
    }

    return this.approveWorkflowStep(url, {
      sessionId,
      extractedText,
      action: 'edit_text',
    });
  }

  /**
   * Retry text extraction
   */
  async retryExtraction(
    sessionId: string,
    resumeUrl?: string
  ) {
    const url = resumeUrl || this.getResumeUrl(sessionId);
    if (!url) {
      throw new Error('No resume URL available for session');
    }

    return this.approveWorkflowStep(url, {
      sessionId,
      action: 'retry_extraction',
      userAction: 'retry',
    });
  }

  /**
   * Confirm, regenerate, or cancel BOG generation in the Generation workflow
   */
  async confirmGeneration(
    sessionId: string,
    action: 'confirm' | 'regenerate' | 'cancel',
    resumeUrl?: string
  ) {
    const url = resumeUrl || this.getResumeUrl(sessionId);
    if (!url) {
      throw new Error('No resume URL available for generation confirmation');
    }

    const result = await this.approveWorkflowStep(url, {
      sessionId,
      action,
      userAction: action,
    });

    // Clear resume URL after confirm or cancel
    if (action === 'confirm' || action === 'cancel') {
      this.clearResumeUrl(sessionId);
    }

    return result;
  }

  /**
   * Parse workflow response to extract relevant data
   */
  parseWorkflowResponse(response: any): WorkflowWaitingResponse | null {
    try {
      // Handle null/undefined gracefully
      if (!response) return null;
      
      // If response is a string, try to parse it
      if (typeof response === 'string') {
        try {
          response = JSON.parse(response);
        } catch {
          return null;
        }
      }
      
      const data = response?.data || response || {};

      // Store resume URL if present
      if (data.resumeUrl && data.sessionId) {
        this.storeResumeUrl(data.sessionId, data.resumeUrl);
      }

      // Normalize step/status so the UI can react reliably even when n8n returns raw items
      // Heuristics:
      // - If a resumeUrl exists and we have extractedText/fullText, treat as initial text review
      // - If analysis/summary present, treat as analysis review
      // - If download/bog info present, treat as generation confirmation/completion
      let computedStep: string | undefined = data.step;
      let computedStatus: string | undefined = data.status;

      const hasResume = Boolean(data.resumeUrl);
      const hasExtracted = Boolean(data.extractedText || data.fullText);
      const hasAnalysis = Boolean(data.analysis || data.analysisData || data.summary);
      const hasArtifact = Boolean(data.downloadUrl || data.bogFilePath);

      if (!computedStep || !computedStatus) {
        if (hasResume && hasExtracted) {
          computedStep = computedStep || 'text_review';
          computedStatus = computedStatus || 'text_extracted';
        } else if (hasResume && hasAnalysis) {
          computedStep = computedStep || 'analysis_review';
          computedStatus = computedStatus || 'analysis_complete';
        } else if (hasResume && hasArtifact) {
          computedStep = computedStep || 'generation_confirmation';
          computedStatus = computedStatus || 'generation_complete';
        } else if (hasResume) {
          // If the upstream returned a chat_ready + resumeUrl (welcome path), DO NOT treat as approval.
          const looksLikeChat = (data.status === 'chat_ready' || data.step === 'welcome' || data.interactionType === 'welcome_chat');
          if (!looksLikeChat) {
            computedStep = computedStep || 'text_review';
            computedStatus = computedStatus || 'awaiting_approval';
          }
        }
      }

      // Detect approval stage
      let approvalType: WorkflowWaitingResponse['approvalType'] | undefined;
      if (computedStep === 'text_review' || computedStatus === 'text_review_required' || computedStatus === 'text_extracted' || data.requiresApproval || (hasResume && !hasAnalysis && !hasArtifact)) {
        approvalType = 'text_review';
      } else if (computedStep === 'analysis_review' || computedStatus === 'analysis_complete' || computedStatus === 'ready_for_review') {
        approvalType = 'analysis_review';
      } else if (computedStep === 'generation_confirmation' || computedStatus === 'generation_complete' || computedStatus === 'awaiting_confirmation') {
        approvalType = 'generation_confirmation';
      }

      return {
        resumeUrl: data.resumeUrl || '',
        status: computedStatus || data.status || 'unknown',
        step: computedStep || data.step || '',
        currentStep: data.currentStep,
        totalSteps: data.totalSteps,
        message: data.message || '',
        extractedText: data.extractedText,
        fullText: data.fullText,
        totalCharacters: data.totalCharacters,
        fileCount: data.fileCount,
        textQuality: data.textQuality,
        qualityScore: data.qualityScore,
        qualityIssues: data.qualityIssues,
        recommendations: data.recommendations,
        hvacTermsFound: data.hvacTermsFound,
        analysis: data.analysis || data.analysisData,
        analysisQuality: data.analysisQuality,
        summary: data.summary,
        actions: data.actions,
        progress: data.progress,
        workflowStatus: data.workflowStatus || data.status,
        interactionType: data.interactionType,
        capabilities: data.capabilities,
        timestamp: data.timestamp || new Date().toISOString(),
        approvalType,
        data: data.data,
        downloadUrl: data.downloadUrl,
        bogFilePath: data.bogFilePath,
      };
    } catch (error) {
      console.error('[N8n Webhook] Failed to parse response:', error);
      return null;
    }
  }

  /**
   * Check if a session has a pending approval
   */
  hasPendingApproval(sessionId: string): boolean {
    return this.getResumeUrl(sessionId) !== null;
  }

  /**
   * Get all sessions with pending approvals
   */
  getPendingSessions(): string[] {
    const sessions: string[] = [];
    
    // Check memory
    this.activeResumeUrls.forEach((_, sessionId) => {
      sessions.push(sessionId);
    });
    
    // Check localStorage
    try {
      for (let i = 0; i < localStorage.length; i++) {
        const key = localStorage.key(i);
        // Ensure key is a string before calling .replace()
        if (key && typeof key === 'string' && key.startsWith('pybog_resume_')) {
          const sessionId = key.replace('pybog_resume_', '');
          if (sessionId && !sessions.includes(sessionId)) {
            sessions.push(sessionId);
          }
        }
      }
    } catch (e) {}
    
    return sessions;
  }

  /**
   * Clear all stored resume URLs (cleanup)
   */
  clearAllResumeUrls(): void {
    this.activeResumeUrls.clear();
    try {
      const keysToRemove: string[] = [];
      for (let i = 0; i < localStorage.length; i++) {
        const key = localStorage.key(i);
        // Ensure key is a string before calling .startsWith()
        if (key && typeof key === 'string' && key.startsWith('pybog_resume_')) {
          keysToRemove.push(key);
        }
      }
      keysToRemove.forEach(key => localStorage.removeItem(key));
    } catch (e) {}
  }
}

const n8nWebhookService = new N8nWebhookService();
export default n8nWebhookService;
export type { WebhookApprovalData, WorkflowWaitingResponse };
