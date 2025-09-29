import React, { useState, useEffect, useCallback, useRef } from 'react';
import SimplifiedWorkbench from './components/SimplifiedWorkbench';
import ConsolePanel, { ConsoleMessage } from './components/ConsolePanel';
import { useToast } from './components/ToastProvider';
import { ChatMessage, Session, WorkflowState } from './types/ChatMessage';
import LoadingOverlay from './components/LoadingOverlay';
import { unifiedAPIService } from './services/UnifiedAPIService';
import chatService from './services/chatService';
import websocketService from './services/websocketService';
import sessionPersistence from './services/sessionPersistence';
import { useChatPipeline } from './hooks/useChatPipeline';
import { generateSessionId, ensureUniqueSessionName, generateSessionDisplayName, shouldUpdateSessionName } from './utils/sessionNaming';
import './utils/clearStorage'; // Import to make clearPyBOGData available globally

const App: React.FC = () => {
  // Sessions and active selection
  const [sessions, setSessions] = useState<Record<string, Session>>({});
  const [activeSessionId, setActiveSessionId] = useState<string>('');

  // UI state
  const [consoleMessages, setConsoleMessages] = useState<ConsoleMessage[]>([]);
  // Console defaults: collapsed in production, remember user preference
  const [isConsoleOpen, setIsConsoleOpen] = useState<boolean>(() => {
    try {
      const saved = localStorage.getItem('pybog_console_open');
      if (saved !== null) return saved === 'true';
    } catch {}
    // Default: open in development, collapsed in production
    return process.env.NODE_ENV !== 'production';
  });
  const [isLoading, setIsLoading] = useState(false);
  const [loadingMessage, setLoadingMessage] = useState<string>('');
  const [isInitializing, setIsInitializing] = useState(true);  // For initial app load
  const [lastFileId, setLastFileId] = useState<number | null>(null);
  const [lastUploadedFile, setLastUploadedFile] = useState<File | null>(null);
  const [workflowState, setWorkflowState] = useState<WorkflowState['state']>('idle');
  const [focusMessageId, setFocusMessageId] = useState<string | undefined>(undefined);
  const [sessionFiles, setSessionFiles] = useState<{ file_id: string; filename: string; file_type: string; file_size: number; preview_url: string; }[]>([]);
  // const [highlightTarget, setHighlightTarget] = useState<{kind:'analysis'|'block'|'input'|'output', label?: string}|undefined>(undefined);

  const analysisWatchdogRef = useRef<number | null>(null);

  // Using unified API service for all backend communication
  const { addToast } = useToast();
  
  const activeSession = activeSessionId ? sessions[activeSessionId] : undefined;
  const messages = activeSession?.messages || [];
  const sessionId = activeSessionId;
  const currentAnalysis = activeSession?.currentAnalysis || null;
  const analysisMessageId = activeSession?.analysisMessageId;

  // Chat pipeline integration
  const addMessageToSession = useCallback((message: ChatMessage) => {
    setSessions(prev => ({
      ...prev,
      [activeSessionId]: {
        ...prev[activeSessionId],
        messages: [...(prev[activeSessionId]?.messages || []), message]
      }
    }));
  }, [activeSessionId]);

  const { 
    pipelineState, 
    startChatPipeline, 
    retryLastStep,
    error: pipelineError 
  } = useChatPipeline(activeSessionId, addMessageToSession);

  // Update workflow state based on pipeline state
  useEffect(() => {
    if (pipelineState.currentStep === 'analyzing') {
      setWorkflowState('analyzing');
    } else if (pipelineState.currentStep === 'generating_bog') {
      setWorkflowState('generating');
    } else if (pipelineState.currentStep === 'complete') {
      setWorkflowState('complete');
    } else if (pipelineState.currentStep === 'error') {
      setWorkflowState('idle');
    }
  }, [pipelineState.currentStep]);
  
  // Load session files when active session changes
  useEffect(() => {
    let cancelled = false;
    if (!activeSessionId) {
      setSessionFiles([]);
      return;
    }

    (async () => {
      try {
        console.log('[App] Loading files for session:', activeSessionId);
        const fullSession = await unifiedAPIService.getFullSession(activeSessionId);
        if (cancelled) return;
        
        setSessionFiles(fullSession.files || []);
        console.log('[App] Loaded', fullSession.files?.length || 0, 'files for session:', activeSessionId);
      } catch (error) {
        console.warn('[App] Failed to load session files:', error);
        if (!cancelled) setSessionFiles([]);
      }
    })();

    return () => { cancelled = true; };
  }, [activeSessionId]);

  // Centralized workflow failure handler: stops loading, surfaces error, enables resend
  const clearAnalysisWatchdog = useCallback(() => {
    if (analysisWatchdogRef.current) {
      clearTimeout(analysisWatchdogRef.current);
      analysisWatchdogRef.current = null;
    }
  }, []);

  const handleWorkflowFailure = useCallback((errorMessage: string | any) => {
    // Ensure errorMessage is a string
    const message = typeof errorMessage === 'string' ? errorMessage : 
                    (errorMessage?.message || errorMessage?.toString() || 'Workflow failed');
    
    clearAnalysisWatchdog();
    setWorkflowState('idle');
    setIsLoading(false);
    setLoadingMessage('');
    addToast('error', 'Workflow error', message);
    // inline console message to avoid dependency ordering
    setConsoleMessages(prev => ([
      ...prev,
      {
        id: `console-${Date.now()}-${Math.random()}`,
        timestamp: new Date(),
        level: 'error',
        source: 'Workflow',
        message: message,
        details: undefined,
      }
    ]));
    if (!activeSessionId) return;

    setSessions(prev => {
      const session = prev[activeSessionId];
      if (!session) return prev;

      // Mark the last user message as failed to enable the Resend button
      const newMessages = [...session.messages];
      for (let i = newMessages.length - 1; i >= 0; i--) {
        const m = newMessages[i];
        if (m.type === 'user') { newMessages[i] = { ...m, status: 'failed' as const }; break; }
      }

      // Append an explicit system error message on canvas
      const errorNode: ChatMessage = {
        id: `error-${Date.now()}`,
        type: 'system',
        messageType: 'status',
        content: message || 'Workflow failed. Please try again or check the console for details.',
        timestamp: new Date(),
        metadata: { status: 'error' as const }
      } as any;
      newMessages.push(errorNode);

      return { ...prev, [activeSessionId]: { ...session, messages: newMessages } };
    });
  }, [activeSessionId, setConsoleMessages, setSessions, addToast, clearAnalysisWatchdog, setWorkflowState, setIsLoading, setLoadingMessage]);

  // Handle pipeline errors
  useEffect(() => {
    if (pipelineError) {
      handleWorkflowFailure(pipelineError);
    }
  }, [pipelineError, handleWorkflowFailure]);

  // Add console message helper
  const addConsoleMessage = useCallback((
    level: ConsoleMessage['level'], 
    source: string, 
    message: string, 
    details?: any
  ) => {
    const consoleMsg: ConsoleMessage = {
      id: `console-${Date.now()}-${Math.random()}`,
      timestamp: new Date(),
      level,
      source,
      message,
      details
    };
    setConsoleMessages(prev => [...prev, consoleMsg]);
  }, []); 
 // Restore sessions from localStorage and database
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        console.log('[App] Starting session restoration...');
        setIsInitializing(true);
        setLoadingMessage('Loading your sessions...');
        
        // Clean invalid local keys only
        try { 
          sessionPersistence.cleanupInvalidLocalKeys();
        } catch (e) {
          console.warn('[App] Cleanup failed:', e);
        }

        // First, fetch recent sessions from backend to get fresh data
        let sessionsObj: Record<string, Session> = {};

        try {
          console.log('[App] Fetching recent sessions from backend...');
          const recentSessions = await unifiedAPIService.getRecentSessions(10);
          const sessionsList = Array.isArray(recentSessions) ? recentSessions : ((recentSessions as any)?.sessions || []);
          console.log('[App] Got', sessionsList.length, 'recent sessions from backend');

          // Load each session with full data from backend
          for (const sessionInfo of sessionsList) {
            try {
              const fullSession = await unifiedAPIService.getFullSession(sessionInfo.session_id);
              console.log('[App] Loaded full session from backend:', sessionInfo.session_id, 'with', fullSession.messages?.length || 0, 'messages');

              // Convert backend messages to frontend format and attach session files
              const messages = (fullSession.messages || []).map((msg: any) => {
                const message: ChatMessage = {
                  id: msg.id || `msg-${msg.created_at}`,
                  type: msg.type,
                  content: msg.content,
                  timestamp: new Date(msg.created_at),
                  sessionId: sessionInfo.session_id,
                  persisted: true,
                  status: 'sent'
                };

                // If this is a system message with file uploads, attach converted files
                if (msg.type === 'system' && fullSession.files && fullSession.files.length > 0) {
                  const messageFiles = fullSession.files.map((file: any) => ({
                    name: file.filename,
                    url: `${process.env.REACT_APP_API_URL || 'http://localhost:8847'}${file.preview_url}`,
                    type: file.file_type?.includes('pdf') ? 'pdf' as const : 'unknown' as const,
                    file_id: file.file_id.toString(),
                    file_size: file.file_size,
                    mime_type: file.file_type
                  }));

                  // Only attach files to messages that mention uploads or are first system messages after user messages
                  if (message.content.toLowerCase().includes('file') || message.content.toLowerCase().includes('upload')) {
                    message.files = messageFiles;
                  }
                }

                return message;
              });

              sessionsObj[sessionInfo.session_id] = {
                id: sessionInfo.session_id,
                name: sessionInfo.name || `Session (${new Date(sessionInfo.created_at).toLocaleTimeString()})`,
                createdAt: new Date(sessionInfo.created_at),
                messages: messages,
                currentAnalysis: null,
                analysisMessageId: undefined,
              };
            } catch (error) {
              console.warn('[App] Failed to load full session:', sessionInfo.session_id, error);
            }
          }

          console.log('[App] Successfully loaded', Object.keys(sessionsObj).length, 'sessions from backend');
        } catch (error) {
          console.warn('[App] Failed to fetch sessions from backend, falling back to localStorage:', error);

          // Fallback to localStorage if backend is unavailable
          const restoredSessions = await sessionPersistence.restoreAllSessions();
          console.log('[App] Restored sessions from localStorage:', restoredSessions.size, 'session(s)');

          restoredSessions.forEach((persistedSession, id) => {
            console.log('[App] Processing localStorage session:', id, persistedSession.name, 'with', persistedSession.messages.length, 'messages');
            sessionsObj[id] = {
              id: persistedSession.id,
              name: persistedSession.name,
              createdAt: persistedSession.createdAt,
              messages: persistedSession.messages,
              currentAnalysis: persistedSession.currentAnalysis,
              analysisMessageId: persistedSession.analysisMessageId,
            };

            // If session has workflow state, update UI state
            if (persistedSession.workflowState?.state === 'awaiting_approval') {
              setWorkflowState('awaiting_approval');
            }

            // Ensure createdAt is a valid Date
            if (!sessionsObj[id].createdAt || isNaN(sessionsObj[id].createdAt.getTime())) {
              sessionsObj[id].createdAt = new Date();
            }
          });
        }

        if (Object.keys(sessionsObj).length > 0) {
          setSessions(sessionsObj);

          // Restore active session or use most recent
          const savedActiveId = sessionPersistence.getActiveSessionId();
          console.log('[App] Saved active ID:', savedActiveId, 'Available sessions:', Object.keys(sessionsObj));
          const activeId = savedActiveId && sessionsObj[savedActiveId] ? 
            savedActiveId : Object.keys(sessionsObj)[0];
          console.log('[App] Setting active session to:', activeId);
          setActiveSessionId(activeId);
          sessionPersistence.saveActiveSessionId(activeId);
        } else {
          console.log('[App] No existing sessions found, creating new session...');
          // Create new session if none exist
          // Attempt to create first session in the database so IDs are authoritative UUIDs
          try {
            const timestamp = new Date().toLocaleTimeString('en-US', { 
              hour: '2-digit', 
              minute: '2-digit',
              hour12: false 
            });
            const name = ensureUniqueSessionName(`Session 1 (${timestamp})`, []);
            const created = await unifiedAPIService.createSession(name);
            const newId = created.session_id;
            console.log('[App] Created new session:', newId, name);
            const initMessage: ChatMessage = {
              id: `init-${newId}`,
              type: 'system',
              content: 'PyBOG Control Builder is ready. Provide a detailed sequence of operations (or upload HVAC control docs: PDFs/specs). I will extract I/O points and synthesize Niagara wire‑sheet logic blocks. Start with equipment type, stages, economizer, occupancy schedule, and key setpoints.',
              timestamp: new Date(),
              persisted: true,
              status: 'sent'
            };
            const newSession: Session = {
              id: newId,
              name,
              createdAt: new Date(),
              messages: [initMessage],
              currentAnalysis: null,
            };
            setSessions({ [newId]: newSession });
            setActiveSessionId(newId);
            sessionPersistence.saveActiveSessionId(newId);
            await sessionPersistence.saveSession({ ...newSession, analysisMessageId: undefined });
            // Fire-and-forget persistence; already marked persisted to avoid double-save
            unifiedAPIService.persistMessage(newId, {
              message_id: initMessage.id,
              type: 'system',
              content: initMessage.content,
              metadata: { kind: 'init' },
              session_state: 'idle'
            }).catch(() => {});
          } catch {
            // Offline/local fallback
            const newId = generateSessionId();
            const timestamp = new Date().toLocaleTimeString('en-US', { 
              hour: '2-digit', 
              minute: '2-digit',
              hour12: false 
            });
            const initMessage: ChatMessage = {
              id: `init-${newId}`,
              type: 'system',
              content: 'PyBOG Control Builder is ready. Provide a detailed sequence of operations (or upload HVAC control docs: PDFs/specs). I will extract I/O points and synthesize Niagara wire‑sheet logic blocks. Start with equipment type, stages, economizer, occupancy schedule, and key setpoints.',
              timestamp: new Date(),
              persisted: false,
              status: 'sent'
            };
            const newSession: Session = {
              id: newId,
              name: ensureUniqueSessionName(`Session 1 (${timestamp})`, []),
              createdAt: new Date(),
              messages: [initMessage],
              currentAnalysis: null,
            };
            setSessions({ [newId]: newSession });
            setActiveSessionId(newId);
            sessionPersistence.saveActiveSessionId(newId);
            await sessionPersistence.saveSession({ ...newSession, analysisMessageId: undefined });
          }
        }
      } catch (e) {
        console.error('Failed to restore sessions:', e);
        // Fallback: create local-only session
        const fallbackId = `session_${Date.now()}`;
        const init: ChatMessage = {
          id: `init-${fallbackId}`,
          type: 'system',
          content: 'PyBOG Control Builder initialized. Upload HVAC documents or describe your control requirements.',
          timestamp: new Date(),
          persisted: false
        };
        setSessions({ [fallbackId]: { id: fallbackId, name: 'Session 1', createdAt: new Date(), messages: [init], currentAnalysis: null } });
        setActiveSessionId(fallbackId);
        
        // Clear initialization loading even on error
        setIsInitializing(false);
        setLoadingMessage('');
      }

      console.log('[App] PyBOG Control Builder initialized');
      console.log('[App] Service connections ready');
      
      // Clear initialization loading
      setIsInitializing(false);
      setLoadingMessage('');
    })();
    return () => { cancelled = true; };
  }, []); // NO DEPENDENCIES - run only once on mount to prevent infinite loops

  // Persist console preference
  useEffect(() => {
    try { localStorage.setItem('pybog_console_open', String(isConsoleOpen)); } catch {}
  }, [isConsoleOpen]);

  // Auto-save sessions periodically and when active session changes
  useEffect(() => {
    const stopAutoSave = sessionPersistence.startAutoSave(
      () => {
        if (!activeSessionId || !activeSession || !activeSession.id) return null;
        return {
          id: activeSession.id,
          name: activeSession.name,
          createdAt: activeSession.createdAt,
          messages: activeSession.messages,
          currentAnalysis: activeSession.currentAnalysis,
          analysisMessageId: activeSession.analysisMessageId,
          workflowState: workflowState !== 'idle' ? {
            state: workflowState,
            resumeUrl: undefined,
          } : undefined,
        };
      },
      30000 // Save every 30 seconds
    );

    return stopAutoSave;
  }, [activeSessionId, activeSession, workflowState]);

  // Save session when switching or when messages change
  useEffect(() => {
    if (!activeSessionId || !activeSession || !activeSession.id) return;
    
    const saveTimeout = setTimeout(async () => {
      await sessionPersistence.saveSession({
        id: activeSession.id,
        name: activeSession.name,
        createdAt: activeSession.createdAt,
        messages: activeSession.messages,
        currentAnalysis: activeSession.currentAnalysis,
        analysisMessageId: activeSession.analysisMessageId,
        workflowState: workflowState !== 'idle' ? {
          state: workflowState,
          resumeUrl: undefined,
        } : undefined,
      });
    }, 1000); // Debounce saves by 1 second

    return () => clearTimeout(saveTimeout);
  }, [activeSession, activeSessionId, workflowState]);

  // Session actions
  const createSession = useCallback(async () => {
    // Generate unique name with timestamp to avoid duplicates
    const timestamp = new Date().toLocaleTimeString('en-US', { 
      hour: '2-digit', 
      minute: '2-digit',
      hour12: false 
    });
    const count = Object.keys(sessions).length + 1;
    const baseName = `Session ${count} (${timestamp})`;
    const name = ensureUniqueSessionName(baseName, Object.values(sessions).map(s => s.name));
    
    // Show loading while creating session
    setIsLoading(true);
    setLoadingMessage('Creating new session...');
    
    try {
      // Create session in database - use server authoritative UUID
      const created = await unifiedAPIService.createSession(name);
      const sessionId = created.session_id;
      console.log('Created session with ID:', sessionId);
      
      const initMessage: ChatMessage = {
        id: `init-${sessionId}`,
        type: 'system',
        content: 'PyBOG Control Builder is ready. Provide a detailed sequence of operations (or upload HVAC control docs: PDFs/specs). I will extract I/O points and synthesize Niagara wire‑sheet logic blocks. Start with equipment type, stages, economizer, occupancy schedule, and key setpoints.',
        timestamp: new Date(),
        sessionId: sessionId,
        persisted: true,
        status: 'sent'
      };
      
      // Update local state
      setSessions(prev => ({
        ...prev,
        [sessionId]: {
          id: sessionId,
          name,
          createdAt: new Date(),
          messages: [initMessage],
          currentAnalysis: null,
        }
      }));
      setActiveSessionId(sessionId);
      setFocusMessageId(undefined);
      setWorkflowState('idle');
      
      // Save to localStorage immediately
      sessionPersistence.saveActiveSessionId(sessionId);
      await sessionPersistence.saveSession({
        id: sessionId,
        name,
        createdAt: new Date(),
        messages: [initMessage],
        currentAnalysis: null,
        analysisMessageId: undefined
      });
      
      // Persist initial message (fire-and-forget); session auto-save will skip due to persisted=true
      unifiedAPIService.persistMessage(sessionId, {
        message_id: initMessage.id,
        type: 'system',
        content: initMessage.content,
        metadata: { kind: 'init' },
        session_state: 'idle'
      }).catch(() => {});
      
      addConsoleMessage('success', 'Session', `Created new session: ${name}`);
      addToast('success', 'Session created', name);
    } catch (e) {
      console.error('Failed to create session:', e);
      addConsoleMessage('error', 'Session', 'Failed to create session in database');
      addToast('error', 'Session creation failed', 'Please try again');
    } finally {
      setIsLoading(false);
      setLoadingMessage('');
    }
  }, [sessions, addConsoleMessage, addToast]);

  // Clear all sessions function
  const clearAllSessions = useCallback(async () => {
    if (!window.confirm('This will delete all sessions and start fresh. Continue?')) {
      return;
    }

    setIsLoading(true);
    setLoadingMessage('Clearing all sessions...');

    try {
      // Delete all sessions from backend
      const sessionIds = Object.keys(sessions);
      await Promise.all(sessionIds.map(id => 
        unifiedAPIService.deleteSession(id).catch(e => 
          console.warn(`Failed to delete session ${id}:`, e)
        )
      ));

      // Clear all local storage
      sessionPersistence.clearAllSessions();

      // Reset local state
      setSessions({});
      setActiveSessionId('');
      setSessionFiles([]);
      setWorkflowState('idle');
      setFocusMessageId(undefined);

      // Disconnect WebSocket
      websocketService.disconnect();

      addConsoleMessage('success', 'Session', 'All sessions cleared');
      addToast('success', 'Sessions cleared', 'Starting fresh');

      // Create a new session automatically
      setTimeout(() => {
        createSession();
      }, 500);

    } catch (e) {
      console.error('Failed to clear all sessions:', e);
      addConsoleMessage('error', 'Session', 'Failed to clear all sessions');
      addToast('error', 'Clear failed', 'Some sessions may remain');
    } finally {
      setIsLoading(false);
      setLoadingMessage('');
    }
  }, [sessions, addConsoleMessage, addToast, createSession]);

  const switchSession = useCallback(async (id: string) => {
    // Show loading while switching
    setIsLoading(true);
    setLoadingMessage('Loading session...');
    
    try {
      // Save current session before switching
      if (activeSessionId && activeSession) {
        await sessionPersistence.saveSession({
          id: activeSession.id,
          name: activeSession.name,
          createdAt: activeSession.createdAt,
          messages: activeSession.messages,
          currentAnalysis: activeSession.currentAnalysis,
          analysisMessageId: activeSession.analysisMessageId,
          workflowState: workflowState !== 'idle' ? {
            state: workflowState,
            resumeUrl: undefined,
          } : undefined,
        });
      }

      // Load the new session
      const persistedSession = await sessionPersistence.loadSession(id);
      if (persistedSession) {
        setSessions(prev => ({
          ...prev,
          [id]: {
            id: persistedSession.id,
            name: persistedSession.name,
            createdAt: persistedSession.createdAt,
            messages: persistedSession.messages,
            currentAnalysis: persistedSession.currentAnalysis,
            analysisMessageId: persistedSession.analysisMessageId,
          }
        }));
        
        // Update workflow state if session has pending approval
        if (persistedSession.workflowState?.state === 'awaiting_approval') {
          setWorkflowState('awaiting_approval');
        } else {
          setWorkflowState('idle');
        }
      }
      
      setActiveSessionId(id);
      sessionPersistence.saveActiveSessionId(id);
      setFocusMessageId(undefined);
    } catch (e) {
      console.error('Failed to switch session:', e);
      if (sessions[id]) {
        setActiveSessionId(id);
        sessionPersistence.saveActiveSessionId(id);
        setFocusMessageId(undefined);
      }
    } finally {
      setIsLoading(false);
      setLoadingMessage('');
    }
  }, [sessions, activeSessionId, activeSession, workflowState]);

  const deleteSession = useCallback(async (id: string) => {
    // Snapshot session data for optimistic UI + possible rollback
    const sessionToDelete = sessions[id];
    if (!sessionToDelete) return;

    const isActive = activeSessionId === id;

    // Compute best candidate to activate next (most recent by createdAt)
    const remaining = Object.values(sessions).filter(s => s.id !== id);
    remaining.sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime());
    const nextCandidate = remaining[0]?.id;

    // Optimistic UI: remove locally and switch immediately
    setSessions(prev => {
      const copy = { ...prev } as Record<string, Session>;
      delete copy[id];
      return copy;
    });

    // Clear local cache quickly (localStorage + resume URL)
    sessionPersistence.clearSession(id);

    if (isActive) {
      if (nextCandidate) {
        // Switch instantly without awaiting remote calls
        setActiveSessionId(nextCandidate);
        sessionPersistence.saveActiveSessionId(nextCandidate);
      } else {
        // Create a fresh session in background
        createSession().catch(() => {});
      }
    }

    addConsoleMessage('success', 'Session', `Deleted session: ${sessionToDelete.name}`);
    addToast('success', 'Session deleted', sessionToDelete.name);

    // Server delete in background; rollback on failure
    try {
      await unifiedAPIService.deleteSession(id);
    } catch (error) {
      console.error('Failed to delete session (server):', error);
      // Rollback local state
      setSessions(prev => ({ ...prev, [id]: sessionToDelete }));
      if (isActive) {
        setActiveSessionId(id);
        sessionPersistence.saveActiveSessionId(id);
      }
      addConsoleMessage('error', 'Session', 'Failed to delete session (reverted)');
      addToast('error', 'Delete failed', 'Session was restored');
    }
  }, [activeSessionId, sessions, addConsoleMessage, addToast, createSession]);

  const renameSession = useCallback(async (id: string, newName: string) => {
    try {
      // Update in database
      await unifiedAPIService.updateSession(id, newName);
      
      // Update local state
      setSessions(prev => ({
        ...prev,
        [id]: {
          ...prev[id],
          name: newName
        }
      }));
      
      addConsoleMessage('success', 'Session', `Renamed session to: ${newName}`);
    } catch (error) {
      console.error('Failed to rename session:', error);
      addConsoleMessage('error', 'Session', 'Failed to rename session');
    }
  }, [addConsoleMessage]);

  // WebSocket connection for real-time updates (replaces polling)
  useEffect(() => {
    // Don't connect if sessionId is empty or 'undefined'
    if (!activeSessionId || activeSessionId === 'undefined') return;
    
    // Ensure session exists in database before connecting WebSocket
    const ensureSessionAndConnect = async () => {
      try {
        // Check if session exists in database, create if needed
        const session = sessions[activeSessionId];
        if (session && !session.persisted) {
          console.log('[App] Ensuring session exists in database:', activeSessionId);
          try {
            // Try to get the session first
            await unifiedAPIService.getSession(activeSessionId);
            console.log('[App] Session already exists in database');
          } catch (error) {
            // Session doesn't exist, create it
            console.log('[App] Creating session in database:', activeSessionId);
            await unifiedAPIService.createSession(session.name);
          }
          // Update session as persisted
          setSessions(prev => ({
            ...prev,
            [activeSessionId]: { ...session, persisted: true }
          }));
        }
        
        // Connect WebSocket for this session with retry logic
        let retryCount = 0;
        const maxRetries = 3;
        
        const attemptConnection = async (): Promise<boolean> => {
          const connected = await websocketService.connect(activeSessionId);
          if (connected) {
            addConsoleMessage('success', 'WebSocket', `Real-time connection established for session`);
            return true;
          } else if (retryCount < maxRetries) {
            retryCount++;
            console.warn(`[App] WebSocket connection failed, retrying... (${retryCount}/${maxRetries})`);
            addConsoleMessage('warn', 'WebSocket', `Connection failed, retrying... (${retryCount}/${maxRetries})`);
            // Wait before retry with exponential backoff
            await new Promise(resolve => setTimeout(resolve, 1000 * Math.pow(2, retryCount - 1)));
            return attemptConnection();
          } else {
            console.error('[App] Failed to establish WebSocket connection after retries');
            addConsoleMessage('error', 'WebSocket', 'Connection failed after retries');
            return false;
          }
        };
        
        await attemptConnection();
      } catch (error) {
        console.error('[App] Failed to ensure session and connect WebSocket:', error);
        addConsoleMessage('error', 'WebSocket', 'Connection failed');
      }
    };
    
    ensureSessionAndConnect();
    
    // Subscribe to connection events
    const unsubscribeConnected = websocketService.on('connected', () => {
      addToast('success', 'Connected', 'Real-time updates enabled');
      addConsoleMessage('success', 'WebSocket', 'Connected - real-time updates enabled');
    });
    const unsubscribeDisconnected = websocketService.on('disconnected', () => {
      addToast('warning', 'Disconnected', 'Attempting to reconnect…');
      addConsoleMessage('warn', 'WebSocket', 'Disconnected - attempting to reconnect...');

      // Mark any pending messages as failed for retry
      setSessions(prev => {
        const session = prev[activeSessionId];
        if (!session) return prev;

        const messages = session.messages.map(msg => {
          // Mark both user messages and streaming assistant messages as failed
          if (msg.status === 'sending' && (msg.type === 'user' || msg.id.startsWith('streaming-assistant-'))) {
            return { ...msg, status: 'failed' as const };
          }
          return msg;
        });

        return {
          ...prev,
          [activeSessionId]: {
            ...session,
            messages
          }
        };
      });

      // Reset workflow state if we were in the middle of analysis
      if (workflowState === 'analyzing') {
        setWorkflowState('idle');
        setIsLoading(false);
        setLoadingMessage('');
      }
    });

    // Subscribe to WebSocket errors
    const unsubscribeError = websocketService.on('error', (event) => {
      console.error('[App] WebSocket error:', event.data);
      const errorMsg = event.data?.error || 'WebSocket connection error';
      const reconnectAttempts = event.data?.reconnectAttempts || 0;

      addConsoleMessage('error', 'WebSocket', `${errorMsg} (attempt ${reconnectAttempts})`);

      // Progressive error handling based on reconnection attempts
      if (reconnectAttempts >= 5) {
        addToast('error', 'Connection lost', 'Please refresh the page to reconnect');
        // Mark all sending messages as failed
        setSessions(prev => {
          const session = prev[activeSessionId];
          if (!session) return prev;

          const messages = session.messages.map(msg => {
            if (msg.status === 'sending') {
              return { ...msg, status: 'failed' as const };
            }
            return msg;
          });

          return {
            ...prev,
            [activeSessionId]: { ...session, messages }
          };
        });

        // Reset workflow state
        setWorkflowState('idle');
        setIsLoading(false);
        setLoadingMessage('');
      } else if (reconnectAttempts >= 3) {
        addToast('warning', 'Connection issues', `Reconnecting... (${reconnectAttempts}/5)`);
      }
    });

    // Subscribe to state changes
    const unsubscribeState = websocketService.on('message', (event) => {
      console.log('[App] WebSocket state change:', event.data);
      if (event.data?.state) {
        setWorkflowState(event.data.state);
        if (event.data.state === 'error') {
          const msg = event.data?.message || 'Workflow failed';
          handleWorkflowFailure(msg);
        } else if (event.data.state === 'awaiting_approval' || event.data.state === 'complete' || event.data.state === 'generating') {
          clearAnalysisWatchdog();
          setIsLoading(false);
          setLoadingMessage('');
        }
      }
    });
    
    // Subscribe to analysis updates
    const unsubscribeAnalysis = websocketService.on('analysis_complete', (event) => {
      console.log('[App] WebSocket analysis update:', event.data);
      if (event.data?.analysis) {
        setSessions(prev => {
          const session = prev[activeSessionId];
          if (!session) return prev;
          return { ...prev, [activeSessionId]: { ...session, currentAnalysis: event.data.analysis } };
        });
      }
    });
    
    // Subscribe to streaming chat responses
    const unsubscribeChat = websocketService.on('chat', (event) => {
      const data = event.data || {};
      console.log('[App] WebSocket chat event:', data);

      // Ignore events that arrive within 2 seconds of WebSocket connection (likely replay events)
      const connectionTime = websocketService.getConnectionTime();
      if (connectionTime && Date.now() - connectionTime < 2000) {
        console.log('[App] Ignoring chat event - too soon after connection (likely replay)');
        return;
      }
      
      if (data.is_complete) {
        // Complete message received - finalize the streaming message
        const finalContent = data.final_content || data.buffer_content || data.content || '';
        if (finalContent.trim()) {
          // Check if this looks like an error response
          const lowerContent = finalContent.toLowerCase();
          const errorPhrases = [
            'unable to analyze',
            'cannot analyze',
            'no file upload',
            'currently unable',
            'failed to',
            'cannot process',
            'unable to process',
            'no files',
            'cannot find'
          ];

          const isErrorResponse = errorPhrases.some(phrase => lowerContent.includes(phrase));
          let finalizedMessageId: string | null = null;

          console.log('[App] WebSocket finalizing message, current session state:', {
            activeSessionId,
            messageCount: sessions[activeSessionId]?.messages?.length || 0,
            finalContent: finalContent.substring(0, 100) + '...'
          });

          setSessions(prev => {
            const session = prev[activeSessionId];
            if (!session) return prev;

            // Find the streaming message and finalize it
            const messages = session.messages.map(msg => {
              if (msg.id.startsWith('streaming-assistant-') && (msg.status === 'sending' || !msg.status)) {
                finalizedMessageId = msg.id; // Store the actual ID for persistence
                return {
                  ...msg,
                  content: finalContent,
                  status: 'sent' as const,
                  persisted: false,
                  timestamp: new Date()
                };
              }
              return msg;
            });

            // If this is an error response, mark the last user message as failed
            if (isErrorResponse) {
              console.log('[App] Detected error in AI response, marking last user message as failed');
              for (let i = messages.length - 1; i >= 0; i--) {
                if (messages[i].type === 'user') {
                  messages[i] = { ...messages[i], status: 'failed' };
                  break;
                }
              }
            }

            return {
              ...prev,
              [activeSessionId]: {
                ...session,
                messages
              }
            };
          });

          // Persist the final assistant message with correct ID
          if (finalizedMessageId) {
            unifiedAPIService.persistMessage(activeSessionId, {
              message_id: finalizedMessageId,
              type: 'assistant',
              content: finalContent,
              metadata: { streaming: true },
              session_state: 'idle'
            }).then(() => {
              setSessions(prev => {
                const s = prev[activeSessionId];
                if (!s) return prev;
                const msgs = s.messages.map(m =>
                  m.id === finalizedMessageId ? { ...m, persisted: true } : m
                );
                return { ...prev, [activeSessionId]: { ...s, messages: msgs } };
              });
            }).catch(console.error);
          }
          
          setWorkflowState('idle');
          setIsLoading(false);
          setLoadingMessage('');
          addConsoleMessage('success', 'Chat', 'Response received');
        }
      } else {
        // Streaming chunk - update existing streaming message or create new one
        const chunk = data.content || '';
        const bufferContent = data.buffer_content || '';

        if (chunk || bufferContent) {
          console.log('[App] WebSocket streaming chunk received:', {
            activeSessionId,
            chunkLength: chunk?.length || 0,
            bufferLength: bufferContent?.length || 0,
            currentMessageCount: sessions[activeSessionId]?.messages?.length || 0
          });

          setSessions(prev => {
            const session = prev[activeSessionId];
            if (!session) return prev;

            const messages = [...session.messages];
            const streamingIndex = messages.findIndex(msg =>
              msg.id.startsWith('streaming-assistant-') && (msg.status === 'sending' || !msg.status)
            );

            if (streamingIndex >= 0) {
              // Update existing streaming message
              const currentMsg = messages[streamingIndex];
              messages[streamingIndex] = {
                ...currentMsg,
                content: bufferContent || (currentMsg.content + chunk),
                timestamp: new Date()
              };
            } else {
              // Create new streaming message with unique ID
              const streamingMessage: ChatMessage = {
                id: `streaming-assistant-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
                type: 'assistant',
                content: bufferContent || chunk,
                timestamp: new Date(),
                sessionId: activeSessionId,
                status: 'sending',
                persisted: false
              };
              messages.push(streamingMessage);
            }

            return { ...prev, [activeSessionId]: { ...session, messages } };
          });
        }
      }
    });

    // Listen for general error messages pushed by backend
    const unsubscribeWsMessage = websocketService.on('message', (event) => {
      const p = event.data || {};
      if (p.type === 'workflow_error' || p.level === 'error' || p.status === 'error' || p.error) {
        handleWorkflowFailure(p.message || p.error || 'Workflow error');
        return;
      }
      if (p.type === 'chat_ready' || p.type === 'chat_response' || p.status === 'chat_ready') {
        const assistantMessage: ChatMessage = {
          id: `assistant-${Date.now()}`,
          type: 'assistant',
          content: p.message || 'Ready.',
          timestamp: new Date(),
          persisted: false,
          status: 'sent'
        } as any;
        setSessions(prev => ({
          ...prev,
          [activeSessionId]: {
            ...prev[activeSessionId],
            messages: [...(prev[activeSessionId]?.messages || []), assistantMessage]
          }
        }));

        // Persist the assistant message
        unifiedAPIService.persistMessage(activeSessionId, {
          message_id: assistantMessage.id,
          type: 'assistant',
          content: assistantMessage.content,
          metadata: { type: p.type },
          session_state: 'idle'
        }).then(() => {
          setSessions(prev => {
            const s = prev[activeSessionId];
            if (!s) return prev;
            const msgs = s.messages.map(m =>
              m.id === assistantMessage.id ? { ...m, persisted: true } : m
            );
            return { ...prev, [activeSessionId]: { ...s, messages: msgs } };
          });
        }).catch(console.error);

        setWorkflowState('idle');
        setIsLoading(false);
        setLoadingMessage('');
        addConsoleMessage('info', 'Workflow', p.message || 'Chat ready');
        addToast('info', 'Chat ready', p.message);
        return;
      }

      // Unified handling of process/analysis/status complete events
      if (p.type === 'process_step') {
        const stableId = `process-${activeSessionId}-${p.stepKey}`;
        const processMsg: ChatMessage = {
          id: stableId,
          type: 'system',
          messageType: 'processing',
          content: p.title || 'Processing...',
          timestamp: new Date(p.ts || Date.now()),
          metadata: {
            processStep: {
              stepKey: p.stepKey,
              detail: p.detail,
              status: p.status,
              metrics: p.extra?.metrics,
            }
          }
        } as any;
        setSessions(prev => {
          const session = prev[activeSessionId];
          if (!session) return prev;
          const existingIndex = session.messages.findIndex(m => m.metadata?.processStep?.stepKey === p.stepKey);
          const newMessages = [...session.messages];
          if (existingIndex >= 0) {
            const existing = newMessages[existingIndex];
            newMessages[existingIndex] = { ...processMsg, id: existing.id || stableId };
          } else {
            newMessages.push(processMsg);
          }
          return { ...prev, [activeSessionId]: { ...session, messages: newMessages } };
        });
        addConsoleMessage(p.status === 'error' ? 'error' : p.status === 'ok' ? 'success' : 'info', 'Workflow', `${p.title}: ${p.detail || p.status}`, p.extra?.metrics);
        return;
      }

      if (p.type === 'analysis_progress' || p.type === 'status') {
        const progressMsg: ChatMessage = {
          id: `progress-${Date.now()}`,
          type: 'system',
          messageType: 'status',
          content: p.message || p.step || 'Working…',
          timestamp: new Date(),
        } as any;
        setSessions(prev => ({
          ...prev,
          [activeSessionId]: {
            ...prev[activeSessionId],
            messages: [...(prev[activeSessionId]?.messages || []), progressMsg]
          }
        }));
        return;
      }

      if (p.type === 'analysis_complete') {
        setSessions(prev => {
          const session = prev[activeSessionId];
          if (!session) return prev;
          if (session.analysisMessageId) {
            const idx = session.messages.findIndex(m => m.id === session.analysisMessageId);
            if (idx >= 0) {
              const updated = [...session.messages];
              updated[idx] = {
                ...updated[idx],
                content: p.message || updated[idx].content,
                metadata: {
                  ...(updated[idx].metadata || {}),
                  analysisData: {
                    inputs: p.analysis?.inputs || p.inputs || [],
                    outputs: p.analysis?.outputs || p.outputs || [],
                    pseudocode: p.analysis?.pseudocode || p.pseudocode || []
                  }
                },
                timestamp: new Date(),
              } as ChatMessage;
              return { ...prev, [activeSessionId]: { ...session, messages: updated, currentAnalysis: { ...(p.analysis || {}), _messageId: session.analysisMessageId } } };
            }
          }
          const analysisMsgId = `analysis-${Date.now()}`;
          const analysisMessage: ChatMessage = {
            id: analysisMsgId,
            type: 'assistant',
            content: p.message || 'HVAC analysis complete. Please review.',
            timestamp: new Date(),
            metadata: { analysisData: { inputs: p.analysis?.inputs || p.inputs || [], outputs: p.analysis?.outputs || p.outputs || [], pseudocode: p.analysis?.pseudocode || p.pseudocode || [] } }
          } as any;
          return { ...prev, [activeSessionId]: { ...session, messages: [...(session.messages || []), analysisMessage], currentAnalysis: { ...(p.analysis || {}), _messageId: analysisMsgId }, analysisMessageId: analysisMsgId } };
        });
        return;
      }

      if (p.type === 'workflow_completed') {
        setWorkflowState('complete');
        setIsLoading(false);
        setLoadingMessage('');
        if (p.message) {
          const assistantMessage: ChatMessage = {
            id: `assistant-${Date.now()}`,
            type: 'assistant',
            content: p.message,
            timestamp: new Date(),
            persisted: false,
            status: 'sent'
          } as any;
          setSessions(prev => ({
            ...prev,
            [activeSessionId]: {
              ...prev[activeSessionId],
              messages: [...(prev[activeSessionId]?.messages || []), assistantMessage]
            }
          }));

          // Persist the completion message
          unifiedAPIService.persistMessage(activeSessionId, {
            message_id: assistantMessage.id,
            type: 'assistant',
            content: assistantMessage.content,
            metadata: { type: 'workflow_completed' },
            session_state: 'complete'
          }).then(() => {
            setSessions(prev => {
              const s = prev[activeSessionId];
              if (!s) return prev;
              const msgs = s.messages.map(m =>
                m.id === assistantMessage.id ? { ...m, persisted: true } : m
              );
              return { ...prev, [activeSessionId]: { ...s, messages: msgs } };
            });
          }).catch(console.error);
        }
        addToast('success', 'Workflow complete', p.message);
        return;
      }
    });
    
    return () => {
      unsubscribeConnected();
      unsubscribeDisconnected();
      unsubscribeError();
      unsubscribeState();
      unsubscribeAnalysis();
      unsubscribeChat();
      unsubscribeWsMessage();
      // Don't disconnect WebSocket here as we may switch sessions
    };
  }, [activeSessionId, addConsoleMessage, handleWorkflowFailure, clearAnalysisWatchdog, setWorkflowState, setIsLoading, setLoadingMessage, addToast]);

  // Handle message sending
  const handleSendMessage = useCallback(async (text: string, files: File[]) => {
    if (!activeSessionId) return;
    
    // Prevent duplicate sends
    if (workflowState === 'analyzing') {
      addToast('warning', 'Please wait', 'Still processing previous request');
      return;
    }
    
    setWorkflowState('analyzing');
    setIsLoading(true);
    setLoadingMessage('Sending message...');
    
    // Check if we should auto-update session name
    const currentSession = sessions[activeSessionId];
    const isGeneric = (n: string | undefined) => {
      if (!n) return true;
      const s = n.trim();
      return s.startsWith('Session ') || s.startsWith('New Session') || /untitled/i.test(s) || /session at /i.test(s);
    };
    if (currentSession) {
      let proposed: string | null = null;
      // Prefer text-based naming when user typed something meaningful
      if (shouldUpdateSessionName(currentSession.name, currentSession.messages)) {
        proposed = generateSessionDisplayName([...currentSession.messages, { type: 'user', content: text }]);
      }
      // If no text or heuristics didn't trigger, name based on first uploaded file
      if ((!proposed || proposed === 'New Session') && isGeneric(currentSession.name) && files && files.length > 0) {
        const base = (files[0].name || 'Document').replace(/\.[^.]+$/, '').replace(/[_-]+/g, ' ').trim();
        proposed = base.length > 0 ? `Review: ${base}` : null;
      }
      if (proposed && proposed.trim() && proposed !== currentSession.name) {
        const newName = proposed.trim();
        setSessions(prev => ({
          ...prev,
          [activeSessionId]: {
            ...prev[activeSessionId],
            name: newName
          }
        }));
        // Update in database
        try {
          await unifiedAPIService.updateSession(activeSessionId, newName);
        } catch (e) {
          console.warn('Failed to update session name:', e);
        }
      }
    }
    
    // Add user message
    const userMessage: ChatMessage = {
      id: `msg-${Date.now()}`,
      type: 'user',
      content: text || `Uploaded ${files.length} file(s)`,
      timestamp: new Date(),
      sessionId: activeSessionId,
      files: files.length > 0 ? files : undefined,
      persisted: false,
      status: 'sending'
    };

    setSessions(prev => ({
      ...prev,
      [activeSessionId]: {
        ...prev[activeSessionId],
        messages: [...(prev[activeSessionId]?.messages || []), userMessage]
      }
    }));

    // Persist user message immediately
    try {
      await unifiedAPIService.persistMessage(activeSessionId, {
        message_id: userMessage.id,
        type: 'user',
        content: userMessage.content,
        session_state: 'analyzing'
      });
      setSessions(prev => {
        const s = prev[activeSessionId];
        if (!s) return prev;
        const msgs = s.messages.map(m => m.id === userMessage.id ? { ...m, persisted: true, status: 'sent' as const } : m);
        return { ...prev, [activeSessionId]: { ...s, messages: msgs } };
      });
    } catch (error) {
      console.error('Failed to persist user message:', error);
      // Mark message as failed so user can retry
      setSessions(prev => {
        const s = prev[activeSessionId];
        if (!s) return prev;
        const msgs = s.messages.map(m => m.id === userMessage.id ? { ...m, status: 'failed' as const } : m);
        return { ...prev, [activeSessionId]: { ...s, messages: msgs } };
      });
    }
    
    try {
      if (files.length > 0) {
        // Handle file uploads
        console.log('[App] Starting file upload process. Session ID:', activeSessionId, 'Files:', files.length);
        let lastFileId: number | null = null;
        for (const f of files) {
          try {
            console.log('[App] Uploading file:', f.name, 'Size:', f.size, 'Type:', f.type);

            // Upload file using the new backend API
            const formData = new FormData();
            formData.append('file', f);
            formData.append('session_id', activeSessionId);

            const uploadResponse = await fetch(`${process.env.REACT_APP_API_URL || 'http://localhost:8847'}/api/files/upload`, {
              method: 'POST',
              body: formData
            });

            console.log('[App] Upload response status:', uploadResponse.status, uploadResponse.statusText);

            if (!uploadResponse.ok) {
              const errorText = await uploadResponse.text();
              console.error('[App] Upload failed - Response:', errorText);
              throw new Error(`Upload failed (${uploadResponse.status}): ${errorText}`);
            }

            const fileResult = await uploadResponse.json();
            console.log('[App] Upload successful:', fileResult);
            setLastFileId(fileResult.file_id); // Store the most recent file ID

            // Store the uploaded file for reference but don't create a separate message
            // The TextReviewNode will show all necessary file information
            setLastUploadedFile(f);

            addConsoleMessage('success', 'Upload', `File stored: ${fileResult.filename} (ID: ${fileResult.file_id})`);
          } catch (e) {
            console.error('[App] File upload failed:', e);
            addConsoleMessage('error', 'Upload', `Failed to upload ${f.name}: ${e}`);
            // Continue with text processing even if upload fails
          }
        }
        
        // After uploading files, extract text for review instead of immediate analysis
        if (files.length > 0 && lastFileId) {
          try {
            // Extract text from uploaded files for review
            const lastUploadedFile = files[files.length - 1];

            console.log('[App] Using file ID for text extraction:', lastFileId);

            if (lastFileId) {
              console.log('[App] Extracting text from file for review:', lastFileId);
              setLoadingMessage('Extracting text from document...');

              const extractResult = await unifiedAPIService.extractTextWithWorkflow(lastFileId, activeSessionId);

              // Create text review message
              const textReviewMessage: ChatMessage = {
                id: `text-review-${Date.now()}`,
                type: 'assistant',
                messageType: 'text_review',
                content: 'Document text extracted. Please review and approve before analysis.',
                timestamp: new Date(),
                sessionId: activeSessionId,
                metadata: {
                  extractedText: extractResult.extracted_text || extractResult.text || extractResult.content,
                  file_id: lastFileId,
                  filename: lastUploadedFile.name,
                  requiresApproval: true,
                  stage: 'text_review'
                }
              };

              setSessions(prev => ({
                ...prev,
                [activeSessionId]: {
                  ...prev[activeSessionId],
                  messages: [...(prev[activeSessionId]?.messages || []), textReviewMessage]
                }
              }));

              setWorkflowState('awaiting_approval');
              addConsoleMessage('info', 'Text Extraction', 'Text extracted and ready for review');
            } else {
              console.error('[App] No file ID found for text extraction');
              addConsoleMessage('error', 'Extraction', 'Failed to find uploaded file for text extraction');
              setWorkflowState('idle');
            }
          } catch (error) {
            console.error('Text extraction failed:', error);
            addConsoleMessage('error', 'Extraction', 'Failed to extract text from document');
            setWorkflowState('idle');
          } finally {
            setIsLoading(false);
            setLoadingMessage('');
          }
        }

        // Handle text-only messages (chat without files)
        else if (text?.trim() && files.length === 0) {
          try {
            // Ensure WebSocket is connected for this session before sending message
            console.log('[App] Ensuring WebSocket connection before sending chat message');
            const wsConnected = await websocketService.connect(activeSessionId);
            if (!wsConnected) {
              throw new Error('Failed to establish WebSocket connection');
            }

            console.log('[App] WebSocket connected, sending chat message');
            // Send chat message with streaming response via WebSocket
            const chatResponse = await chatService.sendMessage({
              session_id: activeSessionId,
              text: text
            });

            if (chatResponse.success) {
              console.log('[App] Chat message sent successfully, awaiting WebSocket stream');

              // Add a loading/streaming assistant message immediately
              const loadingMessage: ChatMessage = {
                id: `streaming-assistant-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
                type: 'assistant',
                content: 'Processing your request...',
                timestamp: new Date(),
                sessionId: activeSessionId,
                status: 'sending',
                persisted: false
              };

              setSessions(prev => ({
                ...prev,
                [activeSessionId]: {
                  ...prev[activeSessionId],
                  messages: [...(prev[activeSessionId]?.messages || []), loadingMessage]
                }
              }));

              addConsoleMessage('success', 'Chat', 'Processing files with AI...');
              // Response will come via WebSocket streaming
            } else {
              throw new Error('Chat service returned unsuccessful response');
            }
          } catch (e) {
            console.error('Chat processing failed:', e);
            handleWorkflowFailure(`Processing failed: ${e}`);
          }
        } else {
          // GATED WORKFLOW FIX: No automatic analysis for file uploads
          // The gated workflow in lines 1388-1449 should handle all file uploads
          console.log('[App] File workflow completed - waiting for user interaction');
          setWorkflowState('idle');
          setIsLoading(false);
          setLoadingMessage('');
        }
      } else if (text) {
        // Text-only message: use chat pipeline
        try {
          // Persist user message first
          await unifiedAPIService.persistMessage(activeSessionId, {
            message_id: userMessage.id,
            type: 'user',
            content: text,
            session_state: 'analyzing'
          });
          setSessions(prev => {
            const s = prev[activeSessionId];
            if (!s) return prev;
            const msgs = s.messages.map(m => m.id === userMessage.id ? { ...m, persisted: true } : m);
            return { ...prev, [activeSessionId]: { ...s, messages: msgs } };
          });

          // Start chat pipeline for end-to-end processing
          await startChatPipeline(text);
          addConsoleMessage('success', 'Pipeline', 'Chat pipeline started - processing message...');
          
        } catch (error: any) {
          console.error('Chat pipeline failed:', error);
          handleWorkflowFailure(error.message || 'Failed to start chat pipeline');
        }
      }
    } catch (error: any) {
      const errMsg = typeof error?.message === 'string' ? error.message : 'Failed to send message';
      handleWorkflowFailure(errMsg);
    } finally {
      setIsLoading(false);
      clearAnalysisWatchdog();
    }
  }, [activeSessionId, workflowState, sessions, addToast, setWorkflowState, setIsLoading, setLoadingMessage, shouldUpdateSessionName, generateSessionDisplayName, addConsoleMessage, handleWorkflowFailure, clearAnalysisWatchdog, startChatPipeline]);

  // Handle analysis approval
  const handleApproveAnalysis = useCallback(async () => {
    if (!activeSessionId || !activeSession) return;
    setWorkflowState('generating');
    
    try {
      // Always use backend approval API to resume workflows
      // Send approval via unified API service
      await unifiedAPIService.sendChatMessage(activeSessionId, 'Analysis approved. Please proceed with BOG generation.');

      // Create approval message
      const bogMessage: ChatMessage = {
        id: `bog-${Date.now()}`,
        type: 'assistant',
        content: 'Analysis approved. BOG generation requested.',
        timestamp: new Date(),
        metadata: { status: 'approved' }
      };
        
      setSessions(prev => ({
        ...prev,
        [activeSessionId]: {
          ...prev[activeSessionId],
          messages: [...(prev[activeSessionId]?.messages || []), bogMessage]
        }
      }));
        
      setWorkflowState('complete');

      // Persist completion or status message
      try {
        const completeMsgId = `complete-${Date.now()}`;
        await unifiedAPIService.persistMessage(activeSessionId, {
          message_id: completeMsgId,
          type: 'assistant',
          content: 'Action completed',
          metadata: { status: 'approved' },
          session_state: 'complete'
        });
        setSessions(prev => {
          const s = prev[activeSessionId];
          if (!s) return prev;
          const msgs = s.messages.map(m => m.id === completeMsgId ? { ...m, persisted: true } : m);
          return { ...prev, [activeSessionId]: { ...s, messages: msgs } };
        });
      } catch {}
      
    } catch (error: any) {
      console.error('Approval failed:', error);
      const errMsg = typeof error?.message === 'string' ? error.message : 'Failed to approve analysis';
      handleWorkflowFailure(errMsg);
    }
  }, [activeSessionId, activeSession, addConsoleMessage, handleWorkflowFailure]);

  // Handle pipeline retry
  const handleRetryPipeline = useCallback(async () => {
    if (!activeSessionId) return;
    
    try {
      setIsLoading(true);
      setLoadingMessage('Retrying last step...');
      await retryLastStep();
      addConsoleMessage('info', 'Pipeline', 'Retrying last step...');
    } catch (error: any) {
      console.error('Pipeline retry failed:', error);
      handleWorkflowFailure(error.message || 'Failed to retry pipeline step');
    } finally {
      setIsLoading(false);
      setLoadingMessage('');
    }
  }, [activeSessionId, retryLastStep, addConsoleMessage, handleWorkflowFailure]);

  const handleResendMessage = useCallback(async (message: ChatMessage) => {
    if (!activeSessionId || !message.content?.trim()) return;
    
    console.log('Resending message:', message.id);
    
    // Mark original message as retrying
    setSessions(prev => ({
      ...prev,
      [activeSessionId]: {
        ...prev[activeSessionId],
        messages: prev[activeSessionId]?.messages.map(m => 
          m.id === message.id ? { ...m, status: 'sending' } : m
        ) || []
      }
    }));
    
    try {
      setWorkflowState('analyzing');
      setIsLoading(true);
      setLoadingMessage('Retrying message...');
      
      // Store failed message for retry functionality
      const failedMessage = { ...message, status: 'failed' as const };
      
      // Resend the message using the chat service
      const chatResponse = await chatService.sendMessage({
        session_id: activeSessionId,
        text: message.content
      });
      
      if (chatResponse.success) {
        // Mark message as sent and remove failed status
        setSessions(prev => ({
          ...prev,
          [activeSessionId]: {
            ...prev[activeSessionId],
            messages: prev[activeSessionId]?.messages.map(m => 
              m.id === message.id ? { ...m, status: 'sent' } : m
            ) || []
          }
        }));
        
        addConsoleMessage('success', 'Retry', 'Message resent successfully');
        addToast('success', 'Message resent', 'Processing response...');
        
        // Response will come via WebSocket streaming
      } else {
        throw new Error('Chat service returned unsuccessful response');
      }
      
    } catch (error) {
      console.error('Message retry failed:', error);
      
      // Mark message as failed again and store for retry
      setSessions(prev => ({
        ...prev,
        [activeSessionId]: {
          ...prev[activeSessionId],
          messages: prev[activeSessionId]?.messages.map(m => 
            m.id === message.id ? { ...m, status: 'failed' } : m
          ) || []
        }
      }));
      
      setWorkflowState('idle');
      setIsLoading(false);
      setLoadingMessage('');
      
      addConsoleMessage('error', 'Retry', 'Failed to resend message');
      addToast('error', 'Retry failed', 'Please try again');
    }
  }, [activeSessionId, addToast, addConsoleMessage, setWorkflowState, setIsLoading, setLoadingMessage]); 
 const handleNavigateToMessage = useCallback((messageId: string) => {
    setFocusMessageId(messageId);
    console.log('Navigating to message:', messageId);
  }, []);

  const handleNavigateToItem = useCallback((target: { kind: 'input' | 'output' | 'block'; label: string }) => {
    console.log('Navigating to item:', target);
    // Implement navigation logic here if needed
  }, []);

  const handleRequestChanges = useCallback(async (feedback: string) => {
    if (!activeSessionId) return;
    
    try {
      // Request modification via backend approval API
      // Send modification request via unified API service
      await unifiedAPIService.sendChatMessage(activeSessionId, `Please modify the analysis based on this feedback: ${feedback}`);
      
      // Create feedback message
      const feedbackMessage: ChatMessage = {
        id: `feedback-${Date.now()}`,
        type: 'assistant', 
        content: 'Feedback received. Please provide updated sequence.',
        timestamp: new Date()
      };
        
      setSessions(prev => ({
        ...prev,
        [activeSessionId]: {
          ...prev[activeSessionId],
          messages: [...(prev[activeSessionId]?.messages || []), feedbackMessage],
          currentAnalysis: null, // Clear current analysis for re-analysis
        }
      }));
        
      setWorkflowState('idle'); // Ready for new input
      // Persist feedback acknowledgement + set idle
      try { 
        await unifiedAPIService.persistMessage(activeSessionId, { 
          message_id: feedbackMessage.id, 
          type: 'assistant', 
          content: feedbackMessage.content, 
          session_state: 'idle' 
        }); 
      } catch {}
      
    } catch (error) {
      console.error('Request changes failed:', error);
      addToast('error', 'Error', 'Failed to request changes');
    }
  }, [activeSessionId, addToast]);

  // BOG workflow handlers
  const handleApproveBOGGeneration = useCallback(async (analysisData: any) => {
    if (!activeSessionId || !activeSession) return;
    setWorkflowState('generating');

    try {
      // Get analysis_id from the analysisData or use a default value
      const analysisId = analysisData?.analysis_id || analysisData?.id || 1;

      // Start BOG generation using the proper API method
      const bogResult = await unifiedAPIService.generateBOGFile(activeSessionId, analysisId);
      console.log('[App] BOG generation started:', bogResult);

      // Create BOG progress message (handle backend response schema)
      const bogProgressMessage: ChatMessage = {
        id: `bog-progress-${Date.now()}`,
        type: 'assistant',
        messageType: 'bog_progress',
        content: 'BOG generation started. Please wait while we create your Niagara BOG file...',
        timestamp: new Date(),
        metadata: {
          stage: 'initializing',
          progress: 0,
          analysisData: analysisData,
          bogFileId: bogResult.file_id || (bogResult as any).artifact_id,
          filename: bogResult.filename || 'generated_bog_file.bog',
          artifactId: (bogResult as any).artifact_id,
          analysisId: analysisId
        }
      };

      setSessions(prev => ({
        ...prev,
        [activeSessionId]: {
          ...prev[activeSessionId],
          messages: [...(prev[activeSessionId]?.messages || []), bogProgressMessage]
        }
      }));

      // Persist the progress message
      try {
        await unifiedAPIService.persistMessage(activeSessionId, {
          message_id: bogProgressMessage.id,
          type: 'assistant',
          message_type: 'bog_progress',
          content: bogProgressMessage.content,
          metadata: bogProgressMessage.metadata,
          session_state: 'generating'
        });
      } catch {}

    } catch (error: any) {
      console.error('BOG generation approval failed:', error);
      const errMsg = typeof error?.message === 'string' ? error.message : 'Failed to start BOG generation';
      handleWorkflowFailure(errMsg);
    }
  }, [activeSessionId, activeSession, handleWorkflowFailure]);

  const handleRequestAnalysisChanges = useCallback(async (feedback: string) => {
    if (!activeSessionId) return;

    try {
      // Request analysis modification via unified API service
      await unifiedAPIService.sendChatMessage(activeSessionId, `Please refine the analysis based on this feedback: ${feedback}`);

      // Create feedback message
      const feedbackMessage: ChatMessage = {
        id: `analysis-feedback-${Date.now()}`,
        type: 'assistant',
        content: 'Analysis refinement requested. Please provide updated requirements or upload a revised document.',
        timestamp: new Date(),
        metadata: { feedbackType: 'analysis_changes', feedback: feedback }
      };

      setSessions(prev => ({
        ...prev,
        [activeSessionId]: {
          ...prev[activeSessionId],
          messages: [...(prev[activeSessionId]?.messages || []), feedbackMessage],
          currentAnalysis: null, // Clear current analysis for re-analysis
        }
      }));

      setWorkflowState('idle'); // Ready for new input

      // Persist feedback acknowledgement
      try {
        await unifiedAPIService.persistMessage(activeSessionId, {
          message_id: feedbackMessage.id,
          type: 'assistant',
          content: feedbackMessage.content,
          metadata: feedbackMessage.metadata,
          session_state: 'idle'
        });
      } catch {}

    } catch (error) {
      console.error('Request analysis changes failed:', error);
      addToast('error', 'Error', 'Failed to request analysis changes');
    }
  }, [activeSessionId, addToast]);

  const handleViewAnalysisDetails = useCallback(async (analysisData: any) => {
    // This will trigger a detailed view of the analysis
    // For now, we can create a detailed analysis message or modal
    console.log('Viewing analysis details:', analysisData);

    // Could implement a modal here or navigate to detailed view
    addToast('info', 'Analysis Details', 'Analysis details view would open here');
  }, [addToast]);

  // Text approval workflow handlers
  const handleApproveText = useCallback(async (approvedText: string) => {
    if (!activeSessionId) return;

    try {
      setWorkflowState('analyzing');

      // Start analysis with approved text and chat context
      const recentMessages = sessions[activeSessionId]?.messages?.slice(-3) || [];
      const contextText = recentMessages
        .filter(m => m.type === 'user' || (m.type === 'assistant' && m.messageType !== 'text_review'))
        .map(m => `${m.type}: ${m.content}`)
        .join('\n');

      const fullContext = `Chat Context:\n${contextText}\n\nApproved Document Text:\n${approvedText}`;

      console.log('[App] Starting analysis with approved text and context');
      await unifiedAPIService.startAnalysisWithWorkflow(activeSessionId, fullContext);

      // Create analysis progress message
      const analysisMessage: ChatMessage = {
        id: `analysis-started-${Date.now()}`,
        type: 'assistant',
        messageType: 'analysis_progress',
        content: 'Analysis started with approved text and chat context.',
        timestamp: new Date(),
        sessionId: activeSessionId,
        metadata: {
          stage: 'starting',
          progress: 0,
          approvedText: approvedText,
          withContext: true
        }
      };

      setSessions(prev => ({
        ...prev,
        [activeSessionId]: {
          ...prev[activeSessionId],
          messages: [...(prev[activeSessionId]?.messages || []), analysisMessage]
        }
      }));

    } catch (error: any) {
      console.error('Text approval failed:', error);
      const errMsg = typeof error?.message === 'string' ? error.message : 'Failed to start analysis';
      handleWorkflowFailure(errMsg);
    }
  }, [activeSessionId, sessions, handleWorkflowFailure]);

  const handleRequestTextChanges = useCallback(async (feedback: string) => {
    if (!activeSessionId) return;

    try {
      // Extract file_id from feedback if it contains it, or use the last uploaded file
      const fileIdMatch = feedback.match(/file ID: (\d+)/);
      let fileId = null;

      if (fileIdMatch) {
        fileId = parseInt(fileIdMatch[1]);
      } else if (lastFileId) {
        fileId = lastFileId;
      }

      if (fileId) {
        // Trigger actual re-extraction using the API
        addToast('info', 'Re-extract', `Re-extracting text from file ID: ${fileId}`);
        setWorkflowState('analyzing');

        const extractResult = await unifiedAPIService.extractTextWithWorkflow(fileId, activeSessionId);

        // Create new text review message with re-extracted content
        const textReviewMessage: ChatMessage = {
          id: `text-review-reextract-${Date.now()}`,
          type: 'assistant',
          messageType: 'text_review',
          content: 'Document text re-extracted. Please review and approve before analysis.',
          timestamp: new Date(),
          sessionId: activeSessionId,
          metadata: {
            extractedText: extractResult.extracted_text || extractResult.text || extractResult.content,
            file_id: fileId,
            filename: extractResult.filename || lastUploadedFile?.name || 'Re-extracted Document',
            requiresApproval: true,
            stage: 'text_review',
            isReExtraction: true,
            feedback: feedback
          }
        };

        setSessions(prev => ({
          ...prev,
          [activeSessionId]: {
            ...prev[activeSessionId],
            messages: [...(prev[activeSessionId]?.messages || []), textReviewMessage]
          }
        }));

        setWorkflowState('idle');
        addToast('success', 'Re-extract', 'Text re-extraction completed');
      } else {
        // Fallback to feedback message if no file ID available
        const feedbackMessage: ChatMessage = {
          id: `text-feedback-${Date.now()}`,
          type: 'assistant',
          content: 'Text re-extraction requested. Please upload a clearer document or provide additional guidance.',
          timestamp: new Date(),
          sessionId: activeSessionId,
          metadata: { feedbackType: 'text_changes', feedback: feedback }
        };

        setSessions(prev => ({
          ...prev,
          [activeSessionId]: {
            ...prev[activeSessionId],
            messages: [...(prev[activeSessionId]?.messages || []), feedbackMessage]
          }
        }));

        setWorkflowState('idle');
        addToast('info', 'Re-extraction', 'Text re-extraction requested');
      }
    } catch (error: any) {
      console.error('Text re-extraction failed:', error);
      setWorkflowState('idle');
      addToast('error', 'Re-extract', `Failed to re-extract text: ${error?.message || error}`);
    }
  }, [activeSessionId, lastFileId, lastUploadedFile, addToast]);

  const handleViewTextDetails = useCallback(async (text: string) => {
    // Open text in modal or detailed view
    console.log('Viewing full text:', text);
    addToast('info', 'Text Details', 'Full text view would open here');
  }, [addToast]);

  // Add debug mode for testing
  const [debugMode, setDebugMode] = useState(false);

  return (
    <div style={{ width: '100vw', height: '100vh', overflow: 'hidden' }}>
      {/* Debug toggle */}
      <div style={{ position: 'fixed', top: '10px', right: '10px', zIndex: 9999 }}>
        <button 
          onClick={() => setDebugMode(!debugMode)}
          style={{ 
            padding: '5px 10px', 
            backgroundColor: debugMode ? '#ff4444' : '#4444ff',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            cursor: 'pointer'
          }}
        >
          {debugMode ? 'Exit Debug' : 'Debug Mode'}
        </button>
      </div>
      
      {debugMode ? (
        <div>Debug mode enabled</div>
      ) : (
        <>
          {/* Main Workbench Interface */}
          <SimplifiedWorkbench
            // session and analysis data
            messages={messages}
            sessionId={sessionId}
            isLoading={isLoading}
            workflowState={workflowState}
            currentAnalysis={currentAnalysis}
            analysisMessageId={analysisMessageId}
            focusMessageId={focusMessageId}
            sessionFiles={sessionFiles}
            // highlightTarget={highlightTarget}
            
            // actions
            onSendMessage={handleSendMessage}
            onApproveAnalysis={handleApproveAnalysis}
            onRequestChanges={handleRequestChanges}
            onResendMessage={handleResendMessage}
            onNavigateToMessage={handleNavigateToMessage}
            onNavigateToItem={handleNavigateToItem}

            // BOG workflow actions
            onApproveBOGGeneration={handleApproveBOGGeneration}
            onRequestAnalysisChanges={handleRequestAnalysisChanges}
            onViewAnalysisDetails={handleViewAnalysisDetails}

            // Text approval workflow actions
            onApproveText={handleApproveText}
            onRequestTextChanges={handleRequestTextChanges}
            onViewTextDetails={handleViewTextDetails}

            // session manager
            sessions={Object.values(sessions)}
            activeSessionId={activeSessionId}
            onCreateSession={createSession}
            onSwitchSession={switchSession}
            onDeleteSession={deleteSession}
            onRenameSession={renameSession}
            onClearAllSessions={clearAllSessions}
            
            // console
            isConsoleOpen={isConsoleOpen}
            onToggleConsole={() => setIsConsoleOpen(!isConsoleOpen)}
          />
          
          {/* Console Panel */}
          <ConsolePanel
            isOpen={isConsoleOpen}
            onClose={() => setIsConsoleOpen(false)}
            messages={consoleMessages}
            onClear={() => setConsoleMessages([])}
          />
          
          {/* Loading Overlay - Show for: initial load, session operations, NOT for analyzing (has its own UI) */}
          <LoadingOverlay 
            isVisible={isInitializing || (isLoading && workflowState !== 'analyzing')} 
            message={loadingMessage || (isInitializing ? 'Loading PyBOG Control Builder...' : 'Processing...')}
          />
        </>
      )}
    </div>
  );
};

export default App;