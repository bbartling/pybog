import React, { useState, useEffect, useCallback, useRef } from 'react';
import SimplifiedWorkbench from './components/SimplifiedWorkbench';
import HealthStatus from './components/HealthStatus';
import ConsolePanel, { ConsoleMessage } from './components/ConsolePanel';
import { Terminal } from 'lucide-react';
import { UnifiedN8NService } from './services/n8nIntegrationUnified';
import apiService from './services/apiService';
import { ChatMessage } from './components/ChatCanvas';

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
  const [highlightTarget, setHighlightTarget] = useState<{kind:'analysis'|'block'|'input'|'output', label?: string}|undefined>(undefined);

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

  // Restore most recent session from database, else create a new one
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const recent = await apiService.getRecentSessions(1);
        if (cancelled) return;
        if (recent.sessions && recent.sessions.length > 0) {
          const sid = recent.sessions[0].session_id;
          const full = await apiService.getFullSession(sid);
          if (cancelled) return;
          const restoredMessages: ChatMessage[] = (full.messages || []).map((m: any) => ({
            id: m.message_id,
            type: (m.type as any) || 'system',
            content: String(m.content || ''),
            timestamp: new Date(m.created_at || Date.now()),
            metadata: m.metadata || undefined,
          }));
          const initialSession: Session = {
            id: sid,
            name: full.session?.name || 'Restored Session',
            createdAt: new Date(full.session?.last_activity || Date.now()),
            messages: restoredMessages,
            currentAnalysis: full.analysis?.analysis_data || null,
            analysisMessageId: undefined,
          };
          setSessions({ [sid]: initialSession });
          setActiveSessionId(sid);
        } else {
          const newId = `session_${Date.now()}`;
          const initMessage: ChatMessage = {
            id: `init-${newId}`,
            type: 'system',
            content: 'PyBOG Control Builder initialized. Upload HVAC documents or describe your control requirements.',
            timestamp: new Date()
          };
          setSessions({
            [newId]: {
              id: newId,
              name: 'Session 1',
              createdAt: new Date(),
              messages: [initMessage],
              currentAnalysis: null,
            }
          });
          setActiveSessionId(newId);
          // Best-effort: create session + persist init message
          try {
            await apiService.createSession(newId, 'Session 1');
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
        // Fallback: local-only init
        const fallbackId = `session_${Date.now()}`;
        const init: ChatMessage = {
          id: `init-${fallbackId}`,
          type: 'system',
          content: 'PyBOG Control Builder initialized. Upload HVAC documents or describe your control requirements.',
          timestamp: new Date()
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

  // Session actions
  const createSession = useCallback(async () => {
    const newId = `session_${Date.now()}`;
    const count = Object.keys(sessions).length + 1;
    const name = `Session ${count}`;
    const initMessage: ChatMessage = {
      id: `init-${newId}`,
      type: 'system',
      content: 'New session started. Upload HVAC documents or describe your control requirements.',
      timestamp: new Date()
    };
    setSessions(prev => ({
      ...prev,
      [newId]: {
        id: newId,
        name,
        createdAt: new Date(),
        messages: [initMessage],
        currentAnalysis: null,
      }
    }));
    setActiveSessionId(newId);
    setFocusMessageId(undefined);
    // Persist session + init message
    try {
      await apiService.createSession(newId, name);
      await apiService.persistMessage(newId, {
        message_id: initMessage.id,
        type: 'system',
        content: initMessage.content,
        metadata: { kind: 'init' },
        session_state: 'idle',
        name
      });
    } catch (e) {
      // best-effort
    }
  }, [sessions]);

  const switchSession = useCallback(async (id: string) => {
    try {
      const full = await apiService.getFullSession(id);
      const restoredMessages: ChatMessage[] = (full.messages || []).map((m: any) => ({
        id: m.message_id,
        type: (m.type as any) || 'system',
        content: String(m.content || ''),
        timestamp: new Date(m.created_at || Date.now()),
        metadata: m.metadata || undefined,
      }));
      setSessions(prev => ({
        ...prev,
        [id]: {
          id,
          name: full.session?.name || prev[id]?.name || 'Session',
          createdAt: prev[id]?.createdAt || new Date(full.session?.last_activity || Date.now()),
          messages: restoredMessages,
          currentAnalysis: full.analysis?.analysis_data || null,
          analysisMessageId: undefined,
        }
      }));
      setActiveSessionId(id);
      setFocusMessageId(undefined);
    } catch (e) {
      if (sessions[id]) {
        setActiveSessionId(id);
        setFocusMessageId(undefined);
      }
    }
  }, [sessions]);

  const deleteSession = useCallback((id: string) => {
    setSessions(prev => {
      const copy = { ...prev };
      delete copy[id];
      return copy;
    });
    if (activeSessionId === id) {
      const remaining = Object.keys(sessions).filter(sid => sid !== id);
      const nextId = remaining[0];
      setActiveSessionId(nextId || '');
    }
  }, [activeSessionId, sessions]);

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
        if (msg.type === 'analysis_progress') {
          const progressMsg: ChatMessage = {
            id: `progress-${Date.now()}`,
            type: 'system',
            messageType: 'status',
            content: msg.message || 'Working…',
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
          const analysisMsgId = `analysis-${Date.now()}`;
          const analysisMessage: ChatMessage = {
            id: analysisMsgId,
            type: 'assistant',
            content: msg.message || 'HVAC analysis complete. Please review.',
            timestamp: new Date(),
            metadata: { analysisData: { inputs: msg.analysis?.inputs || msg.inputs || [], outputs: msg.analysis?.outputs || msg.outputs || [], pseudocode: msg.analysis?.pseudocode || msg.pseudocode || [] } }
          };
          setSessions(prev => ({
            ...prev,
            [activeSessionId]: {
              ...prev[activeSessionId],
              messages: [...(prev[activeSessionId]?.messages || []), analysisMessage],
              currentAnalysis: { ...(msg.analysis || {}), _messageId: analysisMsgId },
              analysisMessageId: analysisMsgId,
            }
          }));
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
  }, [activeSessionId]);

  // Handle message sending
  const handleSendMessage = useCallback(async (text: string, files: File[]) => {
    if (!activeSessionId) return;
    setIsLoading(true);
    setWorkflowState('analyzing');
    
    // Add user message
    const userMessage: ChatMessage = {
      id: `msg-${Date.now()}`,
      type: 'user',
      content: text || `Uploaded ${files.length} file(s)`,
      timestamp: new Date(),
      files: files.length > 0 ? files : undefined
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
            await apiService.persistMessage(activeSessionId, {
              message_id: userMessage.id,
              type: 'user',
              content: userMessage.content,
              metadata: { files: [{ name: f.name, size: f.size, type: f.type }] },
              session_state: 'analyzing'
            });
          } catch {}

          // Persist file to backend (best-effort)
          try {
            const form = new FormData();
            form.append('file', f);
            form.append('session_id', activeSessionId);
            const resp = await fetch(`http://localhost:8000/api/sessions/${activeSessionId}/upload`, { method: 'POST', body: form });
            if (resp.ok) {
              const stored = await resp.json();
              const fileStoredMsg: ChatMessage = {
                id: `file-stored-${Date.now()}`,
                type: 'system',
                content: `Stored file: ${stored.filename}`,
                timestamp: new Date(),
                metadata: { filePersisted: { name: stored.filename } }
              };
              setSessions(prev => ({
                ...prev,
                [activeSessionId]: {
                  ...prev[activeSessionId],
                  messages: [...(prev[activeSessionId]?.messages || []), fileStoredMsg]
                }
              }));
              try { await apiService.persistMessage(activeSessionId, { message_id: fileStoredMsg.id, type: 'system', content: fileStoredMsg.content, metadata: fileStoredMsg.metadata }); } catch {}
            }
          } catch (e) {
            console.warn('File persistence failed', e);
          }

          const response = await n8nService.current.uploadDocument(f);
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
  }, [activeSessionId, workflowState]);

  // Handle analysis approval
  const handleApproveAnalysis = useCallback(async () => {
    if (!activeSessionId) return;
    setWorkflowState('generating');
    
    try {
      // This now calls Generation Workflow correctly
      const response = await n8nService.current.approveAnalysis();
      
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
        
      }
      
      setWorkflowState('complete');
      // Persist artifact message + mark session complete
      try {
        await apiService.persistMessage(activeSessionId, {
          message_id: bogMessage.id,
          type: 'assistant',
          content: bogMessage.content,
          metadata: { downloadUrl: response.downloadUrl },
          session_state: 'complete'
        });
      } catch {}
      
    } catch (error) {
      setWorkflowState('awaiting_approval');
      // Handle error...
    }
  }, [activeSessionId]);

  // Handle analysis changes request
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
      {/* Health Status Monitor */}
      <HealthStatus />
      
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
        highlightTarget={highlightTarget}
        
        // actions
        onSendMessage={handleSendMessage}
        onApproveAnalysis={handleApproveAnalysis}
        onRequestChanges={handleRequestChanges}
        onNavigateToMessage={(id) => setFocusMessageId(id)}
        onNavigateToItem={(target) => { setFocusMessageId(analysisMessageId || ''); setHighlightTarget(target); }}
        
        // session manager
        sessions={Object.values(sessions).map(s => ({ id: s.id, name: s.name, createdAt: s.createdAt }))}
        activeSessionId={activeSessionId}
        onCreateSession={createSession}
        onSwitchSession={switchSession}
        onDeleteSession={deleteSession}
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
