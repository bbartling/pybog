// Session Persistence Service
// Handles saving and restoring chat sessions including workflow wait states

import { ChatMessage } from '../components/ChatCanvasGrid';
import enhancedApiService from './apiServiceEnhanced';
import n8nWebhookService from './n8nWebhookService';

export interface PersistedSession {
  id: string;
  name: string;
  createdAt: Date;
  messages: ChatMessage[];
  currentAnalysis: any | null;
  analysisMessageId?: string;
  workflowState?: {
    state: 'idle' | 'analyzing' | 'awaiting_approval' | 'generating' | 'complete';
    resumeUrl?: string;
    waitingData?: any;
  };
}

class SessionPersistenceService {
  private readonly SESSION_KEY_PREFIX = 'pybog_session_';
  private readonly ACTIVE_SESSION_KEY = 'pybog_active_session';
  private readonly WORKFLOW_STATE_KEY_PREFIX = 'pybog_workflow_state_';

  /**
   * Save session to localStorage and database
   */
  async saveSession(session: PersistedSession): Promise<void> {
    // Don't save if session ID is undefined or invalid
    if (!session.id || session.id === 'undefined') {
      console.warn('[SessionPersistence] Skipping save for invalid session ID:', session.id);
      return;
    }
    
    try {
      // Save to localStorage for immediate recovery
      const sessionKey = `${this.SESSION_KEY_PREFIX}${session.id}`;
      
      // Ensure createdAt is a valid Date
      const createdAt = session.createdAt instanceof Date && !isNaN(session.createdAt.getTime())
        ? session.createdAt
        : new Date();
      
      const sessionData = {
        ...session,
        messages: session.messages.slice(-100), // Keep last 100 messages in localStorage
        createdAt: createdAt.toISOString(),
      };
      localStorage.setItem(sessionKey, JSON.stringify(sessionData));

      // Save workflow state separately if exists
      if (session.workflowState) {
        const workflowKey = `${this.WORKFLOW_STATE_KEY_PREFIX}${session.id}`;
        localStorage.setItem(workflowKey, JSON.stringify(session.workflowState));
      }

      // Persist messages to database
      for (const message of session.messages) {
        if (!message.persisted) {
          try {
            await enhancedApiService.persistMessage(session.id, {
              message_id: message.id,
              type: message.type,
              content: message.content,
              metadata: {
                ...message.metadata,
                workflowState: session.workflowState,
              },
              session_state: session.workflowState?.state || 'idle',
            });
            message.persisted = true;
          } catch (e) {
            console.warn('Failed to persist message:', e);
          }
        }
      }

      console.log('[SessionPersistence] Session saved:', session.id);
    } catch (error) {
      console.error('[SessionPersistence] Failed to save session:', error);
    }
  }

  /**
   * Load session from localStorage or database
   */
  async loadSession(sessionId: string): Promise<PersistedSession | null> {
    try {
      // First try localStorage for quick recovery
      const sessionKey = `${this.SESSION_KEY_PREFIX}${sessionId}`;
      const localData = localStorage.getItem(sessionKey);
      
      if (localData) {
        const parsed = JSON.parse(localData);
        const session: PersistedSession = {
          ...parsed,
          createdAt: new Date(parsed.createdAt),
          messages: parsed.messages || [],
        };

        // Load workflow state if exists
        const workflowKey = `${this.WORKFLOW_STATE_KEY_PREFIX}${sessionId}`;
        const workflowData = localStorage.getItem(workflowKey);
        if (workflowData) {
          session.workflowState = JSON.parse(workflowData);
        }

        // Check for pending resume URL
        const resumeUrl = n8nWebhookService.getResumeUrl(sessionId);
        if (resumeUrl && session.workflowState) {
          session.workflowState.resumeUrl = resumeUrl;
        }

        console.log('[SessionPersistence] Loaded session from localStorage:', sessionId);
        return session;
      }

      // Fallback to database
      const fullSession = await enhancedApiService.getFullSession(sessionId);
      if (fullSession && fullSession.messages) {
        const messages: ChatMessage[] = fullSession.messages.map((m: any) => ({
          id: m.message_id,
          type: m.type || 'system',
          content: String(m.content || ''),
          timestamp: new Date(m.timestamp || m.created_at || Date.now()),
          sessionId: sessionId,
          metadata: m.metadata || undefined,
          persisted: true,
        }));

        const session: PersistedSession = {
          id: sessionId,
          name: fullSession.session?.name || 'Restored Session',
          createdAt: new Date(fullSession.session?.created_at || Date.now()),
          messages,
          currentAnalysis: fullSession.analysis?.data || null,
          analysisMessageId: undefined,
        };

        // Extract workflow state from metadata if present
        const lastMessage = messages[messages.length - 1];
        if (lastMessage?.metadata?.workflowState) {
          session.workflowState = lastMessage.metadata.workflowState;
        }

        // Check for pending resume URL
        const resumeUrl = n8nWebhookService.getResumeUrl(sessionId);
        if (resumeUrl) {
          session.workflowState = {
            state: 'awaiting_approval',
            resumeUrl,
            ...(session.workflowState || {}),
          };
        }

        console.log('[SessionPersistence] Loaded session from database:', sessionId);
        this.saveSession(session); // Cache in localStorage
        return session;
      }

      return null;
    } catch (error) {
      console.error('[SessionPersistence] Failed to load session:', error);
      return null;
    }
  }

  /**
   * Get all session IDs from localStorage
   */
  getLocalSessionIds(): string[] {
    const sessionIds: string[] = [];
    try {
      for (let i = 0; i < localStorage.length; i++) {
        const key = localStorage.key(i);
        if (key && key.startsWith(this.SESSION_KEY_PREFIX)) {
          const id = key.replace(this.SESSION_KEY_PREFIX, '');
          sessionIds.push(id);
        }
      }
    } catch (e) {
      console.warn('[SessionPersistence] Failed to get local sessions:', e);
    }
    return sessionIds;
  }

  /**
   * Save active session ID
   */
  saveActiveSessionId(sessionId: string): void {
    try {
      localStorage.setItem(this.ACTIVE_SESSION_KEY, sessionId);
    } catch (e) {
      console.warn('[SessionPersistence] Failed to save active session:', e);
    }
  }

  /**
   * Get active session ID
   */
  getActiveSessionId(): string | null {
    try {
      return localStorage.getItem(this.ACTIVE_SESSION_KEY);
    } catch (e) {
      return null;
    }
  }

  /**
   * Clear session from localStorage
   */
  clearLocalSession(sessionId: string): void {
    try {
      localStorage.removeItem(`${this.SESSION_KEY_PREFIX}${sessionId}`);
      localStorage.removeItem(`${this.WORKFLOW_STATE_KEY_PREFIX}${sessionId}`);
      n8nWebhookService.clearResumeUrl(sessionId);
    } catch (e) {
      console.warn('[SessionPersistence] Failed to clear session:', e);
    }
  }

  /**
   * Clear session (alias for clearLocalSession for backwards compatibility)
   */
  clearSession(sessionId: string): void {
    this.clearLocalSession(sessionId);
  }

  /**
   * Clear all local sessions
   */
  clearAllLocalSessions(): void {
    const sessionIds = this.getLocalSessionIds();
    sessionIds.forEach(id => this.clearLocalSession(id));
    try {
      localStorage.removeItem(this.ACTIVE_SESSION_KEY);
    } catch (e) {}
  }

  /**
   * Restore all sessions from localStorage and database
   */
  async restoreAllSessions(): Promise<Map<string, PersistedSession>> {
    const sessions = new Map<string, PersistedSession>();

    // First load from localStorage
    const localIds = this.getLocalSessionIds();
    for (const id of localIds) {
      const session = await this.loadSession(id);
      if (session) {
        sessions.set(id, session);
      }
    }

    // Then check database for recent sessions not in localStorage
    try {
      const recent = await enhancedApiService.getRecentSessions(10);
      if (recent.sessions) {
        for (const dbSession of recent.sessions) {
          if (!sessions.has(dbSession.session_id)) {
            const fullSession = await this.loadSession(dbSession.session_id);
            if (fullSession) {
              sessions.set(dbSession.session_id, fullSession);
            }
          }
        }
      }
    } catch (e) {
      console.warn('[SessionPersistence] Failed to load from database:', e);
    }

    // Check for any sessions with pending workflow approvals
    const pendingSessions = n8nWebhookService.getPendingSessions();
    for (const pendingId of pendingSessions) {
      if (sessions.has(pendingId)) {
        const session = sessions.get(pendingId)!;
        if (!session.workflowState || session.workflowState.state !== 'awaiting_approval') {
          session.workflowState = {
            state: 'awaiting_approval',
            resumeUrl: n8nWebhookService.getResumeUrl(pendingId) || undefined,
          };
        }
      }
    }

    console.log('[SessionPersistence] Restored sessions:', sessions.size);
    return sessions;
  }

  /**
   * Auto-save session periodically
   */
  startAutoSave(
    getSession: () => PersistedSession | null, 
    intervalMs = 30000
  ): () => void {
    const interval = setInterval(() => {
      const session = getSession();
      if (session) {
        this.saveSession(session);
      }
    }, intervalMs);

    return () => clearInterval(interval);
  }
}

const sessionPersistenceService = new SessionPersistenceService();
export default sessionPersistenceService;
