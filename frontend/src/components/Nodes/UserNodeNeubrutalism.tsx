import React from 'react';
import { Handle, Position } from 'reactflow';
import { Upload } from 'lucide-react';
import { TOKENS, STYLES, getRoleStyle } from '../../theme/neubrutalism';

interface UserNodeData {
  content: string;
  timestamp: Date;
  files?: File[];
  status?: 'sending' | 'sent' | 'failed';
  onResend?: () => void;
}

const UserNodeNeubrutalism: React.FC<{ data: UserNodeData }> = ({ data }) => {
  const roleStyle = getRoleStyle('user');
  
  return (
    <div style={{
      border: STYLES.border.solid,
      borderRadius: STYLES.radius.large,
      overflow: 'hidden',
      background: TOKENS.white,
      width: '100%',
      minWidth: '320px',
      maxWidth: '440px',
    }}>
      <Handle type="target" position={Position.Left} style={{ opacity: 0 }} />
      
      {/* Header */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        padding: `${STYLES.spacing.sm} ${STYLES.spacing.md}`,
        background: roleStyle.header,
        borderBottom: STYLES.border.solid,
      }}>
        <div style={{
          display: 'flex',
          gap: STYLES.spacing.md,
          alignItems: 'center',
          fontWeight: STYLES.fontWeight.semibold,
          fontSize: STYLES.fontSize.sm,
        }}>
          <span>{roleStyle.icon}</span>
          <span>USER</span>
        </div>
        <div style={{
          display: 'flex',
          gap: STYLES.spacing.md,
          alignItems: 'center',
        }}>
          <span style={{
            width: '10px',
            height: '10px',
            borderRadius: '999px',
            background: data.status === 'failed' ? TOKENS.error : TOKENS.muted,
            display: 'inline-block',
          }} />
          {data.status === 'sending' && (
            <span style={{
              border: STYLES.border.solid,
              borderRadius: STYLES.radius.pill,
              padding: `2px ${STYLES.spacing.md}`,
              background: TOKENS.chip,
              fontSize: STYLES.fontSize.xs,
            }}>Sending...</span>
          )}
        </div>
      </div>
      
      {/* Body */}
      <div style={{
        padding: `${STYLES.spacing.md} ${STYLES.spacing.lg}`,
        background: roleStyle.body,
      }}>
        <div style={{
          fontSize: STYLES.fontSize.base,
          lineHeight: '1.4',
          color: TOKENS.text,
        }}>
          {data.content}
        </div>
        
        {data.files && data.files.length > 0 && (
          <div style={{
            marginTop: STYLES.spacing.md,
            display: 'flex',
            flexWrap: 'wrap',
            gap: STYLES.spacing.sm,
          }}>
            {data.files.map((file, idx) => (
              <div key={idx} style={{
                display: 'flex',
                alignItems: 'center',
                gap: STYLES.spacing.xs,
                padding: `${STYLES.spacing.xs} ${STYLES.spacing.sm}`,
                background: TOKENS.white,
                border: STYLES.border.solid,
                borderRadius: STYLES.radius.small,
                fontSize: STYLES.fontSize.xs,
              }}>
                <Upload size={12} />
                <span>{file.name}</span>
              </div>
            ))}
          </div>
        )}
      </div>
      
      {/* Footer */}
      <div style={{
        padding: `${STYLES.spacing.sm} ${STYLES.spacing.md}`,
        background: TOKENS.nodeFooter,
        borderTop: STYLES.border.light,
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
      }}>
        <span style={{
          fontSize: STYLES.fontSize.xs,
          color: TOKENS.muted,
        }}>
          {new Date(data.timestamp).toLocaleTimeString()}
        </span>
        
        {data.status === 'failed' && data.onResend && (
          <button
            onClick={data.onResend}
            style={{
              border: STYLES.border.solid,
              borderRadius: STYLES.radius.small,
              padding: `2px ${STYLES.spacing.sm}`,
              background: TOKENS.white,
              fontSize: STYLES.fontSize.xs,
              fontWeight: STYLES.fontWeight.medium,
              cursor: 'pointer',
              transition: STYLES.transition.base,
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.transform = 'translateY(-1px)';
              e.currentTarget.style.boxShadow = STYLES.shadow.sm;
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.transform = 'translateY(0)';
              e.currentTarget.style.boxShadow = 'none';
            }}
          >
            Retry ↻
          </button>
        )}
      </div>
      
      <Handle type="source" position={Position.Right} style={{ opacity: 0 }} />
    </div>
  );
};

export default UserNodeNeubrutalism;
