import React, { useState, useEffect, useCallback, useRef } from 'react';
import SimplifiedWorkbench from './components/SimplifiedWorkbench';
import ConsolePanel, { ConsoleMessage } from './components/ConsolePanel';
import SystemMonitor from './components/SystemMonitor';
import { Terminal } from 'lucide-react';
import { workflowAPI } from './services/workflowAPI';
import apiService from './services/apiService';
import enhancedApiService from './services/apiServiceEnhanced';
import n8nWebhookService from './services/n8nWebhookService';
import { useToast } from './components/ToastProvider';
import websocketService from './services/websocketService';
import { ChatMessage } from './components/ChatCanvasGrid';
import sessionPersistence from './services/sessionPersistence';
import { generateSessionId, generateDefaultSessionName, generateSessionDisplayName, shouldUpdateSessionName, ensureUniqueSessionName } from './utils/sessionNaming';
import LoadingOverlay from './components/LoadingOverlay';

// Session model
interface Session {
  id: string;
  name: string;
  createdAt: Date;
  messages: ChatMessage[];
  currentAnalysis: any | null;
  analysisMessageId?: string;
}

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
  const [workflowState, setWorkflowState] = useState<'idle' | 'analyzing' | 'awaiting_approval' | 'generating' | 'complete'>('idle');
  const [focusMessageId, setFocusMessageId] = useState<string | undefined>(undefined);
  const [sessionFiles, setSessionFiles] = useState<{ file_id: string; filename: string; file_type: string; file_size: number; preview_url: string; }[]>([]);
  // const [highlightTarget, setHighlightTarget] = useState<{kind:'analysis'|'block'|'input'|'output', label?: string}|undefined>(undefined);

  const analysisWatchdogRef = useRef<number | null>(null);
  const replayInFlightRef = useRef<Record<string, boolean>>({});

  // Using API-based workflow integration exclusively (no direct n8n client)
  const { addToast } = useToast();
  
  const activeSession = activeSessionId ? sessions[activeSessionId] : undefined;
  const messages = activeSession?.messages || [];
  const sessionId = activeSessionId;
  const currentAnalysis = activeSession?.currentAnalysis || null;
  const analysisMessageId = activeSession?.analysisMessageId;
  
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
        const fullSession = await enhancedApiService.getFullSession(activeSessionId);
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

  // Debug: Log messages being passed to UI
  useEffect(() => {
    console.log('[App] Messages for UI:', {
      activeSessionId,
      messageCount: messages.length,
      messages: messages.map(m => ({
        id: m.id,
        type: m.type,
        content: m.content?.substring(0, 50) + '...'
      }))
    });
  }, [activeSessionId, messages]);

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
  }, [activeSessionId, setConsoleMessages, setSessions]);

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
        
        // Clean invalid local keys before restoring sessions
        try { sessionPersistence.cleanupInvalidLocalKeys(); } catch {}

        // Restore all sessions from persistence
        const restoredSessions = await sessionPersistence.restoreAllSessions();
        console.log('[App] Restored sessions:', restoredSessions.size, 'session(s)');
        if (cancelled) return;

        if (restoredSessions.size > 0) {
          // Convert to Sessions object
          const sessionsObj: Record<string, Session> = {};
          restoredSessions.forEach((persistedSession, id) => {
            console.log('[App] Processing session:', id, persistedSession.name, 'with', persistedSession.messages.length, 'messages');
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
            const name = ensureUniqueSessionName(generateDefaultSessionName(1), []);
            const created = await enhancedApiService.createSession(name);
            const newId = created.session_id;
            console.log('[App] Created new session:', newId, name);
            const initMessage: ChatMessage = {
              id: `init-${newId}`,
              type: 'system',
              content: 'PyBOG Control Builder is ready. Provide a detailed sequence of operations (or upload HVAC control docs: PDFs/specs). I will extract I/O points and synthesize Niagara wire‑sheet logic blocks. Start with equipment type, stages, economizer, occupancy schedule, and key setpoints.',
              timestamp: new Date(),
              persisted: true
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
            enhancedApiService.persistMessage(newId, {
              message_id: initMessage.id,
              type: 'system',
              content: initMessage.content,
              metadata: { kind: 'init' },
              session_state: 'idle'
            }).catch(() => {});
          } catch {
            // Offline/local fallback
            const newId = generateSessionId();
            const initMessage: ChatMessage = {
              id: `init-${newId}`,
              type: 'system',
              content: 'PyBOG Control Builder is ready. Provide a detailed sequence of operations (or upload HVAC control docs: PDFs/specs). I will extract I/O points and synthesize Niagara wire‑sheet logic blocks. Start with equipment type, stages, economizer, occupancy schedule, and key setpoints.',
              timestamp: new Date(),
              persisted: false
            };
            const newSession: Session = {
              id: newId,
              name: ensureUniqueSessionName(generateDefaultSessionName(1), []),
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

      addConsoleMessage('info', 'System', 'PyBOG Control Builder initialized');
      addConsoleMessage('info', 'System', 'Checking service connections...');

      setTimeout(() => {
        addConsoleMessage('success', 'API', 'Backend API connected');
        addConsoleMessage('success', 'Database', 'PostgreSQL connected');
        addConsoleMessage('info', 'n8n', 'Workflow engine ready');
        addConsoleMessage('success', 'WebSocket', 'Real-time updates enabled');
      }, 1000);
      
      // Clear initialization loading
      setIsInitializing(false);
      setLoadingMessage('');
    })();
    return () => { cancelled = true; };
  }, [addConsoleMessage]);

  // Debug: log active session changes
  useEffect(() => {
    console.log('[App] Active session changed:', {
      activeSessionId,
      activeSession: activeSession ? {
        id: activeSession.id,
        name: activeSession.name,
        messageCount: activeSession.messages.length,
        firstMessage: activeSession.messages[0]?.content?.substring(0, 50)
      } : null,
      totalSessions: Object.keys(sessions).length,
      sessionIds: Object.keys(sessions)
    });
  }, [activeSessionId, activeSession, sessions]);

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
            resumeUrl: n8nWebhookService.getResumeUrl(activeSessionId) || undefined,
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
          resumeUrl: n8nWebhookService.getResumeUrl(activeSessionId) || undefined,
        } : undefined,
      });
    }, 1000); // Debounce saves by 1 second

    return () => clearTimeout(saveTimeout);
  }, [activeSession, activeSessionId, workflowState]);

  // Session actions
  const createSession = useCallback(async () => {
    const count = Object.keys(sessions).length + 1;
    const baseName = generateDefaultSessionName(count);
    const name = ensureUniqueSessionName(baseName, Object.values(sessions).map(s => s.name));
    
    // Show loading while creating session
    setIsLoading(true);
    setLoadingMessage('Creating new session...');
    
    try {
      // Create session in database - use server authoritative UUID
      const created = await enhancedApiService.createSession(name);
      const sessionId = created.session_id;
      console.log('Created session with ID:', sessionId);
      
      const initMessage: ChatMessage = {
        id: `init-${sessionId}`,
        type: 'system',
        content: 'PyBOG Control Builder is ready. Provide a detailed sequence of operations (or upload HVAC control docs: PDFs/specs). I will extract I/O points and synthesize Niagara wire‑sheet logic blocks. Start with equipment type, stages, economizer, occupancy schedule, and key setpoints.',
        timestamp: new Date(),
        sessionId: sessionId,
        persisted: true,
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
      
      // Persist initial message (fire-and-forget); session auto-save will skip due to persisted=true
      enhancedApiService.persistMessage(sessionId, {
        message_id: initMessage.id,
        type: 'system',
        content: initMessage.content,
        metadata: { kind: 'init' },
        session_state: 'idle'
      }).catch(() => {});
      
      addConsoleMessage('success', 'Session', `Created new session: ${name}`);
    } catch (e) {
      console.error('Failed to create session:', e);
      addConsoleMessage('error', 'Session', 'Failed to create session in database');
    } finally {
      setIsLoading(false);
      setLoadingMessage('');
    }
  }, [sessions, addConsoleMessage]);

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
            resumeUrl: n8nWebhookService.getResumeUrl(activeSessionId) || undefined,
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
      await enhancedApiService.deleteSession(id);
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
      await enhancedApiService.renameSession(id, newName);
      
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
    
    // Connect WebSocket for this session
    websocketService.connect(activeSessionId).then(connected => {
      if (connected) {
        addConsoleMessage('success', 'WebSocket', `Real-time connection established for session`);
      }
    });
    
    // Subscribe to connection events
    const unsubscribeConnected = websocketService.on('connected', () => {
      addToast('success', 'Connected', 'Real-time updates enabled');
    });
    const unsubscribeDisconnected = websocketService.on('disconnected', () => {
      addToast('warning', 'Disconnected', 'Attempting to reconnect…');
    });

    // Subscribe to state changes
    const unsubscribeState = websocketService.on('state_change', (event) => {
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
    const unsubscribeAnalysis = websocketService.on('analysis_update', (event) => {
      console.log('[App] WebSocket analysis update:', event.data);
      if (event.data?.analysis) {
        setSessions(prev => {
          const session = prev[activeSessionId];
          if (!session) return prev;
          return { ...prev, [activeSessionId]: { ...session, currentAnalysis: event.data.analysis } };
        });
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
        } as any;
        setSessions(prev => ({
          ...prev,
          [activeSessionId]: {
            ...prev[activeSessionId],
            messages: [...(prev[activeSessionId]?.messages || []), assistantMessage]
          }
        }));
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
          const assistantMessage: ChatMessage = { id: `assistant-${Date.now()}`, type: 'assistant', content: p.message, timestamp: new Date() } as any;
          setSessions(prev => ({ ...prev, [activeSessionId]: { ...prev[activeSessionId], messages: [...(prev[activeSessionId]?.messages || []), assistantMessage] } }));
        }
        addToast('success', 'Workflow complete', p.message);
        return;
      }
    });
    
    return () => {
      unsubscribeConnected();
      unsubscribeDisconnected();
      unsubscribeState();
      unsubscribeAnalysis();
      unsubscribeWsMessage();
      // Don't disconnect WebSocket here as we may switch sessions
    };
  }, [activeSessionId, addConsoleMessage]);

  // Handle message sending
  const handleSendMessage = useCallback(async (text: string, files: File[]) => {
    if (!activeSessionId) return;
    
    // Prevent duplicate sends
    if (workflowState === 'analyzing') {
      addToast('warning', 'Please wait', 'Still processing previous request');
      return;
    }
    
    // Don't show loading overlay for analysis - n8n provides its own feedback
    setWorkflowState('analyzing');
    clearAnalysisWatchdog();
    analysisWatchdogRef.current = window.setTimeout(() => {
      handleWorkflowFailure('Workflow did not respond in time. You can retry.');
    }, 60000);
    
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
          await enhancedApiService.renameSession(activeSessionId, newName);
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
      persisted: false
    };
    
    setSessions(prev => ({
      ...prev,
      [activeSessionId]: {
        ...prev[activeSessionId],
        messages: [...(prev[activeSessionId]?.messages || []), userMessage]
      }
    }));
    
    try {
      // Add live status message only for text-only requests (avoid clutter for file uploads)
      if (files.length === 0) {
        const statusId = `status-${Date.now()}`;
        const statusMessage: ChatMessage = {
          id: statusId,
          type: 'system',
          messageType: 'status',
          content: 'Analyzing your request…',
          timestamp: new Date(),
          sessionId: activeSessionId,
        };
        setSessions(prev => ({
          ...prev,
          [activeSessionId]: {
            ...prev[activeSessionId],
            messages: [...(prev[activeSessionId]?.messages || []), statusMessage]
          }
        }));
        try { 
          await apiService.persistMessage(activeSessionId, { message_id: statusId, type: 'system', content: statusMessage.content, metadata: { kind: 'status' }, session_state: 'analyzing' });
          // Mark status message as persisted
          setSessions(prev => {
            const s = prev[activeSessionId];
            if (!s) return prev;
            const msgs = s.messages.map(m => m.id === statusId ? { ...m, persisted: true } : m);
            return { ...prev, [activeSessionId]: { ...s, messages: msgs } };
          });
        } catch {}
      }

      if (files.length > 0) {
        // Persist user message ONCE before processing files
        try {
          const fileMetadata = files.map(f => ({ name: f.name, size: f.size, type: f.type }));
          await enhancedApiService.persistMessage(activeSessionId, {
            message_id: userMessage.id,
            type: 'user',
            content: userMessage.content,
            metadata: { files: fileMetadata },
            session_state: 'analyzing'
          });
          // Mark user message as persisted
          setSessions(prev => {
            const s = prev[activeSessionId];
            if (!s) return prev;
            const msgs = s.messages.map(m => m.id === userMessage.id ? { ...m, persisted: true } : m);
            return { ...prev, [activeSessionId]: { ...s, messages: msgs } };
          });
        } catch (e) {
          console.error('Failed to persist user message:', e);
        }
        
        for (const f of files) {

          // Upload file to backend with proper persistence
          try {
            const fileResult = await enhancedApiService.uploadFile(activeSessionId, f, userMessage.id);
            
            const fileSizeBytes = (fileResult.size ?? f.size ?? 0) as number;
            const fileStoredMsg: ChatMessage = {
              id: `file-stored-${Date.now()}`,
              type: 'system',
              content: `File uploaded: ${fileResult.filename} (${(fileSizeBytes / 1024).toFixed(1)} KB)`,
              timestamp: new Date(),
              sessionId: activeSessionId,
              persisted: true,
              metadata: { 
                status: 'complete' as const, 
                fileName: fileResult.filename,
                file_id: fileResult.file_id,
                preview_url: (fileResult as any).preview_url,
                previewUrl: (fileResult as any).preview_url,  // Keep both for compatibility
              }
            };
            
            setSessions(prev => ({
              ...prev,
              [activeSessionId]: {
                ...prev[activeSessionId],
                messages: [...(prev[activeSessionId]?.messages || []), fileStoredMsg]
              }
            }));
            
            // Persist (already marked persisted to avoid auto-save duplication)
            await enhancedApiService.persistMessage(activeSessionId, {
              message_id: fileStoredMsg.id,
              type: 'system',
              content: fileStoredMsg.content,
              metadata: fileStoredMsg.metadata
            });
            // Mark file stored message as persisted
            setSessions(prev => {
              const s = prev[activeSessionId];
              if (!s) return prev;
              const msgs = s.messages.map(m => m.id === fileStoredMsg.id ? { ...m, persisted: true } : m);
              return { ...prev, [activeSessionId]: { ...s, messages: msgs } };
            });
            
            addConsoleMessage('success', 'Upload', `File stored: ${fileResult.filename}`);
          } catch (e) {
            console.error('File upload failed:', e);
            addConsoleMessage('error', 'Upload', `Failed to upload ${f.name}`);
          }

          // Note: Do not trigger analysis here to avoid duplicate uploads.
          // Analysis will be triggered once after all files are uploaded using the backend replay mechanism.
        }
        // After uploading all files, trigger analysis by replaying stored files from backend once
        try {
          // Compose a single execution: include the user's text if provided
          if (replayInFlightRef.current[activeSessionId]) {
            addConsoleMessage('warning', 'Workflow', 'Replay already in progress – skipping duplicate trigger');
          } else {
            replayInFlightRef.current[activeSessionId] = true;
          }
          const replayResp = await enhancedApiService.replayFiles(activeSessionId, undefined, text?.trim() ? text : undefined);
          const parsedResponse = n8nWebhookService.parseWorkflowResponse(replayResp);
          if (parsedResponse && parsedResponse.resumeUrl) {
            n8nWebhookService.storeResumeUrl(activeSessionId, parsedResponse.resumeUrl);
            if (
              parsedResponse.status === 'text_extracted' ||
              parsedResponse.step === 'text_review' ||
              parsedResponse.approvalType === 'text_review' ||
              parsedResponse.data?.requiresApproval ||
              Boolean(parsedResponse.extractedText)
            ) {
              const textReviewMsg: ChatMessage = {
                id: `text-review-${Date.now()}`,
                type: 'system',
                messageType: 'status',
                content: parsedResponse.message || 'Text extracted. Please review before analysis.',
                timestamp: new Date(),
                sessionId: activeSessionId,
                  metadata: {
                    status: 'awaiting_approval',
                    extractedText: parsedResponse.extractedText,
                    data: { fullText: (parsedResponse as any)?.fullText },
                    textQuality: parsedResponse.textQuality,
                  qualityScore: parsedResponse.qualityScore,
                  qualityIssues: parsedResponse.qualityIssues,
                  recommendations: parsedResponse.recommendations,
                  hvacTermsFound: parsedResponse.hvacTermsFound,
                  actions: parsedResponse.actions,
                  progress: parsedResponse.progress ? {
                    percentage: parsedResponse.progress.percentage,
                    phase: parsedResponse.progress.phase,
                    description: parsedResponse.progress.description || '',
                    eta: parsedResponse.progress.eta || ''
                  } : undefined,
                  resumeUrl: parsedResponse.resumeUrl
                }
              };
              setSessions(prev => ({
                ...prev,
                [activeSessionId]: {
                  ...prev[activeSessionId],
                  messages: [...(prev[activeSessionId]?.messages || []), textReviewMsg]
                }
              }));
              // Focus the canvas on the new review node
              setFocusMessageId(textReviewMsg.id);
              setWorkflowState('awaiting_approval');
              addConsoleMessage('info', 'Workflow', 'Text extraction complete. Awaiting user approval.');
            } else if (parsedResponse.status === 'analysis_complete' || parsedResponse.step === 'analysis_review') {
              const analysisMsgId = `analysis-${Date.now()}`;
              const analysisMessage: ChatMessage = {
                id: analysisMsgId,
                type: 'assistant',
                messageType: 'analysis',
                content: parsedResponse.message || 'HVAC analysis complete. Please review.',
                timestamp: new Date(),
                sessionId: activeSessionId,
                metadata: {
                  analysisData: parsedResponse.analysis,
                  analysisQuality: parsedResponse.analysisQuality,
                  summary: parsedResponse.summary,
                  actions: parsedResponse.actions,
                  resumeUrl: parsedResponse.resumeUrl
                }
              };
              setSessions(prev => ({
                ...prev,
                [activeSessionId]: {
                  ...prev[activeSessionId],
                  messages: [...(prev[activeSessionId]?.messages || []), analysisMessage],
                  currentAnalysis: parsedResponse.analysis,
                  analysisMessageId: analysisMsgId,
                }
              }));
              // Focus the canvas on the review node
              setFocusMessageId(analysisMsgId);
              setWorkflowState('awaiting_approval');
              addConsoleMessage('success', 'Analysis', 'HVAC analysis complete. Ready for review.');
            } else if (parsedResponse.step === 'generation_confirmation' || parsedResponse.status === 'generation_complete') {
              n8nWebhookService.storeResumeUrl(activeSessionId, parsedResponse.resumeUrl || '');
              const confirmationMsg: ChatMessage = {
                id: `generation-confirm-${Date.now()}`,
                type: 'assistant',
                messageType: 'status',
                content: parsedResponse.message || 'BOG generated. Awaiting confirmation…',
                timestamp: new Date(),
                sessionId: activeSessionId,
                metadata: {
                  status: 'awaiting_approval',
                  actions: parsedResponse.actions,
                  resumeUrl: parsedResponse.resumeUrl
                }
              };
              setSessions(prev => ({
                ...prev,
                [activeSessionId]: {
                  ...prev[activeSessionId],
                  messages: [...(prev[activeSessionId]?.messages || []), confirmationMsg]
                }
              }));
              setWorkflowState('awaiting_approval');
              addConsoleMessage('info', 'Generation', 'Awaiting generation confirmation.');
            } else {
              // Fallback: we received a resumeUrl but not enough hints to classify; show generic approval
              const waitingMsg: ChatMessage = {
                id: `wait-approval-${Date.now()}`,
                type: 'system',
                messageType: 'status',
                content: parsedResponse.message || 'Awaiting your approval to continue…',
                timestamp: new Date(),
                sessionId: activeSessionId,
                metadata: {
                  status: 'awaiting_approval',
                  resumeUrl: parsedResponse.resumeUrl
                }
              } as any;
              setSessions(prev => ({
                ...prev,
                [activeSessionId]: {
                  ...prev[activeSessionId],
                  messages: [...(prev[activeSessionId]?.messages || []), waitingMsg]
                }
              }));
              setWorkflowState('awaiting_approval');
              addConsoleMessage('info', 'Workflow', 'Waiting for approval.');
            }
          }
        } catch (e) {
          console.warn('Replay trigger failed:', e);
        } finally {
          delete replayInFlightRef.current[activeSessionId];
        }
      } else if (text) {
        // Persist user text message first
        try {
          await apiService.persistMessage(activeSessionId, {
            message_id: userMessage.id,
            type: 'user',
            content: text,
            metadata: {},
            session_state: 'analyzing'
          });
          // Mark user text message as persisted
          setSessions(prev => {
            const s = prev[activeSessionId];
            if (!s) return prev;
            const msgs = s.messages.map(m => m.id === userMessage.id ? { ...m, persisted: true } : m);
            return { ...prev, [activeSessionId]: { ...s, messages: msgs } };
          });
        } catch {}

        const raw = await workflowAPI.sendChatMessage({ sessionId: activeSessionId, message: text, includeContext: true });
        const response = n8nWebhookService.parseWorkflowResponse(raw) || raw;
        if ((response?.status === 'ready_for_review' || response?.status === 'analysis_complete') && (response.analysis || response.summary)) {
          const analysisMsgId = `analysis-${Date.now()}`;
          const analysisMessage: ChatMessage = {
            id: analysisMsgId,
            type: 'assistant',
            content: response.message || 'HVAC analysis complete. Please review.',
            timestamp: new Date(),
            metadata: { analysisData: response.analysis }
          };
          setSessions(prev => ({
            ...prev,
            [activeSessionId]: {
              ...prev[activeSessionId],
              messages: [...(prev[activeSessionId]?.messages || []), analysisMessage],
              currentAnalysis: { ...response.analysis, _messageId: analysisMsgId },
              analysisMessageId: analysisMsgId,
            }
          }));
          setWorkflowState('awaiting_approval');
          try {
            await apiService.persistMessage(activeSessionId, {
              message_id: analysisMsgId,
              type: 'assistant',
              content: analysisMessage.content,
              metadata: { analysisData: response.analysis },
              session_state: 'awaiting_approval'
            });
            // Mark analysis message as persisted
            setSessions(prev => {
              const s = prev[activeSessionId];
              if (!s) return prev;
              const msgs = s.messages.map(m => m.id === analysisMsgId ? { ...m, persisted: true } : m);
              return { ...prev, [activeSessionId]: { ...s, messages: msgs } };
            });
          } catch {}
        } else if (response?.message) {
          const assistantMessage: ChatMessage = {
            id: `assistant-${Date.now()}`,
            type: 'assistant',
            content: response.message,
            timestamp: new Date(),
          };
          setSessions(prev => ({
            ...prev,
            [activeSessionId]: {
              ...prev[activeSessionId],
              messages: [...(prev[activeSessionId]?.messages || []), assistantMessage],
            }
          }));
          try { 
            await apiService.persistMessage(activeSessionId, { message_id: assistantMessage.id, type: 'assistant', content: assistantMessage.content });
            setSessions(prev => {
              const s = prev[activeSessionId];
              if (!s) return prev;
              const msgs = s.messages.map(m => m.id === assistantMessage.id ? { ...m, persisted: true } : m);
              return { ...prev, [activeSessionId]: { ...s, messages: msgs } };
            });
          } catch {}
        }
      }
    } catch (error: any) {
      const errMsg = typeof error?.message === 'string' ? error.message : 'Failed to send message';
      handleWorkflowFailure(errMsg);
    } finally {
      setIsLoading(false);
      clearAnalysisWatchdog();
    }
  }, [activeSessionId, addConsoleMessage]);
  // Handle analysis approval
  const handleApproveAnalysis = useCallback(async () => {
    if (!activeSessionId || !activeSession) return;
    setWorkflowState('generating');
    
    try {
      // Always use backend approval API to resume workflows
      const response = await workflowAPI.handleApproval({ sessionId: activeSessionId, action: 'approve_analysis' });

      if ((response?.status === 'complete' || response?.status === 'bog_generated') && response?.downloadUrl) {
        const bogMessage: ChatMessage = {
          id: `bog-${Date.now()}`,
          type: 'assistant',
          content: response.message || 'BOG file generated successfully!',
          timestamp: new Date(),
          metadata: { downloadUrl: response.downloadUrl }
        };
        
        setSessions(prev => ({
          ...prev,
          [activeSessionId]: {
            ...prev[activeSessionId],
            messages: [...(prev[activeSessionId]?.messages || []), bogMessage]
          }
        }));
        
        setWorkflowState('complete');
      } else if (response?.resumeUrl) {
        // If another wait step is returned, store resume URL client-side for UI
        n8nWebhookService.storeResumeUrl(activeSessionId, response.resumeUrl);
        setWorkflowState('awaiting_approval');
      }

      // Persist completion or status message
      try {
        const completeMsgId = `complete-${Date.now()}`;
        await apiService.persistMessage(activeSessionId, {
          message_id: completeMsgId,
          type: 'assistant',
          content: response?.message || 'Action completed',
          metadata: { downloadUrl: response?.downloadUrl },
          session_state: response?.downloadUrl ? 'complete' : 'awaiting_approval'
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
  }, [activeSessionId, activeSession, addConsoleMessage]);

  // Handle analysis changes request

  const handleResendMessage = useCallback(async (message: ChatMessage) => {
    if (!activeSessionId) return;
    
    console.log('Resending message:', message.id);

    const findLatestExtractedText = () => {
      const session = sessions[activeSessionId];
      if (!session) return undefined;
      for (let i = session.messages.length - 1; i >= 0; i--) {
        const m = session.messages[i] as any;
        const t = m?.metadata?.extractedText || m?.metadata?.data?.extractedText;
        if (t && typeof t === 'string' && t.trim()) return t;
      }
      return undefined;
    };
    
    // Update message status to sending
    setSessions(prev => {
      const session = prev[activeSessionId];
      if (!session) return prev;
      
      const updatedMessages = session.messages.map(m => 
        m.id === message.id ? { ...m, status: 'sending' as const } : m
      );
      
      return {
        ...prev,
        [activeSessionId]: {
          ...session,
          messages: updatedMessages
        }
      };
    });
    
    try {
      // Resend to backend for audit trail only (non-blocking)
      try { await enhancedApiService.resendMessage(activeSessionId, message); } catch {}
      
      // Always prefer backend replay first to avoid duplicate uploads
      let replaySucceeded = false;
      try {
        const replay = await enhancedApiService.replayFiles(activeSessionId, message.id);
        const parsed = n8nWebhookService.parseWorkflowResponse(replay);
        if (parsed?.status === 'text_extracted' || parsed?.step === 'text_review') {
          addConsoleMessage('success', 'Retry', 'Replayed stored files successfully');
          addToast('success', 'Retry', 'Replayed stored files successfully');
          // Render a Text Review approval message node
          const textReviewMsg: ChatMessage = {
            id: `text-review-${Date.now()}`,
            type: 'system',
            messageType: 'status',
            content: parsed?.message || 'Text extracted. Please review before analysis.',
            timestamp: new Date(),
            sessionId: activeSessionId,
            metadata: {
              status: 'awaiting_approval',
              extractedText: parsed?.extractedText,
              textQuality: parsed?.textQuality,
              qualityScore: parsed?.qualityScore,
              qualityIssues: parsed?.qualityIssues,
              recommendations: parsed?.recommendations,
              hvacTermsFound: parsed?.hvacTermsFound,
              actions: parsed?.actions,
              progress: parsed?.progress,
              resumeUrl: parsed?.resumeUrl
            }
          } as any;
          setSessions(prev => ({
            ...prev,
            [activeSessionId]: {
              ...prev[activeSessionId],
              messages: [...(prev[activeSessionId]?.messages || []), textReviewMsg]
            }
          }));
          setWorkflowState('awaiting_approval');
          replaySucceeded = true;
        } else if (parsed?.status === 'chat_ready' || parsed?.status === 'chat_response' || replay?.status === 'chat_ready') {
          const assistantMessage: ChatMessage = {
            id: `assistant-${Date.now()}`,
            type: 'assistant',
            content: parsed?.message || replay?.message || 'Ready.',
            timestamp: new Date(),
          } as any;
          setSessions(prev => ({
            ...prev,
            [activeSessionId]: {
              ...prev[activeSessionId],
              messages: [...(prev[activeSessionId]?.messages || []), assistantMessage]
            }
          }));
          setWorkflowState('idle');
          replaySucceeded = true;
        } else {
          throw new Error('Replay did not return a terminal state');
        }
      } catch (_err) {
        replaySucceeded = false;
      }
      
      // If replay didn’t work, try re-uploading local files (last resort)
      if (!replaySucceeded) {
        const isRealFile = (f: any) => !!f && typeof f === 'object' && 'name' in f && 'size' in f && typeof (f as any).arrayBuffer === 'function';
        const realFiles = Array.isArray(message.files) ? message.files.filter(isRealFile) as unknown as File[] : [];
        if (realFiles.length > 0) {
          await handleSendMessage(message.content, realFiles);
        } else {
          // No server files and no in-memory files: prompt user to re-upload or fallback to extracted text
          addToast('warning', 'Retry', 'Original files are not available. Re-upload the document or retry with extracted text.');
          // Fallback: re-analyze from extracted text or resend plain text
          const extracted = findLatestExtractedText();
          if (extracted) {
            setWorkflowState('analyzing');
            clearAnalysisWatchdog();
            analysisWatchdogRef.current = window.setTimeout(() => {
              handleWorkflowFailure('Workflow did not respond in time. You can retry.');
            }, 60000);
            // Re-run analysis through backend API (unified path)
            await workflowAPI.sendChatMessage({ sessionId: activeSessionId, message: extracted, includeContext: true });
            addConsoleMessage('info', 'Retry', 'Re-analyzing from extracted text');
            addToast('info', 'Retry', 'Re-analyzing from extracted text');
          } else {
            await handleSendMessage(message.content, []);
          }
        }
      }

      // Mark as sent
      setSessions(prev => {
        const session = prev[activeSessionId];
        if (!session) return prev;
        
        const updatedMessages = session.messages.map(m => 
          m.id === message.id ? { ...m, status: 'sent' as const } : m
        );
        
        return {
          ...prev,
          [activeSessionId]: {
            ...session,
            messages: updatedMessages
          }
        };
      });
      
      addConsoleMessage('success', 'Message', 'Message resent');
      addToast('success', 'Message', 'Message resent');
    } catch (error) {
      console.error('Failed to resend message:', error);
      
      // Mark as failed again
      setSessions(prev => {
        const session = prev[activeSessionId];
        if (!session) return prev;
        
        const updatedMessages = session.messages.map(m => 
          m.id === message.id ? { ...m, status: 'failed' as const } : m
        );
        
        return {
          ...prev,
          [activeSessionId]: {
            ...session,
            messages: updatedMessages
          }
        };
      });
      
      addConsoleMessage('error', 'Message', 'Failed to resend message');
      addToast('error', 'Message', 'Failed to resend message');
    }
  }, [activeSessionId, sessions, addConsoleMessage, handleSendMessage, clearAnalysisWatchdog, handleWorkflowFailure]);

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
      const response = await workflowAPI.handleApproval({ sessionId: activeSessionId, action: 'modify', feedback });
      
      if (response?.success || response?.status === 'refinement_requested') {
        const feedbackMessage: ChatMessage = {
          id: `feedback-${Date.now()}`,
          type: 'assistant', 
          content: response.message || 'Feedback received. Please provide updated sequence.',
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
        try { await apiService.persistMessage(activeSessionId, { message_id: feedbackMessage.id, type: 'assistant', content: feedbackMessage.content, session_state: 'idle' }); } catch {}
      }
      
    } catch (error) {
      // Handle error...
    }
  }, [activeSessionId]);

  return (
    <div style={{ width: '100vw', height: '100vh', overflow: 'hidden' }}>
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
        
        // session manager
        sessions={Object.values(sessions).map(s => ({ id: s.id, name: s.name, createdAt: s.createdAt }))}
        activeSessionId={activeSessionId}
        onCreateSession={createSession}
        onSwitchSession={switchSession}
        onDeleteSession={deleteSession}
        onRenameSession={renameSession}
        
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
    </div>
  );
};

export default App;
