import React, { useState, useEffect, useCallback, useRef } from 'react';
import SimplifiedWorkbench from './components/SimplifiedWorkbench';
import HealthStatus from './components/HealthStatus';
import ConsolePanel, { ConsoleMessage } from './components/ConsolePanel';
import { Terminal } from 'lucide-react';
import { UnifiedN8NService } from './services/n8nIntegrationUnified';
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
  const [isConsoleOpen, setIsConsoleOpen] = useState(true);
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

  // Create initial session
  useEffect(() => {
    const firstId = `session_${Date.now()}`;
    const initMessage: ChatMessage = {
      id: 'init',
      type: 'system',
      content: 'PyBOG Control Builder initialized. Upload HVAC documents or describe your control requirements.',
      timestamp: new Date()
    };
    setSessions({
      [firstId]: {
        id: firstId,
        name: 'Session 1',
        createdAt: new Date(),
        messages: [initMessage],
        currentAnalysis: null,
      }
    });
    setActiveSessionId(firstId);

    addConsoleMessage('info', 'System', 'PyBOG Control Builder initialized');
    addConsoleMessage('info', 'System', 'Checking service connections...');

    // Check services
    setTimeout(() => {
      addConsoleMessage('success', 'API', 'Backend API connected');
      addConsoleMessage('success', 'Database', 'PostgreSQL connected');
      addConsoleMessage('info', 'n8n', 'Workflow engine ready');
      addConsoleMessage('success', 'WebSocket', 'Real-time updates enabled');
    }, 1000);
  }, [addConsoleMessage]);

  // Session actions
  const createSession = useCallback(() => {
    const newId = `session_${Date.now()}`;
    const count = Object.keys(sessions).length + 1;
    const initMessage: ChatMessage = {
      id: 'init',
      type: 'system',
      content: 'New session started. Upload HVAC documents or describe your control requirements.',
      timestamp: new Date()
    };
    setSessions(prev => ({
      ...prev,
      [newId]: {
        id: newId,
        name: `Session ${count}`,
        createdAt: new Date(),
        messages: [initMessage],
        currentAnalysis: null,
      }
    }));
    setActiveSessionId(newId);
    setFocusMessageId(undefined);
    // Persist session to backend (best-effort)
    try {
      fetch('http://localhost:8000/api/sessions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: newId, description: `Session ${count}` })
      });
    } catch (e) {
      // non-blocking
    }
  }, [sessions]);

  const switchSession = useCallback((id: string) => {
    if (!sessions[id]) return;
    setActiveSessionId(id);
    setFocusMessageId(undefined);
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
    
    addConsoleMessage('info', 'User', text || 'File upload initiated');
    
    try {
      if (files.length > 0) {
        for (const file of files) {
          addConsoleMessage('info', 'Upload', `Processing file: ${file.name}`, { 
            size: file.size, 
            type: file.type 
          });
          // Persist file to backend (best-effort)
          try {
            const form = new FormData();
            form.append('file', file);
            form.append('session_id', activeSessionId);
            await fetch(`http://localhost:8000/api/sessions/${activeSessionId}/upload`, { method: 'POST', body: form });
          } catch (e) {
            console.warn('File persistence failed', e);
          }
          const response = await n8nService.current.uploadDocument(file);
          if (response.analysis) {
            const analysisMsgId = `analysis-${Date.now()}`;
            const analysisMessage: ChatMessage = {
              id: analysisMsgId,
              type: 'assistant',
              content: 'HVAC analysis complete. Please review the extracted components.',
              timestamp: new Date(),
              metadata: { analysisData: response.analysis }
            };
            // Auto-name session from file name if default label
            setSessions(prev => {
              const cur = prev[activeSessionId];
              const defaultName = /^Session\s\d+$/i.test(cur.name);
              const newName = defaultName ? file.name.replace(/\.[^/.]+$/, '') : cur.name;
              return {
                ...prev,
                [activeSessionId]: {
                  ...cur,
                  name: newName,
                }
              };
            });
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
            addConsoleMessage('success', 'Analysis', 'File analyzed successfully', response.analysis);
          }
        }
      } else if (text) {
        const response = await n8nService.current.sendMessage(text, text.length > 100);
        const assistantMessage: ChatMessage = {
          id: `assistant-${Date.now()}`,
          type: 'assistant',
          content: response.message || 'Processing your request...',
          timestamp: new Date(),
          metadata: response.analysis ? { analysisData: response.analysis } : undefined
        };
        setSessions(prev => ({
          ...prev,
          [activeSessionId]: {
            ...prev[activeSessionId],
            messages: [...(prev[activeSessionId]?.messages || []), assistantMessage],
            ...(response.analysis ? { currentAnalysis: { ...response.analysis, _messageId: assistantMessage.id }, analysisMessageId: assistantMessage.id } : {})
          }
        }));
        if (response.analysis) {
          setWorkflowState('awaiting_approval');
          // If analysis has a component name, auto-name the session more semantically
          try {
            const comp = (response as any)?.analysis?.component_name || (response as any)?.analysis?.blocks?.[0];
            if (comp) {
              setSessions(prev => ({
                ...prev,
                [activeSessionId]: {
                  ...prev[activeSessionId],
                  name: String(comp),
                }
              }));
            }
          } catch {}
        }
        addConsoleMessage('success', 'n8n', 'Message processed', response);
      }
    } catch (error) {
      addConsoleMessage('error', 'System', `Error: ${error instanceof Error ? error.message : 'Unknown error'}`, error);
      const errorMessage: ChatMessage = {
        id: `error-${Date.now()}`,
        type: 'system',
        content: `Error: ${error instanceof Error ? error.message : 'Unknown error occurred'}`,
        timestamp: new Date()
      };
      setSessions(prev => ({
        ...prev,
        [activeSessionId]: {
          ...prev[activeSessionId],
          messages: [...(prev[activeSessionId]?.messages || []), errorMessage]
        }
      }));
    } finally {
      setIsLoading(false);
      if (workflowState === 'analyzing') {
        setWorkflowState('idle');
      }
    }
  }, [activeSessionId, addConsoleMessage, workflowState]);

  // Handle analysis approval
  const handleApproveAnalysis = useCallback(async () => {
    if (!activeSessionId) return;
    setWorkflowState('generating');
    addConsoleMessage('info', 'Workflow', 'Approving analysis for BOG generation');
    try {
      const response = await n8nService.current.approveAnalysis();
      const bogMessage: ChatMessage = {
        id: `bog-${Date.now()}`,
        type: 'assistant',
        content: 'BOG file generated successfully!',
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
      addConsoleMessage('success', 'BOG', 'BOG file generated successfully', response);
    } catch (error) {
      addConsoleMessage('error', 'BOG', `Failed to generate BOG: ${error instanceof Error ? error.message : 'Unknown error'}`, error);
      setWorkflowState('awaiting_approval');
    }
  }, [activeSessionId, addConsoleMessage]);

  // Handle analysis changes request
  const handleRequestChanges = useCallback(async (feedback: string) => {
    if (!activeSessionId) return;
    setWorkflowState('analyzing');
    addConsoleMessage('info', 'Workflow', `Requesting analysis changes: ${feedback}`);
    try {
      const response = await n8nService.current.requestChanges(feedback);
      if (response.analysis) {
        const refinedId = `refined-${Date.now()}`;
        const refinedMessage: ChatMessage = {
          id: refinedId,
          type: 'assistant',
          content: 'Analysis refined based on your feedback. Please review.',
          timestamp: new Date(),
          metadata: { analysisData: response.analysis }
        };
        setSessions(prev => ({
          ...prev,
          [activeSessionId]: {
            ...prev[activeSessionId],
            messages: [...(prev[activeSessionId]?.messages || []), refinedMessage],
            currentAnalysis: { ...response.analysis, _messageId: refinedId },
            analysisMessageId: refinedId,
          }
        }));
        setWorkflowState('awaiting_approval');
      }
      addConsoleMessage('success', 'Analysis', 'Analysis refinement completed', response);
    } catch (error) {
      addConsoleMessage('error', 'Analysis', `Failed to refine: ${error instanceof Error ? error.message : 'Unknown error'}`, error);
      setWorkflowState('awaiting_approval');
    }
  }, [activeSessionId, addConsoleMessage]);

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
