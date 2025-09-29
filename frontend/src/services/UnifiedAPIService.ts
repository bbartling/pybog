/**
 * Unified API Service for PyBOG Frontend
 * Single FastAPI backend integration for all operations
 */

export interface FileUploadResponse {
  file_id: number;
  filename: string;
  file_size: number;
  mime_type: string;
  state: 'queued' | 'processing' | 'complete' | 'failed';
  session_id: string;
}

export interface AnalysisRequest {
  session_id: string;
  file_id: number;
  options?: Record<string, any>;
}

export interface AnalysisResponse {
  analysis_id: number;
  session_id: string;
  state: 'queued' | 'processing' | 'finalizing' | 'complete' | 'failed';
  file_id: number;
}

export interface BOGGenerationRequest {
  session_id: string;
  analysis_id: number;
  filename?: string;
}

export interface BOGGenerationResponse {
  file_id: number;
  filename: string;
  analysis_id: number;
  session_id: string;
}

export interface SessionData {
  session_id: string;
  name: string;
  metadata: Record<string, any>;
  created_at: string;
  updated_at: string;
}

export interface ChatMessageRequest {
  session_id: string;
  message: string;
}

export interface FileMetadata {
  id: number;
  session_id: string;
  filename: string;
  original_name: string;
  mime_type: string;
  file_type: 'upload' | 'bog' | 'analysis' | 'document';
  file_size: number;
  state: 'queued' | 'processing' | 'finalizing' | 'complete' | 'failed';
  created_at: string;
}

export interface AnalysisResult {
  id: number;
  session_id: string;
  input_file_id: number;
  bog_file_id?: number;
  state: 'queued' | 'processing' | 'finalizing' | 'complete' | 'failed';
  analysis_data: {
    io_points: Array<{
      name: string;
      type: 'input' | 'output';
      data_type: 'boolean' | 'numeric' | 'string';
      units?: string;
      description: string;
    }>;
    control_blocks: Array<{
      name: string;
      type: string;
      description: string;
      logic: string[];
      complexity: number;
    }>;
    pseudocode: Array<{
      step: number;
      description: string;
      code: string;
    }>;
    quality_score: number;
    issues: string[];
    metadata: {
      document_type: string;
      confidence: number;
      recommendations: string[];
    };
  };
  error_message?: string;
  created_at: string;
  completed_at?: string;
}

class UnifiedAPIService {
  private readonly baseUrl: string;

  constructor() {
    // Use runtime config if available, fallback to build-time env vars
    const runtimeConfig = (window as any).RUNTIME_CONFIG;
    this.baseUrl = runtimeConfig?.API_URL || process.env.REACT_APP_API_URL || 'http://localhost:8847';
    console.log('[UnifiedAPIService] Configured API URL:', this.baseUrl);
  }

  // Health check
  async healthCheck(): Promise<{ status: string; timestamp: string }> {
    const response = await fetch(`${this.baseUrl}/api/health`);
    if (!response.ok) {
      throw new Error(`Health check failed: ${response.status}`);
    }
    return response.json();
  }

  // Session Management
  async createSession(name?: string): Promise<SessionData> {
    const response = await fetch(`${this.baseUrl}/api/sessions`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name: name || 'New PyBOG Session',
        metadata: {}
      })
    });

    if (!response.ok) {
      throw new Error(`Failed to create session: ${response.status}`);
    }

    return response.json();
  }

  async getSession(sessionId: string): Promise<SessionData> {
    const response = await fetch(`${this.baseUrl}/api/sessions/${sessionId}`);
    
    if (!response.ok) {
      throw new Error(`Failed to get session: ${response.status}`);
    }

    return response.json();
  }

  async listSessions(): Promise<{ sessions: SessionData[] }> {
    const response = await fetch(`${this.baseUrl}/api/sessions`);
    
    if (!response.ok) {
      throw new Error(`Failed to list sessions: ${response.status}`);
    }

    return response.json();
  }

  async updateSession(sessionId: string, name: string): Promise<SessionData> {
    const response = await fetch(`${this.baseUrl}/api/sessions/${sessionId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name })
    });

    if (!response.ok) {
      throw new Error(`Failed to update session: ${response.status}`);
    }

    return response.json();
  }

  async deleteSession(sessionId: string): Promise<{ success: boolean }> {
    const response = await fetch(`${this.baseUrl}/api/sessions/${sessionId}`, {
      method: 'DELETE'
    });

    if (!response.ok) {
      throw new Error(`Failed to delete session: ${response.status}`);
    }

    return { success: true };
  }

  async getFullSession(sessionId: string): Promise<any> {
    const response = await fetch(`${this.baseUrl}/api/sessions/${sessionId}/full`);
    
    if (!response.ok) {
      throw new Error(`Failed to get full session: ${response.status}`);
    }

    return response.json();
  }

  async getRecentSessions(limit: number = 20): Promise<{ sessions: any[] }> {
    const response = await fetch(`${this.baseUrl}/api/recent-sessions?limit=${limit}`);
    
    if (!response.ok) {
      throw new Error(`Failed to get recent sessions: ${response.status}`);
    }

    return response.json();
  }

  async persistMessage(sessionId: string, messageData: any): Promise<any> {
    const response = await fetch(`${this.baseUrl}/api/sessions/${sessionId}/messages`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(messageData)
    });

    if (!response.ok) {
      throw new Error(`Failed to persist message: ${response.status}`);
    }

    return response.json();
  }

  // File Management
  async uploadFile(sessionId: string, file: File): Promise<FileUploadResponse> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('session_id', sessionId);

    const response = await fetch(`${this.baseUrl}/api/files/upload`, {
      method: 'POST',
      body: formData
    });

    if (!response.ok) {
      throw new Error(`Failed to upload file: ${response.status}`);
    }

    return response.json();
  }

  async getFile(fileId: number): Promise<FileMetadata> {
    const response = await fetch(`${this.baseUrl}/api/files/${fileId}`);
    
    if (!response.ok) {
      throw new Error(`Failed to get file: ${response.status}`);
    }

    return response.json();
  }

  async listSessionFiles(sessionId: string): Promise<{ files: FileMetadata[] }> {
    const response = await fetch(`${this.baseUrl}/api/files?session_id=${sessionId}`);
    
    if (!response.ok) {
      throw new Error(`Failed to list files: ${response.status}`);
    }

    const result = await response.json();
    return { files: result.files || result };
  }

  async downloadFile(fileId: number): Promise<Blob> {
    const response = await fetch(`${this.baseUrl}/api/files/${fileId}/download`);
    
    if (!response.ok) {
      throw new Error(`Failed to download file: ${response.status}`);
    }

    // Handle both blob and JSON responses from backend
    const contentType = response.headers.get('content-type');
    if (contentType && contentType.includes('application/json')) {
      const jsonResponse = await response.json();
      // Convert text content to blob for consistency
      return new Blob([jsonResponse.content || ''], { type: 'text/plain' });
    }
    
    return response.blob();
  }

  // Chat Management
  async sendChatMessage(sessionId: string, message: string): Promise<{ success: boolean }> {
    const response = await fetch(`${this.baseUrl}/api/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: sessionId,
        text: message
      })
    });

    if (!response.ok) {
      throw new Error(`Failed to send chat message: ${response.status}`);
    }

    return response.json();
  }

  async getChatHistory(sessionId: string): Promise<{ messages: any[] }> {
    const response = await fetch(`${this.baseUrl}/api/chat/history/${sessionId}`);
    
    if (!response.ok) {
      throw new Error(`Failed to get chat history: ${response.status}`);
    }

    return response.json();
  }

  async clearChatHistory(sessionId: string): Promise<{ success: boolean }> {
    const response = await fetch(`${this.baseUrl}/api/chat/history/${sessionId}`, {
      method: 'DELETE'
    });

    if (!response.ok) {
      throw new Error(`Failed to clear chat history: ${response.status}`);
    }

    return response.json();
  }

  async getHVACGuidance(sessionId: string, context: Record<string, any>): Promise<{ guidance: string }> {
    const response = await fetch(`${this.baseUrl}/api/chat/guidance`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: sessionId, context })
    });

    if (!response.ok) {
      throw new Error(`Failed to get HVAC guidance: ${response.status}`);
    }

    return response.json();
  }

  async getActiveAgentSessions(): Promise<{ active_sessions: string[] }> {
    const response = await fetch(`${this.baseUrl}/api/agent/sessions`);
    
    if (!response.ok) {
      throw new Error(`Failed to get active agent sessions: ${response.status}`);
    }

    return response.json();
  }

  // Analysis Management
  async analyzeDocumentContent(sessionId: string, content: string, analysisType: string = 'hvac_analysis'): Promise<any> {
    const response = await fetch(`${this.baseUrl}/api/analysis/document`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: sessionId,
        content,
        analysis_type: analysisType
      })
    });

    if (!response.ok) {
      throw new Error(`Failed to analyze document: ${response.status}`);
    }

    return response.json();
  }

  async testAnalysis(sessionId: string, content: string, analysisType?: string): Promise<any> {
    const response = await fetch(`${this.baseUrl}/api/analysis/test`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: sessionId,
        content,
        analysis_type: analysisType || 'hvac_analysis'
      })
    });

    if (!response.ok) {
      throw new Error(`Failed to test analysis: ${response.status}`);
    }

    return response.json();
  }

  // Legacy analysis methods - temporarily disabled in backend
  async startAnalysis(sessionId: string, fileId: number, options?: Record<string, any>): Promise<AnalysisResponse> {
    throw new Error('Analysis functionality temporarily disabled - use analyzeDocumentContent instead');
  }

  async getAnalysisResult(analysisId: number): Promise<AnalysisResult> {
    throw new Error('Analysis functionality temporarily disabled');
  }

  async listSessionAnalyses(sessionId: string): Promise<{ analyses: AnalysisResult[] }> {
    return { analyses: [] };
  }

  async cancelAnalysis(sessionId: string, analysisId?: number): Promise<{ cancelled_count: number }> {
    return { cancelled_count: 0 };
  }

  // Workflow Management
  async getWorkflowStatus(sessionId: string): Promise<any> {
    const response = await fetch(`${this.baseUrl}/api/workflow/status/${sessionId}`);
    
    if (!response.ok) {
      throw new Error(`Failed to get workflow status: ${response.status}`);
    }

    return response.json();
  }

  async submitReview(sessionId: string, reviewId: string, decision: string, feedback?: string, modifiedData?: any): Promise<any> {
    const response = await fetch(`${this.baseUrl}/api/workflow/review/${sessionId}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        review_id: reviewId,
        decision,
        feedback,
        modified_data: modifiedData
      })
    });

    if (!response.ok) {
      throw new Error(`Failed to submit review: ${response.status}`);
    }

    return response.json();
  }

  async resetWorkflow(sessionId: string): Promise<any> {
    const response = await fetch(`${this.baseUrl}/api/workflow/reset/${sessionId}`, {
      method: 'POST'
    });

    if (!response.ok) {
      throw new Error(`Failed to reset workflow: ${response.status}`);
    }

    return response.json();
  }

  async extractTextWithWorkflow(fileId: number, sessionId: string): Promise<any> {
    const formData = new FormData();
    formData.append('session_id', sessionId);

    const response = await fetch(`${this.baseUrl}/api/files/${fileId}/extract-text`, {
      method: 'POST',
      body: formData
    });

    if (!response.ok) {
      throw new Error(`Failed to extract text with workflow: ${response.status}`);
    }

    return response.json();
  }

  async startAnalysisWithWorkflow(sessionId: string, approvedText: string): Promise<any> {
    const response = await fetch(`${this.baseUrl}/api/analysis/start-with-workflow`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: sessionId,
        approved_text: approvedText
      })
    });

    if (!response.ok) {
      throw new Error(`Failed to start analysis with workflow: ${response.status}`);
    }

    return response.json();
  }

  // BOG File Generation
  async generateBOGFile(sessionId: string, analysisId: number, filename?: string): Promise<BOGGenerationResponse> {
    const response = await fetch(`${this.baseUrl}/api/bog`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: sessionId,
        analysis_id: analysisId
      })
    });

    if (!response.ok) {
      throw new Error(`Failed to generate BOG file: ${response.status}`);
    }

    return response.json();
  }

  // Utility Methods
  async fileToText(file: File): Promise<string> {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => {
        if (typeof reader.result === 'string') {
          resolve(reader.result);
        } else {
          reject(new Error('Failed to read file as text'));
        }
      };
      reader.onerror = reject;
      reader.readAsText(file);
    });
  }

  async fileToBase64(file: File): Promise<string> {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => {
        if (typeof reader.result === 'string') {
          // Remove the data URL prefix
          resolve(reader.result.split(',')[1]);
        } else {
          reject(new Error('Failed to read file'));
        }
      };
      reader.onerror = reject;
      reader.readAsDataURL(file);
    });
  }
}

// Export singleton instance
export const unifiedAPIService = new UnifiedAPIService();
export default unifiedAPIService;