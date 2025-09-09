/**
 * WebSocket Service for Real-time Updates
 * Handles live connections to backend for session updates, analysis progress, etc.
 */

import { ChatMessage } from '../components/ChatCanvasGrid';

export type WebSocketEventType = 
  | 'connected'
  | 'disconnected'
  | 'message'
  | 'state_change'
  | 'analysis_update'
  | 'bog_generated'
  | 'error'
  | 'health_update';

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

  constructor() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    // Derive host from REACT_APP_API_URL safely (strip any path like /api)
    const raw = process.env.REACT_APP_API_URL || 'http://localhost:8000';
    let host = 'localhost:8000';
    try {
      const u = new URL(raw);
      host = u.host; // host:port
    } catch {
      host = raw.replace(/^https?:\/\//, '').replace(/\/$/, '').split('/')[0] || 'localhost:8000';
    }
    this.url = `${protocol}//${host}/ws`;
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

        this.ws.onclose = () => {
          console.log('[WebSocket] Connection closed');
          this.isConnecting = false;
          this.stopHeartbeat();
          this.emit('disconnected', { sessionId: this.sessionId });
          this.attemptReconnect();
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
  }

  /**
   * Handle incoming WebSocket messages
   */
  private handleMessage(data: any): void {
    const { type, ...payload } = data;

    switch (type) {
      case 'state_change':
        console.log('[WebSocket] State change:', payload);
        this.emit('state_change', payload);
        break;

      case 'analysis_update':
        console.log('[WebSocket] Analysis update:', payload);
        this.emit('analysis_update', payload);
        break;

      case 'bog_generated':
        console.log('[WebSocket] BOG generated:', payload);
        this.emit('bog_generated', payload);
        break;

      case 'message':
        console.log('[WebSocket] New message:', payload);
        this.emit('message', payload);
        break;

      case 'process_step':
      case 'analysis_progress':
      case 'status':
      case 'analysis_complete':
      case 'workflow_completed':
        this.emit('message', { type, ...payload });
        break;

      case 'health':
        this.emit('health_update', payload);
        break;

      case 'pong':
        // Heartbeat response
        break;

      default:
        console.log('[WebSocket] Unknown message type:', type, payload);
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
      return;
    }

    if (!this.sessionId) {
      return;
    }

    this.reconnectAttempts++;
    const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);

    console.log(`[WebSocket] Attempting reconnection ${this.reconnectAttempts}/${this.maxReconnectAttempts} in ${delay}ms`);

    setTimeout(() => {
      if (this.sessionId) {
        this.connect(this.sessionId);
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
}

// Export singleton instance
const websocketService = new WebSocketService();
export default websocketService;
