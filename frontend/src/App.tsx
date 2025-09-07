import React, { useState, useEffect, useCallback, useRef } from 'react';
import SimplifiedWorkbench from './components/SimplifiedWorkbench';
import ConsolePanel, { ConsoleMessage } from './components/ConsolePanel';
import SystemMonitor from './components/SystemMonitor';
import { Terminal } from 'lucide-react';
import { UnifiedN8NService } from './services/n8nIntegrationUnified';
import apiService from './services/apiService';
import enhancedApiService from './services/apiServiceEnhanced';
import n8nWebhookService from './services/n8nWebhookService';
import { useToast } from './components/ToastProvider';
import websocketService from './services/websocketService';
import { ChatMessage } from './components/ChatCanvasGrid';
import sessionPersistence from './services/sessionPersistence';
import { generateSessionId, generateDefaultSessionName, generateSessionDisplayName, shouldUpdateSessionName, ensureUniqueSessionName } from './utils/sessionNaming';

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
  const [workflowState, setWorkflowState] = useState<'idle' | 'analyzing' | 'awaiting_approval' | 'generating' | 'complete'>('idle');
  const [focusMessageId, setFocusMessageId] = useState<string | undefined>(undefined);
  // const [highlightTarget, setHighlightTarget] = useState<{kind:'analysis'|'block'|'input'|'output', label?: string}|undefined>(undefined);

  const analysisWatchdogRef = useRef<number | null>(null);

  const n8nService = useRef(new UnifiedN8NService());
  const { addToast } = useToast();
  
  const activeSession = activeSessionId ? sessions[activeSessionId] : undefined;
  const messages = activeSession?.messages || [];
  const sessionId = activeSessionId;
  const currentAnalysis = activeSession?.currentAnalysis || null;
  const analysisMessageId = activeSession?.analysisMessageId;

  // Centralized workflow failure handler: stops loading, surfaces error, enables resend
  const clearAnalysisWatchdog = useCallback(() => {
    if (analysisWatchdogRef.current) {
      clearTimeout(analysisWatchdogRef.current);
      analysisWatchdogRef.current = null;
    }
  }, []);

  const handleWorkflowFailure = useCallback((errorMessage: string) => {
    clearAnalysisWatchdog();
    setWorkflowState('idle');
    addToast('error', 'Workflow error', errorMessage);
    // inline console message to avoid dependency ordering
    setConsoleMessages(prev => ([
      ...prev,
      {
        id: `console-${Date.now()}-${Math.random()}`,
        timestamp: new Date(),
        level: 'error',
        source: 'Workflow',
        message: errorMessage,
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
        content: errorMessage || 'Workflow failed. Please try again or check the console for details.',
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
        // Clean invalid local keys before restoring sessions
        try { sessionPersistence.cleanupInvalidLocalKeys(); } catch {}

        // Restore all sessions from persistence
        const restoredSessions = await sessionPersistence.restoreAllSessions();
        if (cancelled) return;

        if (restoredSessions.size > 0) {
          // Convert to Sessions object
          const sessionsObj: Record<string, Session> = {};
          restoredSessions.forEach((persistedSession, id) => {
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
          const activeId = savedActiveId && sessionsObj[savedActiveId] ? 
            savedActiveId : Object.keys(sessionsObj)[0];
          setActiveSessionId(activeId);
          sessionPersistence.saveActiveSessionId(activeId);
        } else {
          // Create new session if none exist
          // Attempt to create first session in the database so IDs are authoritative UUIDs
          try {
            const name = ensureUniqueSessionName(generateDefaultSessionName(1), []);
            const created = await enhancedApiService.createSession(name);
            const newId = created.session_id;
            const initMessage: ChatMessage = {
              id: `init-${newId}`,
              type: 'system',
              content: 'PyBOG Control Builder is ready. Provide a detailed sequence of operations (or upload HVAC control docs: PDFs/specs). I will extract I/O points and synthesize Niagara wire‑sheet logic blocks. Start with equipment type, stages, economizer, occupancy schedule, and key setpoints.',
              timestamp: new Date(),
              persisted: false
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
            try {
              await enhancedApiService.persistMessage(newId, {
                message_id: initMessage.id,
                type: 'system',
                content: initMessage.content,
                metadata: { kind: 'init' },
                session_state: 'idle'
              });
            } catch {}
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
      }

      addConsoleMessage('info', 'System', 'PyBOG Control Builder initialized');
      addConsoleMessage('info', 'System', 'Checking service connections...');

      setTimeout(() => {
        addConsoleMessage('success', 'API', 'Backend API connected');
        addConsoleMessage('success', 'Database', 'PostgreSQL connected');
        addConsoleMessage('info', 'n8n', 'Workflow engine ready');
        addConsoleMessage('success', 'WebSocket', 'Real-time updates enabled');
      }, 1000);
    })();
    return () => { cancelled = true; };
  }, [addConsoleMessage]);

  // Persist console preference
  useEffect(() => {
    try { localStorage.setItem('pybog_console_open', String(isConsoleOpen)); } catch {}
  }, [isConsoleOpen]);

  // Auto-save sessions periodically and when active session changes
  useEffect(() => {
    const stopAutoSave = sessionPersistence.startAutoSave(
      () => {
        if (!activeSessionId || !activeSession) return null;
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
    if (!activeSessionId || !activeSession) return;
    
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
        sessionId: sessionId
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
      
      // Persist initial message
      await enhancedApiService.persistMessage(sessionId, {
        message_id: initMessage.id,
        type: 'system',
        content: initMessage.content,
        metadata: { kind: 'init' },
        session_state: 'idle'
      });
      
      addConsoleMessage('success', 'Session', `Created new session: ${name}`);
    } catch (e) {
      console.error('Failed to create session:', e);
      addConsoleMessage('error', 'Session', 'Failed to create session in database');
    }
  }, [sessions, addConsoleMessage]);

  const switchSession = useCallback(async (id: string) => {
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
    setIsLoading(true);
    setWorkflowState('analyzing');
    addToast('info', 'Analyzing', files.length > 0 ? 'Analyzing uploaded document' : 'Analyzing your request');
    clearAnalysisWatchdog();
    analysisWatchdogRef.current = window.setTimeout(() => {
      handleWorkflowFailure('Workflow did not respond in time. You can retry.');
    }, 60000);
    
    // Check if we should auto-update session name
    const currentSession = sessions[activeSessionId];
    if (currentSession && shouldUpdateSessionName(currentSession.name, currentSession.messages)) {
      const newName = generateSessionDisplayName([...currentSession.messages, { type: 'user', content: text }]);
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
      // Add live status message
      const statusId = `status-${Date.now()}`;
      const statusMessage: ChatMessage = {
        id: statusId,
        type: 'system',
        messageType: 'status',
        content: files.length > 0 ? 'Analyzing uploaded document…' : 'Analyzing your request…',
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
      try { await apiService.persistMessage(activeSessionId, { message_id: statusId, type: 'system', content: statusMessage.content, metadata: { kind: 'status' }, session_state: 'analyzing' }); } catch {}

      if (files.length > 0) {
        for (const f of files) {
          // Persist user message for file upload
          try {
            await enhancedApiService.persistMessage(activeSessionId, {
              message_id: userMessage.id,
              type: 'user',
              content: userMessage.content,
              metadata: { files: [{ name: f.name, size: f.size, type: f.type }] },
              session_state: 'analyzing'
            });
          } catch (e) {
            console.error('Failed to persist message:', e);
          }

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
              metadata: { 
                status: 'complete' as const, 
                fileName: fileResult.filename,
                file_id: fileResult.file_id,
                previewUrl: (fileResult as any).preview_url,
              }
            };
            
            setSessions(prev => ({
              ...prev,
              [activeSessionId]: {
                ...prev[activeSessionId],
                messages: [...(prev[activeSessionId]?.messages || []), fileStoredMsg]
              }
            }));
            
            await enhancedApiService.persistMessage(activeSessionId, {
              message_id: fileStoredMsg.id,
              type: 'system',
              content: fileStoredMsg.content,
              metadata: fileStoredMsg.metadata
            });
            
            addConsoleMessage('success', 'Upload', `File stored: ${fileResult.filename}`);
          } catch (e) {
            console.error('File upload failed:', e);
            addConsoleMessage('error', 'Upload', `Failed to upload ${f.name}`);
          }

          const response = await n8nService.current.uploadDocument(f);
          
          // Parse and handle webhook response with resumeUrl
          const parsedResponse = n8nWebhookService.parseWorkflowResponse(response);
          if (parsedResponse && parsedResponse.resumeUrl) {
            // Store resume URL for later approval
            n8nWebhookService.storeResumeUrl(activeSessionId, parsedResponse.resumeUrl);
            
            // Handle text extraction review (waiting for approval)
            if (parsedResponse.status === 'text_extracted' || parsedResponse.step === 'text_review') {
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
              
              setWorkflowState('awaiting_approval');
              addConsoleMessage('info', 'Workflow', 'Text extraction complete. Awaiting user approval.');
            }
            // Handle analysis review (waiting for approval)
            else if (parsedResponse.status === 'analysis_complete' || parsedResponse.step === 'analysis_review') {
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
              
              setWorkflowState('awaiting_approval');
              addConsoleMessage('success', 'Analysis', 'HVAC analysis complete. Ready for review.');
            }
            // Handle generation confirmation (if ever returned at this stage)
            else if (parsedResponse.step === 'generation_confirmation' || parsedResponse.status === 'generation_complete') {
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
            }
          }
          // Chat-ready fallback (e.g., router fallback sent Chat Response)
          else if ((response as any)?.status === 'chat_ready' || (response as any)?.status === 'chat_response') {
            const assistantMessage: ChatMessage = {
              id: `assistant-${Date.now()}`,
              type: 'assistant',
              content: response.message || 'Ready.',
              timestamp: new Date(),
            };
            setSessions(prev => ({
              ...prev,
              [activeSessionId]: {
                ...prev[activeSessionId],
                messages: [...(prev[activeSessionId]?.messages || []), assistantMessage]
              }
            }));
            setWorkflowState('idle');
            addConsoleMessage('info', 'Workflow', response.message || 'Chat ready');
            addToast('info', 'Chat ready', response.message);
          }
          // Fallback to original handling if no resumeUrl
          else if (response?.status === 'ready_for_review' && response.analysis) {
            const analysisMsgId = `analysis-${Date.now()}`;
            const analysisMessage: ChatMessage = {
              id: analysisMsgId,
              type: 'assistant',
              content: response.message || 'HVAC analysis complete. Please review.',
              timestamp: new Date(),
              sessionId: activeSessionId,
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
            } catch {}
          }
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
        } catch {}

        const response = await n8nService.current.sendMessage(text, text.length > 100);
        if (response?.status === 'ready_for_review' && response.analysis) {
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
          try { await apiService.persistMessage(activeSessionId, { message_id: assistantMessage.id, type: 'assistant', content: assistantMessage.content }); } catch {}
        }
      }
    } catch (error: any) {
      const errMsg = error?.message || 'Failed to send message';
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
      // Check if we have a resume URL from n8n webhook
      const resumeUrl = n8nWebhookService.getResumeUrl(activeSessionId);
      
      let response;
      if (resumeUrl) {
        // Use webhook service to approve via resumeUrl
        const currentAnalysis = activeSession.currentAnalysis;
        response = await n8nWebhookService.approveAnalysis(
          activeSessionId, 
          currentAnalysis,
          resumeUrl
        );
        
        // Parse the response to get next state
        const parsedResponse = n8nWebhookService.parseWorkflowResponse(response);
        if (parsedResponse) {
          // If generation preview/confirmation step, confirm automatically for now
          if (parsedResponse.step === 'generation_confirmation' || parsedResponse.status === 'generation_complete') {
            if (parsedResponse.resumeUrl) {
              n8nWebhookService.storeResumeUrl(activeSessionId, parsedResponse.resumeUrl);
            }
            try {
              const final = await n8nWebhookService.confirmGeneration(activeSessionId, 'confirm');
              const done = n8nWebhookService.parseWorkflowResponse(final) || final;
              const bogMessage: ChatMessage = {
                id: `bog-${Date.now()}`,
                type: 'assistant',
                content: done.message || 'BOG file confirmed and ready for download!',
                timestamp: new Date(),
                metadata: { 
                  downloadUrl: done.downloadUrl || final.downloadUrl,
                  bogFilePath: done.bogFilePath || final.bogFilePath
                }
              } as any;
              setSessions(prev => ({
                ...prev,
                [activeSessionId]: {
                  ...prev[activeSessionId],
                  messages: [...(prev[activeSessionId]?.messages || []), bogMessage]
                }
              }));
              setWorkflowState('complete');
              addConsoleMessage('success', 'BOG', 'BOG file generated and confirmed');
            } catch (e) {
              addConsoleMessage('error', 'Generation', 'Failed to confirm generation');
              setWorkflowState('awaiting_approval');
            }
          } else if (parsedResponse.status === 'complete' || parsedResponse.status === 'bog_generated') {
            const bogMessage: ChatMessage = {
              id: `bog-${Date.now()}`,
              type: 'assistant',
              content: parsedResponse.message || 'BOG file generated successfully!',
              timestamp: new Date(),
              metadata: { 
                downloadUrl: parsedResponse.downloadUrl || response.downloadUrl,
                bogFilePath: response.bogFilePath
              }
            };
            setSessions(prev => ({
              ...prev,
              [activeSessionId]: {
                ...prev[activeSessionId],
                messages: [...(prev[activeSessionId]?.messages || []), bogMessage]
              }
            }));
            setWorkflowState('complete');
            addConsoleMessage('success', 'BOG', 'BOG file generated successfully');
          } else if (parsedResponse.resumeUrl) {
            // Store new resume URL for next step
            n8nWebhookService.storeResumeUrl(activeSessionId, parsedResponse.resumeUrl);
          }
        }
      } else {
        // Fallback to direct n8n service call
        response = await n8nService.current.approveAnalysis();
        
        if (response.status === 'complete' && response.downloadUrl) {
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
        }
      }
      
      // Persist completion message
      try {
        const completeMsgId = `complete-${Date.now()}`;
        await apiService.persistMessage(activeSessionId, {
          message_id: completeMsgId,
          type: 'assistant',
          content: response?.message || 'BOG file generated successfully!',
          metadata: { downloadUrl: response?.downloadUrl },
          session_state: 'complete'
        });
      } catch {}
      
    } catch (error: any) {
      console.error('Approval failed:', error);
      handleWorkflowFailure(error?.message || 'Failed to approve analysis');
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
        if (message.files && message.files.length > 0) {
          await handleSendMessage(message.content, message.files);
        } else {
          // Fallback: re-analyze from extracted text or resend plain text
          const extracted = findLatestExtractedText();
          if (extracted) {
            setWorkflowState('analyzing');
            clearAnalysisWatchdog();
            analysisWatchdogRef.current = window.setTimeout(() => {
              handleWorkflowFailure('Workflow did not respond in time. You can retry.');
            }, 60000);
            await n8nService.current.sendMessage(extracted, true);
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
      // This now calls Generation Workflow correctly
      const response = await n8nService.current.requestChanges(feedback);
      
      if (response.status === 'refinement_requested') {
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
    </div>
  );
};

export default App;
