import React, { useMemo, useState } from 'react';
import type { NodeProps } from 'reactflow';
import { Handle, Position } from 'reactflow';
import { Database, CheckCircle, XCircle, Wand2 } from 'lucide-react';
import n8nWebhookService from '../../services/n8nWebhookService';
import { workflowAPI } from '../../services/workflowAPI';
import { TOKENS, STYLES, COMPONENTS } from '../../theme/neubrutalism';

interface ActionDef { label: string; action: string; primary?: boolean; color?: string; recommended?: boolean; }

interface SystemData {
  content?: string;
  timestamp?: Date | string;
  analysis?: any;
  downloadUrl?: string;
  // Option B wiring
  sessionId?: string;
  actions?: Record<string, ActionDef> | undefined;
  resumeUrl?: string;
  workflowStatus?: string;
}

const SystemNodeNiagara: React.FC<NodeProps<SystemData>> = ({ data }) => {
  const time = data?.timestamp ? new Date(data.timestamp) : null;
  const [submitting, setSubmitting] = useState<string | null>(null);
  const [note, setNote] = useState<{ kind: 'success' | 'error'; text: string } | null>(null);

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
      return { bg: TOKENS.awaitingApproval, label: 'Awaiting approval' };
    }
    if (status === 'generating' || status === 'processing') {
      return { bg: TOKENS.running, label: 'Running…' };
    }
    return { bg: '#D6F3D7', label: 'OK' };
  }, [data?.workflowStatus]);

  const handleAction = async (kind: 'confirm' | 'regenerate' | 'cancel' | 'approve_analysis' | 'refine_analysis') => {
    if (!data?.sessionId) return;
    setSubmitting(kind);
    try {
      if (kind === 'approve_analysis') {
        await workflowAPI.handleApproval({ sessionId: data.sessionId!, action: 'approve_analysis' });
      } else if (kind === 'refine_analysis') {
        await workflowAPI.handleApproval({ sessionId: data.sessionId!, action: 'refine_analysis' });
      } else {
        await n8nWebhookService.confirmGeneration(
          data.sessionId!,
          kind as any,
          data.resumeUrl
        );
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
  
  return (
    <div style={{
      background: TOKENS.white,
      border: STYLES.border.solid,
      borderRadius: STYLES.radius.medium,
      boxShadow: STYLES.shadow.sm,
      minWidth: '280px',
      fontFamily: 'Inter, system-ui, -apple-system, Segoe UI, Roboto, sans-serif',
      position: 'relative'
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
          background: statusPill.bg,
          border: STYLES.border.solid,
          color: TOKENS.text
        }}>
          <CheckCircle size={12} style={{ display: 'inline', marginRight: '4px' }} />
          {statusPill.label}
        </div>
      </div>
      
      {/* Node Content */}
      <div style={{
        padding: '12px',
        background: TOKENS.systemBody,
        borderRadius: '0 0 6px 6px'
      }}>
        <div style={{
          fontSize: '12px',
          lineHeight: '1.5',
          color: TOKENS.text,
          // Removed maxHeight to allow content to expand
          // Removed overflow: hidden
          // Removed WebkitLineClamp to show full content
          wordBreak: 'break-word',
          whiteSpace: 'pre-wrap',
          // Optional: Add max-width if needed to maintain bubble width
          maxWidth: '400px'
        }}>
          {data?.content || 'No content'}
        </div>
        
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
      
      {/* Output Port */}
      <Handle 
        type="source" 
        position={Position.Right}
        style={{ 
          background: '#f59e0b',
          width: 10,
          height: 10,
          border: `2px solid ${TOKENS.black}`,
          right: -5
        }} 
      />
    </div>
  );
};

export default SystemNodeNiagara;
