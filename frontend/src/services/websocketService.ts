/**
 * WebSocket Service for Real-time Updates
 * Handles live connections to backend for session updates, analysis progress, etc.
 */

export type WebSocketEventType = 
  | 'connected'
  | 'disconnected'
  | 'message'
  | 'progress'
  | 'chat'
  | 'analysis_complete'
  | 'bog_generated'
  | 'cancellation_complete'
  | 'error'
  | 'health_update'
  | 'text_review_ready'
  | 'analysis_review_ready'
  | 'review_completed'
  | 'workflow_reset'
  | 'workflow_error';

export interface WebSocketEvent {
  type: WebSocketEventType;
  sessionId?: string;
  data?: any;
  timestamp: Date;
}

type EventHandler = (event: WebSocketEvent) => void;

class WebSocketService {
  private ws: WebSocket | null = null;
  private url: string;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 1000;
  private heartbeatInterval: NodeJS.Timeout | null = null;
  private eventHandlers: Map<WebSocketEventType, Set<EventHandler>> = new Map();
  private sessionId: string | null = null;
  private isConnecting = false;
  private connectionTime: number | null = null;

  constructor() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    
    // Use runtime config if available, fallback to build-time env vars
    const runtimeConfig = (window as any).RUNTIME_CONFIG;
    const apiUrl = runtimeConfig?.API_URL || process.env.REACT_APP_API_URL || 'http://localhost:8847';
    const wsUrl = runtimeConfig?.WS_URL;
    
    let host = 'localhost:8847';
    
    if (wsUrl) {
      // Use explicit WebSocket URL from runtime config
      try {
        const u = new URL(wsUrl);
        host = u.host;
      } catch {
        host = wsUrl.replace(/^wss?:\/\//, '').replace(/\/$/, '').split('/')[0] || 'localhost:8847';
      }
    } else {
      // Derive host from API URL
      try {
        const u = new URL(apiUrl);
        host = u.host; // host:port
      } catch {
        host = apiUrl.replace(/^https?:\/\//, '').replace(/\/$/, '').split('/')[0] || 'localhost:8847';
      }
    }
    
    // Updated to match backend WebSocket endpoint structure: /ws/{session_id}
    this.url = `${protocol}//${host}/ws`;
    console.log('[WebSocket] Configured WebSocket URL:', this.url);
  }

  /**
   * Connect to WebSocket server for a specific session
   */
  async connect(sessionId: string): Promise<boolean> {
    if (this.isConnecting) {
      console.log('[WebSocket] Already connecting...');
      return false;
    }

    if (this.ws?.readyState === WebSocket.OPEN) {
      if (this.sessionId === sessionId) {
        console.log('[WebSocket] Already connected to session:', sessionId);
        return true;
      }
      // Disconnect from current session
      this.disconnect();
    }

    this.isConnecting = true;
    this.sessionId = sessionId;

    return new Promise((resolve) => {
      try {
        const wsUrl = `${this.url}/${sessionId}`;
        console.log('[WebSocket] Connecting to:', wsUrl);
        this.ws = new WebSocket(wsUrl);

        this.ws.onopen = () => {
          console.log('[WebSocket] Connected successfully');
          this.isConnecting = false;
          this.reconnectAttempts = 0;
          this.connectionTime = Date.now(); // Track connection time
          this.startHeartbeat();
          this.emit('connected', { sessionId });
          resolve(true);
        };

        this.ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            this.handleMessage(data);
          } catch (error) {
            console.error('[WebSocket] Failed to parse message:', error);
          }
        };

        this.ws.onerror = (error) => {
          console.error('[WebSocket] Error:', error);
          this.isConnecting = false;
          this.emit('error', { error });
          resolve(false);
        };

        this.ws.onclose = (event) => {
          console.log('[WebSocket] Connection closed', { code: event.code, reason: event.reason });
          this.isConnecting = false;
          this.stopHeartbeat();
          this.emit('disconnected', { sessionId: this.sessionId });
          
          // Only attempt reconnect if it wasn't a clean close
          if (event.code !== 1000 && this.sessionId) {
            this.attemptReconnect();
          }
        };

      } catch (error) {
        console.error('[WebSocket] Connection failed:', error);
        this.isConnecting = false;
        resolve(false);
      }
    });
  }

  /**
   * Disconnect from WebSocket server
   */
  disconnect(): void {
    if (this.ws) {
      this.stopHeartbeat();
      this.ws.close();
      this.ws = null;
    }
    this.sessionId = null;
    this.reconnectAttempts = 0;
  }

  /**
   * Send a message through WebSocket
   */
  send(type: string, data: any): boolean {
    if (this.ws?.readyState !== WebSocket.OPEN) {
      console.warn('[WebSocket] Not connected, cannot send message');
      return false;
    }

    try {
      const message = JSON.stringify({
        type,
        sessionId: this.sessionId,
        data,
        timestamp: new Date().toISOString()
      });
      this.ws.send(message);
      return true;
    } catch (error) {
      console.error('[WebSocket] Failed to send message:', error);
      return false;
    }
  }

  /**
   * Subscribe to WebSocket events
   */
  on(eventType: WebSocketEventType, handler: EventHandler): () => void {
    if (!this.eventHandlers.has(eventType)) {
      this.eventHandlers.set(eventType, new Set());
    }
    
    const handlers = this.eventHandlers.get(eventType)!;
    handlers.add(handler);

    // Return unsubscribe function
    return () => {
      handlers.delete(handler);
      if (handlers.size === 0) {
        this.eventHandlers.delete(eventType);
      }
    };
  }

  /**
   * Emit an event to all registered handlers
   */
  private emit(eventType: WebSocketEventType, data?: any): void {
    const event: WebSocketEvent = {
      type: eventType,
      sessionId: this.sessionId || undefined,
      data,
      timestamp: new Date()
    };

    const handlers = this.eventHandlers.get(eventType);
    if (handlers) {
      handlers.forEach(handler => {
        try {
          handler(event);
        } catch (error) {
          console.error('[WebSocket] Handler error:', error);
        }
      });
    }
  }  /**

   * Handle incoming WebSocket messages
   */
  private handleMessage(data: any): void {
    const { type, ...payload } = data;

    switch (type) {
      case 'progress':
        console.log('[WebSocket] Progress update:', payload);
        this.emit('progress', payload);
        break;

      case 'chat':
        console.log('[WebSocket] Chat message:', payload);
        this.emit('chat', payload);
        break;

      case 'analysis_complete':
        console.log('[WebSocket] Analysis complete:', payload);
        this.emit('analysis_complete', payload);
        break;

      case 'bog_generated':
        console.log('[WebSocket] BOG generated:', payload);
        this.emit('bog_generated', payload);
        break;

      case 'cancellation_complete':
        console.log('[WebSocket] Cancellation complete:', payload);
        this.emit('message', { type: 'cancellation', ...payload });
        break;

      case 'error':
        console.log('[WebSocket] Error:', payload);
        this.emit('error', payload);
        break;

      case 'health':
        this.emit('health_update', payload);
        break;

      case 'text_review_ready':
        console.log('[WebSocket] Text review ready:', payload);
        this.emit('text_review_ready', payload);
        break;

      case 'analysis_review_ready':
        console.log('[WebSocket] Analysis review ready:', payload);
        this.emit('analysis_review_ready', payload);
        break;

      case 'review_completed':
        console.log('[WebSocket] Review completed:', payload);
        this.emit('review_completed', payload);
        break;

      case 'workflow_reset':
        console.log('[WebSocket] Workflow reset:', payload);
        this.emit('workflow_reset', payload);
        break;

      case 'workflow_error':
        console.log('[WebSocket] Workflow error:', payload);
        this.emit('workflow_error', payload);
        break;

      case 'pong':
        // Heartbeat response
        break;

      // Legacy support for existing message types
      case 'message':
      case 'process_step':
      case 'analysis_progress':
      case 'status':
      case 'workflow_completed':
        console.log('[WebSocket] Legacy message:', type, payload);
        this.emit('message', { type, ...payload });
        break;

      default:
        console.log('[WebSocket] Unknown message type:', type, payload);
        // Emit as generic message for backward compatibility
        this.emit('message', { type, ...payload });
    }
  }

  /**
   * Start heartbeat to keep connection alive
   */
  private startHeartbeat(): void {
    this.stopHeartbeat();
    this.heartbeatInterval = setInterval(() => {
      if (this.ws?.readyState === WebSocket.OPEN) {
        this.send('ping', {});
      }
    }, 30000); // Ping every 30 seconds
  }

  /**
   * Stop heartbeat
   */
  private stopHeartbeat(): void {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval);
      this.heartbeatInterval = null;
    }
  }

  /**
   * Attempt to reconnect after disconnection
   */
  private attemptReconnect(): void {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.log('[WebSocket] Max reconnection attempts reached');
      this.emit('error', {
        error: 'Max reconnection attempts reached',
        reconnectAttempts: this.reconnectAttempts
      });
      return;
    }

    if (!this.sessionId) {
      return;
    }

    this.reconnectAttempts++;
    const delay = Math.min(this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1), 30000); // Cap at 30 seconds

    console.log(`[WebSocket] Attempting reconnection ${this.reconnectAttempts}/${this.maxReconnectAttempts} in ${delay}ms`);

    // Emit error with current attempt count for UI feedback
    this.emit('error', {
      error: `Reconnecting... (${this.reconnectAttempts}/${this.maxReconnectAttempts})`,
      reconnectAttempts: this.reconnectAttempts
    });

    setTimeout(async () => {
      if (this.sessionId) {
        console.log(`[WebSocket] Executing reconnection attempt ${this.reconnectAttempts}`);
        const connected = await this.connect(this.sessionId);
        if (connected) {
          console.log('[WebSocket] Reconnection successful');
          this.reconnectAttempts = 0; // Reset on successful reconnection
          this.emit('connected', { sessionId: this.sessionId });
        } else {
          console.log('[WebSocket] Reconnection attempt failed, will retry...');
          this.attemptReconnect(); // Recursive retry
        }
      }
    }, delay);
  }

  /**
   * Get connection status
   */
  isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }

  /**
   * Get current session ID
   */
  getCurrentSessionId(): string | null {
    return this.sessionId;
  }

  /**
   * Get connection time for replay event filtering
   */
  getConnectionTime(): number | null {
    return this.connectionTime;
  }
}

// Export singleton instance
const websocketService = new WebSocketService();
export default websocketService;
export {};