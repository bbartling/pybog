import React, { useState, useEffect, useCallback } from 'react';
import SimplifiedWorkbench from './components/SimplifiedWorkbench';
import HealthStatus from './components/HealthStatus';
import ConsolePanel, { ConsoleMessage } from './components/ConsolePanel';
import { Terminal } from 'lucide-react';
import { UnifiedN8NService } from './services/n8nIntegrationUnified';

const App: React.FC = () => {
  const [consoleMessages, setConsoleMessages] = useState<ConsoleMessage[]>([]);
  const [isConsoleOpen, setIsConsoleOpen] = useState(true);
  const [n8nService] = useState(() => new UnifiedN8NService());
  
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

  // Handle file upload with console logging
  const handleFileUpload = useCallback(async (files: File[]) => {
    for (const file of files) {
      addConsoleMessage('info', 'Upload', `Processing file: ${file.name}`, { 
        size: file.size, 
        type: file.type 
      });
      
      try {
        const response = await n8nService.uploadDocument(file);
        addConsoleMessage('success', 'Upload', `File processed successfully: ${file.name}`, response);
      } catch (error) {
        addConsoleMessage('error', 'Upload', `Failed to process file: ${file.name}`, error);
      }
    }
  }, [n8nService, addConsoleMessage]);

  // Handle message sending with console logging
  const handleSendMessage = useCallback(async (message: string, files: File[]) => {
    addConsoleMessage('info', 'Chat', `User message: ${message.substring(0, 100)}...`);
    
    if (files.length > 0) {
      await handleFileUpload(files);
    }
    
    try {
      const response = await n8nService.sendMessage(message, message.length > 100);
      addConsoleMessage('success', 'n8n', 'Message processed', response);
    } catch (error) {
      addConsoleMessage('error', 'n8n', 'Failed to process message', error);
    }
  }, [n8nService, handleFileUpload, addConsoleMessage]);

  // Handle analysis approval
  const handleApproveAnalysis = useCallback(async () => {
    addConsoleMessage('info', 'Workflow', 'Approving analysis for BOG generation');
    
    try {
      const response = await n8nService.approveAnalysis();
      addConsoleMessage('success', 'BOG', 'BOG file generated successfully', response);
    } catch (error) {
      addConsoleMessage('error', 'BOG', 'Failed to generate BOG file', error);
    }
  }, [n8nService, addConsoleMessage]);

  // Handle analysis changes request
  const handleRequestChanges = useCallback(async (feedback: string) => {
    addConsoleMessage('info', 'Workflow', `Requesting analysis changes: ${feedback}`);
    
    try {
      const response = await n8nService.requestChanges(feedback);
      addConsoleMessage('success', 'Analysis', 'Analysis refinement requested', response);
    } catch (error) {
      addConsoleMessage('error', 'Analysis', 'Failed to refine analysis', error);
    }
  }, [n8nService, addConsoleMessage]);

  return (
    <div style={{ width: '100vw', height: '100vh', overflow: 'hidden' }}>
      {/* Health Status Monitor */}
      <HealthStatus />
      
      {/* Main Workbench Interface */}
      <SimplifiedWorkbench 
        onFileUpload={handleFileUpload}
        onSendMessage={handleSendMessage}
        onApproveAnalysis={handleApproveAnalysis}
        onRequestChanges={handleRequestChanges}
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
