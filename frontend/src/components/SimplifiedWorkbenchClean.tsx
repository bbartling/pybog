import React, { useState, useRef } from 'react';
import { 
  Send, Upload, FileText, Loader2,
  PanelLeftOpen, PanelLeftClose, Database
} from 'lucide-react';
import ChatCanvasGrid, { ChatMessage } from './ChatCanvasGrid';
import ProjectNavigator from './ProjectNavigatorEnhanced';
import './SimplifiedWorkbench.css';
import './NiagaraWorkbench.css';
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
  onNavigateToMessage: (messageId: string) => void;
  onNavigateToItem: (target: { kind: 'input' | 'output' | 'block'; label: string }) => void;
  
  // session manager
  sessions: SessionSummary[];
  activeSessionId: string;
  onCreateSession: () => void;
  onSwitchSession: (id: string) => void;
  onDeleteSession: (id: string) => void;
  onRenameSession?: (id: string, name: string) => void;
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
  onNavigateToMessage,
  onNavigateToItem,
  
  // session manager
  sessions,
  activeSessionId,
  onCreateSession,
  onSwitchSession,
  onDeleteSession,
  onRenameSession,
}) => {
  const [inputText, setInputText] = useState('');
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [confirmDelete, setConfirmDelete] = useState<{open: boolean; sessionId?: string}>({open: false});
  const [showNavigator, setShowNavigator] = useState(true);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleSend = () => {
    if (selectedFiles.length > 0) {
      // IMPORTANT: When files are attached, send an empty text payload to avoid chat-only routing.
      onSendMessage('', selectedFiles);
      setInputText('');
      setSelectedFiles([]);
      return;
    }
    if (inputText.trim()) {
      onSendMessage(inputText, []);
      setInputText('');
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    setSelectedFiles(prev => [...prev, ...files]);
  };

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
      <div className="workbench-header">
        <div className="header-logo">
          <button 
            className="navigator-toggle" 
            onClick={() => setShowNavigator(!showNavigator)}
            style={{
              background: '#ffffff',
              border: '1px solid #e5e7eb',
              borderRadius: '4px',
              padding: '4px 6px',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              transition: 'all 0.2s ease'
            }}
          >
            {showNavigator ? <PanelLeftClose size={18} /> : <PanelLeftOpen size={18} />}
          </button>
          <Database size={20} style={{ color: '#7c3aed' }} />
          <span>N4 Builder</span>
          <span style={{ fontSize: 12, marginLeft: 8, color: '#6b7280' }}>Powered by PyBOG</span>
        </div>
        <div className="header-status">
          {workflowState === 'analyzing' && (
            <>
              <Loader2 className="animate-spin" size={16} />
              <span>Analyzing...</span>
            </>
          )}
          {workflowState === 'awaiting_approval' && (
            <>
              <span style={{ color: '#f59e0b', fontWeight: 700 }}>Review Required</span>
              {focusMessageId && (
                <button
                  onClick={() => onNavigateToMessage(focusMessageId)}
                  style={{
                    marginLeft: 8,
                    padding: '4px 8px',
                    border: '1px solid #d97706',
                    borderRadius: 6,
                    background: '#FEF3C7',
                    color: '#92400E',
                    fontSize: 12,
                    fontWeight: 600,
                    cursor: 'pointer'
                  }}
                  title="Jump to review"
                >
                  Open Review
                </button>
              )}
            </>
          )}
          {workflowState === 'generating' && (
            <>
              <Loader2 className="animate-spin" size={16} />
              <span>Generating BOG...</span>
            </>
          )}
          {workflowState === 'complete' && (
            <span style={{ color: '#10b981' }}>Complete</span>
          )}
        </div>
      </div>

      <div className="workbench-body" style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
        {/* Clean Project Navigator */}
        {showNavigator && (
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
        )}

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

        {/* Main Canvas */}
        <div className="workbench-canvas" style={{ flex: 1 }}>
          <ReactFlowProvider>
            <ChatCanvasGrid
              messages={messages}
              sessionId={sessionId}
              onApproveAnalysis={onApproveAnalysis}
              onRequestChanges={onRequestChanges}
              workflowState={workflowState}
              focusMessageId={focusMessageId}
            />
          </ReactFlowProvider>
        </div>
      </div>

      {/* Input Bar */}
      <div className="workbench-input">
        <div className="input-container">
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
              title="Attach files"
            >
              <Upload size={18} />
            </button>
            <input
              type="text"
              className="message-input"
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && handleSend()}
              placeholder="Describe your HVAC control requirements or upload sequence documents..."
              disabled={isLoading}
            />
            <button 
              className="send-btn"
              onClick={handleSend}
              disabled={isLoading || (!inputText.trim() && selectedFiles.length === 0)}
            >
              {isLoading ? <Loader2 className="animate-spin" size={18} /> : <Send size={18} />}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default SimplifiedWorkbenchClean;
