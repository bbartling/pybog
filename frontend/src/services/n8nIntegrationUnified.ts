// n8nIntegrationUnified.ts - Unified n8n workflow integration for PyBOG
import { useState, useCallback, useEffect } from 'react';

// Unified response interface for all workflow operations
interface WorkflowResponse {
  status:
    | 'extraction_complete'
    | 'analysis_complete'
    | 'ready_for_review'
    | 'generation_complete'
    | 'complete'
    | 'refinement_requested'
    | 'chat_response'
    | 'ready'
    | 'error';
  sessionId: string;
  message: string;
  extractedText?: string;
  characterCount?: number;
  analysis?: {
    inputs: string[];
    outputs: string[];
    control_blocks?: string[];
    controlBlocks?: string[];
    pseudocode: Array<{ block: string; logic: string[] }>;
    issues: string[];
  };
  actions?: any;
  success?: boolean;
  downloadUrl?: string;
  bogFilePath?: string;
  components?: {
    inputs: number;
    outputs: number;
    logic_blocks: number;
  };
  readyForBOG?: boolean;
  nextStep?: string;
  timestamp?: string;
  capabilities?: string[];
}

interface ChatMessage {
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: string;
  metadata?: any;
}

interface SessionData {
  sessionId: string;
  analysis?: WorkflowResponse['analysis'];
  extractedText?: string;
  isReady: boolean;
  lastUpdate: string;
}

export class UnifiedN8NService {
  private baseUrl: string;
  private n8nUrl: string;
  private analysisWebhookPath: string = '/webhook/pybog-analyze';    // NEW: Analysis workflow
  private approvalWebhookPath: string = '/webhook/pybog-approve';    // NEW: Generation/approval workflow
  private sessionId: string | null = null;
  private chatHistory: ChatMessage[] = [];
  private currentAnalysis: WorkflowResponse['analysis'] | null = null;

  constructor(baseUrl: string = 'http://localhost:8000', n8nUrl: string = 'http://localhost:5678') {
    this.baseUrl = baseUrl;
    this.n8nUrl = n8nUrl;
    this.restoreSession();
  }

  /**
   * Upload and process a document through the unified workflow
   */
  async uploadDocument(file: File): Promise<WorkflowResponse> {
    if (!this.sessionId) {
      this.sessionId = this.generateSessionId();
    }

    try {
      // Create FormData with binary file support
      const formData = new FormData();
      formData.append('files', file);
      formData.append('sessionId', this.sessionId);
      formData.append('message', `Analyze HVAC sequence from: ${file.name}`);
      formData.append('action', 'analyze');

      // Call Analysis Workflow (NEW ENDPOINT)
      const response = await fetch(`${this.n8nUrl}${this.analysisWebhookPath}`, {
        method: 'POST',
        body: formData
      });

      if (!response.ok) {
        throw new Error(`Analysis workflow failed: ${response.statusText}`);
      }

      const data: WorkflowResponse = await response.json();

      if (data.status === 'ready_for_review' && data.analysis) {
        this.currentAnalysis = data.analysis;
        if (data.message) this.addToChat('assistant', data.message);
      }

      this.saveSession(data);
      return data;
    } catch (error) {
      const errorMsg = error instanceof Error ? error.message : 'Unknown error';
      this.addToChat('system', `Error uploading document: ${errorMsg}`);
      throw error;
    }
  }

  /**
   * Send a text message for processing or chat
   */
  async sendMessage(message: string, isHvacSequence: boolean = false): Promise<WorkflowResponse> {
    if (!this.sessionId) {
      this.sessionId = this.generateSessionId();
    }

    this.addToChat('user', message);

    const payload = {
      sessionId: this.sessionId,
      message: message,
      action: isHvacSequence ? 'analyze' : 'chat',
      extractedText: isHvacSequence ? message : ''
    };

    try {
      // Call Analysis Workflow (NEW ENDPOINT)
      const response = await fetch(`${this.n8nUrl}${this.analysisWebhookPath}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (!response.ok) {
        throw new Error(`Analysis workflow failed: ${response.statusText}`);
      }

      const data: WorkflowResponse = await response.json();

      if (data.message) {
        this.addToChat('assistant', data.message);
      }

      if (data.status === 'ready_for_review' && data.analysis) {
        this.currentAnalysis = data.analysis;
        this.saveSession(data);
      }

      return data;
    } catch (error) {
      const errorMsg = error instanceof Error ? error.message : 'Unknown error';
      this.addToChat('system', `Error: ${errorMsg}`);
      throw error;
    }
  }

  /**
   * Approve the current analysis and generate BOG
   */
  async approveAnalysis(): Promise<WorkflowResponse> {
    if (!this.sessionId) {
      throw new Error('No session available');
    }

    const payload = {
      sessionId: this.sessionId,
      action: 'approve'
    };

    try {
      // Call Generation Workflow (NEW ENDPOINT)
      const response = await fetch(`${this.n8nUrl}${this.approvalWebhookPath}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (!response.ok) {
        throw new Error(`Generation workflow failed: ${response.statusText}`);
      }

      const data: WorkflowResponse = await response.json();
      this.addToChat('assistant', data.message || 'BOG generation started...');
      return data;
    } catch (error) {
      const errorMsg = error instanceof Error ? error.message : 'Unknown error';
      this.addToChat('system', `Error: ${errorMsg}`);
      throw error;
    }
  }
  
  /**
   * Request changes to the analysis with feedback
   */
  async requestChanges(feedback: string): Promise<WorkflowResponse> {
    if (!this.sessionId) {
      throw new Error('No session available');
    }

    const payload = {
      sessionId: this.sessionId,
      action: 'refine',
      feedback: feedback
    };

    try {
      // Call Generation Workflow (NEW ENDPOINT)
      const response = await fetch(`${this.n8nUrl}${this.approvalWebhookPath}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (!response.ok) {
        throw new Error(`Refinement workflow failed: ${response.statusText}`);
      }

      const data: WorkflowResponse = await response.json();
      this.addToChat('assistant', data.message || 'Refinement processed...');
      return data;
    } catch (error) {
      const errorMsg = error instanceof Error ? error.message : 'Unknown error';
      this.addToChat('system', `Error: ${errorMsg}`);
      throw error;
    }
  }
  
  /**
   * Analyze extracted text through the unified workflow
   */
  private async analyzeExtractedText(extractedText: string): Promise<WorkflowResponse> {
    const payload = {
      sessionId: this.sessionId,
      action: 'analyze',
      extractedText: extractedText,
      message: 'Analyze HVAC control sequence from uploaded document'
    };

    try {
      const response = await fetch(`${this.n8nUrl}${this.analysisWebhookPath}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload)
      });

      if (!response.ok) {
        throw new Error(`Analysis failed: ${response.statusText}`);
      }

      const data: WorkflowResponse = await response.json();
      
      if (data.status === 'analysis_complete' || data.status === 'ready_for_review') {
        this.currentAnalysis = data.analysis || null;
        this.addToChat('system', 'Analysis complete. Ready to generate BOG file.');
        this.saveSession(data);
      }
      
      return data;
    } catch (error) {
      const errorMsg = error instanceof Error ? error.message : 'Unknown error';
      this.addToChat('system', `Analysis error: ${errorMsg}`);
      throw error;
    }
  }

  /**
   * Generate BOG file from current analysis
   */
  async generateBOG(): Promise<WorkflowResponse> {
    if (!this.sessionId) {
      throw new Error('No session available');
    }

    this.addToChat('user', 'Generate BOG file from analysis');

    const payload = {
      sessionId: this.sessionId,
      action: 'approve'
    };

    try {
      const response = await fetch(`${this.n8nUrl}${this.approvalWebhookPath}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload)
      });

      if (!response.ok) {
        throw new Error(`Generation failed: ${response.statusText}`);
      }

      const data: WorkflowResponse = await response.json();
      
      if (data.status === 'complete' && data.downloadUrl) {
        this.addToChat('system', `BOG file generated successfully! [Download](${data.downloadUrl})`);
        this.saveSession(data);
      }
      
      return data;
    } catch (error) {
      const errorMsg = error instanceof Error ? error.message : 'Unknown error';
      this.addToChat('system', `Generation error: ${errorMsg}`);
      throw error;
    }
  }


  /**
   * Chat history management
   */
  private addToChat(role: ChatMessage['role'], content: string): void {
    this.chatHistory.push({
      role,
      content,
      timestamp: new Date().toISOString(),
      metadata: {
        sessionId: this.sessionId
      }
    });
  }

  getChatHistory(): ChatMessage[] {
    return this.chatHistory;
  }

  clearChatHistory(): void {
    this.chatHistory = [];
  }

  /**
   * Session management
   */
  private generateSessionId(): string {
    return `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  private saveSession(data: WorkflowResponse): void {
    if (!this.sessionId) return;
    
    const sessionData: SessionData = {
      sessionId: this.sessionId,
      analysis: data.analysis,
      extractedText: data.extractedText,
      isReady: data.readyForBOG || false,
      lastUpdate: new Date().toISOString()
    };
    
    localStorage.setItem(`pybog_session_${this.sessionId}`, JSON.stringify(sessionData));
    localStorage.setItem('pybog_current_session', this.sessionId);
  }

  private restoreSession(): void {
    const currentSessionId = localStorage.getItem('pybog_current_session');
    if (currentSessionId) {
      const sessionData = localStorage.getItem(`pybog_session_${currentSessionId}`);
      if (sessionData) {
        try {
          const data: SessionData = JSON.parse(sessionData);
          this.sessionId = data.sessionId;
          this.currentAnalysis = data.analysis || null;
          this.addToChat('system', 'Previous session restored.');
        } catch (e) {
          console.error('Failed to restore session:', e);
        }
      }
    }
  }

  resetSession(): void {
    if (this.sessionId) {
      localStorage.removeItem(`pybog_session_${this.sessionId}`);
    }
    localStorage.removeItem('pybog_current_session');
    
    this.sessionId = null;
    this.chatHistory = [];
    this.currentAnalysis = null;
  }

  getSessionId(): string | null {
    return this.sessionId;
  }

  setSessionId(sessionId: string): void {
    this.sessionId = sessionId;
    this.restoreSession();
  }

  /**
   * Analysis data access
   */
  getCurrentAnalysis(): WorkflowResponse['analysis'] | null {
    return this.currentAnalysis;
  }

  hasAnalysis(): boolean {
    return this.currentAnalysis !== null;
  }

  /**
   * Utility methods
   */
  downloadBOG(downloadUrl: string): void {
    const fullUrl = downloadUrl.startsWith('http') 
      ? downloadUrl 
      : `${this.baseUrl}${downloadUrl}`;
    
    window.open(fullUrl, '_blank');
  }
}

// Export singleton instance
export const unifiedN8nService = new UnifiedN8NService();

// React hook for using the unified service
export function useUnifiedN8N() {
  const [isProcessing, setIsProcessing] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [chatHistory, setChatHistory] = useState<ChatMessage[]>([]);
  const [currentAnalysis, setCurrentAnalysis] = useState<any>(null);
  const [readyForBOG, setReadyForBOG] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // Initialize from service
    setSessionId(unifiedN8nService.getSessionId());
    setChatHistory(unifiedN8nService.getChatHistory());
    setCurrentAnalysis(unifiedN8nService.getCurrentAnalysis());
    setReadyForBOG(unifiedN8nService.hasAnalysis());
  }, []);

  const uploadDocument = useCallback(async (file: File) => {
    setIsProcessing(true);
    setError(null);
    try {
      const result = await unifiedN8nService.uploadDocument(file);
      setSessionId(unifiedN8nService.getSessionId());
      setChatHistory(unifiedN8nService.getChatHistory());
      
      if (result.analysis) {
        setCurrentAnalysis(result.analysis);
        setReadyForBOG(true);
      }
      
      return result;
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Upload failed';
      setError(errorMsg);
      throw err;
    } finally {
      setIsProcessing(false);
    }
  }, []);

  const sendMessage = useCallback(async (message: string, isHvacSequence = false) => {
    setIsProcessing(true);
    setError(null);
    try {
      const result = await unifiedN8nService.sendMessage(message, isHvacSequence);
      setChatHistory(unifiedN8nService.getChatHistory());
      
      if (result.analysis) {
        setCurrentAnalysis(result.analysis);
        setReadyForBOG(true);
      }
      
      return result;
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Message failed';
      setError(errorMsg);
      throw err;
    } finally {
      setIsProcessing(false);
    }
  }, []);

  const generateBOG = useCallback(async () => {
    setIsProcessing(true);
    setError(null);
    try {
      const result = await unifiedN8nService.generateBOG();
      setChatHistory(unifiedN8nService.getChatHistory());
      return result;
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Generation failed';
      setError(errorMsg);
      throw err;
    } finally {
      setIsProcessing(false);
    }
  }, []);

  const resetSession = useCallback(() => {
    unifiedN8nService.resetSession();
    setSessionId(null);
    setChatHistory([]);
    setCurrentAnalysis(null);
    setReadyForBOG(false);
    setError(null);
  }, []);

  return {
    isProcessing,
    sessionId,
    chatHistory,
    currentAnalysis,
    readyForBOG,
    error,
    uploadDocument,
    sendMessage,
    generateBOG,
    resetSession,
    approveAnalysis: unifiedN8nService.approveAnalysis.bind(unifiedN8nService),
    downloadBOG: unifiedN8nService.downloadBOG.bind(unifiedN8nService)
  };
}
