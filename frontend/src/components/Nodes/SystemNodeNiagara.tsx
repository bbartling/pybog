import React, { useMemo, useState } from 'react';
import type { NodeProps } from 'reactflow';
import { Handle, Position } from 'reactflow';
import { Database, CheckCircle, XCircle, Wand2, File, Download, Eye, FileText, Zap, Settings, Maximize2 } from 'lucide-react';
// Using unified API service for all backend communication
import { unifiedAPIService } from '../../services/UnifiedAPIService';
import { TOKENS, STYLES, COMPONENTS } from '../../theme/neubrutalism';
import TextExpansionModal from '../TextExpansionModal';
import FileViewerModal, { FileToView } from '../FileViewerModal';

interface ActionDef { label: string; action: string; primary?: boolean; color?: string; recommended?: boolean; }

interface SystemData {
  content?: string;
  timestamp?: Date | string;
  analysis?: any;
  downloadUrl?: string;
  files?: FileToView[];
  // Option B wiring
  sessionId?: string;
  actions?: Record<string, ActionDef> | undefined;
  resumeUrl?: string;
  workflowStatus?: string;
}

const SystemNodeNiagara: React.FC<NodeProps<SystemData>> = ({ data, id }) => {
  const time = data?.timestamp ? new Date(data.timestamp) : null;
  const [submitting, setSubmitting] = useState<string | null>(null);
  const [note, setNote] = useState<{ kind: 'success' | 'error'; text: string } | null>(null);
  const [showFullText, setShowFullText] = useState(false);
  const [fileToView, setFileToView] = useState<FileToView | null>(null);

  const actionSet = useMemo(() => {
    const a: Record<string, ActionDef> = (data?.actions as any) || {};
    // Normalize known actions to keys
    const confirm = a.confirm || a.approve || a['generation_confirm'];
    const regenerate = a.regenerate || a.retry || a['generation_regenerate'];
    const cancel = a.cancel || a.abort || a['generation_cancel'];
    const approveAnalysis = a.approve_analysis;
    const refineAnalysis = a.refine_analysis || a.request_changes;
    return { confirm, regenerate, cancel, approveAnalysis, refineAnalysis } as const;
  }, [data?.actions]);

  const statusPill = useMemo(() => {
    const status = data?.workflowStatus;
    if (status === 'awaiting_approval' || status === 'awaiting_confirmation') {
      return { bg: TOKENS.awaitingApproval, label: 'AWAITING' };
    }
    if (status === 'generating' || status === 'processing') {
      return { bg: TOKENS.running, label: 'RUNNING' };
    }
    return { bg: '#D6F3D7', label: 'READY' };
  }, [data?.workflowStatus]);

  const handleAction = async (kind: 'confirm' | 'regenerate' | 'cancel' | 'approve_analysis' | 'refine_analysis') => {
    if (!data?.sessionId) return;
    setSubmitting(kind);
    try {
      if (kind === 'approve_analysis') {
        // Send approval message via chat
        await unifiedAPIService.sendChatMessage(data.sessionId!, 'Analysis approved. Please proceed with BOG generation.');
      } else if (kind === 'refine_analysis') {
        // Send refinement request via chat
        await unifiedAPIService.sendChatMessage(data.sessionId!, 'Please refine the analysis based on my feedback.');
      } else {
        // Handle other actions via chat
        await unifiedAPIService.sendChatMessage(data.sessionId!, `Action requested: ${kind}`);
      }
      setNote({ kind: 'success', text: 'Action sent' });
      setTimeout(() => setNote(null), 2000);
    } catch (e) {
      console.error('Confirm/Regenerate/Cancel failed', e);
      setNote({ kind: 'error', text: 'Action failed' });
      setTimeout(() => setNote(null), 2500);
    } finally {
      setSubmitting(null);
    }
  };

  const handleFileWorkflow = async (action: 'extract_text' | 'analyze' | 'generate_bog') => {
    if (!data?.sessionId || !data?.files || data.files.length === 0) return;

    setSubmitting(action);
    try {
      const file = data.files.find(f => f.type === 'pdf') || data.files[0];

      if (action === 'extract_text') {
        // Extract text from PDF
        const response = await fetch(`${process.env.REACT_APP_API_URL || 'http://localhost:8847'}/api/files/${file.file_id}/content`);
        if (response.ok) {
          const textData = await response.json();
          await unifiedAPIService.sendChatMessage(data.sessionId,
            `📄 **Text Extracted from ${file.name}:**\n\n${textData.content}\n\n*Please review this extracted text and let me know if you want to proceed with HVAC analysis.*`
          );
          setNote({ kind: 'success', text: 'Text extracted successfully' });
        } else {
          throw new Error('Failed to extract text');
        }
      } else if (action === 'analyze') {
        // Start HVAC analysis
        await unifiedAPIService.sendChatMessage(data.sessionId,
          `🔍 **Starting HVAC Analysis of ${file.name}**\n\nAnalyzing the document for:\n• I/O Points (sensors, actuators)\n• Control Sequences\n• Equipment Schedules\n• Control Logic\n\nThis may take a few moments...`
        );
        setNote({ kind: 'success', text: 'Analysis started' });
      } else if (action === 'generate_bog') {
        // Generate BOG file
        await unifiedAPIService.sendChatMessage(data.sessionId,
          `⚙️ **Generating BOG File from Analysis**\n\nCreating Niagara-compatible BOG file with:\n• All identified I/O points\n• Control logic components\n• Equipment configurations\n• Wire sheet definitions\n\nGenerating BOG file...`
        );
        setNote({ kind: 'success', text: 'BOG generation started' });
      }

      setTimeout(() => setNote(null), 3000);
    } catch (e) {
      console.error(`File workflow ${action} failed:`, e);
      setNote({ kind: 'error', text: `${action} failed` });
      setTimeout(() => setNote(null), 3000);
    } finally {
      setSubmitting(null);
    }
  };

  // Format content with better code block support
  const formatContent = (content: string) => {
    if (!content) {
      return {
        text: 'No content',
        hasCodeBlocks: false,
        isLongContent: false
      };
    }

    // Check if content contains code patterns
    const hasCodeBlocks = content.includes('```') || content.includes('    ') || /^\s*[\w]+:\s/.test(content);

    return {
      text: content,
      hasCodeBlocks,
      isLongContent: content.length > 300
    };
  };

  const contentInfo = formatContent(data?.content || '');
  const truncatedContent = contentInfo.isLongContent ?
    `${contentInfo.text.slice(0, 300)}...` :
    contentInfo.text;

  return (
    <div style={{
      background: TOKENS.white,
      border: `4px solid ${TOKENS.text}`, // Thicker border for Neo-Brutalism
      borderRadius: STYLES.radius.medium,
      boxShadow: `6px 6px 0px ${TOKENS.text}`, // Hard-edged offset shadow
      minWidth: '320px',
      maxWidth: '480px',
      fontFamily: "'JetBrains Mono', 'Fira Code', 'SF Mono', Consolas, monospace", // Monospaced for technical feel
      position: 'relative',
      transition: 'transform 0.1s ease'
    }}>
      {/* Input Port - Niagara wiresheet style */}
      <Handle
        type="target"
        position={Position.Left}
        style={{
          background: TOKENS.info,
          width: 12,
          height: 12,
          border: `3px solid ${TOKENS.text}`,
          borderRadius: '2px', // Slightly rounded for wiresheet feel
          left: -6
        }}
      />
      
      {/* Node Header - Enhanced Niagara style */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        padding: '10px 14px',
        background: TOKENS.systemHeader,
        borderBottom: `3px solid ${TOKENS.text}`,
        gap: '10px'
      }}>
        <div style={{
          width: '26px',
          height: '26px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          background: TOKENS.white,
          borderRadius: '3px',
          border: `2px solid ${TOKENS.text}`,
          color: TOKENS.text
        }}>
          <Database size={14} />
        </div>
        <div style={{
          flex: 1,
          fontSize: '14px',
          fontWeight: 700,
          color: TOKENS.text,
          textTransform: 'uppercase',
          letterSpacing: '0.5px'
        }}>
          SYSTEM NODE
        </div>
        <div style={{
          padding: '4px 10px',
          borderRadius: '4px',
          fontSize: '10px',
          fontWeight: 700,
          textTransform: 'uppercase',
          letterSpacing: '0.5px',
          background: statusPill.bg,
          border: `2px solid ${TOKENS.text}`,
          color: TOKENS.text,
          boxShadow: `2px 2px 0px ${TOKENS.text}`
        }}>
          <CheckCircle size={10} style={{ display: 'inline', marginRight: '4px' }} />
          {statusPill.label}
        </div>
      </div>
      
      {/* Node Content */}
      <div style={{
        padding: '14px',
        background: TOKENS.systemBody,
        borderRadius: '0 0 4px 4px'
      }}>
        {/* Enhanced content display with better formatting */}
        <div
          onClick={() => setShowFullText(true)}
          style={{
            fontSize: contentInfo.hasCodeBlocks ? '11px' : '12px',
            lineHeight: contentInfo.hasCodeBlocks ? '1.4' : '1.5',
            wordBreak: 'break-word',
            whiteSpace: 'pre-wrap',
            minHeight: '60px',
            maxHeight: '220px',
            overflow: 'hidden',
            cursor: contentInfo.isLongContent ? 'pointer' : 'default',
            border: `3px solid ${TOKENS.text}`,
            padding: '12px',
            paddingBottom: contentInfo.isLongContent ? '35px' : '12px',
            borderRadius: '6px',
            background: contentInfo.hasCodeBlocks ? '#1a1a1a' : TOKENS.white,
            color: contentInfo.hasCodeBlocks ? '#00ff41' : TOKENS.text,
            fontFamily: contentInfo.hasCodeBlocks ?
              "'JetBrains Mono', 'Fira Code', 'SF Mono', Consolas, monospace" :
              "'Inter', system-ui, sans-serif",
            position: 'relative',
            boxShadow: `3px 3px 0px ${TOKENS.text}`,
            transition: 'transform 0.1s ease'
          }}
          title={contentInfo.isLongContent ? "Click to view full content" : undefined}
          onMouseEnter={(e) => {
            if (contentInfo.isLongContent) {
              e.currentTarget.style.transform = 'translate(-1px, -1px)';
              e.currentTarget.style.boxShadow = `4px 4px 0px ${TOKENS.text}`;
            }
          }}
          onMouseLeave={(e) => {
            if (contentInfo.isLongContent) {
              e.currentTarget.style.transform = 'translate(0px, 0px)';
              e.currentTarget.style.boxShadow = `3px 3px 0px ${TOKENS.text}`;
            }
          }}
        >
          {truncatedContent}
          {contentInfo.isLongContent && (
            <div style={{
              position: 'absolute',
              bottom: '8px',
              right: '10px',
              background: TOKENS.warning,
              color: TOKENS.text,
              fontSize: '9px',
              padding: '4px 8px',
              borderRadius: '3px',
              fontWeight: 700,
              textTransform: 'uppercase',
              letterSpacing: '0.5px',
              border: `2px solid ${TOKENS.text}`,
              boxShadow: `2px 2px 0px ${TOKENS.text}`,
              zIndex: 10,
              cursor: 'pointer'
            }}>
              <Maximize2 size={8} style={{ marginRight: 4 }} />
              VIEW FULL
            </div>
          )}
        </div>

        {/* File attachments */}
        {data?.files && data.files.length > 0 && (
          <div style={{ marginTop: 12 }}>
            {data.files.map((file, index) => (
              <div key={index} style={{
                display: 'flex',
                alignItems: 'center',
                gap: 8,
                padding: '8px 12px',
                background: TOKENS.white,
                border: `2px solid ${TOKENS.border}`,
                borderRadius: STYLES.radius.medium,
                marginBottom: 8
              }}>
                <File size={16} color={TOKENS.primary} />
                <div style={{ flex: 1, fontSize: '11px', fontWeight: 600, color: TOKENS.text }}>
                  {file.name}
                  {file.file_size && (
                    <span style={{ color: TOKENS.muted, fontWeight: 400 }}>
                      {' '}({(file.file_size / 1024).toFixed(1)} KB)
                    </span>
                  )}
                </div>
                <button
                  onClick={() => setFileToView(file)}
                  style={{
                    ...COMPONENTS.button.base,
                    ...COMPONENTS.button.primary,
                    padding: '4px 8px',
                    fontSize: '10px'
                  }}
                  title="Preview file"
                >
                  <Eye size={12} style={{ marginRight: 4 }} />
                  View
                </button>
                <a
                  href={file.file_id ?
                    `${process.env.REACT_APP_API_URL || 'http://localhost:8847'}/api/files/${file.file_id}/download` :
                    file.url
                  }
                  download
                  style={{
                    ...COMPONENTS.button.base,
                    ...COMPONENTS.button.success,
                    padding: '4px 8px',
                    fontSize: '10px',
                    textDecoration: 'none'
                  }}
                  title="Download file"
                >
                  <Download size={12} style={{ marginRight: 4 }} />
                  DL
                </a>
              </div>
            ))}

            {/* Workflow Actions for PDF files */}
            {data.files.some(f => f.type === 'pdf') && (
              <div style={{
                display: 'flex',
                gap: 8,
                marginTop: 8,
                padding: '8px',
                background: TOKENS.bg,
                border: `1px dashed ${TOKENS.border}`,
                borderRadius: STYLES.radius.small
              }}>
                <button
                  onClick={() => handleFileWorkflow('extract_text')}
                  style={{
                    ...COMPONENTS.button.base,
                    ...COMPONENTS.button.primary,
                    flex: 1,
                    fontSize: '10px',
                    padding: '6px 8px'
                  }}
                  title="Extract text from PDF for analysis"
                  disabled={!!submitting}
                >
                  <FileText size={12} style={{ marginRight: 4 }} />
                  {submitting === 'extract_text' ? 'Extracting...' : 'Extract Text'}
                </button>
                <button
                  onClick={() => handleFileWorkflow('analyze')}
                  style={{
                    ...COMPONENTS.button.base,
                    ...COMPONENTS.button.success,
                    flex: 1,
                    fontSize: '10px',
                    padding: '6px 8px'
                  }}
                  title="Analyze file for HVAC I/O points"
                  disabled={!!submitting}
                >
                  <Zap size={12} style={{ marginRight: 4 }} />
                  {submitting === 'analyze' ? 'Analyzing...' : 'Analyze'}
                </button>
                <button
                  onClick={() => handleFileWorkflow('generate_bog')}
                  style={{
                    ...COMPONENTS.button.base,
                    ...COMPONENTS.button.warning,
                    flex: 1,
                    fontSize: '10px',
                    padding: '6px 8px'
                  }}
                  title="Generate BOG file"
                  disabled={!!submitting}
                >
                  <Settings size={12} style={{ marginRight: 4 }} />
                  {submitting === 'generate_bog' ? 'Generating...' : 'Generate BOG'}
                </button>
              </div>
            )}
          </div>
        )}

        {/* Option B: Render action buttons when present */}
        {(actionSet.confirm || actionSet.regenerate || actionSet.cancel || actionSet.approveAnalysis || actionSet.refineAnalysis) && (
          <div style={{ display: 'flex', gap: 8, marginTop: 10, flexWrap: 'wrap' }}>
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
                {submitting === 'approve_analysis' ? 'Submitting…' : (actionSet.approveAnalysis.label || 'Approve Analysis')}
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
                {submitting === 'refine_analysis' ? 'Sending…' : (actionSet.refineAnalysis.label || 'Request Changes')}
              </button>
            )}
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
                onMouseEnter={(e) => { e.currentTarget.style.transform = 'translateY(-1px)'; e.currentTarget.style.boxShadow = STYLES.shadow.sm; }}
                onMouseLeave={(e) => { e.currentTarget.style.transform = 'translateY(0)'; e.currentTarget.style.boxShadow = 'none'; }}
              >
                <CheckCircle size={14} style={{ marginRight: 6 }} />
                {submitting === 'confirm' ? 'Submitting…' : (actionSet.confirm.label || 'Confirm')}
              </button>
            )}
            {actionSet.regenerate && (
              <button
                onClick={() => handleAction('regenerate')}
                disabled={!!submitting}
                style={{
                  ...COMPONENTS.button.base,
                  ...COMPONENTS.button.primary,
                  flex: 1,
                }}
                onMouseEnter={(e) => { e.currentTarget.style.transform = 'translateY(-1px)'; e.currentTarget.style.boxShadow = STYLES.shadow.sm; }}
                onMouseLeave={(e) => { e.currentTarget.style.transform = 'translateY(0)'; e.currentTarget.style.boxShadow = 'none'; }}
              >
                <Wand2 size={14} style={{ marginRight: 6 }} />
                {submitting === 'regenerate' ? 'Regenerating…' : (actionSet.regenerate.label || 'Regenerate')}
              </button>
            )}
            {actionSet.cancel && (
              <button
                onClick={() => handleAction('cancel')}
                disabled={!!submitting}
                style={{
                  ...COMPONENTS.button.base,
                  ...COMPONENTS.button.warning,
                  flex: 1,
                }}
                onMouseEnter={(e) => { e.currentTarget.style.transform = 'translateY(-1px)'; e.currentTarget.style.boxShadow = STYLES.shadow.sm; }}
                onMouseLeave={(e) => { e.currentTarget.style.transform = 'translateY(0)'; e.currentTarget.style.boxShadow = 'none'; }}
              >
                <XCircle size={14} style={{ marginRight: 6 }} />
                {submitting === 'cancel' ? 'Cancelling…' : (actionSet.cancel.label || 'Cancel')}
              </button>
            )}
          </div>
        )}

        {note && (
          <div style={{
            marginTop: 8,
            fontSize: 11,
            color: note.kind === 'success' ? TOKENS.ok : TOKENS.error,
            fontWeight: 600
          }}>
            {note.text}
          </div>
        )}

        {time && (
          <div style={{
            marginTop: '8px',
            paddingTop: '8px',
            borderTop: STYLES.border.light,
            fontSize: '10px',
            color: TOKENS.muted,
            fontStyle: 'italic'
          }}>
            {time.toLocaleTimeString()}
          </div>
        )}
      </div>
      
      {/* Output Port - Niagara wiresheet style */}
      <Handle
        type="source"
        position={Position.Right}
        style={{
          background: TOKENS.warning,
          width: 12,
          height: 12,
          border: `3px solid ${TOKENS.text}`,
          borderRadius: '2px',
          right: -6
        }}
      />

      {/* Text Expansion Modal */}
      <TextExpansionModal
        isOpen={showFullText}
        onClose={() => setShowFullText(false)}
        title="System Response"
        content={data?.content || 'No content'}
        timestamp={data?.timestamp}
        messageType="assistant"
      />

      {/* File Viewer Modal */}
      <FileViewerModal
        isOpen={!!fileToView}
        file={fileToView}
        onClose={() => setFileToView(null)}
      />
    </div>
  );
};

export default SystemNodeNiagara;
