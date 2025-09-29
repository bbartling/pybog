/**
 * Chat Service for PyBOG Control Builder
 * Handles chat interactions with the FastAPI backend
 */

// Use runtime config if available, fallback to build-time env vars
const runtimeConfig = (window as any).RUNTIME_CONFIG;
const API_BASE_URL = runtimeConfig?.API_URL || process.env.REACT_APP_API_URL || 'http://localhost:8847';

export interface ChatMessageRequest {
  session_id: string;
  text: string;  // Changed from 'message' to 'text' to match backend
  files?: Array<{
    filename: string;
    mimeType: string;
    content: string;
    size: number;
  }>;
}

export interface ChatResponse {
  success: boolean;
  message: string;
  session_id: string;
}

class ChatService {
  private baseUrl: string;

  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = baseUrl;
  }

  /**
   * Send a chat message to the backend
   */
  async sendMessage(request: ChatMessageRequest): Promise<ChatResponse> {
    try {
      const response = await fetch(`${this.baseUrl}/api/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(request)
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `HTTP ${response.status}: ${response.statusText}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Failed to send chat message:', error);
      throw error;
    }
  }

  /**
   * Get chat history for a session
   */
  async getChatHistory(sessionId: string): Promise<any[]> {
    try {
      const response = await fetch(`${this.baseUrl}/api/chat/history/${sessionId}`, {
        method: 'GET',
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `HTTP ${response.status}: ${response.statusText}`);
      }

      const data = await response.json();
      return data.messages || [];
    } catch (error) {
      console.error('Failed to get chat history:', error);
      throw error;
    }
  }

  /**
   * Health check for chat service
   */
  async healthCheck(): Promise<boolean> {
    try {
      const response = await fetch(`${this.baseUrl}/api/health`);
      return response.ok;
    } catch (error) {
      console.error('Chat service health check failed:', error);
      return false;
    }
  }
}

// Export singleton instance
export const chatService = new ChatService();
export default chatService;