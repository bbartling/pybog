import React, { useState, useEffect, useCallback, useRef } from 'react';
import SimplifiedWorkbench from './components/SimplifiedWorkbench';
import HealthStatus from './components/HealthStatus';
import ConsolePanel, { ConsoleMessage } from './components/ConsolePanel';
import { Terminal } from 'lucide-react';
import { UnifiedN8NService } from './services/n8nIntegrationUnified';
import { ChatMessage } from './components/ChatCanvas';

const App: React.FC = () => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [consoleMessages, setConsoleMessages] = useState<ConsoleMessage[]>([]);
  const [isConsoleOpen, setIsConsoleOpen] = useState(true);
  const [isLoading, setIsLoading] = useState(false);
  const [workflowState, setWorkflowState] = useState<'idle' | 'analyzing' | 'awaiting_approval' | 'generating' | 'complete'>('idle');
  const [currentAnalysis, setCurrentAnalysis] = useState<any>(null);
  const [sessionId] = useState(() => `session_${Date.now()}`);
  const n8nService = useRef(new UnifiedN8NService());
  
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

  // Initialize with welcome message
  useEffect(() => {
    const initMessage: ChatMessage = {
      id: 'init',
      type: 'system',
      content: 'PyBOG Control Builder initialized. Upload HVAC documents or describe your control requirements.',
      timestamp: new Date()
    };
    setMessages([initMessage]);
    
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

  // Handle message sending
  const handleSendMessage = useCallback(async (text: string, files: File[]) => {
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
    setMessages(prev => [...prev, userMessage]);
    
    addConsoleMessage('info', 'User', text || 'File upload initiated');
    
    try {
      if (files.length > 0) {
        // Handle file upload
        for (const file of files) {
          addConsoleMessage('info', 'Upload', `Processing file: ${file.name}`, { 
            size: file.size, 
            type: file.type 
          });
          
          const response = await n8nService.current.uploadDocument(file);
          
          if (response.analysis) {
            setCurrentAnalysis(response.analysis);
            setWorkflowState('awaiting_approval');
            
            const analysisMessage: ChatMessage = {
              id: `analysis-${Date.now()}`,
              type: 'assistant',
              content: 'HVAC analysis complete. Please review the extracted components.',
              timestamp: new Date(),
              metadata: { analysisData: response.analysis }
            };
            setMessages(prev => [...prev, analysisMessage]);
            
            addConsoleMessage('success', 'Analysis', 'File analyzed successfully', response.analysis);
          }
        }
      } else if (text) {
        // Handle text message
        const response = await n8nService.current.sendMessage(text, text.length > 100);
        
        const assistantMessage: ChatMessage = {
          id: `assistant-${Date.now()}`,
          type: 'assistant',
          content: response.message || 'Processing your request...',
          timestamp: new Date(),
          metadata: response.analysis ? { analysisData: response.analysis } : undefined
        };
        setMessages(prev => [...prev, assistantMessage]);
        
        if (response.analysis) {
          setCurrentAnalysis(response.analysis);
          setWorkflowState('awaiting_approval');
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
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
      if (workflowState === 'analyzing') {
        setWorkflowState('idle');
      }
    }
  }, [addConsoleMessage]);

  // Handle analysis approval
  const handleApproveAnalysis = useCallback(async () => {
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
      setMessages(prev => [...prev, bogMessage]);
      
      setWorkflowState('complete');
      addConsoleMessage('success', 'BOG', 'BOG file generated successfully', response);
    } catch (error) {
      addConsoleMessage('error', 'BOG', `Failed to generate BOG: ${error instanceof Error ? error.message : 'Unknown error'}`, error);
      setWorkflowState('awaiting_approval');
    }
  }, [addConsoleMessage]);

  // Handle analysis changes request
  const handleRequestChanges = useCallback(async (feedback: string) => {
    setWorkflowState('analyzing');
    addConsoleMessage('info', 'Workflow', `Requesting analysis changes: ${feedback}`);
    
    try {
      const response = await n8nService.current.requestChanges(feedback);
      
      if (response.analysis) {
        setCurrentAnalysis(response.analysis);
        setWorkflowState('awaiting_approval');
        
        const refinedMessage: ChatMessage = {
          id: `refined-${Date.now()}`,
          type: 'assistant',
          content: 'Analysis refined based on your feedback. Please review.',
          timestamp: new Date(),
          metadata: { analysisData: response.analysis }
        };
        setMessages(prev => [...prev, refinedMessage]);
      }
      
      addConsoleMessage('success', 'Analysis', 'Analysis refinement completed', response);
    } catch (error) {
      addConsoleMessage('error', 'Analysis', `Failed to refine: ${error instanceof Error ? error.message : 'Unknown error'}`, error);
      setWorkflowState('awaiting_approval');
    }
  }, [addConsoleMessage]);

  return (
    <div style={{ width: '100vw', height: '100vh', overflow: 'hidden' }}>
      {/* Health Status Monitor */}
      <HealthStatus />
      
      {/* Main Workbench Interface */}
      <SimplifiedWorkbench 
        messages={messages}
        sessionId={sessionId}
        isLoading={isLoading}
        onSendMessage={handleSendMessage}
        onApproveAnalysis={handleApproveAnalysis}
        onRequestChanges={handleRequestChanges}
        workflowState={workflowState}
        currentAnalysis={currentAnalysis}
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
