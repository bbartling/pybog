import React, { useRef, useEffect } from 'react';
import { 
  Send, Upload, FileText, Download, Loader2, 
  MessageCircle, User, Bot, X, RefreshCw,
  Activity, Cpu, FolderOpen, CheckCircle, AlertCircle
} from 'lucide-react';
import AnalysisBlock, { AnalysisData } from './AnalysisBlock';
import './ZebraTheme.css';

interface Message {
  id: string;
  type: 'user' | 'assistant';
  messageType?: 'system-status' | 'analysis' | 'artifact' | 'user' | 'processing';
  content: string;
  timestamp: Date;
  files?: File[];
  metadata?: {
    analysisData?: AnalysisData;
    downloadUrl?: string;
  };
}

interface ChatFlowProps {
  messages: Message[];
  isLoading: boolean;
  currentWorkflowState: string;
  currentAnalysis: AnalysisData | null;
  onSendMessage: (text: string, files: File[]) => void;
  onApproveAnalysis: () => void;
  onRequestChanges: (feedback: string) => void;
  onFileUpload: (files: File[]) => void;
}

const ChatFlow: React.FC<ChatFlowProps> = ({
  messages,
  isLoading,
  currentWorkflowState,
  currentAnalysis,
  onSendMessage,
  onApproveAnalysis,
  onRequestChanges,
  onFileUpload
}) => {
  const [inputText, setInputText] = React.useState('');
  const [attachedFiles, setAttachedFiles] = React.useState<File[]>([]);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [showWires, setShowWires] = React.useState(true);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = () => {
    if (!inputText.trim() && attachedFiles.length === 0) return;
    onSendMessage(inputText, attachedFiles);
    setInputText('');
    setAttachedFiles([]);
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    setAttachedFiles(prev => [...prev, ...files]);
    onFileUpload(files);
  };

  const removeAttachedFile = (index: number) => {
    setAttachedFiles(prev => prev.filter((_, i) => i !== index));
  };

  const getMessageIcon = (messageType?: string) => {
    switch (messageType) {
      case 'analysis':
        return <Cpu size={14} />;
      case 'artifact':
        return <FolderOpen size={14} />;
      case 'system-status':
        return <Activity size={14} />;
      case 'processing':
        return <Loader2 size={14} className="animate-spin" />;
      default:
        return <MessageCircle size={14} />;
    }
  };

  const getMessageTypeLabel = (message: Message) => {
    if (message.type === 'user') return 'User Input';
    
    switch (message.messageType) {
      case 'analysis':
        return 'HVAC Analysis';
      case 'artifact':
        return 'BOG Output';
      case 'system-status':
        return 'System Status';
      case 'processing':
        return 'Processing';
      default:
        return 'Assistant';
    }
  };

  const formatTime = (date: Date) => {
    return new Date(date).toLocaleTimeString('en-US', { 
      hour: '2-digit', 
      minute: '2-digit' 
    });
  };

  const renderMessageContent = (message: Message) => {
    // Analysis block gets special treatment
    if (message.messageType === 'analysis' && message.metadata?.analysisData) {
      return (
        <div className="analysis-content">
          <AnalysisBlock
            analysis={message.metadata.analysisData}
            onApprove={onApproveAnalysis}
            onRequestChanges={onRequestChanges}
            status={currentWorkflowState === 'awaiting_approval' ? 'pending' : 
                   currentWorkflowState === 'generating' ? 'approved' : 'idle'}
          />
        </div>
      );
    }

    // Regular message content
    return (
      <>
        <div className="message-content">
          {message.content.split('\n').map((line, i) => (
            <React.Fragment key={i}>
              {line}
              {i < message.content.split('\n').length - 1 && <br />}
            </React.Fragment>
          ))}
        </div>

        {/* File attachments */}
        {message.files && message.files.length > 0 && (
          <div className="message-attachments">
            {message.files.map((file, idx) => (
              <div key={idx} className="attachment-chip">
                <FileText size={12} />
                <span>{file.name}</span>
              </div>
            ))}
          </div>
        )}

        {/* Download button for artifacts */}
        {message.metadata?.downloadUrl && (
          <div className="message-attachments">
            <button 
              className="attachment-chip"
              style={{ cursor: 'pointer', background: '#e3f2fd' }}
              onClick={() => window.open(message.metadata?.downloadUrl, '_blank')}
            >
              <Download size={12} />
              <span>Download BOG File</span>
            </button>
          </div>
        )}
      </>
    );
  };

  return (
    <div className="zebra-chat-container">
      {/* Chat Header */}
      <div className="chat-header">
        <div className="chat-title">
          <Cpu size={16} style={{ marginRight: '8px' }} />
          HVAC Control Logic Builder
        </div>
        <div className="chat-actions">
          <button 
            className="action-button"
            onClick={() => setShowWires(!showWires)}
            title="Toggle wire connections"
          >
            <Activity size={14} />
            Wires
          </button>
          <button 
            className="action-button"
            onClick={() => window.location.reload()}
          >
            <RefreshCw size={14} />
            New Session
          </button>
        </div>
      </div>

      {/* Messages Area */}
      <div className="chat-messages">
        <div className="chat-grid-bg" />
        
        {/* Wire connections SVG overlay */}
        {showWires && messages.length > 1 && (
          <svg className="wire-svg">
            {messages.map((_, index) => {
              if (index === 0) return null;
              const prevY = (index - 1) * 120 + 60;
              const currY = index * 120 + 60;
              const startX = index % 2 === 0 ? '30%' : '70%';
              const endX = (index + 1) % 2 === 0 ? '30%' : '70%';
              
              return (
                <path
                  key={`wire-${index}`}
                  className="wire-line"
                  d={`M ${startX} ${prevY} Q 50% ${(prevY + currY) / 2}, ${endX} ${currY}`}
                />
              );
            })}
          </svg>
        )}

        {/* Messages */}
        {messages.map((message, index) => {
          const messageClass = `message-wrapper ${message.type} ${message.messageType || ''}`;
          
          return (
            <div key={message.id} className={messageClass}>
              {/* Connection wire to previous message */}
              {index > 0 && showWires && <div className="message-connector" />}
              
              {/* Message bubble */}
              <div className="message-bubble">
                {/* Decorative pins */}
                <div className="message-pins input">
                  <div className="pin" title="Input" />
                  {message.messageType === 'analysis' && <div className="pin" title="Data" />}
                </div>
                <div className="message-pins output">
                  <div className="pin output" title="Output" />
                  {message.messageType === 'analysis' && <div className="pin output" title="Logic" />}
                </div>

                {/* Message header */}
                <div className="message-header">
                  <div className="message-type">
                    {getMessageIcon(message.messageType)}
                    <span>{getMessageTypeLabel(message)}</span>
                  </div>
                  <span className="message-time">{formatTime(message.timestamp)}</span>
                </div>

                {/* Message content */}
                {renderMessageContent(message)}
              </div>
            </div>
          );
        })}

        {/* Loading indicator */}
        {isLoading && (
          <div className="message-wrapper processing">
            <div className="message-connector" />
            <div className="message-bubble">
              <div className="message-pins input">
                <div className="pin" />
              </div>
              <div className="message-pins output">
                <div className="pin output" />
              </div>
              
              <div className="message-header">
                <div className="message-type">
                  <Loader2 size={14} className="animate-spin" />
                  <span>Processing</span>
                </div>
              </div>
              
              <div className="processing-dots">
                <div className="dot" />
                <div className="dot" />
                <div className="dot" />
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div className="chat-input-area">
        {/* Attached files display */}
        {attachedFiles.length > 0 && (
          <div style={{ width: '100%', marginBottom: '8px' }}>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
              {attachedFiles.map((file, idx) => (
                <div key={idx} className="attachment-chip">
                  <FileText size={12} />
                  <span>{file.name}</span>
                  <button
                    onClick={() => removeAttachedFile(idx)}
                    style={{ 
                      background: 'none', 
                      border: 'none', 
                      padding: '0 0 0 4px',
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center'
                    }}
                  >
                    <X size={12} />
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}

        <input
          type="file"
          ref={fileInputRef}
          onChange={handleFileSelect}
          accept=".pdf,.docx,.txt"
          multiple
          style={{ display: 'none' }}
        />
        
        <button 
          className="input-button attach"
          onClick={() => fileInputRef.current?.click()}
          title="Attach files"
        >
          <Upload size={16} />
        </button>
        
        <textarea
          className="input-field"
          value={inputText}
          onChange={(e) => setInputText(e.target.value)}
          onKeyPress={handleKeyPress}
          placeholder="Describe HVAC control requirements or upload sequence documents..."
          disabled={isLoading}
        />
        
        <div className="input-actions">
          <button 
            className="input-button"
            onClick={handleSend}
            disabled={isLoading || (!inputText.trim() && attachedFiles.length === 0)}
          >
            <Send size={16} />
          </button>
        </div>
      </div>
    </div>
  );
};

export default ChatFlow;
