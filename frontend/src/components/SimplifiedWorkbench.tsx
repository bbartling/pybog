import React, { useState, useRef, useEffect } from 'react';
import { 
  Send, Upload, FileText, Loader2,
  PanelLeftOpen, PanelLeftClose, Database,
  Activity, CheckCircle, AlertCircle, XCircle,
  Terminal, Wifi, WifiOff, Server, HardDrive, Zap,
  ExternalLink, RefreshCw, GitBranch, Cpu, CircuitBoard
} from 'lucide-react';
import ChatCanvasGrid, { ChatMessage } from './ChatCanvasGrid';
import ProjectNavigator from './ProjectNavigatorEnhanced';
import './SimplifiedWorkbench.neubrutalism.css';
import { ReactFlowProvider } from 'reactflow';
import ConfirmModal from './ConfirmModal';

interface IOPoint {
  id: string;
  name: string;
  type: 'input' | 'output';
  dataType: string;
}

interface SessionSummary {
  id: string;
  name: string;
  createdAt: Date | string;
}

interface SimplifiedWorkbenchProps {
  // session and analysis data
  messages: ChatMessage[];
  sessionId: string;
  isLoading: boolean;
  workflowState?: 'idle' | 'analyzing' | 'awaiting_approval' | 'generating' | 'complete';
  currentAnalysis?: any;
  analysisMessageId?: string;
  focusMessageId?: string;
  highlightTarget?: { kind: 'analysis' | 'block' | 'input' | 'output'; label?: string };
  
  // actions
  onSendMessage: (text: string, files: File[]) => void;
  onApproveAnalysis: () => void;
  onRequestChanges: (feedback: string) => void;
  onResendMessage?: (message: ChatMessage) => void;
  onNavigateToMessage: (messageId: string) => void;
  onNavigateToItem: (target: { kind: 'input' | 'output' | 'block'; label: string }) => void;
  
  // session manager
  sessions: SessionSummary[];
  activeSessionId: string;
  onCreateSession: () => void;
  onSwitchSession: (id: string) => void;
  onDeleteSession: (id: string) => void;
  onRenameSession?: (id: string, name: string) => void;
  
  // console
  isConsoleOpen?: boolean;
  onToggleConsole?: () => void;
}

const SimplifiedWorkbenchClean: React.FC<SimplifiedWorkbenchProps> = ({
  // session and analysis data
  messages,
  sessionId,
  isLoading,
  workflowState = 'idle',
  currentAnalysis,
  analysisMessageId,
  focusMessageId,
  highlightTarget,
  
  // actions
  onSendMessage,
  onApproveAnalysis,
  onRequestChanges,
  onResendMessage,
  onNavigateToMessage,
  onNavigateToItem,
  
  // session manager
  sessions,
  activeSessionId,
  onCreateSession,
  onSwitchSession,
  onDeleteSession,
  onRenameSession,
  
  // console
  isConsoleOpen = false,
  onToggleConsole,
}) => {
  const [inputText, setInputText] = useState('');
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [confirmDelete, setConfirmDelete] = useState<{open: boolean; sessionId?: string}>({open: false});
  const [showNavigator, setShowNavigator] = useState(true);
  const [systemStatus, setSystemStatus] = useState<'healthy' | 'degraded' | 'error'>('healthy');
  const [showSystemDetails, setShowSystemDetails] = useState(false);
  const [systemServices, setSystemServices] = useState({
    api: { name: 'API Server', status: 'healthy', message: 'Running', url: 'http://localhost:8000/docs' },
    database: { name: 'PostgreSQL', status: 'healthy', message: 'Connected', url: 'http://localhost:5050' },
    redis: { name: 'Redis Cache', status: 'healthy', message: 'Operational', url: null },
    n8n: { name: 'n8n Workflow', status: 'healthy', message: 'Ready', url: 'http://localhost:5678' },
    websocket: { name: 'WebSocket', status: 'healthy', message: 'Active', url: null },
  });
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleSend = () => {
    if (inputText.trim() || selectedFiles.length > 0) {
      onSendMessage(inputText, selectedFiles);
      setInputText('');
      setSelectedFiles([]);
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    setSelectedFiles(prev => [...prev, ...files]);
  };
  
  // Close system details when clicking outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      const target = e.target as HTMLElement;
      if (showSystemDetails && !target.closest('.system-status-container')) {
        setShowSystemDetails(false);
      }
    };
    
    if (showSystemDetails) {
      document.addEventListener('click', handleClickOutside);
      return () => document.removeEventListener('click', handleClickOutside);
    }
  }, [showSystemDetails]);

  const removeFile = (index: number) => {
    setSelectedFiles(prev => prev.filter((_, i) => i !== index));
  };

  // Prepare IOPoints for display
  const ioPoints: IOPoint[] = [];
  if (currentAnalysis) {
    const inputsRaw = currentAnalysis.inputs || currentAnalysis.io_points?.inputs || [];
    const outputsRaw = currentAnalysis.outputs || currentAnalysis.io_points?.outputs || [];

    const normalize = (arr: any[], kind: 'input' | 'output') => {
      arr.forEach((entry: any, idx: number) => {
        if (typeof entry === 'string') {
          const lower = entry.toLowerCase();
          const dataType = lower.includes('temp') || lower.includes('pressure') || lower.includes('setpoint') 
            ? 'Analog' 
            : (lower.includes('status') || lower.includes('command') ? 'Binary' : 'Unknown');
          ioPoints.push({ 
            id: `${kind}-${idx}`, 
            name: entry, 
            type: kind, 
            dataType 
          });
        } else if (entry && typeof entry === 'object') {
          ioPoints.push({ 
            id: `${kind}-${idx}`, 
            name: entry.name || `Point_${idx + 1}`, 
            type: kind, 
            dataType: entry.type || 'Unknown' 
          });
        }
      });
    };

    normalize(inputsRaw, 'input');
    normalize(outputsRaw, 'output');
  }

  return (
    <div className="simplified-workbench">
      {/* Header */}
      <div className="workbench-header" style={{
        background: '#FFFFFF',
        border: '2px solid #3F3F4B',
        borderRadius: '12px',
        boxShadow: '4px 4px 0 0 rgba(63, 63, 75, 0.15)',
        margin: '12px',
        marginBottom: '0',
        height: '60px',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        padding: '0 20px',
      }}>
        <div className="header-left" style={{
          display: 'flex',
          alignItems: 'center',
          gap: '12px',
        }}>
          <div style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            width: '36px',
            height: '36px',
            background: 'linear-gradient(135deg, #569BFF 0%, #4A8EE8 100%)',
            borderRadius: '8px',
            border: '2px solid #3F3F4B',
          }}>
            <CircuitBoard size={20} style={{ color: '#FFFFFF' }} />
          </div>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: '8px' }}>
            <span className="header-title" style={{
              fontSize: '18px',
              fontWeight: '700',
              color: '#3F3F4B',
              letterSpacing: '-0.02em',
            }}>N4 Builder</span>
            <span className="header-subtitle" style={{
              fontSize: '12px',
              color: '#6B7280',
              fontWeight: '500',
            }}>AI Logic Generation</span>
          </div>
        </div>
        <div className="header-right">
          {/* Workflow Status */}
          {workflowState !== 'idle' && (
            <div className="workflow-status">
              {workflowState === 'analyzing' && (
                <>
                  <Loader2 className="animate-spin" size={14} />
                  <span>Analyzing</span>
                </>
              )}
              {workflowState === 'awaiting_approval' && (
                <span style={{ color: '#F59E0B' }}>Review Required</span>
              )}
              {workflowState === 'generating' && (
                <>
                  <Loader2 className="animate-spin" size={14} />
                  <span>Generating</span>
                </>
              )}
              {workflowState === 'complete' && (
                <span style={{ color: '#10B981' }}>✓ Complete</span>
              )}
            </div>
          )}
          
          {/* System Status Indicator */}
          <div className="system-status-container" style={{ position: 'relative' }}>
            <div 
              className="system-status"
              style={{ cursor: 'pointer' }}
              onClick={() => setShowSystemDetails(!showSystemDetails)}
            >
              {systemStatus === 'healthy' && (
                <>
                  <CheckCircle size={14} style={{ color: '#10B981' }} />
                  <span style={{ color: '#10B981' }}>All Systems</span>
                </>
              )}
              {systemStatus === 'degraded' && (
                <>
                  <AlertCircle size={14} style={{ color: '#F59E0B' }} />
                  <span style={{ color: '#F59E0B' }}>Degraded</span>
                </>
              )}
              {systemStatus === 'error' && (
                <>
                  <XCircle size={14} style={{ color: '#EF4444' }} />
                  <span style={{ color: '#EF4444' }}>Error</span>
                </>
              )}
            </div>
            
            {/* System Details Flyout */}
            {showSystemDetails && (
              <div style={{
                position: 'absolute',
                top: '40px',
                right: 0,
                background: '#FFFFFF',
                border: '2px solid #3F3F4B',
                borderRadius: '12px',
                padding: '16px',
                width: '320px',
                boxShadow: '4px 4px 0 0 rgba(63, 63, 75, 0.1)',
                zIndex: 1000,
              }}>
                <div style={{
                  fontSize: '14px',
                  fontWeight: 600,
                  color: '#3F3F4B',
                  marginBottom: '12px',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                }}>
                  System Health
                  <RefreshCw 
                    size={14} 
                    style={{ cursor: 'pointer', color: '#6B7280' }}
                    onClick={() => console.log('Refresh health')}
                  />
                </div>
                
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  {Object.entries(systemServices).map(([key, service]) => (
                    <div
                      key={key}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        padding: '8px 12px',
                        background: '#F7F8FA',
                        borderRadius: '8px',
                        gap: '8px',
                      }}
                    >
                      {key === 'database' && <Database size={14} style={{ color: '#6B7280' }} />}
                      {key === 'redis' && <HardDrive size={14} style={{ color: '#6B7280' }} />}
                      {key === 'api' && <Server size={14} style={{ color: '#6B7280' }} />}
                      {key === 'n8n' && <Zap size={14} style={{ color: '#6B7280' }} />}
                      {key === 'websocket' && (
                        service.status === 'healthy' ? 
                          <Wifi size={14} style={{ color: '#6B7280' }} /> :
                          <WifiOff size={14} style={{ color: '#6B7280' }} />
                      )}
                      
                      <div style={{ flex: 1 }}>
                        <div style={{ fontSize: '12px', fontWeight: 500, color: '#3F3F4B' }}>
                          {service.name}
                        </div>
                        <div style={{ fontSize: '11px', color: '#6B7280' }}>
                          {service.message}
                        </div>
                      </div>
                      
                      <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                        {service.status === 'healthy' && <CheckCircle size={12} style={{ color: '#10B981' }} />}
                        {service.status === 'degraded' && <AlertCircle size={12} style={{ color: '#F59E0B' }} />}
                        {service.status === 'error' && <XCircle size={12} style={{ color: '#EF4444' }} />}
                        
                        {service.url && (
                          <ExternalLink
                            size={12}
                            style={{ color: '#6B7280', cursor: 'pointer' }}
                            onClick={() => window.open(service.url!, '_blank')}
                          />
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      <div className="workbench-body">
        {/* Sidebar */}
        <div className="workbench-sidebar">
          <ProjectNavigator
            sessionId={sessionId}
            sessions={sessions}
            currentAnalysis={currentAnalysis}
            messages={messages}
            onCreateSession={onCreateSession}
            onSwitchSession={onSwitchSession}
            onDeleteSession={(id) => {
              setConfirmDelete({ open: true, sessionId: id });
            }}
            onRenameSession={onRenameSession}
          />
        </div>

        {/* Canvas Container */}
        <div className="workbench-canvas-container">
          {/* Main Canvas */}
          <div className="workbench-canvas">
            <ReactFlowProvider>
              <ChatCanvasGrid
                messages={messages}
                sessionId={sessionId}
                onApproveAnalysis={onApproveAnalysis}
                onRequestChanges={onRequestChanges}
                onResendMessage={onResendMessage}
                workflowState={workflowState}
                focusMessageId={focusMessageId}
              />
            </ReactFlowProvider>
          </div>

          {/* Input Bar */}
          <div className="workbench-input">
            {selectedFiles.length > 0 && (
              <div className="selected-files">
                {selectedFiles.map((file, index) => (
                  <div key={index} className="selected-file">
                    <FileText size={14} />
                    <span>{file.name}</span>
                    <button onClick={() => removeFile(index)} className="remove-file">
                      ×
                    </button>
                  </div>
                ))}
              </div>
            )}
            <div className="input-row">
              <input
                type="file"
                ref={fileInputRef}
                onChange={handleFileSelect}
                multiple
                accept=".pdf,.txt,.doc,.docx"
                style={{ display: 'none' }}
              />
              <button 
                className="attach-btn"
                onClick={() => fileInputRef.current?.click()}
                title="Upload"
              >
                <Upload size={18} />
              </button>
              <input
                type="text"
                className="message-input"
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && handleSend()}
                placeholder="Describe your HVAC control requirements or drop sequence PDFs..."
                disabled={isLoading}
              />
              <button 
                className="send-btn"
                onClick={handleSend}
                disabled={isLoading || (!inputText.trim() && selectedFiles.length === 0)}
              >
                {isLoading ? (
                  <Loader2 className="animate-spin" size={18} />
                ) : (
                  <>
                    <Send size={18} style={{ marginRight: 6 }} />
                    <span>Send</span>
                  </>
                )}
              </button>
              
              {/* Console Toggle Button */}
              {onToggleConsole && (
                <button
                  onClick={onToggleConsole}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px',
                    padding: '12px 20px',
                    background: '#3F3F4B',
                    color: '#FFFFFF',
                    border: '2px solid #3F3F4B',
                    borderRadius: '12px',
                    fontSize: '14px',
                    fontWeight: 600,
                    fontFamily: 'Inter, system-ui, -apple-system, sans-serif',
                    cursor: 'pointer',
                    transition: 'all 0.2s ease',
                    textTransform: 'uppercase',
                    letterSpacing: '0.05em',
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.background = '#2F2F3B';
                    e.currentTarget.style.transform = 'translateY(-2px)';
                    e.currentTarget.style.boxShadow = '0 4px 0 0 #3F3F4B';
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.background = '#3F3F4B';
                    e.currentTarget.style.transform = 'translateY(0)';
                    e.currentTarget.style.boxShadow = 'none';
                  }}
                >
                  <Terminal size={14} />
                  <span>{isConsoleOpen ? 'Hide' : 'Show'} Console</span>
                </button>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Confirm delete modal */}
      <ConfirmModal
        isOpen={confirmDelete.open}
        title="Remove Session"
        message="Are you sure you want to delete this session? This will remove its messages from the current view."
        confirmLabel="Delete"
        onConfirm={() => { 
          if (confirmDelete.sessionId) { 
            onDeleteSession(confirmDelete.sessionId); 
          } 
          setConfirmDelete({open:false}); 
        }}
        onCancel={() => setConfirmDelete({open:false})}
      />
    </div>
  );
};

export default SimplifiedWorkbenchClean;
