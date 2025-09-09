/**
 * Workflow API Service
 * Handles all interactions with n8n workflows through the backend API
 */

import { 
  ApprovalRequest,
  FileUploadRequest,
  ChatMessageRequest,
  StreamResponse,
  WorkflowEvent,
  Session,
  Message
} from '../types/unified';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

class WorkflowAPI {
  private baseUrl: string;
  private eventSources: Map<string, EventSource> = new Map();

  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = baseUrl;
  }

  // --- Internal: robust JSON parsing to avoid "Unexpected end of JSON input" ---
  private async parseJsonSafe(response: Response): Promise<any> {
    try {
      const ct = response.headers.get('content-type') || '';
      const cl = response.headers.get('content-length');
      const isEmpty = response.status === 204 || cl === '0';
      if (isEmpty) return {};
      if (ct.includes('application/json')) {
        return await response.json();
      }
      const text = await response.text();
      if (!text) return {};
      try {
        return JSON.parse(text);
      } catch {
        return { text };
      }
    } catch {
      return {};
    }
  }

  // ==================== Document Ingestion ====================

  async uploadDocuments(sessionId: string, files: File[], message?: string): Promise<any> {
    const formData = new FormData();
    formData.append('session_id', sessionId);
    
    files.forEach((file, index) => {
      formData.append('files', file);
    });
    
    if (message) {
      formData.append('message', message);
    }

    const response = await fetch(`${this.baseUrl}/api/workflow/ingest/documents`, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to upload documents');
    }

    return response.json();
  }

  // ==================== Chat Interaction ====================

  async sendChatMessage(request: ChatMessageRequest): Promise<any> {
    // Route ALL text-only messages through the unified analyze webhook proxy.
    // n8n Analysis workflow (pybog-analyze) routes chat/welcome paths internally.
    const response = await fetch(`${this.baseUrl}/api/workflow/webhook/pybog-analyze`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ sessionId: request.sessionId, message: request.message }),
    });

    if (!response.ok) {
      // Try to parse JSON; fallback to text
      let detail = 'Failed to send message';
      try { const err = await this.parseJsonSafe(response); detail = err?.detail || err?.message || detail; } catch {}
      throw new Error(detail);
    }

    return this.parseJsonSafe(response);
  }

  // ==================== Approval Handling ====================

  async handleApproval(request: ApprovalRequest | (ApprovalRequest & { action: string })): Promise<any> {
    const response = await fetch(`${this.baseUrl}/api/workflow/approve`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to process approval');
    }

    return response.json();
  }

  // ==================== Workflow Status ====================

  async getWorkflowStatus(sessionId: string): Promise<any> {
    const response = await fetch(`${this.baseUrl}/api/workflow/status/${sessionId}`, {
      method: 'GET',
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to get workflow status');
    }

    return response.json();
  }

  // ==================== Analysis ====================

  async triggerAnalysis(sessionId: string): Promise<any> {
    const response = await fetch(`${this.baseUrl}/api/workflow/analyze`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ session_id: sessionId }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to trigger analysis');
    }

    return response.json();
  }

  // ==================== BOG Generation ====================

  async generateBOG(sessionId: string): Promise<any> {
    const response = await fetch(`${this.baseUrl}/api/workflow/generate-bog`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ session_id: sessionId }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to generate BOG');
    }

    return response.json();
  }

  // ==================== SSE Event Streaming ====================

  subscribeToWorkflowEvents(
    sessionId: string,
    onEvent: (event: WorkflowEvent) => void,
    onError?: (error: Error) => void
  ): () => void {
    // Close existing connection if any
    this.unsubscribeFromWorkflowEvents(sessionId);

    const eventSource = new EventSource(`${this.baseUrl}/api/workflow/events/${sessionId}`);
    
    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        onEvent(data as WorkflowEvent);
      } catch (error) {
        console.error('Failed to parse SSE event:', error);
      }
    };

    eventSource.addEventListener('connected', (event: any) => {
      console.log('Connected to workflow events:', event.data);
    });

    eventSource.addEventListener('workflow_started', (event: any) => {
      try {
        const data = JSON.parse(event.data);
        onEvent({ type: 'workflow_started', ...data } as WorkflowEvent);
      } catch (error) {
        console.error('Failed to parse workflow_started event:', error);
      }
    });

    eventSource.addEventListener('workflow_completed', (event: any) => {
      try {
        const data = JSON.parse(event.data);
        onEvent({ type: 'workflow_completed', ...data } as WorkflowEvent);
      } catch (error) {
        console.error('Failed to parse workflow_completed event:', error);
      }
    });

    eventSource.addEventListener('workflow_error', (event: any) => {
      try {
        const data = JSON.parse(event.data);
        onEvent({ type: 'workflow_error', ...data } as WorkflowEvent);
      } catch (error) {
        console.error('Failed to parse workflow_error event:', error);
      }
    });

    eventSource.addEventListener('message', (event: any) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === 'message') {
          onEvent({ type: 'message', ...data } as WorkflowEvent);
        }
      } catch (error) {
        console.error('Failed to parse message event:', error);
      }
    });

    eventSource.addEventListener('state_changed', (event: any) => {
      try {
        const data = JSON.parse(event.data);
        onEvent({ type: 'state_changed', ...data } as any);
      } catch (error) {
        console.error('Failed to parse state_changed event:', error);
      }
    });

    eventSource.addEventListener('workflow_resumed', (event: any) => {
      try {
        const data = JSON.parse(event.data);
        onEvent({ type: 'workflow_resumed', ...data } as any);
      } catch (error) {
        console.error('Failed to parse workflow_resumed event:', error);
      }
    });

    eventSource.onerror = (error) => {
      console.error('SSE connection error:', error);
      if (onError) {
        onError(new Error('Lost connection to workflow events'));
      }
      // Attempt to reconnect after 5 seconds
      setTimeout(() => {
        if (this.eventSources.has(sessionId)) {
          console.log('Attempting to reconnect to workflow events...');
          this.subscribeToWorkflowEvents(sessionId, onEvent, onError);
        }
      }, 5000);
    };

    this.eventSources.set(sessionId, eventSource);

    // Return cleanup function
    return () => {
      this.unsubscribeFromWorkflowEvents(sessionId);
    };
  }

  unsubscribeFromWorkflowEvents(sessionId: string): void {
    const eventSource = this.eventSources.get(sessionId);
    if (eventSource) {
      eventSource.close();
      this.eventSources.delete(sessionId);
      console.log(`Unsubscribed from workflow events for session ${sessionId}`);
    }
  }

  // ==================== Session Management ====================

  async getSession(sessionId: string): Promise<Session> {
    const response = await fetch(`${this.baseUrl}/api/sessions/${sessionId}`, {
      method: 'GET',
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to get session');
    }

    return response.json();
  }

  async getSessionMessages(sessionId: string, limit: number = 50): Promise<Message[]> {
    const response = await fetch(`${this.baseUrl}/api/sessions/${sessionId}/messages?limit=${limit}`, {
      method: 'GET',
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to get messages');
    }

    return response.json();
  }

  // ==================== Utility Methods ====================

  async streamToArray<T>(
    stream: ReadableStream<Uint8Array>,
    onChunk?: (chunk: T) => void
  ): Promise<T[]> {
    const reader = stream.getReader();
    const decoder = new TextDecoder();
    const results: T[] = [];
    let buffer = '';

    try {
      while (true) {
        const { done, value } = await reader.read();
        
        if (done) break;
        
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';
        
        for (const line of lines) {
          if (line.trim()) {
            try {
              const data = JSON.parse(line) as T;
              results.push(data);
              onChunk?.(data);
            } catch (e) {
              console.error('Failed to parse streaming data:', e);
            }
          }
        }
      }
      
      // Process any remaining buffer
      if (buffer.trim()) {
        try {
          const data = JSON.parse(buffer) as T;
          results.push(data);
          onChunk?.(data);
        } catch (e) {
          console.error('Failed to parse final buffer:', e);
        }
      }
    } finally {
      reader.releaseLock();
    }
    
    return results;
  }

  // ==================== Direct N8N Webhook Proxy ====================

  async callN8NWebhook(webhookPath: string, data: any): Promise<any> {
    const response = await fetch(`${this.baseUrl}/api/workflow/webhook/${webhookPath}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data),
    });

    if (!response.ok) {
      const error = await this.parseJsonSafe(response);
      throw new Error(error.detail || error.message || 'Webhook call failed');
    }

    return this.parseJsonSafe(response);
  }
}

// Export singleton instance
export const workflowAPI = new WorkflowAPI();
