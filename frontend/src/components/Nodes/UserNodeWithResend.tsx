import React from 'react';
import { Handle, Position } from 'reactflow';
import { User, RefreshCw, AlertCircle } from 'lucide-react';
import { TOKENS, STYLES, COMPONENTS } from '../../theme/neubrutalism';

interface UserNodeProps {
  data: {
    content: string;
    timestamp?: Date | string;
    files?: File[];
    status?: 'sending' | 'sent' | 'failed';
    onResend?: () => void;
  };
}

const UserNodeWithResend: React.FC<UserNodeProps> = ({ data }) => {
  const { content, timestamp, files, status, onResend } = data;
  const isFailed = status === 'failed';
  const isSending = status === 'sending';

  const ActionBar = () => {
    if (!data.onResend) return null;
    return (
      <div
        style={{
          display: 'flex',
          justifyContent: 'flex-end',
          gap: STYLES.spacing.sm,
          marginTop: STYLES.spacing.sm,
        }}
      >
        <button
          onClick={data.onResend}
          disabled={isSending}
          title={isFailed ? 'Resend failed message' : 'Retry this message'}
          style={{
            ...COMPONENTS.button.base,
            ...(isFailed ? {} : { borderColor: TOKENS.border }),
            color: isFailed ? TOKENS.error : TOKENS.text,
            fontSize: STYLES.fontSize.sm,
            background: TOKENS.white,
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
          <RefreshCw size={12} style={{ marginRight: 6 }} />
          {isFailed ? 'Resend' : 'Retry'}
        </button>
      </div>
    );
  };

  return (
    <div 
      style={{
        background: TOKENS.userBody,
        border: STYLES.border.solid,
        borderRadius: STYLES.radius.large,
        padding: STYLES.spacing.md,
        minWidth: '280px',
        maxWidth: '440px',
        opacity: isSending ? 0.7 : 1,
        boxShadow: STYLES.shadow.sm,
      }}
    >
      <Handle type="target" position={Position.Left} style={{ opacity: 0 }} />
      
      <div style={{ 
        display: 'flex', 
        alignItems: 'flex-start', 
        gap: STYLES.spacing.md,
        marginBottom: STYLES.spacing.sm 
      }}>
        <div style={{
          background: isFailed ? TOKENS.error : TOKENS.info,
          borderRadius: '50%',
          padding: STYLES.spacing.sm,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: TOKENS.white,
        }}>
          <User size={16} />
        </div>
        
        <div style={{ flex: 1 }}>
          <div style={{ 
            fontWeight: STYLES.fontWeight.semibold, 
            color: TOKENS.text,
            marginBottom: STYLES.spacing.xs,
            display: 'flex',
            alignItems: 'center',
            gap: STYLES.spacing.sm
          }}>
            User
            {isFailed && (
              <span style={{
                ...COMPONENTS.badge.base,
                ...COMPONENTS.badge.error,
              }}>
                <AlertCircle size={12} /> Failed
              </span>
            )}
            {isSending && (
              <span style={{
                ...COMPONENTS.badge.base,
                ...COMPONENTS.badge.info,
              }}>
                Sending…
              </span>
            )}
          </div>
          
          <div style={{ 
            fontSize: STYLES.fontSize.base, 
            color: TOKENS.text,
            lineHeight: '1.4',
            wordBreak: 'break-word'
          }}>
            {content}
          </div>
          
          {files && files.length > 0 && (
            <div style={{ 
              marginTop: STYLES.spacing.sm, 
              fontSize: STYLES.fontSize.sm, 
              color: TOKENS.muted 
            }}>
              📎 {files.length} file(s) attached
            </div>
          )}
          
          <div style={{ 
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            marginTop: STYLES.spacing.sm
          }}>
            {timestamp && (
              <div style={{ 
                fontSize: STYLES.fontSize.xs, 
                color: TOKENS.muted 
              }}>
                {new Date(timestamp as any).toLocaleTimeString()}
              </div>
            )}
          </div>

          {/* Floating action row below message */}
          <ActionBar />
        </div>
      </div>
      
      <Handle type="source" position={Position.Right} style={{ opacity: 0 }} />
    </div>
  );
};

export default UserNodeWithResend;
