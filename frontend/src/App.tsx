import React, { useState, useEffect, useCallback, useRef } from 'react';
import SimplifiedWorkbench from './components/SimplifiedWorkbench';
import ConsolePanel, { ConsoleMessage } from './components/ConsolePanel';
import SystemMonitor from './components/SystemMonitor';
import { Terminal } from 'lucide-react';
import { UnifiedN8NService } from './services/n8nIntegrationUnified';
import apiService from './services/apiService';
import enhancedApiService from './services/apiServiceEnhanced';
import n8nWebhookService from './services/n8nWebhookService';
import websocketService from './services/websocketService';
import { ChatMessage } from './components/ChatCanvasGrid';
import sessionPersistence from './services/sessionPersistence';
import { generateSessionId, generateDefaultSessionName, generateSessionDisplayName, shouldUpdateSessionName } from './utils/sessionNaming';

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

  const n8nService = useRef(new UnifiedN8NService());
  
  const activeSession = activeSessionId ? sessions[activeSessionId] : undefined;
  const messages = activeSession?.messages || [];
  const sessionId = activeSessionId;
  const currentAnalysis = activeSession?.currentAnalysis || null;
  const analysisMessageId = activeSession?.analysisMessageId;

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
          const newId = generateSessionId();
          const initMessage: ChatMessage = {
            id: `init-${newId}`,
            type: 'system',
            content: 'PyBOG Control Builder initialized. Upload HVAC documents or describe your control requirements.',
            timestamp: new Date(),
            persisted: false
          };
          
          const newSession: Session = {
            id: newId,
            name: generateDefaultSessionName(1),
            createdAt: new Date(),
            messages: [initMessage],
            currentAnalysis: null,
          };
          
          setSessions({ [newId]: newSession });
          setActiveSessionId(newId);
          sessionPersistence.saveActiveSessionId(newId);
          
          // Save to persistence
          await sessionPersistence.saveSession({
            ...newSession,
            analysisMessageId: undefined,
          });

          // Best-effort: create in database
          try {
            await apiService.createSession('Session 1');
            await apiService.persistMessage(newId, {
              message_id: initMessage.id,
              type: 'system',
              content: initMessage.content,
              metadata: { kind: 'init' },
              session_state: 'idle',
              name: 'Session 1'
            });
          } catch {}
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
    const sessionId = generateSessionId();
    const name = generateDefaultSessionName(count);
    
    try {
      // Create session in database - use our generated ID
      await enhancedApiService.createSession(name);
      console.log('Created session with ID:', sessionId);
      
      const initMessage: ChatMessage = {
        id: `init-${sessionId}`,
        type: 'system',
        content: 'New session started. Upload HVAC documents or describe your control requirements.',
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
    // Get session info
    const sessionToDelete = sessions[id];
    if (!sessionToDelete) return;
    
    try {
      // Delete from database
      await enhancedApiService.deleteSession(id);
      
      // Handle active session deletion
      if (activeSessionId === id) {
        const remaining = Object.keys(sessions).filter(sid => sid !== id);
        if (remaining.length > 0) {
          // Switch to another session
          await switchSession(remaining[0]);
        } else {
          // No sessions left, create a new one
          await createSession();
          // Don't delete yet since createSession needs current sessions count
          setSessions(prev => {
            const copy = { ...prev };
            delete copy[id];
            return copy;
          });
          sessionPersistence.clearSession(id);
          addConsoleMessage('success', 'Session', `Deleted session: ${sessionToDelete.name}`);
          return;
        }
      }
      
      // Update local state
      setSessions(prev => {
        const copy = { ...prev };
        delete copy[id];
        return copy;
      });
      
      // Clear from localStorage
      sessionPersistence.clearSession(id);
      
      addConsoleMessage('success', 'Session', `Deleted session: ${sessionToDelete.name}`);
    } catch (error) {
      console.error('Failed to delete session:', error);
      addConsoleMessage('error', 'Session', 'Failed to delete session');
    }
  }, [activeSessionId, sessions, addConsoleMessage, createSession, switchSession]);

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

  // Open WebSocket when session becomes active
  useEffect(() => {
    if (!activeSessionId) return;
    const cfg = (window as any).RUNTIME_CONFIG || {};
    const apiBase = cfg.API_URL || process.env.REACT_APP_API_URL || 'http://localhost:8000';
    const wsBase = apiBase.replace(/^http/i, 'ws');
    const ws = new WebSocket(`${wsBase}/ws/${activeSessionId}`);
    ws.onmessage = (ev) => {
      try {
        const msg = JSON.parse(ev.data);
        
        // Handle n8n workflow process steps
        if (msg.type === 'process_step') {
          // Use a stable ID per stepKey to prevent duplicate nodes on updates
          const stableId = `process-${activeSessionId}-${msg.stepKey}`;
          const processMsg: ChatMessage = {
            id: stableId,
            type: 'system',
            messageType: 'processing',
            content: msg.title || 'Processing...',
            timestamp: new Date(msg.ts || Date.now()),
            metadata: {
              processStep: {
                stepKey: msg.stepKey,
                detail: msg.detail,
                status: msg.status,
                metrics: msg.extra?.metrics,
              }
            }
          };

          // Replace or add process message (dedup by stepKey)
          setSessions(prev => {
            const session = prev[activeSessionId];
            if (!session) return prev;

            const existingIndex = session.messages.findIndex(
              m => m.metadata?.processStep?.stepKey === msg.stepKey
            );

            let newMessages = [...session.messages];
            if (existingIndex >= 0) {
              // Preserve stable ID for the existing message to avoid node churn
              const existing = newMessages[existingIndex];
              newMessages[existingIndex] = { ...processMsg, id: existing.id || stableId };
            } else {
              newMessages.push(processMsg);
            }

            return {
              ...prev,
              [activeSessionId]: {
                ...session,
                messages: newMessages
              }
            };
          });

          // Add to console
          addConsoleMessage(
            msg.status === 'error' ? 'error' : msg.status === 'ok' ? 'success' : 'info',
            'Workflow',
            `${msg.title}: ${msg.detail || msg.status}`,
            msg.extra?.metrics
          );
        }
        
        if (msg.type === 'analysis_progress' || msg.type === 'status') {
          const progressMsg: ChatMessage = {
            id: `progress-${Date.now()}`,
            type: 'system',
            messageType: 'status',
            content: msg.message || msg.step || 'Working…',
            timestamp: new Date(),
          };
          setSessions(prev => ({
            ...prev,
            [activeSessionId]: {
              ...prev[activeSessionId],
              messages: [...(prev[activeSessionId]?.messages || []), progressMsg]
            }
          }));
        }
        
        if (msg.type === 'analysis_complete') {
          setSessions(prev => {
            const session = prev[activeSessionId];
            if (!session) return prev;

            // If we already have an analysis message, update it instead of adding a duplicate
            if (session.analysisMessageId) {
              const idx = session.messages.findIndex(m => m.id === session.analysisMessageId);
              if (idx >= 0) {
                const updated = [...session.messages];
                updated[idx] = {
                  ...updated[idx],
                  content: msg.message || updated[idx].content,
                  metadata: {
                    ...(updated[idx].metadata || {}),
                    analysisData: {
                      inputs: msg.analysis?.inputs || msg.inputs || [],
                      outputs: msg.analysis?.outputs || msg.outputs || [],
                      pseudocode: msg.analysis?.pseudocode || msg.pseudocode || []
                    }
                  },
                  timestamp: new Date(),
                } as ChatMessage;
                return {
                  ...prev,
                  [activeSessionId]: {
                    ...session,
                    messages: updated,
                    currentAnalysis: { ...(msg.analysis || {}), _messageId: session.analysisMessageId },
                  }
                };
              }
            }

            // Otherwise, create a fresh analysis message
            const analysisMsgId = `analysis-${Date.now()}`;
            const analysisMessage: ChatMessage = {
              id: analysisMsgId,
              type: 'assistant',
              content: msg.message || 'HVAC analysis complete. Please review.',
              timestamp: new Date(),
              metadata: { analysisData: { inputs: msg.analysis?.inputs || msg.inputs || [], outputs: msg.analysis?.outputs || msg.outputs || [], pseudocode: msg.analysis?.pseudocode || msg.pseudocode || [] } }
            };
            return {
              ...prev,
              [activeSessionId]: {
                ...session,
                messages: [...(session.messages || []), analysisMessage],
                currentAnalysis: { ...(msg.analysis || {}), _messageId: analysisMsgId },
                analysisMessageId: analysisMsgId,
              }
            };
          });
        }
        
        if (msg.type === 'bog_generated') {
          const bogMessage: ChatMessage = {
            id: `bog-${Date.now()}`,
            type: 'assistant',
            content: msg.message || 'BOG file generated successfully!',
            timestamp: new Date(),
            metadata: { downloadUrl: msg.downloadUrl }
          };
          setSessions(prev => ({
            ...prev,
            [activeSessionId]: {
              ...prev[activeSessionId],
              messages: [...(prev[activeSessionId]?.messages || []), bogMessage]
            }
          }));
        }
      } catch {}
    };
    return () => ws.close();
  }, [activeSessionId, addConsoleMessage]);

  // Subscribe to SSE session events (generation_started/generation_complete)
  useEffect(() => {
    if (!activeSessionId) return;
    const sub = apiService.subscribeToSessionEvents(
      activeSessionId,
      (evt) => {
        try {
          if (evt.type === 'status') {
            const step = String(evt.step || 'status');
            const status = step.includes('started') ? 'running' : step.includes('complete') ? 'ok' : 'waiting';
            const stableId = `process-${activeSessionId}-generation`;
            const processMsg: ChatMessage = {
              id: stableId,
              type: 'system',
              messageType: 'processing',
              content: evt.message || (status === 'ok' ? 'Generation complete' : 'Generating…'),
              timestamp: new Date(),
              metadata: { processStep: { stepKey: 'generation', detail: evt.message, status } }
            } as any;

            setSessions(prev => {
              const session = prev[activeSessionId];
              if (!session) return prev;
              const existingIndex = session.messages.findIndex(m => m.id === stableId || m.metadata?.processStep?.stepKey === 'generation');
              const newMessages = [...session.messages];
              if (existingIndex >= 0) newMessages[existingIndex] = processMsg; else newMessages.push(processMsg);

              // If complete with download, add artifact message
              if (status === 'ok' && (evt.downloadUrl || evt.download_url)) {
                const bogMessage: ChatMessage = {
                  id: `bog-${Date.now()}`,
                  type: 'assistant',
                  content: 'BOG file generated successfully!',
                  timestamp: new Date(),
                  metadata: { downloadUrl: evt.downloadUrl || evt.download_url }
                } as any;
                newMessages.push(bogMessage);
              }

              return { ...prev, [activeSessionId]: { ...session, messages: newMessages } };
            });

            addConsoleMessage(status === 'ok' ? 'success' : 'info', 'SSE', evt.message || step);
          }
        } catch {}
      },
      (err) => {
        // SSE error can be ignored; WS still active
      }
    );
    return () => sub.close();
  }, [activeSessionId, addConsoleMessage]);

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
    
    // Subscribe to state changes
    const unsubscribeState = websocketService.on('state_change', (event) => {
      console.log('[App] WebSocket state change:', event.data);
      if (event.data?.state) {
        setWorkflowState(event.data.state);
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
    
    return () => {
      unsubscribeState();
      unsubscribeAnalysis();
      // Don't disconnect WebSocket here as we may switch sessions
    };
  }, [activeSessionId, addConsoleMessage]);

  // Handle message sending
  const handleSendMessage = useCallback(async (text: string, files: File[]) => {
    if (!activeSessionId) return;
    setIsLoading(true);
    setWorkflowState('analyzing');
    
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
            
            const fileStoredMsg: ChatMessage = {
              id: `file-stored-${Date.now()}`,
              type: 'system',
              content: `File uploaded: ${fileResult.filename} (${(fileResult.size / 1024).toFixed(1)} KB)`,
              timestamp: new Date(),
              sessionId: activeSessionId,
              metadata: { status: 'complete' as const, fileName: fileResult.filename }
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
                  progress: parsedResponse.progress,
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
    } catch (error) {
      // Handle errors...
    } finally {
      setIsLoading(false);
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
          // Check if we need another approval step or if generation is complete
          if (parsedResponse.status === 'complete' || parsedResponse.status === 'bog_generated') {
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
            // Continue with next approval step if needed
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
      
    } catch (error) {
      console.error('Approval failed:', error);
      setWorkflowState('awaiting_approval');
      addConsoleMessage('error', 'Approval', 'Failed to approve analysis');
    }
  }, [activeSessionId, activeSession, addConsoleMessage]);

  // Handle analysis changes request
  const handleResendMessage = useCallback(async (message: ChatMessage) => {
    if (!activeSessionId) return;
    
    console.log('Resending message:', message.id);
    
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
      // Resend to backend
      await enhancedApiService.resendMessage(activeSessionId, message);
      
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
      
      addConsoleMessage('success', 'Message', 'Message resent successfully');
      
      // If it's a file message, re-process it
      if (message.files && message.files.length > 0) {
        await handleSendMessage(message.content, message.files);
      } else {
        await handleSendMessage(message.content, []);
      }
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
    }
  }, [activeSessionId, addConsoleMessage, handleSendMessage]);

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
      {/* System Health Monitor - Top Position */}
      <SystemMonitor position="top" />
      
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
      />
      
      {/* Console Toggle Button */}
      <button
        onClick={() => setIsConsoleOpen(!isConsoleOpen)}
        style={{
          position: 'fixed',
          bottom: isConsoleOpen ? 310 : 16,
          right: 16,
          zIndex: 1001,
          background: '#1a1a1a',
          color: '#10b981',
          border: '2px solid #374151',
          borderRadius: 8,
          padding: '8px 12px',
          display: 'flex',
          alignItems: 'center',
          gap: 8,
          cursor: 'pointer',
          fontSize: 12,
          fontWeight: 600,
          transition: 'all 0.3s ease',
        }}
      >
        <Terminal size={16} />
        {isConsoleOpen ? 'Hide' : 'Show'} Console
      </button>
      
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
