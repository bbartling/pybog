import React, { useState, useRef } from 'react';
import { 
  Send, Upload, FileText, CheckCircle, Loader2,
  ChevronRight, ChevronDown, Folder, FolderOpen,
  Database, Clock, AlertCircle
} from 'lucide-react';
import ChatCanvas, { ChatMessage } from './ChatCanvas';
import './SimplifiedWorkbench.css';

// ProjectFile interface may be used in future for file management

interface IOPoint {
  id: string;
  name: string;
  type: 'input' | 'output';
  dataType: string;
}

interface SimplifiedWorkbenchProps {
  messages: ChatMessage[];
  sessionId: string;
  isLoading: boolean;
  onSendMessage: (text: string, files: File[]) => void;
  onApproveAnalysis: () => void;
  onRequestChanges: (feedback: string) => void;
  workflowState?: 'idle' | 'analyzing' | 'awaiting_approval' | 'generating' | 'complete';
  currentAnalysis?: any;
}

const SimplifiedWorkbench: React.FC<SimplifiedWorkbenchProps> = ({
  messages,
  sessionId,
  isLoading,
  onSendMessage,
  onApproveAnalysis,
  onRequestChanges,
  workflowState = 'idle',
  currentAnalysis
}) => {
  const [inputText, setInputText] = useState('');
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [expandedSections, setExpandedSections] = useState<Set<string>>(new Set(['files', 'io-points']));
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

  const removeFile = (index: number) => {
    setSelectedFiles(prev => prev.filter((_, i) => i !== index));
  };

  const toggleSection = (section: string) => {
    setExpandedSections(prev => {
      const newSet = new Set(prev);
      if (newSet.has(section)) {
        newSet.delete(section);
      } else {
        newSet.add(section);
      }
      return newSet;
    });
  };

  // Extract files and IO points from messages
  const uploadedFiles = messages
    .filter(m => m.files && m.files.length > 0)
    .flatMap(m => m.files!)
    .map((file, idx) => ({
      id: `file-${idx}`,
      name: file.name,
      type: file.name.endsWith('.pdf') ? 'pdf' as const : 'txt' as const,
      uploadedAt: new Date()
    }));

  const ioPoints: IOPoint[] = [];
  if (currentAnalysis) {
    // Extract IO points from analysis
    if (currentAnalysis.inputs) {
      Object.entries(currentAnalysis.inputs).forEach(([key, value]: [string, any]) => {
        ioPoints.push({
          id: `input-${key}`,
          name: key,
          type: 'input',
          dataType: typeof value === 'object' ? value.type || 'unknown' : typeof value
        });
      });
    }
    if (currentAnalysis.outputs) {
      Object.entries(currentAnalysis.outputs).forEach(([key, value]: [string, any]) => {
        ioPoints.push({
          id: `output-${key}`,
          name: key,
          type: 'output',
          dataType: typeof value === 'object' ? value.type || 'unknown' : typeof value
        });
      });
    }
    // Also check for io_summary
    if (currentAnalysis.io_summary) {
      const ioSummary = currentAnalysis.io_summary;
      if (ioSummary.total_inputs) {
        for (let i = 0; i < Math.min(3, ioSummary.total_inputs); i++) {
          ioPoints.push({
            id: `input-auto-${i}`,
            name: `Input_${i + 1}`,
            type: 'input',
            dataType: 'auto-detected'
          });
        }
      }
      if (ioSummary.total_outputs) {
        for (let i = 0; i < Math.min(3, ioSummary.total_outputs); i++) {
          ioPoints.push({
            id: `output-auto-${i}`,
            name: `Output_${i + 1}`,
            type: 'output',
            dataType: 'auto-detected'
          });
        }
      }
    }
  }

  return (
    <div className="simplified-workbench">
      {/* Header */}
      <div className="workbench-header">
        <div className="header-logo">
          <Database size={20} />
          <span>PyBOG Control Builder</span>
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
              <AlertCircle size={16} className="text-yellow-500" />
              <span>Review Required</span>
            </>
          )}
          {workflowState === 'generating' && (
            <>
              <Loader2 className="animate-spin" size={16} />
              <span>Generating BOG...</span>
            </>
          )}
          {workflowState === 'complete' && (
            <>
              <CheckCircle size={16} className="text-green-500" />
              <span>Complete</span>
            </>
          )}
        </div>
      </div>

      <div className="workbench-body">
        {/* Sidebar */}
        <div className="workbench-sidebar">
          <div className="sidebar-section">
            <h3>Project Navigator</h3>
            
            {/* Session Info */}
            <div className="nav-item">
              <Clock size={14} />
              <span className="nav-label">Session: {new Date().toLocaleTimeString()}</span>
            </div>

            {/* Uploaded Files */}
            <div className="nav-section">
              <div 
                className="nav-section-header"
                onClick={() => toggleSection('files')}
              >
                {expandedSections.has('files') ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                {expandedSections.has('files') ? <FolderOpen size={14} /> : <Folder size={14} />}
                <span>Uploaded Files ({uploadedFiles.length})</span>
              </div>
              {expandedSections.has('files') && (
                <div className="nav-section-content">
                  {uploadedFiles.length === 0 ? (
                    <div className="nav-empty">No files uploaded</div>
                  ) : (
                    uploadedFiles.map(file => (
                      <div key={file.id} className="nav-file">
                        <FileText size={12} />
                        <span>{file.name}</span>
                      </div>
                    ))
                  )}
                </div>
              )}
            </div>

            {/* I/O Points */}
            {currentAnalysis && (
              <div className="nav-section">
                <div 
                  className="nav-section-header"
                  onClick={() => toggleSection('io-points')}
                >
                  {expandedSections.has('io-points') ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                  <Database size={14} />
                  <span>I/O Points ({ioPoints.length})</span>
                </div>
                {expandedSections.has('io-points') && (
                  <div className="nav-section-content">
                    {ioPoints.length === 0 ? (
                      <div className="nav-empty">No I/O points detected</div>
                    ) : (
                      <>
                        <div className="io-group">
                          <span className="io-group-label">Inputs</span>
                          {ioPoints.filter(p => p.type === 'input').map(point => (
                            <div key={point.id} className="nav-io-point input">
                              <span className="io-indicator">→</span>
                              <span>{point.name}</span>
                              <span className="io-type">{point.dataType}</span>
                            </div>
                          ))}
                        </div>
                        <div className="io-group">
                          <span className="io-group-label">Outputs</span>
                          {ioPoints.filter(p => p.type === 'output').map(point => (
                            <div key={point.id} className="nav-io-point output">
                              <span className="io-indicator">←</span>
                              <span>{point.name}</span>
                              <span className="io-type">{point.dataType}</span>
                            </div>
                          ))}
                        </div>
                      </>
                    )}
                  </div>
                )}
              </div>
            )}

            {/* Analysis Summary */}
            {currentAnalysis && currentAnalysis.io_summary && (
              <div className="nav-section">
                <div className="nav-section-header">
                  <AlertCircle size={14} />
                  <span>Analysis Summary</span>
                </div>
                <div className="nav-section-content">
                  <div className="summary-item">
                    <span>Components:</span>
                    <span>{currentAnalysis.component_count || 0}</span>
                  </div>
                  <div className="summary-item">
                    <span>Total I/O:</span>
                    <span>
                      {currentAnalysis.io_summary.total_inputs || 0} in, 
                      {currentAnalysis.io_summary.total_outputs || 0} out
                    </span>
                  </div>
                  {currentAnalysis.io_summary.has_errors && (
                    <div className="summary-error">
                      ⚠️ Errors detected in logic
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Main Canvas */}
        <div className="workbench-canvas">
          <ChatCanvas
            messages={messages}
            sessionId={sessionId}
            onApproveAnalysis={onApproveAnalysis}
            onRequestChanges={onRequestChanges}
            workflowState={workflowState}
          />
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

export default SimplifiedWorkbench;
