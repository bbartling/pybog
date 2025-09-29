import React, { useState, useCallback } from 'react';
import type { NodeProps } from 'reactflow';
import { Handle, Position } from 'reactflow';
import { 
  Database, 
  CheckCircle, 
  XCircle, 
  AlertCircle,
  Download,
  ChevronDown,
  ChevronUp,
  Copy,
  ExternalLink,
  FileText,
  RefreshCw
} from 'lucide-react';
import { TOKENS, STYLES, COMPONENTS } from '../../theme/neubrutalism';
import { unifiedAPIService } from '../../services/UnifiedAPIService';

interface ActionItem {
  id: string;
  type: 'primary' | 'secondary' | 'danger';
  label: string;
  action: string;
  data?: any;
  placeholder?: string;
  requiresInput?: boolean;
  inputType?: 'text' | 'textarea';
}

interface FileItem {
  id: string;
  name: string;
  size?: number;
  type?: string;
  url?: string;
  downloadUrl?: string;
}

interface ResponseData {
  actions?: ActionItem[];
  files?: FileItem[];
  [key: string]: any;
}

interface StreamlinedSystemData {
  sessionId: string;
  response: ResponseData;
  timestamp?: Date | string;
}

const StreamlinedSystemNode: React.FC<NodeProps<StreamlinedSystemData>> = ({ data }) => {
  const time = data?.timestamp ? new Date(data.timestamp) : new Date();
  const [expanded, setExpanded] = useState(false);
  const [submitting, setSubmitting] = useState<string | null>(null);
  const [inputValues, setInputValues] = useState<Record<string, string>>({});
  const [note, setNote] = useState<{ kind: 'success' | 'error'; text: string } | null>(null);
  const [copiedField, setCopiedField] = useState<string | null>(null);
  
  const response = data?.response;
  
  if (!response) {
    return null;
  }
  
  const handleCopy = useCallback((field: string, content: string) => {
    navigator.clipboard.writeText(content);
    setCopiedField(field);
    setTimeout(() => setCopiedField(null), 2000);
  }, []);
  
  const handleAction = useCallback(async (action: ActionItem) => {
    if (!data?.sessionId) return;
    
    setSubmitting(action.id);
    try {
      let actionData: any = {};
      
      // Include input data if action requires input
      if (action.requiresInput && inputValues[action.id]) {
        if (action.action === 'edit_text') {
          actionData.extractedText = inputValues[action.id];
          actionData.approvedText = inputValues[action.id];
        } else if (action.action === 'refine_analysis') {
          actionData.feedback = inputValues[action.id];
        } else {
          actionData.input = inputValues[action.id];
        }
      }
      
      // For text approval, include the current text
      if (action.action === 'approve_text' && response.fullText) {
        actionData.extractedText = response.fullText;
        actionData.approvedText = response.fullText;
      }
      
      // For analysis approval, include the analysis data
      if (action.action === 'approve_analysis' && response.analysis) {
        actionData.analysis = response.analysis;
      }
      
      // Send action via unified API service
      await unifiedAPIService.sendChatMessage(data.sessionId, `Action: ${action.action} - ${JSON.stringify(actionData)}`);
      
      console.log('[StreamlinedSystemNode] Action completed');
      
      setNote({ kind: 'success', text: `${action.label} completed` });
      setInputValues(prev => ({ ...prev, [action.id]: '' })); // Clear input
      setTimeout(() => setNote(null), 2000);
      
      // The parent component should handle the response update via real-time updates
      
    } catch (error) {
      console.error(`[StreamlinedSystemNode] Action ${action.action} failed:`, error);
      const errorMessage = error instanceof Error ? error.message : 'Action failed';
      setNote({ kind: 'error', text: errorMessage });
      setTimeout(() => setNote(null), 3000);
    } finally {
      setSubmitting(null);
    }
  }, [data?.sessionId, response, inputValues]);
  
  const statusInfo = React.useMemo(() => {
    switch (response.status) {
      case 'awaiting_approval':
        return { 
          bg: TOKENS.awaitingApproval, 
          label: 'Awaiting approval',
          icon: <AlertCircle size={12} />,
          pulse: true
        };
      case 'processing':
        return { 
          bg: TOKENS.running, 
          label: 'Processing…',
          icon: <RefreshCw size={12} className="animate-spin" />,
          pulse: true
        };
      case 'complete':
        return { 
          bg: '#D6F3D7', 
          label: 'Complete',
          icon: <CheckCircle size={12} />,
          pulse: false
        };
      case 'error':
        return { 
          bg: '#FFD6D6', 
          label: 'Error',
          icon: <XCircle size={12} />,
          pulse: false
        };
      default:
        return { 
          bg: '#E5E5E5', 
          label: 'Ready',
          icon: <Database size={12} />,
          pulse: false
        };
    }
  }, [response.status]);
  
  const renderContent = () => {
    const content = response.content || response.message;
    if (!content) return null;
    
    const isLong = content.length > 500;
    
    if (!isLong) {
      return <div style={{ whiteSpace: 'pre-wrap' }}>{content}</div>;
    }
    
    return (
      <>
        <div style={{
          maxHeight: expanded ? 'none' : '120px',
          overflow: expanded ? 'visible' : 'hidden',
          position: 'relative',
          whiteSpace: 'pre-wrap'
        }}>
          {content}
          {!expanded && (
            <div style={{
              position: 'absolute',
              bottom: 0,
              left: 0,
              right: 0,
              height: '40px',
              background: `linear-gradient(transparent, ${TOKENS.systemBody})`,
              pointerEvents: 'none'
            }} />
          )}
        </div>
        <button
          onClick={() => setExpanded(!expanded)}
          style={{
            marginTop: '8px',
            padding: '4px 8px',
            fontSize: '11px',
            background: TOKENS.white,
            border: STYLES.border.solid,
            borderRadius: STYLES.radius.small,
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '4px'
          }}
        >
          {expanded ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
          {expanded ? 'Show less' : 'Show more'}
        </button>
      </>
    );
  };
  
  const renderExtractedText = () => {
    if (!response.extractedText && !response.fullText) return null;
    
    const text = response.fullText || response.extractedText;
    
    return (
      <div style={{
        marginTop: '12px',
        padding: '12px',
        background: TOKENS.white,
        border: STYLES.border.solid,
        borderRadius: STYLES.radius.small,
      }}>
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: '8px'
        }}>
          <h4 style={{ fontSize: '13px', fontWeight: 600, color: TOKENS.text, margin: 0 }}>
            <FileText size={14} style={{ display: 'inline', marginRight: '4px' }} />
            Extracted Text ({text?.length || 0} chars)
          </h4>
          <div style={{ display: 'flex', gap: '4px' }}>
            <button
              onClick={() => handleCopy('text', text || '')}
              style={{
                padding: '2px 6px',
                fontSize: '11px',
                background: copiedField === 'text' ? TOKENS.success : TOKENS.white,
                border: STYLES.border.solid,
                borderRadius: STYLES.radius.small,
                cursor: 'pointer'
              }}
            >
              <Copy size={12} />
            </button>
          </div>
        </div>
        
        <div style={{
          fontSize: '12px',
          lineHeight: '1.5',
          color: TOKENS.text,
          maxHeight: expanded ? 'none' : '100px',
          overflow: expanded ? 'visible' : 'hidden',
          whiteSpace: 'pre-wrap',
          fontFamily: 'monospace',
          background: '#F5F5F5',
          padding: '8px',
          borderRadius: STYLES.radius.small
        }}>
          {text}
        </div>
        
        {/* Quality indicators */}
        {response.quality && (
          <div style={{
            marginTop: '8px',
            padding: '6px',
            background: response.quality.score > 0.8 ? '#D6F3D7' : response.quality.score > 0.5 ? '#FFF3CD' : '#FFD6D6',
            border: STYLES.border.solid,
            borderRadius: STYLES.radius.small,
            fontSize: '11px'
          }}>
            Quality Score: {(response.quality.score * 100).toFixed(0)}%
            {response.quality.hvacTermsFound > 0 && (
              <span style={{ marginLeft: '8px' }}>
                | HVAC Terms: {response.quality.hvacTermsFound}
              </span>
            )}
          </div>
        )}
        
        {/* Issues and recommendations */}
        {response.quality?.issues && response.quality.issues.length > 0 && (
          <div style={{
            marginTop: '8px',
            padding: '6px',
            background: '#FFF3CD',
            border: STYLES.border.solid,
            borderRadius: STYLES.radius.small,
            fontSize: '11px'
          }}>
            <strong>Issues:</strong> {response.quality.issues.join(', ')}
          </div>
        )}
      </div>
    );
  };
  
  const renderAnalysis = () => {
    if (!response.analysis) return null;
    
    return (
      <div style={{
        marginTop: '12px',
        padding: '12px',
        background: TOKENS.white,
        border: STYLES.border.solid,
        borderRadius: STYLES.radius.small,
      }}>
        <h4 style={{ fontSize: '13px', fontWeight: 600, color: TOKENS.text, marginBottom: '8px', margin: 0 }}>
          HVAC Analysis Results
        </h4>
        
        <div style={{
          fontSize: '12px',
          lineHeight: '1.5',
          color: TOKENS.text,
          maxHeight: expanded ? 'none' : '150px',
          overflow: expanded ? 'visible' : 'auto',
          whiteSpace: 'pre-wrap',
          background: '#F5F5F5',
          padding: '8px',
          borderRadius: STYLES.radius.small
        }}>
          {typeof response.analysis === 'string' 
            ? response.analysis 
            : JSON.stringify(response.analysis, null, 2)}
        </div>
      </div>
    );
  };
  
  const renderProgress = () => {
    if (!response.progress) return null;
    
    return (
      <div style={{
        marginTop: '8px',
        padding: '8px',
        background: TOKENS.white,
        border: STYLES.border.solid,
        borderRadius: STYLES.radius.small,
      }}>
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: '4px',
          fontSize: '11px'
        }}>
          <span style={{ fontWeight: 600 }}>{response.progress.phase}</span>
          <span>{response.progress.percentage}%</span>
        </div>
        <div style={{
          height: '4px',
          background: '#E5E5E5',
          borderRadius: '2px',
          overflow: 'hidden'
        }}>
          <div style={{
            height: '100%',
            width: `${response.progress.percentage}%`,
            background: TOKENS.primary,
            transition: 'width 0.3s ease'
          }} />
        </div>
        {response.progress.description && (
          <div style={{ fontSize: '10px', color: '#666', marginTop: '4px' }}>
            {response.progress.description}
          </div>
        )}
      </div>
    );
  };
  
  const renderActions = () => {
    if (!response.actions || response.actions.length === 0) return null;
    
    return (
      <div style={{ marginTop: '12px' }}>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', marginBottom: '8px' }}>
          {response.actions.map((action) => (
            <div key={action.id} style={{ flex: action.type === 'primary' ? 2 : 1, minWidth: '100px' }}>
              <button
                onClick={() => handleAction(action)}
                disabled={!!submitting}
                style={{
                  ...COMPONENTS.button.base,
                  ...(action.type === 'primary' ? COMPONENTS.button.success : 
                      action.type === 'danger' ? COMPONENTS.button.danger : 
                      COMPONENTS.button.warning),
                  width: '100%',
                  fontWeight: action.type === 'primary' ? 700 : 600
                }}
              >
                {action.type === 'primary' ? <CheckCircle size={14} style={{ marginRight: 6 }} /> :
                 action.type === 'danger' ? <XCircle size={14} style={{ marginRight: 6 }} /> :
                 <AlertCircle size={14} style={{ marginRight: 6 }} />}
                {submitting === action.id ? 'Processing...' : action.label}
              </button>
              
              {/* Input field for actions that require input */}
              {action.requiresInput && (
                <div style={{ marginTop: '8px' }}>
                  {action.inputType === 'textarea' ? (
                    <textarea
                      value={inputValues[action.id] || ''}
                      onChange={(e) => setInputValues(prev => ({ ...prev, [action.id]: e.target.value }))}
                      placeholder={action.placeholder}
                      style={{
                        width: '100%',
                        minHeight: '60px',
                        padding: '6px',
                        fontSize: '11px',
                        border: STYLES.border.solid,
                        borderRadius: STYLES.radius.small,
                        resize: 'vertical'
                      }}
                    />
                  ) : (
                    <input
                      type="text"
                      value={inputValues[action.id] || ''}
                      onChange={(e) => setInputValues(prev => ({ ...prev, [action.id]: e.target.value }))}
                      placeholder={action.placeholder}
                      style={{
                        width: '100%',
                        padding: '6px',
                        fontSize: '11px',
                        border: STYLES.border.solid,
                        borderRadius: STYLES.radius.small
                      }}
                    />
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    );
  };
  
  const renderFiles = () => {
    if (!response.files || response.files.length === 0) return null;
    
    return (
      <div style={{
        marginTop: '12px',
        padding: '12px',
        background: TOKENS.white,
        border: STYLES.border.solid,
        borderRadius: STYLES.radius.small,
      }}>
        <h4 style={{ fontSize: '13px', fontWeight: 600, color: TOKENS.text, marginBottom: '8px' }}>
          Files ({response.files.length})
        </h4>
        
        {response.files.map((file: FileItem, idx: number) => (
          <div key={idx} style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            padding: '4px 8px',
            marginBottom: '4px',
            background: '#F5F5F5',
            borderRadius: STYLES.radius.small,
            fontSize: '11px'
          }}>
            <span>{file.name}</span>
            <div style={{ display: 'flex', gap: '4px' }}>
              <span style={{ color: '#666' }}>
                {file.size ? (file.size / 1024).toFixed(1) + ' KB' : 'Unknown size'}
              </span>
              {file.downloadUrl && (
                <a
                  href={file.downloadUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  style={{
                    color: TOKENS.primary,
                    textDecoration: 'none'
                  }}
                >
                  <Download size={12} />
                </a>
              )}
            </div>
          </div>
        ))}
      </div>
    );
  };
  
  return (
    <div style={{
      background: TOKENS.white,
      border: STYLES.border.solid,
      borderRadius: STYLES.radius.medium,
      boxShadow: statusInfo.pulse ? STYLES.shadow.lg : STYLES.shadow.sm,
      minWidth: '320px',
      maxWidth: '500px',
      fontFamily: 'Inter, system-ui, -apple-system, Segoe UI, Roboto, sans-serif',
      position: 'relative',
      transition: 'box-shadow 0.3s ease'
    }}>
      {/* Input Port */}
      <Handle 
        type="target" 
        position={Position.Left}
        style={{ 
          background: TOKENS.info,
          width: 10,
          height: 10,
          border: `2px solid ${TOKENS.black}`,
          left: -5
        }} 
      />
      
      {/* Node Header */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        padding: '8px 12px',
        background: TOKENS.systemHeader,
        borderBottom: STYLES.border.solid,
        gap: '8px'
      }}>
        <div style={{
          width: '24px',
          height: '24px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          background: TOKENS.white,
          borderRadius: '4px',
          color: TOKENS.text
        }}>
          <Database size={16} />
        </div>
        <div style={{
          flex: 1,
          fontSize: '13px',
          fontWeight: 600,
          color: TOKENS.text
        }}>
          {response.step === 'text_review' ? 'Text Review' :
           response.step === 'analysis_review' ? 'Analysis Review' :
           response.step === 'generation_confirmation' ? 'Generation Confirmation' :
           'System Response'}
        </div>
        <div style={{
          padding: '2px 8px',
          borderRadius: STYLES.radius.pill,
          fontSize: '11px',
          fontWeight: 600,
          textTransform: 'uppercase',
          background: statusInfo.bg,
          border: STYLES.border.solid,
          color: TOKENS.text,
          display: 'flex',
          alignItems: 'center',
          gap: '4px'
        }}>
          {statusInfo.icon}
          {statusInfo.label}
        </div>
      </div>
      
      {/* Node Content */}
      <div style={{
        padding: '12px',
        background: TOKENS.systemBody,
        borderRadius: '0 0 6px 6px'
      }}>
        {/* Main content */}
        <div style={{
          fontSize: '12px',
          lineHeight: '1.5',
          color: TOKENS.text,
          wordBreak: 'break-word',
        }}>
          {renderContent()}
        </div>
        
        {/* Progress indicator */}
        {renderProgress()}
        
        {/* Extracted text section */}
        {renderExtractedText()}
        
        {/* Analysis section */}
        {renderAnalysis()}
        
        {/* Files */}
        {renderFiles()}
        
        {/* Download link for BOG */}
        {response.downloadUrl && (
          <div style={{
            marginTop: '12px',
            padding: '8px',
            background: '#D6F3D7',
            border: STYLES.border.solid,
            borderRadius: STYLES.radius.small,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between'
          }}>
            <span style={{ fontSize: '12px', fontWeight: 600 }}>
              BOG File Ready
            </span>
            <a
              href={response.downloadUrl}
              target="_blank"
              rel="noopener noreferrer"
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '4px',
                padding: '4px 8px',
                background: TOKENS.white,
                border: STYLES.border.solid,
                borderRadius: STYLES.radius.small,
                color: TOKENS.primary,
                textDecoration: 'none',
                fontSize: '11px',
                fontWeight: 600
              }}
            >
              <Download size={12} />
              Download
            </a>
          </div>
        )}
        
        {/* Action buttons */}
        {renderActions()}
        
        {/* Warnings */}
        {response.warnings && response.warnings.length > 0 && (
          <div style={{
            marginTop: '8px',
            padding: '6px 8px',
            background: '#FFF3CD',
            border: STYLES.border.solid,
            borderRadius: STYLES.radius.small,
            fontSize: '11px',
            color: TOKENS.text
          }}>
            <AlertCircle size={12} style={{ display: 'inline', marginRight: '4px' }} />
            {response.warnings.join('; ')}
          </div>
        )}
        
        {/* Status note */}
        {note && (
          <div style={{
            marginTop: '8px',
            padding: '6px 8px',
            background: note.kind === 'success' ? '#D6F3D7' : '#FFD6D6',
            border: STYLES.border.solid,
            borderRadius: STYLES.radius.small,
            fontSize: '11px',
            color: TOKENS.text,
            display: 'flex',
            alignItems: 'center',
            gap: '4px'
          }}>
            {note.kind === 'success' ? <CheckCircle size={12} /> : <XCircle size={12} />}
            {note.text}
          </div>
        )}
        
        {/* Timestamp */}
        <div style={{
          marginTop: '8px',
          fontSize: '10px',
          color: '#666',
          textAlign: 'right'
        }}>
          {time.toLocaleTimeString()}
        </div>
      </div>
      
      {/* Output Port */}
      <Handle 
        type="source" 
        position={Position.Right}
        style={{ 
          background: TOKENS.success,
          width: 10,
          height: 10,
          border: `2px solid ${TOKENS.black}`,
          right: -5
        }} 
      />
    </div>
  );
};

export default StreamlinedSystemNode;