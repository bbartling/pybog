import React, { useState, useRef } from 'react';
import { 
  Send, Upload, FileText, CheckCircle, Loader2,
  ChevronRight, ChevronDown, Folder, FolderOpen,
  Database, AlertCircle, Plus, Trash2, FolderTree
} from 'lucide-react';
import ChatCanvas, { ChatMessage } from './ChatCanvas';
import './SimplifiedWorkbench.css';
import { ReactFlowProvider } from 'reactflow';
import ConfirmModal from './ConfirmModal';

// ProjectFile interface may be used in future for file management

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
  
  // actions
  onSendMessage: (text: string, files: File[]) => void;
  onApproveAnalysis: () => void;
  onRequestChanges: (feedback: string) => void;
  onNavigateToMessage: (messageId: string) => void;
  
  // session manager
  sessions: SessionSummary[];
  activeSessionId: string;
  onCreateSession: () => void;
  onSwitchSession: (id: string) => void;
  onDeleteSession: (id: string) => void;
}

const SimplifiedWorkbench: React.FC<SimplifiedWorkbenchProps> = ({
  // session and analysis data
  messages,
  sessionId,
  isLoading,
  workflowState = 'idle',
  currentAnalysis,
  analysisMessageId,
  focusMessageId,
  
  // actions
  onSendMessage,
  onApproveAnalysis,
  onRequestChanges,
  onNavigateToMessage,
  
  // session manager
  sessions,
  activeSessionId,
  onCreateSession,
  onSwitchSession,
  onDeleteSession,
}) => {
  const [inputText, setInputText] = useState('');
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [expandedSections, setExpandedSections] = useState<Set<string>>(new Set(['sessions', 'files', 'project-tree']));
  const [expandedSessionIds, setExpandedSessionIds] = useState<Set<string>>(new Set([activeSessionId]));
  const [confirmDelete, setConfirmDelete] = useState<{open: boolean; sessionId?: string}>({open: false});
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

  // Attach uploaded files to session list for tree
  const uploadedFiles = messages
    .filter(m => m.files && m.files.length > 0)
    .flatMap(m => m.files!)
    .map((file, idx) => ({
      id: `file-${idx}`,
      name: file.name,
      type: file.name.endsWith('.pdf') ? 'pdf' as const : 'txt' as const,
      uploadedAt: new Date()
    }));


  // Normalize analysis I/O into IOPoint[]
  const ioPoints: IOPoint[] = [];
  if (currentAnalysis) {
    const inputsRaw = currentAnalysis.inputs
      || currentAnalysis.io_points?.inputs
      || [];
    const outputsRaw = currentAnalysis.outputs
      || currentAnalysis.io_points?.outputs
      || [];

    const normalize = (arr: any[], kind: 'input' | 'output') => {
      arr.forEach((entry: any, idx: number) => {
        if (typeof entry === 'string') {
          // Heuristic for dataType from name
          const lower = entry.toLowerCase();
          const dataType = lower.includes('temp') || lower.includes('pressure') || lower.includes('setpoint') ? 'Analog' : (lower.includes('status') || lower.includes('command') ? 'Binary' : 'Unknown');
          ioPoints.push({ id: `${kind}-${idx}`, name: entry, type: kind, dataType });
        } else if (entry && typeof entry === 'object') {
          ioPoints.push({ id: `${kind}-${idx}`, name: entry.name || `Point_${idx + 1}`, type: kind, dataType: entry.type || 'Unknown' });
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
          <Database size={20} />
          <span>N4 Builder</span>
          <span style={{ fontSize: 12, marginLeft: 8, color: '#94a3b8' }}>Powered by PyBOG</span>
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

            {/* Session Manager - compact tree style */}
            <div className="nav-section">
              <div 
                className="nav-section-header"
                onClick={() => toggleSection('sessions')}
              >
                {expandedSections.has('sessions') ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                <FolderTree size={14} />
                <span>Chat History</span>
                <button 
                  className="nav-action"
                  onClick={(e) => { e.stopPropagation(); onCreateSession(); }}
                  title="New session"
                  aria-label="New session"
                  style={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'center' }}
                >
                  <Plus size={14} />
                </button>
              </div>
              {expandedSections.has('sessions') && (
                <div className="nav-section-content">
                  {sessions.length === 0 ? (
                    <div className="nav-empty">No sessions</div>
                  ) : (
                    sessions.map((s) => {
                      const expanded = expandedSessionIds.has(s.id);
                      const isActive = s.id === activeSessionId;
                      const onToggle = (e: React.MouseEvent) => {
                        e.stopPropagation();
                        setExpandedSessionIds(prev => {
                          const ns = new Set(prev);
                          ns.has(s.id) ? ns.delete(s.id) : ns.add(s.id);
                          return ns;
                        });
                      };
                      return (
                        <div key={s.id}>
                          <div 
                            className={`nav-session ${isActive ? 'active' : ''}`}
                            onClick={() => onSwitchSession(s.id)}
                          >
                            <span onClick={onToggle} style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
                              {expanded ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
                              <span className="session-name">{s.name || s.id}</span>
                            </span>
                            <span className="session-time">{new Date(s.createdAt).toLocaleString()}</span>
                            <button 
                              className="session-delete"
                              title="Remove session"
                              onClick={(e) => { e.stopPropagation(); setConfirmDelete({open: true, sessionId: s.id}); }}
                            >
                              <Trash2 size={14} />
                            </button>
                          </div>
                          {expanded && (
                            <div className="nav-section-content">
                              {/* Uploaded Files under this session */}
                              <div className="nav-section">
                                <div className="nav-section-header" onClick={(e) => e.stopPropagation()}>
                                  <Folder size={14} />
                                  <span>Uploads ({uploadedFiles.length})</span>
                                </div>
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
                              </div>
                              {/* Analysis tree for ACTIVE session only */}
                              {s.id === activeSessionId && currentAnalysis && (
                                <div className="nav-section">
                                  <div className="nav-section-header" onClick={(e) => e.stopPropagation()}>
                                    <Database size={14} />
                                    <span>Analysis</span>
                                  </div>
                                  <div className="nav-section-content">
                                    {/* I/O Points counts */}
                                    <div className="io-group">
                                      <span className="io-group-label">I/O Points</span>
                                      <div className="nav-io-point input" onClick={() => analysisMessageId && onNavigateToMessage(analysisMessageId)}>
                                        <span className="io-indicator">●</span>
                                        <span>Inputs</span>
                                        <span className="io-type">{ioPoints.filter(p => p.type==='input').length}</span>
                                      </div>
                                      <div className="nav-io-point output" onClick={() => analysisMessageId && onNavigateToMessage(analysisMessageId)}>
                                        <span className="io-indicator">●</span>
                                        <span>Outputs</span>
                                        <span className="io-type">{ioPoints.filter(p => p.type==='output').length}</span>
                                      </div>
                                    </div>
                                    {/* Functional Blocks */}
                                    {(() => {
                                      const blocks: any[] = (currentAnalysis?.blocks
                                        || currentAnalysis?.functional_blocks
                                        || currentAnalysis?.controlBlocks
                                        || []);
                                      return (
                                        <div className="io-group">
                                          <span className="io-group-label">Functional Blocks ({blocks?.length || 0})</span>
                                          {(blocks || []).slice(0, 6).map((b: any, idx: number) => (
                                            <div key={`blk-${idx}`} className="nav-io-point" onClick={() => analysisMessageId && onNavigateToMessage(analysisMessageId)}>
                                              <span className="io-indicator">■</span>
                                              <span>{typeof b === 'string' ? b : (b?.name || 'Block')}</span>
                                            </div>
                                          ))}
                                        </div>
                                      );
                                    })()}
                                    {/* BOG Files placeholder */}
                                    <div className="io-group">
                                      <span className="io-group-label">BOG Files</span>
                                      <div className="nav-empty">No files yet</div>
                                    </div>
                                  </div>
                                </div>
                              )}
                            </div>
                          )}
                        </div>
                      );
                    })
                  )}
                </div>
              )}
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

            {/* Project Tree (Post-Analysis) */}
            {currentAnalysis && (
              <div className="nav-section">
                <div 
                  className="nav-section-header"
                  onClick={() => toggleSection('project-tree')}
                >
                  {expandedSections.has('project-tree') ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                  <Database size={14} />
                  <span>N4 Builder</span>
                  <span className="nav-subtle" style={{ marginLeft: 6, fontStyle: 'italic', color: '#94a3b8', fontSize: 11 }}>Powered by PyBOG</span>
                </div>
                {expandedSections.has('project-tree') && (
                  <div className="nav-section-content">
                    {/* Title */}
                    <div className="nav-subtle">Project: {uploadedFiles[0]?.name || 'Current Session'}</div>

                    {/* Inputs */}
                    <div className="io-group">
                      <span className="io-group-label">Inputs (AI/BI)</span>
                      {ioPoints.filter(p => p.type === 'input').length === 0 ? (
                        <div className="nav-empty">No inputs detected</div>
                      ) : (
                        ioPoints.filter(p => p.type === 'input').map(point => (
                          <div key={point.id} className="nav-io-point input" onClick={() => analysisMessageId && onNavigateToMessage(analysisMessageId)}>
                            <span className="io-indicator">→</span>
                            <span>{point.name}</span>
                            <span className="io-type">{point.dataType}</span>
                          </div>
                        ))
                      )}
                    </div>

                    {/* Outputs */}
                    <div className="io-group">
                      <span className="io-group-label">Outputs (AO/BO)</span>
                      {ioPoints.filter(p => p.type === 'output').length === 0 ? (
                        <div className="nav-empty">No outputs detected</div>
                      ) : (
                        ioPoints.filter(p => p.type === 'output').map(point => (
                          <div key={point.id} className="nav-io-point output" onClick={() => analysisMessageId && onNavigateToMessage(analysisMessageId)}>
                            <span className="io-indicator">←</span>
                            <span>{point.name}</span>
                            <span className="io-type">{point.dataType}</span>
                          </div>
                        ))
                      )}
                    </div>

                    {/* Functional Blocks */}
                    {(() => {
                      const blocks: any[] = (currentAnalysis?.blocks
                        || currentAnalysis?.functional_blocks
                        || currentAnalysis?.controlBlocks
                        || []);
                      if (!blocks || blocks.length === 0) return null;
                      return (
                        <div className="io-group" style={{ marginTop: 8 }}>
                          <span className="io-group-label">Functional Blocks</span>
                          {blocks.map((b: any, idx: number) => (
                            <div key={`block-${idx}`} className="nav-io-point" onClick={() => analysisMessageId && onNavigateToMessage(analysisMessageId)}>
                              <span className="io-indicator">■</span>
                              <span>{typeof b === 'string' ? b : (b?.name || 'Block')}</span>
                            </div>
                          ))}
                        </div>
                      );
                    })()}
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

        {/* Confirm delete modal */}
        <ConfirmModal
          isOpen={confirmDelete.open}
          title="Remove Session"
          message="Are you sure you want to delete this session? This will remove its messages from the current view."
          confirmLabel="Delete"
          onConfirm={() => { if (confirmDelete.sessionId) { onDeleteSession(confirmDelete.sessionId); } setConfirmDelete({open:false}); }}
          onCancel={() => setConfirmDelete({open:false})}
        />

        {/* Main Canvas */}
        <div className="workbench-canvas">
          <ReactFlowProvider>
            <ChatCanvas
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

export default SimplifiedWorkbench;
