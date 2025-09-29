// Session Persistence Service
// Handles saving and restoring chat sessions including workflow wait states

import { ChatMessage } from '../types/ChatMessage';
import { unifiedAPIService } from './UnifiedAPIService';

export interface PersistedSession {
  id: string;
  name: string;
  createdAt: Date;
  messages: ChatMessage[];
  currentAnalysis: any | null;
  analysisMessageId?: string;
  workflowState?: {
    state: 'idle' | 'analyzing' | 'awaiting_approval' | 'generating' | 'complete' | 'awaiting_analysis_review';
    resumeUrl?: string;
    waitingData?: any;
  };
}

class SessionPersistenceService {
  private readonly SESSION_KEY_PREFIX = 'pybog_session_';
  private readonly ACTIVE_SESSION_KEY = 'pybog_active_session';
  private readonly WORKFLOW_STATE_KEY_PREFIX = 'pybog_workflow_state_';
  private readonly API_BASE = (process.env.REACT_APP_API_URL || 'http://localhost:8847').replace(/\/$/, '');

  private isValidSessionId(id: string | null | undefined): boolean {
    if (!id) return false;
    const s = String(id).trim();
    // Allow formats like session_1699999999999, session-708587f7, or UUIDs
    const uuid = /^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-5][0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}$/;
    const legacy = /^session_\d{6,}$/;
    const current = /^session-[0-9a-fA-F]{8}$/; // New format: session-708587f7
    return uuid.test(s) || legacy.test(s) || current.test(s);
  }

  /**
   * Remove invalid localStorage keys that can cause ghost sessions
   */
  cleanupInvalidLocalKeys(): string[] {
    const removed: string[] = [];
    try {
      // Remove invalid active session id
      const rawActive = localStorage.getItem(this.ACTIVE_SESSION_KEY);
      if (rawActive && (rawActive === 'undefined' || rawActive === 'null' || rawActive.trim() === '')) {
        localStorage.removeItem(this.ACTIVE_SESSION_KEY);
        removed.push(this.ACTIVE_SESSION_KEY);
      }

      // Collect keys to remove first (don't mutate while iterating)
      const toRemove: string[] = [];
      for (let i = 0; i < localStorage.length; i++) {
        const key = localStorage.key(i) || '';
        if (!key) continue;
        if (key === this.ACTIVE_SESSION_KEY) continue;

        if (key.startsWith(this.SESSION_KEY_PREFIX)) {
          const id = key.replace(this.SESSION_KEY_PREFIX, '');
          if (!this.isValidSessionId(id)) toRemove.push(key);
        }
        if (key.startsWith(this.WORKFLOW_STATE_KEY_PREFIX)) {
          const id = key.replace(this.WORKFLOW_STATE_KEY_PREFIX, '');
          if (!this.isValidSessionId(id)) toRemove.push(key);
        }
        if (key.startsWith('pybog_resume_')) {
          const id = key.replace('pybog_resume_', '');
          if (!this.isValidSessionId(id)) toRemove.push(key);
        }
      }

      toRemove.forEach(k => {
        try { localStorage.removeItem(k); } catch {}
        removed.push(k);
      });

      if (removed.length) {
        console.log('[SessionPersistence] Cleaned invalid keys:', removed);
      }
    } catch (e) {
      console.warn('[SessionPersistence] Failed during cleanupInvalidLocalKeys:', e);
    }
    return removed;
  }

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
            await unifiedAPIService.persistMessage(session.id, {
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
          } catch (e: any) {
            // Gracefully handle duplicate message_id or server-side upsert
            const msg = String(e?.message || e || '');
            if (msg.includes('UniqueViolationError') || msg.includes('duplicate key value')) {
              // Treat as persisted to avoid retry storms
              message.persisted = true;
              console.warn('Duplicate message detected; marking as persisted:', message.id);
            } else {
              console.warn('Failed to persist message:', e);
            }
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
      // Guard against invalid IDs
      if (!sessionId || sessionId === 'undefined' || sessionId === 'null') {
        console.warn('[SessionPersistence] Invalid sessionId passed to loadSession:', sessionId);
        return null;
      }

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

        // Resume URL handling removed - now handled by unified backend

        console.log('[SessionPersistence] Loaded session from localStorage:', sessionId);
        return session;
      }

      // Fallback to database
      const fullSession = await unifiedAPIService.getFullSession(sessionId);
      if (fullSession && fullSession.messages) {
        const messages: ChatMessage[] = fullSession.messages.map((m: any) => ({
          id: String(m.id || m.message_id), // Handle both id formats
          type: m.type || 'system',
          content: String(m.content || ''),
          timestamp: new Date(m.created_at || m.timestamp || Date.now()),
          sessionId: sessionId,
          metadata: typeof m.metadata === 'string' ? JSON.parse(m.metadata || '{}') : (m.metadata || {}),
          persisted: true,
        }));

        // Ensure uploaded files are represented in chat history for preview
        try {
          const referencedFileIds = new Set<string>();
          for (const msg of messages) {
            const fid = (msg as any)?.metadata?.file_id;
            if (fid) referencedFileIds.add(fid);
          }
          if (Array.isArray(fullSession.files)) {
            for (const f of fullSession.files) {
              const fid = (f as any).file_id;
              if (!fid || referencedFileIds.has(fid)) continue;
              const sizeKb = f.file_size ? `${(f.file_size / 1024).toFixed(1)} KB` : undefined;
              // Use relative URLs for file previews to work through proxy
              const absolutize = (u?: string) => {
                if (!u) return undefined;
                // If already absolute URL, return as-is
                if (/^https?:\/\//i.test(u)) return u;
                // Return relative URL that will go through the proxy
                return u.startsWith('/') ? u : `/${u}`;
              };
              const fileMsg: ChatMessage = {
                id: `file-stored-${fid}`,
                type: 'system',
                content: `File uploaded: ${f.filename}${sizeKb ? ` (${sizeKb})` : ''}`,
                timestamp: new Date(fullSession.session?.created_at || Date.now()),
                sessionId,
                metadata: {
                  status: 'complete' as const,
                  fileName: f.filename,
                  file_id: fid,
                  previewUrl: absolutize((f as any).preview_url),
                }
              } as any;
              messages.push(fileMsg);
            }
          }
        } catch {}

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

        // Resume URL handling removed - now handled by unified backend

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
          if (this.isValidSessionId(id)) sessionIds.push(id);
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
      const raw = localStorage.getItem(this.ACTIVE_SESSION_KEY);
      const id = (raw || '').trim();
      if (!this.isValidSessionId(id)) return null;
      return id;
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
   * Clear all sessions (alias for clearAllLocalSessions)
   */
  clearAllSessions(): void {
    this.clearAllLocalSessions();
  }


  /**
   * Restore all sessions from localStorage and database
   */
  async restoreAllSessions(): Promise<Map<string, PersistedSession>> {
    console.log('[SessionPersistence] restoreAllSessions() called');
    const sessions = new Map<string, PersistedSession>();
    const processedIds = new Set<string>();

    // First load from localStorage
    const localIds = this.getLocalSessionIds();
    console.log('[SessionPersistence] Found local session IDs:', localIds);
    for (const id of localIds) {
      if (processedIds.has(id)) continue;
      processedIds.add(id);
      
      try {
        // Try to load from localStorage first
        const localKey = `${this.SESSION_KEY_PREFIX}${id}`;
        const localData = localStorage.getItem(localKey);
        
        if (localData) {
          try {
            const parsed = JSON.parse(localData);
            const session: PersistedSession = {
              ...parsed,
              createdAt: new Date(parsed.createdAt),
              messages: parsed.messages || [],
            };
            sessions.set(id, session);
            console.log('[SessionPersistence] Loaded session from localStorage:', id);
          } catch (e) {
            // If localStorage data is corrupted, try database
            console.warn('[SessionPersistence] Corrupted localStorage data for:', id);
            const dbSession = await this.loadSession(id);
            if (dbSession) {
              sessions.set(id, dbSession);
            } else {
              // Remove orphaned session from localStorage
              console.log('[SessionPersistence] Removing orphaned session:', id);
              this.clearLocalSession(id);
            }
          }
        }
      } catch (error) {
        console.warn('[SessionPersistence] Error loading session:', id, error);
      }
    }

    // Then check database for recent sessions not in localStorage
    try {
      console.log('[SessionPersistence] Fetching recent sessions from database...');
      const recent = await unifiedAPIService.getRecentSessions(10);
      console.log('[SessionPersistence] Database returned:', recent.sessions?.length || 0, 'recent session(s)');
      if (recent.sessions) {
        for (const dbSession of recent.sessions) {
          const sid = (dbSession as any)?.session_id;
          if (!sid || sid === 'undefined' || sid === 'null') {
            console.warn('[SessionPersistence] Skipping invalid recent session id:', sid);
            continue;
          }
          console.log('[SessionPersistence] Processing database session:', sid);
          if (!processedIds.has(sid) && !sessions.has(sid)) {
            processedIds.add(sid);
            try {
              console.log('[SessionPersistence] Loading full session data for:', sid);
              const fullSession = await this.loadSession(sid);
              if (fullSession) {
                sessions.set(sid, fullSession);
              }
            } catch (e) {
              console.warn('[SessionPersistence] Failed to load session from DB:', sid, e);
            }
          }
        }
      }
    } catch (e) {
      console.warn('[SessionPersistence] Failed to load from database:', e);
    }

    // Check for any sessions with pending workflow approvals
    // Pending workflow approvals now handled by unified backend

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
