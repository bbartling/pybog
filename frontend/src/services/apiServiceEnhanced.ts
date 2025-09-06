// Enhanced API Service with full database persistence
import { ChatMessage } from '../components/ChatCanvasGrid';

const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:8000';

export interface SessionSummary {
  session_id: string;
  name: string;
  state?: string;
  last_activity?: string;
  message_count?: number;
  file_count?: number;
  has_analysis?: boolean;
  has_bog?: boolean;
}

export interface FullSession {
  session: {
    session_id: string;
    name: string;
    state: string;
    created_at?: string;
    last_activity?: string;
  };
  messages: Array<{
    message_id: string;
    type: string;
    content: string;
    timestamp?: string;
    metadata?: any;
  }>;
  files?: Array<{
    file_id: string;
    filename: string;
    file_type?: string;
    file_size?: number;
  }>;
  bog_files?: Array<{
    bog_id: string;
    filename: string;
    download_url?: string;
  }>;
  analysis?: {
    state: string;
    data: any;
    updated_at?: string;
  };
}

class EnhancedApiService {
  // Session Management
  async createSession(name: string = 'New Session'): Promise<{ session_id: string; name: string }> {
    console.log('📦 Creating session in database:', name);
    
    const response = await fetch(`${API_BASE}/api/sessions/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name,
        initial_message: 'PyBOG Control Builder initialized. Upload HVAC documents or describe your control requirements.'
      })
    });

    if (!response.ok) {
      const error = await response.text();
      console.error('❌ Failed to create session:', error);
      throw new Error(`Failed to create session: ${error}`);
    }

    const result = await response.json();
    console.log('✅ Session created:', result);
    return result;
  }

  async getRecentSessions(limit: number = 10): Promise<{ sessions: SessionSummary[] }> {
    console.log('📋 Fetching recent sessions...');
    
    try {
      const response = await fetch(`${API_BASE}/api/recent-sessions?limit=${limit}`);
      
      if (!response.ok) {
        // Log the error but don't throw - return empty list for graceful degradation
        const errorText = await response.text().catch(() => 'Unknown error');
        console.warn('⚠️ Failed to fetch recent sessions:', response.status, errorText);
        return { sessions: [] };
      }

      const result = await response.json();
      console.log(`✅ Found ${result.sessions?.length || 0} recent sessions`);
      return result;
    } catch (error) {
      // Network error or other issue - return empty list
      console.warn('⚠️ Network error fetching sessions:', error);
      return { sessions: [] };
    }
  }

  async getFullSession(sessionId: string): Promise<FullSession> {
    console.log('📖 Loading full session:', sessionId);
    
    const response = await fetch(`${API_BASE}/api/sessions/${sessionId}/full`);
    
    if (!response.ok) {
      const error = await response.text();
      console.error('❌ Failed to load session:', error);
      throw new Error(`Failed to load session: ${error}`);
    }

    const result = await response.json();
    console.log('✅ Session loaded with', result.messages?.length || 0, 'messages');
    return result;
  }

  async persistMessage(sessionId: string, message: {
    message_id: string;
    type: string;
    content: string;
    metadata?: any;
    session_state?: string;
  }): Promise<void> {
    console.log('💾 Persisting message:', message.message_id);
    
    const response = await fetch(`${API_BASE}/api/sessions/${sessionId}/messages`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(message)
    });

    if (!response.ok) {
      const error = await response.text();
      console.error('❌ Failed to persist message:', error);
      throw new Error(`Failed to persist message: ${error}`);
    }

    console.log('✅ Message persisted');
  }

  async uploadFile(sessionId: string, file: File, messageId?: string): Promise<{
    file_id: string;
    filename: string;
    size: number;
  }> {
    console.log('📤 Uploading file:', file.name, 'Size:', file.size);
    
    const formData = new FormData();
    formData.append('file', file);
    if (messageId) {
      formData.append('message_id', messageId);
    }

    const response = await fetch(`${API_BASE}/api/sessions/${sessionId}/upload`, {
      method: 'POST',
      body: formData
    });

    if (!response.ok) {
      const error = await response.text();
      console.error('❌ Failed to upload file:', error);
      throw new Error(`Failed to upload file: ${error}`);
    }

    const result = await response.json();
    console.log('✅ File uploaded:', result);
    return result;
  }

  async deleteSession(sessionId: string): Promise<void> {
    console.log('🗑️ Deleting session:', sessionId);
    
    const response = await fetch(`${API_BASE}/api/sessions/${sessionId}`, {
      method: 'DELETE'
    });

    if (!response.ok) {
      const error = await response.text();
      console.error('❌ Failed to delete session:', error);
      throw new Error(`Failed to delete session: ${error}`);
    }

    console.log('✅ Session deleted');
  }

  async renameSession(sessionId: string, newName: string): Promise<void> {
    console.log('✏️ Renaming session:', sessionId, 'to', newName);
    
    const response = await fetch(`${API_BASE}/api/sessions/${sessionId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: newName })
    });

    if (!response.ok) {
      const error = await response.text();
      console.error('❌ Failed to rename session:', error);
      throw new Error(`Failed to rename session: ${error}`);
    }

    console.log('✅ Session renamed');
  }

  // Analysis & BOG Generation
  async saveAnalysis(sessionId: string, analysisData: any, messageId?: string): Promise<void> {
    console.log('💾 Saving analysis for session:', sessionId);
    
    const response = await fetch(`${API_BASE}/api/sessions/${sessionId}/analysis`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        analysis_data: analysisData,
        message_id: messageId
      })
    });

    if (!response.ok) {
      const error = await response.text();
      console.error('❌ Failed to save analysis:', error);
      throw new Error(`Failed to save analysis: ${error}`);
    }

    console.log('✅ Analysis saved');
  }

  // WebSocket & SSE
  subscribeToSessionEvents(sessionId: string, onMessage: (event: any) => void, onError?: (error: any) => void): EventSource {
    console.log('📡 Subscribing to session events:', sessionId);
    
    const eventSource = new EventSource(`${API_BASE}/api/sessions/${sessionId}/events`);
    
    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        console.log('📨 Event received:', data.type);
        onMessage(data);
      } catch (error) {
        console.error('❌ Failed to parse event:', error);
      }
    };

    eventSource.onerror = (error) => {
      console.error('❌ EventSource error:', error);
      if (onError) onError(error);
    };

    return eventSource;
  }

  // Session polling for state reconciliation
  private pollingIntervals: Map<string, NodeJS.Timeout> = new Map();

  startSessionPolling(sessionId: string, onUpdate: (state: any) => void, interval: number = 5000): string {
    console.log('🔄 Starting session polling:', sessionId);
    
    const pollId = `poll-${sessionId}-${Date.now()}`;
    
    const poll = async () => {
      try {
        const response = await fetch(`${API_BASE}/api/sessions/${sessionId}/state`);
        if (response.ok) {
          const state = await response.json();
          onUpdate(state);
        }
      } catch (error) {
        console.error('Polling error:', error);
      }
    };

    // Initial poll
    poll();
    
    // Set up interval
    const intervalId = setInterval(poll, interval);
    this.pollingIntervals.set(pollId, intervalId);
    
    return pollId;
  }

  stopSessionPolling(pollId: string): void {
    const intervalId = this.pollingIntervals.get(pollId);
    if (intervalId) {
      clearInterval(intervalId);
      this.pollingIntervals.delete(pollId);
      console.log('🛑 Stopped polling:', pollId);
    }
  }

  // Resend failed message
  async resendMessage(sessionId: string, message: ChatMessage): Promise<void> {
    console.log('🔄 Resending message:', message.id);
    
    // Mark message as sending
    const resendMessage = {
      message_id: message.id,
      type: message.type,
      content: message.content,
      metadata: {
        ...message.metadata,
        resent: true,
        original_timestamp: message.timestamp
      }
    };

    await this.persistMessage(sessionId, resendMessage);
    console.log('✅ Message resent');
  }

  // Test connection
  async testConnection(): Promise<boolean> {
    try {
      const response = await fetch(`${API_BASE}/api/health`);
      const isHealthy = response.ok;
      console.log(isHealthy ? '✅ API connection healthy' : '❌ API connection failed');
      return isHealthy;
    } catch (error) {
      console.error('❌ API connection error:', error);
      return false;
    }
  }
}

export const enhancedApiService = new EnhancedApiService();
export default enhancedApiService;
