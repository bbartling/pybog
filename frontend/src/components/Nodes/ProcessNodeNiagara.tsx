import React from 'react';
import { Handle, Position } from 'reactflow';
import { CheckCircle, AlertCircle, Loader2, Zap, Activity } from 'lucide-react';
import { TOKENS, STYLES, COMPONENTS } from '../../theme/neubrutalism';

interface ProcessNodeData {
  stepKey: string;
  title: string;
  detail?: string;
  status: 'running' | 'ok' | 'error' | 'waiting';
  metrics?: Record<string, any>;
  timestamp?: string;
}

const ProcessNodeNiagara: React.FC<{ data: ProcessNodeData }> = ({ data }) => {
  const getStatusIcon = () => {
    switch (data.status) {
      case 'running':
        return <Loader2 className="animate-spin" size={14} />;
      case 'ok':
        return <CheckCircle size={14} />;
      case 'error':
        return <AlertCircle size={14} />;
      default:
        return <Activity size={14} />;
    }
  };

  const statusColor = () => {
    switch (data.status) {
      case 'running':
        return TOKENS.info;
      case 'ok':
        return TOKENS.ok;
      case 'error':
        return TOKENS.error;
      default:
        return TOKENS.muted;
    }
  };

  return (
    <div
      style={{
        background: TOKENS.processBody,
        border: STYLES.border.solid,
        borderRadius: STYLES.radius.medium,
        minWidth: '200px',
        boxShadow: STYLES.shadow.sm,
      }}
    >
      {/* Input Port */}
      <Handle
        type="target"
        position={Position.Left}
        style={{
          background: TOKENS.info,
          width: 10,
          height: 10,
          border: `2px solid ${TOKENS.black}`,
          left: -5,
          borderRadius: '50%'
        }}
      />
      
      {/* Header */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        padding: `${STYLES.spacing.sm} ${STYLES.spacing.md}`,
        background: TOKENS.processHeader,
        borderBottom: STYLES.border.solid,
        gap: STYLES.spacing.sm,
      }}>
        <div style={{
          width: 24,
          height: 24,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          background: TOKENS.white,
          borderRadius: STYLES.radius.small,
          color: TOKENS.text,
        }}>
          <Zap size={14} />
        </div>
        <div style={{ flex: 1, fontWeight: STYLES.fontWeight.semibold, fontSize: STYLES.fontSize.sm, color: TOKENS.text }}>
          {data.stepKey || 'Process'}
        </div>
        <div style={{
          ...COMPONENTS.badge.base,
          background: statusColor(),
          color: TOKENS.white,
          borderColor: TOKENS.border,
        }}>
          {getStatusIcon()}
          <span style={{ marginLeft: 4 }}>{data.status}</span>
        </div>
      </div>
      
      {/* Content */}
      <div style={{ padding: STYLES.spacing.md, background: TOKENS.white }}>
        <div style={{ fontSize: STYLES.fontSize.sm, color: TOKENS.text }}>
          {data.title}
        </div>
        
        {data.detail && (
          <div style={{ marginTop: STYLES.spacing.xs, fontSize: STYLES.fontSize.xs, color: TOKENS.muted, fontStyle: 'italic' }}>
            {data.detail}
          </div>
        )}
        
        {data.metrics && Object.keys(data.metrics).length > 0 && (
          <div style={{
            display: 'flex',
            gap: STYLES.spacing.lg,
            marginTop: STYLES.spacing.sm,
            paddingTop: STYLES.spacing.sm,
            borderTop: STYLES.border.light,
          }}>
            {Object.entries(data.metrics).slice(0, 3).map(([key, value]) => (
              <div key={key} style={{ fontSize: STYLES.fontSize.xs }}>
                <span style={{ color: TOKENS.muted, textTransform: 'uppercase' }}>{key}:</span>
                <span style={{ color: TOKENS.text, marginLeft: 4, fontWeight: STYLES.fontWeight.semibold }}>
                  {typeof value === 'number' ? value.toLocaleString() : String(value)}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
      
      {/* Output Port */}
      <Handle
        type="source"
        position={Position.Right}
        style={{
          background: TOKENS.warning,
          width: 10,
          height: 10,
          border: `2px solid ${TOKENS.black}`,
          right: -5,
          borderRadius: '50%'
        }}
      />
    </div>
  );
};

export default ProcessNodeNiagara;
