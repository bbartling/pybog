// n8nIntegration.ts - Complete n8n workflow integration for PyBOG
import { useState, useCallback, useEffect } from 'react';

interface UploadResponse {
  success: boolean;
  session_id: string;
  file_name: string;
  extraction_results?: any;
  message: string;
}

interface ChatResponse {
  success: boolean;
  response: string;
  ready_to_generate: boolean;
  missing_information?: string[];
  session_id: string;
}

interface GenerationResponse {
  success: boolean;
  download_url: string;
  bog_file_path: string;
  components: {
    inputs: number;
    outputs: number;
    logic_blocks: number;
  };
}

export class N8NIntegrationService {
  private baseUrl: string;
  private sessionId: string | null = null;

  constructor(baseUrl: string = 'http://localhost:5678') {
    this.baseUrl = baseUrl;
  }

  /**
   * Upload and process HVAC document
   */
  async uploadDocument(file: File): Promise<UploadResponse> {
    try {
      const formData = new FormData();
      formData.append('file', file);
      
      // Generate or use existing session ID
      if (!this.sessionId) {
        this.sessionId = `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
      }
      formData.append('session_id', this.sessionId);

      const response = await fetch(`${this.baseUrl}/webhook/document-upload`, {
        method: 'POST',
        body: formData
      });

      if (!response.ok) {
        throw new Error(`Upload failed: ${response.statusText}`);
      }

      const data = await response.json();
      return {
        success: true,
        session_id: this.sessionId,
        file_name: file.name,
        extraction_results: data.extraction_results,
        message: 'Document uploaded and processed successfully'
      };
    } catch (error) {
      console.error('Document upload error:', error);
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      return {
        success: false,
        session_id: this.sessionId || '',
        file_name: file.name,
        message: `Upload failed: ${errorMessage}`
      };
    }
  }

  /**
   * Send chat message for conversation
   */
  async sendChatMessage(message: string): Promise<ChatResponse> {
    if (!this.sessionId) {
      throw new Error('No active session. Please upload a document first.');
    }

    try {
      const response = await fetch(`${this.baseUrl}/webhook/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          session_id: this.sessionId,
          message: message,
          timestamp: new Date().toISOString()
        })
      });

      if (!response.ok) {
        throw new Error(`Chat request failed: ${response.statusText}`);
      }

      const data = await response.json();
      return {
        success: true,
        response: data.ai_response || data.message,
        ready_to_generate: data.ready_to_generate || false,
        missing_information: data.missing_information,
        session_id: this.sessionId
      };
    } catch (error) {
      console.error('Chat error:', error);
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      return {
        success: false,
        response: `Chat failed: ${errorMessage}`,
        ready_to_generate: false,
        session_id: this.sessionId
      };
    }
  }

  /**
   * Generate BOG file from extracted data
   */
  async generateBOG(): Promise<GenerationResponse> {
    if (!this.sessionId) {
      throw new Error('No active session. Please upload a document first.');
    }

    try {
      const response = await fetch(`${this.baseUrl}/webhook/generate-bog`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          session_id: this.sessionId,
          request_type: 'generate'
        })
      });

      if (!response.ok) {
        throw new Error(`Generation failed: ${response.statusText}`);
      }

      const data = await response.json();
      return {
        success: true,
        download_url: data.download_url,
        bog_file_path: data.bog_file_path,
        components: data.components || { inputs: 0, outputs: 0, logic_blocks: 0 }
      };
    } catch (error) {
      console.error('BOG generation error:', error);
      throw error;
    }
  }

  /**
   * Get current session status
   */
  async getSessionStatus(): Promise<any> {
    if (!this.sessionId) {
      return { status: 'no_session' };
    }

    try {
      const response = await fetch(`${this.baseUrl}/webhook/session-status`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          session_id: this.sessionId
        })
      });

      if (!response.ok) {
        throw new Error(`Status check failed: ${response.statusText}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Status check error:', error);
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      return { status: 'error', message: errorMessage };
    }
  }

  /**
   * Reset session for new document
   */
  resetSession(): void {
    this.sessionId = null;
  }

  /**
   * Get current session ID
   */
  getSessionId(): string | null {
    return this.sessionId;
  }

  /**
   * Set session ID (for resuming sessions)
   */
  setSessionId(sessionId: string): void {
    this.sessionId = sessionId;
  }

  /**
   * Download generated BOG file
   */
  downloadBOG(downloadUrl: string): void {
    const fullUrl = downloadUrl.startsWith('http') 
      ? downloadUrl 
      : `${this.baseUrl}${downloadUrl}`;
    
    window.open(fullUrl, '_blank');
  }

  /**
   * Get chat interface URL for embedded chat
   */
  getChatInterfaceUrl(): string {
    return `${this.baseUrl}/chat/${this.sessionId || 'new'}`;
  }
}

// Export singleton instance
export const n8nService = new N8NIntegrationService();

export function useN8NIntegration() {
  const [isProcessing, setIsProcessing] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [readyToGenerate, setReadyToGenerate] = useState(false);
  const [extractionResults, setExtractionResults] = useState<any>(null);
  const [chatHistory, setChatHistory] = useState<Array<{role: string, content: string}>>([]);

  useEffect(() => {
    const storedSessionId = n8nService.getSessionId();
    if (storedSessionId) {
      setSessionId(storedSessionId);
    }
  }, []);

  const uploadDocument = useCallback(async (file: File) => {
    setIsProcessing(true);
    try {
      const result = await n8nService.uploadDocument(file);
      if (result.success) {
        setSessionId(result.session_id);
        setExtractionResults(result.extraction_results);
        setChatHistory([{
          role: 'system',
          content: `Document "${result.file_name}" uploaded and processed successfully.`
        }]);
      }
      return result;
    } finally {
      setIsProcessing(false);
    }
  }, []);

  const sendMessage = useCallback(async (message: string) => {
    if (!sessionId) {
      throw new Error('No active session');
    }

    setIsProcessing(true);
    try {
      // Add user message to history
      setChatHistory(prev => [...prev, { role: 'user', content: message }]);
      
      const result = await n8nService.sendChatMessage(message);
      if (result.success) {
        // Add AI response to history
        setChatHistory(prev => [...prev, { role: 'assistant', content: result.response }]);
        setReadyToGenerate(result.ready_to_generate);
      }
      return result;
    } finally {
      setIsProcessing(false);
    }
  }, [sessionId]);

  const generateBOG = useCallback(async () => {
    if (!sessionId) {
      throw new Error('No active session');
    }

    setIsProcessing(true);
    try {
      const result = await n8nService.generateBOG();
      if (result.success) {
        setChatHistory(prev => [...prev, {
          role: 'system',
          content: `BOG file generated successfully! Components: ${result.components.inputs} inputs, ${result.components.outputs} outputs, ${result.components.logic_blocks} logic blocks.`
        }]);
      }
      return result;
    } finally {
      setIsProcessing(false);
    }
  }, [sessionId]);

  const resetSession = useCallback(() => {
    n8nService.resetSession();
    setSessionId(null);
    setReadyToGenerate(false);
    setExtractionResults(null);
    setChatHistory([]);
  }, []);

  return {
    isProcessing,
    sessionId,
    readyToGenerate,
    extractionResults,
    chatHistory,
    uploadDocument,
    sendMessage,
    generateBOG,
    resetSession
  };
}
