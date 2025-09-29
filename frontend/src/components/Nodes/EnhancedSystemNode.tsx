import React, { useMemo, useState, useCallback } from 'react';
import type { NodeProps } from 'reactflow';
import { Handle, Position } from 'reactflow';
import { 
  Database, 
  CheckCircle, 
  XCircle, 
  Wand2, 
  FileText, 
  AlertCircle,
  Download,
  Edit3,
  RefreshCw,
  ChevronDown,
  ChevronUp,
  Copy
} from 'lucide-react';
// Using unified API service for all backend communication
import { unifiedAPIService } from '../../services/UnifiedAPIService';
import { TOKENS, STYLES, COMPONENTS } from '../../theme/neubrutalism';

interface ActionDef { 
  label: string; 
  action: string; 
  primary?: boolean; 
  color?: string; 
  recommended?: boolean; 
  icon?: string;
}

interface SystemData {
  content?: string;
  timestamp?: Date | string;
  analysis?: any;
  downloadUrl?: string;
  sessionId?: string;
  actions?: Record<string, ActionDef> | undefined;
  resumeUrl?: string;
  workflowStatus?: string;
  
  // Enhanced data fields
  extractedText?: string;
  textQuality?: any;
  qualityScore?: number;
  qualityIssues?: string[];
  recommendations?: string[];
  hvacTermsFound?: string[];
  bogFilePath?: string;
  stored_files?: Array<{
    file_id: string;
    filename: string;
    file_size: number;
    download_url: string;
  }>;
  progress?: {
    percentage: number;
    phase: string;
    description: string;
    eta?: string;
  };
  
  // Workflow status fields
  status?: string;
  step?: string;
  interactionType?: string;
  message?: string;
  
  // Approval/Wait Node data
  metadata?: {
    requiresAction?: boolean;
    actionType?: string;
    waitNode?: {
      nodeId: string;
      nodeName: string;
      executionId: string;
      resumeUrl: string;
      waitType: 'approval' | 'input' | 'confirmation';
      displayData?: {
        title: string;
        description?: string;
        data: Record<string, any>;
        actions: Array<{
          id: string;
          label: string;
          type: 'primary' | 'secondary' | 'danger';
          payload: Record<string, any>;
          requiresInput?: boolean;
          inputFields?: Array<{
            name: string;
            label: string;
            type: 'text' | 'textarea' | 'boolean' | 'number' | 'select';
            required: boolean;
            options?: string[];
            defaultValue?: any;
          }>;
        }>;
      };
    };
  };
}

const EnhancedSystemNode: React.FC<NodeProps<SystemData>> = ({ data }) => {
  const time = data?.timestamp ? new Date(data.timestamp) : null;
  const [submitting, setSubmitting] = useState<string | null>(null);
  const [note, setNote] = useState<{ kind: 'success' | 'error'; text: string } | null>(null);
  const [expanded, setExpanded] = useState(false);
  const [editMode, setEditMode] = useState(false);
  const [editedText, setEditedText] = useState(data?.extractedText || '');
  const [copiedField, setCopiedField] = useState<string | null>(null);
  
  // Approval interface state
  const [showApprovalInputs, setShowApprovalInputs] = useState<string | null>(null);
  const [approvalInputs, setApprovalInputs] = useState<Record<string, any>>({});

  const actionSet = useMemo(() => {
    const a: Record<string, ActionDef> = (data?.actions as any) || {};
    return {
      confirm: a.confirm || a.approve || a['generation_confirm'],
      regenerate: a.regenerate || a.retry || a['generation_regenerate'],
      cancel: a.cancel || a.abort || a['generation_cancel'],
      approveAnalysis: a.approve_analysis,
      refineAnalysis: a.refine_analysis || a.request_changes,
      approveText: a.approve_text,
      editText: a.edit_text,
    } as const;
  }, [data?.actions]);

  const statusInfo = useMemo(() => {
    const status = data?.workflowStatus;
    if (status === 'awaiting_approval' || status === 'awaiting_confirmation') {
      return { 
        bg: TOKENS.awaitingApproval, 
        label: 'Awaiting approval',
        icon: <AlertCircle size={12} />,
        pulse: true
      };
    }
    if (status === 'generating' || status === 'processing') {
      return { 
        bg: TOKENS.running, 
        label: 'Processing…',
        icon: <RefreshCw size={12} className="animate-spin" />,
        pulse: true
      };
    }
    if (status === 'complete' || status === 'success') {
      return { 
        bg: '#D6F3D7', 
        label: 'Complete',
        icon: <CheckCircle size={12} />,
        pulse: false
      };
    }
    if (status === 'error' || status === 'failed') {
      return { 
        bg: '#FFD6D6', 
        label: 'Error',
        icon: <XCircle size={12} />,
        pulse: false
      };
    }
    return { 
      bg: '#E5E5E5', 
      label: 'Ready',
      icon: <Database size={12} />,
      pulse: false
    };
  }, [data?.workflowStatus]);

  const handleAction = useCallback(async (kind: string, additionalData?: any) => {
    if (!data?.sessionId) return;
    setSubmitting(kind);
    try {
      const payload: any = {
        sessionId: data.sessionId,
        action: kind,
        resumeUrl: data.resumeUrl
      };

      // Add specific data based on action type
      if (kind === 'edit_text' && editedText) {
        payload.extractedText = editedText;
        payload.approvedText = editedText;
      } else if (kind === 'approve_text') {
        // For text approval, include the extracted text
payload.extractedText = data.extractedText || editedText;
        payload.approvedText = data.extractedText || editedText;
      } else if (kind === 'approve_analysis' && data.analysis) {
        payload.analysis = data.analysis;
      } else if (kind === 'refine_analysis') {
        payload.feedback = additionalData?.feedback || 'Please refine the analysis';
      }

      // Use appropriate service method
      if (kind === 'approve_analysis') {
        await unifiedAPIService.sendChatMessage(data.sessionId, 'Analysis approved. Please proceed with BOG generation.');
      } else if (kind === 'refine_analysis') {
        await unifiedAPIService.sendChatMessage(data.sessionId, 'Please refine the analysis based on my feedback.');
      } else if (kind === 'approve_text') {
        await unifiedAPIService.sendChatMessage(data.sessionId, 'Text approved. Please proceed.');
      } else if (kind === 'edit_text') {
        await unifiedAPIService.sendChatMessage(data.sessionId, 'Please edit the text as requested.');
      } else {
        // Handle other actions via chat
        await unifiedAPIService.sendChatMessage(data.sessionId, `Action requested: ${kind}`);
      }
      
      setNote({ kind: 'success', text: `${kind} action completed` });
      setEditMode(false);
      setTimeout(() => setNote(null), 2000);
    } catch (e) {
      console.error(`Action ${kind} failed`, e);
      setNote({ kind: 'error', text: `${kind} failed` });
      setTimeout(() => setNote(null), 2500);
    } finally {
      setSubmitting(null);
    }
  }, [data, editedText]);
  
  const handleApprovalAction = useCallback(async (actionId: string, actionPayload: any, inputData?: any) => {
    if (!data?.sessionId || !data?.metadata?.waitNode) return;
    
    setSubmitting(actionId);
    try {
      const waitNode = data.metadata.waitNode;
      const payload: any = {
        sessionId: data.sessionId,
        action: actionPayload.action || actionId,
        resumeUrl: waitNode.resumeUrl,
        userAction: actionId
      };
      
      // Add any input data (e.g., feedback for modify actions)
      if (inputData) {
        Object.keys(inputData).forEach(key => {
          if (inputData[key] !== undefined && inputData[key] !== '') {
            payload[key] = inputData[key];
          }
        });
      }
      
      // Add execution metadata
      payload.executionId = waitNode.executionId;
      
      // Send approval via unified API service
      await unifiedAPIService.sendChatMessage(data.sessionId, `Action: ${payload.action || 'approval'}`);
      
      setNote({ kind: 'success', text: `${actionPayload.action || actionId} action completed` });
      setShowApprovalInputs(null);
      setApprovalInputs({});
      setTimeout(() => setNote(null), 2000);
    } catch (e) {
      console.error(`Approval action ${actionId} failed`, e);
      setNote({ kind: 'error', text: `${actionPayload.action || actionId} failed` });
      setTimeout(() => setNote(null), 2500);
    } finally {
      setSubmitting(null);
    }
  }, [data]);

  const handleCopy = useCallback((field: string, content: string) => {
    navigator.clipboard.writeText(content);
    setCopiedField(field);
    setTimeout(() => setCopiedField(null), 2000);
  }, []);

  const renderExtractedText = () => {
    if (!data?.extractedText) return null;

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
          <h4 style={{ fontSize: '13px', fontWeight: 600, color: TOKENS.text }}>
            <FileText size={14} style={{ display: 'inline', marginRight: '4px' }} />
            Extracted Text
          </h4>
          <div style={{ display: 'flex', gap: '4px' }}>
            {!editMode && (
              <button
                onClick={() => setEditMode(true)}
                style={{
                  padding: '2px 6px',
                  fontSize: '11px',
                  background: TOKENS.white,
                  border: STYLES.border.solid,
                  borderRadius: STYLES.radius.small,
                  cursor: 'pointer'
                }}
              >
                <Edit3 size={12} />
              </button>
            )}
            <button
              onClick={() => handleCopy('text', data.extractedText!)}
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
            <button
              onClick={() => setExpanded(!expanded)}
              style={{
                padding: '2px 6px',
                fontSize: '11px',
                background: TOKENS.white,
                border: STYLES.border.solid,
                borderRadius: STYLES.radius.small,
                cursor: 'pointer'
              }}
            >
              {expanded ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
            </button>
          </div>
        </div>
        
        {editMode ? (
          <textarea
            value={editedText}
            onChange={(e) => setEditedText(e.target.value)}
            style={{
              width: '100%',
              minHeight: '150px',
              padding: '8px',
              fontSize: '12px',
              border: STYLES.border.solid,
              borderRadius: STYLES.radius.small,
              fontFamily: 'monospace',
              resize: 'vertical'
            }}
          />
        ) : (
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
            {data.extractedText}
          </div>
        )}

        {/* Quality indicators */}
        {data.qualityScore !== undefined && (
          <div style={{
            marginTop: '8px',
            padding: '6px',
            background: data.qualityScore > 0.8 ? '#D6F3D7' : data.qualityScore > 0.5 ? '#FFF3CD' : '#FFD6D6',
            border: STYLES.border.solid,
            borderRadius: STYLES.radius.small,
            fontSize: '11px'
          }}>
            Quality Score: {(data.qualityScore * 100).toFixed(0)}%
            {data.hvacTermsFound && data.hvacTermsFound.length > 0 && (
              <span style={{ marginLeft: '8px' }}>
                | HVAC Terms: {data.hvacTermsFound.length}
              </span>
            )}
          </div>
        )}

        {/* Issues and recommendations */}
        {data.qualityIssues && data.qualityIssues.length > 0 && (
          <div style={{
            marginTop: '8px',
            padding: '6px',
            background: '#FFF3CD',
            border: STYLES.border.solid,
            borderRadius: STYLES.radius.small,
            fontSize: '11px'
          }}>
            <strong>Issues:</strong> {data.qualityIssues.join(', ')}
          </div>
        )}
      </div>
    );
  };

  const renderAnalysis = () => {
    if (!data?.analysis) return null;

    return (
      <div style={{
        marginTop: '12px',
        padding: '12px',
        background: TOKENS.white,
        border: STYLES.border.solid,
        borderRadius: STYLES.radius.small,
      }}>
        <h4 style={{ fontSize: '13px', fontWeight: 600, color: TOKENS.text, marginBottom: '8px' }}>
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
          {typeof data.analysis === 'string' 
            ? data.analysis 
            : JSON.stringify(data.analysis, null, 2)}
        </div>
      </div>
    );
  };

  const renderStoredFiles = () => {
    if (!data?.stored_files || data.stored_files.length === 0) return null;

    return (
      <div style={{
        marginTop: '12px',
        padding: '12px',
        background: TOKENS.white,
        border: STYLES.border.solid,
        borderRadius: STYLES.radius.small,
      }}>
        <h4 style={{ fontSize: '13px', fontWeight: 600, color: TOKENS.text, marginBottom: '8px' }}>
          Stored Files ({data.stored_files.length})
        </h4>
        
        {data.stored_files.map((file, idx) => (
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
            <span>{file.filename}</span>
            <div style={{ display: 'flex', gap: '4px' }}>
              <span style={{ color: '#666' }}>
                {(file.file_size / 1024).toFixed(1)} KB
              </span>
              <a
                href={file.download_url}
                target="_blank"
                rel="noopener noreferrer"
                style={{
                  color: TOKENS.primary,
                  textDecoration: 'none'
                }}
              >
                <Download size={12} />
              </a>
            </div>
          </div>
        ))}
      </div>
    );
  };

  
  const renderProgress = () => {
    if (!data?.progress) return null;

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
          <span style={{ fontWeight: 600 }}>{data.progress.phase}</span>
          <span>{data.progress.percentage}%</span>
        </div>
        <div style={{
          height: '4px',
          background: '#E5E5E5',
          borderRadius: '2px',
          overflow: 'hidden'
        }}>
          <div style={{
            height: '100%',
            width: `${data.progress.percentage}%`,
            background: TOKENS.primary,
            transition: 'width 0.3s ease'
          }} />
        </div>
        {data.progress.description && (
          <div style={{ fontSize: '10px', color: '#666', marginTop: '4px' }}>
            {data.progress.description}
          </div>
        )}
      </div>
    );
  };
  
  const renderApprovalInterface = () => {
    const waitNode = data?.metadata?.waitNode;
    if (!waitNode || !data?.metadata?.requiresAction) return null;
    
    const displayData = waitNode.displayData;
    if (!displayData) return null;
    
    // Ensure actions array exists with default values if not provided
    const actions = displayData.actions || [
      {
        id: 'approve',
        label: 'Approve',
        type: 'primary',
        payload: { action: 'approve' }
      },
      {
        id: 'reject',
        label: 'Reject',
        type: 'danger',
        payload: { action: 'reject' }
      }
    ];
    
    return (
      <div style={{
        marginTop: '12px',
        padding: '12px',
        background: TOKENS.awaitingApproval,
        border: STYLES.border.solid,
        borderRadius: STYLES.radius.small,
      }}>
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          marginBottom: '8px'
        }}>
          <AlertCircle size={16} style={{ color: TOKENS.warning }} />
          <h4 style={{ fontSize: '13px', fontWeight: 600, color: TOKENS.text, margin: 0 }}>
            {displayData.title || 'Review Required'}
          </h4>
        </div>
        
        {displayData.description && (
          <div style={{
            fontSize: '12px',
            color: TOKENS.text,
            marginBottom: '12px',
            lineHeight: '1.4'
          }}>
            {displayData.description}
          </div>
        )}
        
        {/* Display extracted text if available */}
        {displayData.data?.extractedText && (
          <div style={{
            marginBottom: '12px',
            padding: '8px',
            background: TOKENS.white,
            border: STYLES.border.solid,
            borderRadius: STYLES.radius.small,
            maxHeight: expanded ? 'none' : '120px',
            overflow: expanded ? 'visible' : 'hidden'
          }}>
            <div style={{
              fontSize: '11px',
              fontWeight: 600,
              marginBottom: '4px',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center'
            }}>
              <span>Extracted Text:</span>
              <button
                onClick={() => setExpanded(!expanded)}
                style={{
                  background: 'none',
                  border: 'none',
                  cursor: 'pointer',
                  padding: '2px'
                }}
              >
                {expanded ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
              </button>
            </div>
            <div style={{
              fontSize: '11px',
              fontFamily: 'monospace',
              whiteSpace: 'pre-wrap',
              color: '#555'
            }}>
              {displayData.data.extractedText}
            </div>
          </div>
        )}
        
        {/* Display file information */}
        {displayData.data?.files && Array.isArray(displayData.data.files) && displayData.data.files.length > 0 && (
          <div style={{
            marginBottom: '12px',
            padding: '8px',
            background: TOKENS.white,
            border: STYLES.border.solid,
            borderRadius: STYLES.radius.small
          }}>
            <div style={{
              fontSize: '11px',
              fontWeight: 600,
              marginBottom: '4px'
            }}>
              Files:
            </div>
            {displayData.data.files.map((file: any, idx: number) => (
              <div key={idx} style={{
                fontSize: '11px',
                color: '#666',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center'
              }}>
                <span>{file.fileName || file.name || 'Unknown'}</span>
                {file.size && (
                  <span>({(file.size / 1024).toFixed(1)} KB)</span>
                )}
              </div>
            ))}
          </div>
        )}
        
        {/* Approval Actions */}
        {actions && actions.length > 0 && (
          <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
            {actions.map((action) => {
              const isShowingInputs = showApprovalInputs === action.id;
              const hasInputs = action.requiresInput && action.inputFields && action.inputFields.length > 0;
              
              return (
                <div key={action.id} style={{ flex: action.type === 'primary' ? 2 : 1 }}>
                  <button
                    onClick={() => {
                      if (hasInputs && !isShowingInputs) {
                        setShowApprovalInputs(action.id);
                        // Initialize default values
                        const defaults: Record<string, any> = {};
                        action.inputFields?.forEach(field => {
                          defaults[field.name] = field.defaultValue || '';
                        });
                        setApprovalInputs(prev => ({ ...prev, [action.id]: defaults }));
                      } else if (!hasInputs || isShowingInputs) {
                        handleApprovalAction(action.id, action.payload, approvalInputs[action.id]);
                      }
                    }}
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
                     <Edit3 size={14} style={{ marginRight: 6 }} />}
                    {submitting === action.id ? 'Processing...' : action.label}
                  </button>
                  
                  {/* Input fields for actions that require input */}
                  {isShowingInputs && hasInputs && (
                    <div style={{
                      marginTop: '8px',
                      padding: '8px',
                      background: TOKENS.white,
                      border: STYLES.border.solid,
                      borderRadius: STYLES.radius.small
                    }}>
                      {action.inputFields?.map((field) => (
                        <div key={field.name} style={{ marginBottom: '8px' }}>
                          <label style={{
                            fontSize: '11px',
                            fontWeight: 600,
                            color: TOKENS.text,
                            display: 'block',
                            marginBottom: '4px'
                          }}>
                            {field.label}{field.required && <span style={{ color: TOKENS.error }}>*</span>}
                          </label>
                          {field.type === 'textarea' ? (
                            <textarea
                              value={approvalInputs[action.id]?.[field.name] || ''}
                              onChange={(e) => setApprovalInputs(prev => ({
                                ...prev,
                                [action.id]: {
                                  ...prev[action.id],
                                  [field.name]: e.target.value
                                }
                              }))}
                              placeholder={field.label}
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
                              type={field.type === 'number' ? 'number' : 'text'}
                              value={approvalInputs[action.id]?.[field.name] || ''}
                              onChange={(e) => setApprovalInputs(prev => ({
                                ...prev,
                                [action.id]: {
                                  ...prev[action.id],
                                  [field.name]: e.target.value
                                }
                              }))}
                              placeholder={field.label}
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
                      ))}
                      <div style={{ display: 'flex', gap: '4px', marginTop: '8px' }}>
                        <button
                          onClick={() => handleApprovalAction(action.id, action.payload, approvalInputs[action.id])}
                          disabled={!!submitting}
                          style={{
                            ...COMPONENTS.button.base,
                            ...COMPONENTS.button.success,
                            flex: 1,
                            fontSize: '11px'
                          }}
                        >
                          Submit
                        </button>
                        <button
                          onClick={() => {
                            setShowApprovalInputs(null);
                            setApprovalInputs(prev => ({ ...prev, [action.id]: {} }));
                          }}
                          disabled={!!submitting}
                          style={{
                            ...COMPONENTS.button.base,
                            ...COMPONENTS.button.secondary,
                            flex: 1,
                            fontSize: '11px'
                          }}
                        >
                          Cancel
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              );
          })}
          </div>
        )}
      </div>
    );
  };

  const renderActions = () => {
    const hasActions = Object.values(actionSet).some(a => a);
    if (!hasActions) return null;

    return (
      <div style={{ display: 'flex', gap: 8, marginTop: 10, flexWrap: 'wrap' }}>
        {/* Text approval actions */}
        {editMode && actionSet.editText && (
          <>
            <button
              onClick={() => handleAction('edit_text')}
              disabled={!!submitting}
              style={{
                ...COMPONENTS.button.base,
                ...COMPONENTS.button.success,
                flex: 1,
                fontWeight: 600,
              }}
            >
              <CheckCircle size={14} style={{ marginRight: 6 }} />
              {submitting === 'edit_text' ? 'Saving…' : 'Save & Continue'}
            </button>
            <button
              onClick={() => {
                setEditMode(false);
                setEditedText(data?.extractedText || '');
              }}
              disabled={!!submitting}
              style={{
                ...COMPONENTS.button.base,
                ...COMPONENTS.button.secondary,
                flex: 1,
              }}
            >
              Cancel Edit
            </button>
          </>
        )}

        {!editMode && actionSet.approveText && (
          <button
            onClick={() => handleAction('approve_text')}
            disabled={!!submitting}
            style={{
              ...COMPONENTS.button.base,
              ...COMPONENTS.button.success,
              flex: 2,
              fontWeight: 700,
            }}
          >
            <CheckCircle size={14} style={{ marginRight: 6 }} />
            {submitting === 'approve_text' ? 'Approving…' : (actionSet.approveText.label || 'Approve Text')}
          </button>
        )}

        {/* Analysis approval actions */}
        {actionSet.approveAnalysis && (
          <button
            onClick={() => handleAction('approve_analysis')}
            disabled={!!submitting}
            style={{
              ...COMPONENTS.button.base,
              ...COMPONENTS.button.success,
              flex: 2,
              fontWeight: 700,
            }}
          >
            <CheckCircle size={14} style={{ marginRight: 6 }} />
            {submitting === 'approve_analysis' ? 'Approving…' : (actionSet.approveAnalysis.label || 'Approve Analysis')}
          </button>
        )}

        {actionSet.refineAnalysis && (
          <button
            onClick={() => handleAction('refine_analysis')}
            disabled={!!submitting}
            style={{
              ...COMPONENTS.button.base,
              ...COMPONENTS.button.warning,
              flex: 1,
              fontWeight: 600,
            }}
          >
            <Wand2 size={14} style={{ marginRight: 6 }} />
            {submitting === 'refine_analysis' ? 'Requesting…' : (actionSet.refineAnalysis.label || 'Request Changes')}
          </button>
        )}

        {/* Generation confirmation actions */}
        {actionSet.confirm && (
          <button
            onClick={() => handleAction('confirm')}
            disabled={!!submitting}
            style={{
              ...COMPONENTS.button.base,
              ...COMPONENTS.button.success,
              flex: 2,
              fontWeight: 700,
            }}
          >
            <CheckCircle size={14} style={{ marginRight: 6 }} />
            {submitting === 'confirm' ? 'Confirming…' : (actionSet.confirm.label || 'Confirm')}
          </button>
        )}

        {actionSet.regenerate && (
          <button
            onClick={() => handleAction('regenerate')}
            disabled={!!submitting}
            style={{
              ...COMPONENTS.button.base,
              ...COMPONENTS.button.warning,
              flex: 1,
              fontWeight: 600,
            }}
          >
            <RefreshCw size={14} style={{ marginRight: 6 }} />
            {submitting === 'regenerate' ? 'Regenerating…' : (actionSet.regenerate.label || 'Regenerate')}
          </button>
        )}

        {actionSet.cancel && (
          <button
            onClick={() => handleAction('cancel')}
            disabled={!!submitting}
            style={{
              ...COMPONENTS.button.base,
              ...COMPONENTS.button.danger,
              flex: 1,
            }}
          >
            <XCircle size={14} style={{ marginRight: 6 }} />
            {submitting === 'cancel' ? 'Cancelling…' : (actionSet.cancel.label || 'Cancel')}
          </button>
        )}
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
          System Response
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
          whiteSpace: 'pre-wrap',
        }}>
          {/* ENHANCED: Show full content with expand/collapse for long messages */}
          {(() => {
            const content = data?.content || 'Processing...';
            // Minimal logging - only for unique content
            const contentHash = content.substring(0, 100);
            if (process.env.NODE_ENV === 'development' && 
                contentHash !== (window as any).__lastSystemContentHash) {
              console.log('[EnhancedSystemNode] New content:', contentHash + '...');
              (window as any).__lastSystemContentHash = contentHash;
            }
            const isLong = content.length > 500;
            
            if (!isLong) {
              return content;
            }
            
            return (
              <>
                <div style={{
                  maxHeight: expanded ? 'none' : '120px',
                  overflow: expanded ? 'visible' : 'hidden',
                  position: 'relative'
                }}>
                  {content}
                  {!expanded && (
                    <div style={{
                      position: 'absolute',
                      bottom: 0,
                      left: 0,
                      right: 0,
                      height: '40px',
                      background: 'linear-gradient(transparent, ' + TOKENS.systemBody + ')',
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
          })()}
        </div>

        {/* Progress indicator */}
        {renderProgress()}

        {/* Extracted text section */}
        {renderExtractedText()}

        {/* Analysis section */}
        {renderAnalysis()}

        {/* Stored files */}
        {renderStoredFiles()}
        
        {/* Approval Interface */}
        {renderApprovalInterface()}

        {/* Download link for BOG */}
        {data?.downloadUrl && (
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
              href={data.downloadUrl}
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
        {time && (
          <div style={{
            marginTop: '8px',
            fontSize: '10px',
            color: '#666',
            textAlign: 'right'
          }}>
            {time.toLocaleTimeString()}
          </div>
        )}
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

export default EnhancedSystemNode;