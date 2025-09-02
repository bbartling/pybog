import React, { useState, useRef, useEffect } from 'react';
import { 
  Send, Upload, FileText, Download, CheckCircle, X, Loader2,
  ChevronRight, ChevronDown, Folder, FolderOpen, File, FileCode, 
  Package, Terminal, AlertCircle, Clock, Play, Pause, Settings,
  Database, Activity, Layers, GitBranch, Zap
} from 'lucide-react';
import AnalysisBlock, { AnalysisData } from './AnalysisBlock';
import './N4WorkbenchLayout.css';

interface Message {
  id: string;
  type: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: Date;
  component?: 'string-writable' | 'enum-writable' | 'bool-writable' | 'folder' | 'numeric';
  metadata?: {
    analysisData?: AnalysisData;
    downloadUrl?: string;
    status?: 'processing' | 'complete' | 'error' | 'awaiting_approval';
  };
  files?: File[];
  position?: { x: number; y: number };
}

interface BogFile {
  id: string;
  name: string;
  size: number;
  timestamp: Date;
  status: 'ready' | 'generating';
}

interface ChatSession {
  id: string;
  name: string;
  timestamp: Date;
  messages: Message[];
  uploads: UploadedFile[];
  analysis?: AnalysisData;
}

interface UploadedFile {
  id: string;
  name: string;
  type: string;
  size: number;
  content?: string;
  timestamp: Date;
}

interface ConsoleLog {
  id: string;
  timestamp: Date;
  level: 'info' | 'warn' | 'error' | 'success';
  message: string;
}

interface N4WorkbenchLayoutProps {
  messages: Message[];
  isLoading: boolean;
  bogFiles: BogFile[];
  onSendMessage: () => void;
  onApproveAnalysis?: () => void;
  onRequestChanges?: (feedback: string) => void;
  workflowState?: 'idle' | 'analyzing' | 'awaiting_approval' | 'generating' | 'complete';
  currentAnalysis?: AnalysisData;
}

const N4WorkbenchLayout: React.FC<N4WorkbenchLayoutProps> = ({
  messages,
  isLoading,
  bogFiles,
  onSendMessage,
  onApproveAnalysis,
  onRequestChanges,
  workflowState,
  currentAnalysis
}) => {
  const [inputText, setInputText] = useState('');
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [expandedFolders, setExpandedFolders] = useState<Set<string>>(new Set(['chat-history']));
  const [selectedNode, setSelectedNode] = useState<string | null>(null);
  const [consoleLogs, setConsoleLogs] = useState<ConsoleLog[]>([]);
  const [showPdfViewer, setShowPdfViewer] = useState<string | null>(null);
  const [chatSessions, setChatSessions] = useState<ChatSession[]>([]);
  const [currentSessionId] = useState(`session_${Date.now()}`);
  
  const canvasRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const consoleEndRef = useRef<HTMLDivElement>(null);

  // Initialize chat session
  useEffect(() => {
    const currentSession: ChatSession = {
      id: currentSessionId,
      name: `Session ${new Date().toLocaleTimeString()}`,
      timestamp: new Date(),
      messages: messages,
      uploads: selectedFiles.map(f => ({
        id: `file_${Date.now()}`,
        name: f.name,
        type: f.type,
        size: f.size,
        timestamp: new Date()
      })),
      analysis: currentAnalysis
    };
    
    setChatSessions(prev => {
      const existing = prev.find(s => s.id === currentSessionId);
      if (existing) {
        return prev.map(s => s.id === currentSessionId ? currentSession : s);
      }
      return [...prev, currentSession];
    });
  }, [messages, selectedFiles, currentAnalysis, currentSessionId]);

  // Add console logs based on workflow state
  useEffect(() => {
    if (workflowState === 'analyzing') {
      addConsoleLog('info', '🔄 Initiating n8n workflow processing...');
      addConsoleLog('info', '📄 Extracting text from uploaded documents...');
    } else if (workflowState === 'awaiting_approval') {
      addConsoleLog('success', '✅ Analysis complete. Awaiting user approval.');
    } else if (workflowState === 'generating') {
      addConsoleLog('info', '⚙️ Generating BOG file from approved schema...');
      addConsoleLog('info', '🔧 Calling PyBOG API with formatted control logic...');
    } else if (workflowState === 'complete') {
      addConsoleLog('success', '🎉 BOG file generated successfully!');
    }
  }, [workflowState]);

  const addConsoleLog = (level: ConsoleLog['level'], message: string) => {
    const log: ConsoleLog = {
      id: `log_${Date.now()}_${Math.random()}`,
      timestamp: new Date(),
      level,
      message
    };
    setConsoleLogs(prev => [...prev, log]);
    
    // Auto-scroll console
    setTimeout(() => {
      consoleEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, 100);
  };

  const toggleFolder = (folderId: string) => {
    setExpandedFolders(prev => {
      const newSet = new Set(prev);
      if (newSet.has(folderId)) {
        newSet.delete(folderId);
      } else {
        newSet.add(folderId);
      }
      return newSet;
    });
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    setSelectedFiles(prev => [...prev, ...files]);
    files.forEach(file => {
      addConsoleLog('info', `📎 File attached: ${file.name} (${(file.size / 1024).toFixed(2)} KB)`);
    });
  };

  const removeFile = (index: number) => {
    const file = selectedFiles[index];
    setSelectedFiles(prev => prev.filter((_, i) => i !== index));
    addConsoleLog('info', `🗑️ Removed file: ${file.name}`);
  };

  const handleSend = () => {
    if (inputText.trim() || selectedFiles.length > 0) {
      addConsoleLog('info', '📤 Sending message to n8n workflow...');
      onSendMessage();
      setInputText('');
      setSelectedFiles([]);
    }
  };

  const renderNiagaraNode = (message: Message, index: number) => {
    const isUser = message.type === 'user';
    const nodeType = isUser ? 'input-node' : 
                    message.metadata?.analysisData ? 'analysis-node' :
                    message.metadata?.downloadUrl ? 'output-node' :
                    'process-node';
    
    // Calculate node position in a flow layout
    const row = Math.floor(index / 3);
    const col = index % 3;
    const x = 100 + (col * 350);
    const y = 100 + (row * 200);

    return (
      <div
        key={message.id}
        className={`niagara-node ${nodeType} ${selectedNode === message.id ? 'selected' : ''}`}
        style={{
          left: `${x}px`,
          top: `${y}px`
        }}
        onClick={() => setSelectedNode(message.id)}
      >
        <div className="node-header">
          <div className="node-icon">
            {isUser ? <Upload size={14} /> :
             message.metadata?.analysisData ? <Layers size={14} /> :
             message.metadata?.downloadUrl ? <Download size={14} /> :
             <Zap size={14} />}
          </div>
          <div className="node-title">
            {isUser ? 'User Input' :
             message.metadata?.analysisData ? 'Analysis Result' :
             message.metadata?.downloadUrl ? 'BOG Output' :
             'Process'}
          </div>
          <div className="node-status">
            {message.metadata?.status === 'processing' ? 
              <Loader2 className="spin" size={12} /> :
              <CheckCircle size={12} />}
          </div>
        </div>
        
        <div className="node-body">
          {message.metadata?.analysisData ? (
            <div className="analysis-preview">
              <div className="stat">
                <span className="label">Inputs:</span>
                <span className="value">{message.metadata.analysisData.inputs?.length || 0}</span>
              </div>
              <div className="stat">
                <span className="label">Outputs:</span>
                <span className="value">{message.metadata.analysisData.outputs?.length || 0}</span>
              </div>
              <div className="stat">
                <span className="label">Blocks:</span>
                <span className="value">{message.metadata.analysisData.blocks?.length || 0}</span>
              </div>
              {workflowState === 'awaiting_approval' && (
                <div className="node-actions">
                  <button className="approve-btn" onClick={onApproveAnalysis}>
                    <CheckCircle size={12} /> Approve
                  </button>
                  <button className="changes-btn" onClick={() => onRequestChanges?.('Changes needed')}>
                    <X size={12} /> Changes
                  </button>
                </div>
              )}
            </div>
          ) : message.metadata?.downloadUrl ? (
            <div className="download-preview">
              <FileCode size={32} />
              <button className="download-btn">
                <Download size={14} /> Download BOG
              </button>
            </div>
          ) : (
            <div className="node-content">
              {message.content.split('\n').slice(0, 3).map((line, i) => (
                <div key={i} className="content-line">{line}</div>
              ))}
            </div>
          )}
        </div>
        
        <div className="node-slots">
          <div className="input-slot"></div>
          <div className="output-slot"></div>
        </div>
      </div>
    );
  };

  const renderWireConnections = () => {
    return messages.slice(0, -1).map((_, index) => {
      const fromRow = Math.floor(index / 3);
      const fromCol = index % 3;
      const toRow = Math.floor((index + 1) / 3);
      const toCol = (index + 1) % 3;
      
      const x1 = 100 + (fromCol * 350) + 280; // Right side of node
      const y1 = 100 + (fromRow * 200) + 60;  // Middle height
      const x2 = 100 + (toCol * 350);         // Left side of next node
      const y2 = 100 + (toRow * 200) + 60;    // Middle height
      
      // Create bezier curve for smooth connection
      const cx1 = x1 + 50;
      const cy1 = y1;
      const cx2 = x2 - 50;
      const cy2 = y2;
      
      return (
        <svg
          key={`wire_${index}`}
          className="wire-connection"
          style={{
            position: 'absolute',
            top: 0,
            left: 0,
            width: '100%',
            height: '100%',
            pointerEvents: 'none',
            zIndex: 1
          }}
        >
          <path
            d={`M ${x1} ${y1} C ${cx1} ${cy1}, ${cx2} ${cy2}, ${x2} ${y2}`}
            stroke="#4a9eff"
            strokeWidth="2"
            fill="none"
            className="wire-path"
          />
        </svg>
      );
    });
  };

  return (
    <div className="n4-workbench">
      {/* Header Bar */}
      <div className="n4-header">
        <div className="n4-logo">
          <Layers size={20} />
          <span className="n4-title">N4 Builder</span>
          <span className="n4-subtitle">Powered by PyBOG</span>
        </div>
        <div className="n4-toolbar">
          <button className="tool-btn" title="Run Workflow">
            <Play size={16} />
          </button>
          <button className="tool-btn" title="Pause">
            <Pause size={16} />
          </button>
          <button className="tool-btn" title="Settings">
            <Settings size={16} />
          </button>
        </div>
      </div>

      <div className="n4-main">
        {/* Left Sidebar - Project Navigator */}
        <div className="n4-sidebar">
          <div className="sidebar-header">
            <Database size={14} />
            <span>Project Navigator</span>
          </div>
          
          <div className="tree-view">
            {/* Chat History */}
            <div className="tree-item">
              <div 
                className="tree-label"
                onClick={() => toggleFolder('chat-history')}
              >
                {expandedFolders.has('chat-history') ? 
                  <ChevronDown size={14} /> : 
                  <ChevronRight size={14} />}
                {expandedFolders.has('chat-history') ? 
                  <FolderOpen size={14} /> : 
                  <Folder size={14} />}
                <span>Chat History</span>
              </div>
              
              {expandedFolders.has('chat-history') && chatSessions.map(session => (
                <div key={session.id} className="tree-children">
                  <div className="tree-item">
                    <div 
                      className="tree-label"
                      onClick={() => toggleFolder(session.id)}
                    >
                      {expandedFolders.has(session.id) ? 
                        <ChevronDown size={14} /> : 
                        <ChevronRight size={14} />}
                      <Clock size={14} />
                      <span>{session.name}</span>
                    </div>
                    
                    {expandedFolders.has(session.id) && (
                      <div className="tree-children">
                        {/* Uploads Folder */}
                        <div className="tree-item">
                          <div 
                            className="tree-label"
                            onClick={() => toggleFolder(`${session.id}-uploads`)}
                          >
                            {expandedFolders.has(`${session.id}-uploads`) ? 
                              <ChevronDown size={14} /> : 
                              <ChevronRight size={14} />}
                            <Folder size={14} />
                            <span>Uploads ({session.uploads.length})</span>
                          </div>
                          
                          {expandedFolders.has(`${session.id}-uploads`) && (
                            <div className="tree-children">
                              {session.uploads.map(file => (
                                <div key={file.id} className="tree-item">
                                  <div 
                                    className="tree-label file-item"
                                    onClick={() => setShowPdfViewer(file.id)}
                                  >
                                    <FileText size={14} />
                                    <span>{file.name}</span>
                                  </div>
                                </div>
                              ))}
                            </div>
                          )}
                        </div>
                        
                        {/* Analysis Folder */}
                        {session.analysis && (
                          <div className="tree-item">
                            <div 
                              className="tree-label"
                              onClick={() => toggleFolder(`${session.id}-analysis`)}
                            >
                              {expandedFolders.has(`${session.id}-analysis`) ? 
                                <ChevronDown size={14} /> : 
                                <ChevronRight size={14} />}
                              <Package size={14} />
                              <span>Analysis</span>
                            </div>
                            
                            {expandedFolders.has(`${session.id}-analysis`) && (
                              <div className="tree-children">
                                <div className="analysis-summary">
                                  <div>I/O Points: {(session.analysis.inputs?.length || 0) + (session.analysis.outputs?.length || 0)}</div>
                                  <div>Logic Blocks: {session.analysis.blocks?.length || 0}</div>
                                </div>
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
            
            {/* BOG Files */}
            <div className="tree-item">
              <div 
                className="tree-label"
                onClick={() => toggleFolder('bog-files')}
              >
                {expandedFolders.has('bog-files') ? 
                  <ChevronDown size={14} /> : 
                  <ChevronRight size={14} />}
                <FileCode size={14} />
                <span>BOG Files ({bogFiles.length})</span>
              </div>
              
              {expandedFolders.has('bog-files') && (
                <div className="tree-children">
                  {bogFiles.map(file => (
                    <div key={file.id} className="tree-item">
                      <div className="tree-label file-item">
                        <File size={14} />
                        <span>{file.name}</span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Main Canvas - Wire Sheet */}
        <div className="n4-canvas" ref={canvasRef}>
          <div className="canvas-grid">
            {renderWireConnections()}
            {messages.map((msg, idx) => renderNiagaraNode(msg, idx))}
          </div>
        </div>

        {/* Right Panel - Properties/PDF Viewer */}
        {showPdfViewer && (
          <div className="n4-right-panel">
            <div className="panel-header">
              <FileText size={14} />
              <span>Document Viewer</span>
              <button 
                className="close-btn"
                onClick={() => setShowPdfViewer(null)}
              >
                <X size={14} />
              </button>
            </div>
            <iframe 
              src={`/api/files/${showPdfViewer}`}
              className="pdf-viewer"
              title="PDF Viewer"
            />
          </div>
        )}
      </div>

      {/* Bottom Console */}
      <div className="n4-console">
        <div className="console-header">
          <Terminal size={14} />
          <span>Console Output</span>
          <button 
            className="clear-btn"
            onClick={() => setConsoleLogs([])}
          >
            Clear
          </button>
        </div>
        
        <div className="console-logs">
          {consoleLogs.map(log => (
            <div key={log.id} className={`console-log ${log.level}`}>
              <span className="log-time">
                [{log.timestamp.toLocaleTimeString()}]
              </span>
              <span className="log-message">{log.message}</span>
            </div>
          ))}
          <div ref={consoleEndRef} />
        </div>
        
        <div className="console-input">
          <input
            ref={fileInputRef}
            type="file"
            multiple
            accept=".pdf,.txt,.docx,.doc"
            onChange={handleFileSelect}
            style={{ display: 'none' }}
          />
          
          <div className="input-group">
            {selectedFiles.length > 0 && (
              <div className="attached-files">
                {selectedFiles.map((file, idx) => (
                  <div key={idx} className="file-chip">
                    <FileText size={12} />
                    <span>{file.name}</span>
                    <button onClick={() => removeFile(idx)}>
                      <X size={12} />
                    </button>
                  </div>
                ))}
              </div>
            )}
            
            <div className="input-controls">
              <button 
                className="attach-btn"
                onClick={() => fileInputRef.current?.click()}
                title="Attach files"
              >
                <Upload size={16} />
              </button>
              
              <input
                type="text"
                className="console-text-input"
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
                onKeyPress={(e) => {
                  if (e.key === 'Enter') {
                    handleSend();
                  }
                }}
                placeholder="Describe HVAC control requirements..."
              />
              
              <button 
                className="send-btn"
                onClick={handleSend}
                disabled={!inputText.trim() && selectedFiles.length === 0}
              >
                <Send size={16} />
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default N4WorkbenchLayout;
