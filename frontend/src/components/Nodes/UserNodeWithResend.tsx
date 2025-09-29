import React from 'react';
import { Handle, Position, NodeProps } from 'reactflow';
import { User, RefreshCw, AlertCircle, Maximize2 } from 'lucide-react';
import { TOKENS, STYLES, COMPONENTS } from '../../theme/neubrutalism';
import TextExpansionModal from '../TextExpansionModal';

interface UserNodeData {
  content: string;
  timestamp?: Date | string;
  files?: File[];
  status?: 'sending' | 'sent' | 'failed';
  onResend?: () => void;
}

const UserNodeWithResend: React.FC<NodeProps<UserNodeData>> = ({ data, id }) => {
  const { content, timestamp, files, status, onResend } = data;
  const isFailed = status === 'failed';
  const isSending = status === 'sending';
  const [showFullText, setShowFullText] = React.useState(false);

  // Enhanced content formatting
  const isLongContent = content.length > 200;
  const truncatedContent = isLongContent ? `${content.slice(0, 200)}...` : content;

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
        border: `4px solid ${TOKENS.text}`, // Thicker Neo-Brutalism border
        borderRadius: '8px',
        padding: '14px',
        minWidth: '300px',
        maxWidth: '460px',
        opacity: isSending ? 0.7 : 1,
        boxShadow: `6px 6px 0px ${TOKENS.text}`, // Hard-edged offset shadow
        fontFamily: "'JetBrains Mono', 'Fira Code', 'SF Mono', Consolas, monospace",
        transition: 'transform 0.1s ease'
      }}
    >
      <Handle
        type="target"
        position={Position.Left}
        style={{
          background: TOKENS.primary,
          width: 12,
          height: 12,
          border: `3px solid ${TOKENS.text}`,
          borderRadius: '2px',
          left: -6
        }}
      />
      
      <div style={{ 
        display: 'flex', 
        alignItems: 'flex-start', 
        gap: STYLES.spacing.md,
        marginBottom: STYLES.spacing.sm 
      }}>
        <div style={{
          background: isFailed ? TOKENS.error : TOKENS.primary,
          borderRadius: '4px',
          border: `2px solid ${TOKENS.text}`,
          padding: '6px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: TOKENS.white,
          boxShadow: `2px 2px 0px ${TOKENS.text}`
        }}>
          <User size={14} />
        </div>
        
        <div style={{ flex: 1 }}>
          <div style={{
            fontWeight: 700,
            color: TOKENS.text,
            marginBottom: '6px',
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            textTransform: 'uppercase',
            letterSpacing: '0.5px',
            fontSize: '13px'
          }}>
            USER NODE
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
          
          <div
            onClick={() => setShowFullText(true)}
            style={{
              fontSize: '12px',
              color: TOKENS.text,
              lineHeight: '1.5',
              wordBreak: 'break-word',
              cursor: isLongContent ? 'pointer' : 'default',
              minHeight: '50px',
              maxHeight: '140px',
              overflow: 'hidden',
              position: 'relative',
              background: TOKENS.white,
              border: `3px solid ${TOKENS.text}`,
              borderRadius: '6px',
              padding: '10px',
              paddingBottom: isLongContent ? '30px' : '10px',
              boxShadow: `3px 3px 0px ${TOKENS.text}`,
              transition: 'transform 0.1s ease',
              fontFamily: "'Inter', system-ui, sans-serif"
            }}
            title={isLongContent ? "Click to view full message" : undefined}
            onMouseEnter={(e) => {
              if (isLongContent) {
                e.currentTarget.style.transform = 'translate(-1px, -1px)';
                e.currentTarget.style.boxShadow = `4px 4px 0px ${TOKENS.text}`;
              }
            }}
            onMouseLeave={(e) => {
              if (isLongContent) {
                e.currentTarget.style.transform = 'translate(0px, 0px)';
                e.currentTarget.style.boxShadow = `3px 3px 0px ${TOKENS.text}`;
              }
            }}
          >
            {truncatedContent}
            {isLongContent && (
              <div style={{
                position: 'absolute',
                bottom: '6px',
                right: '8px',
                background: TOKENS.primary,
                color: TOKENS.white,
                fontSize: '9px',
                padding: '3px 6px',
                borderRadius: '3px',
                fontWeight: 700,
                textTransform: 'uppercase',
                letterSpacing: '0.5px',
                border: `2px solid ${TOKENS.text}`,
                boxShadow: `2px 2px 0px ${TOKENS.text}`,
                zIndex: 10,
                cursor: 'pointer'
              }}>
                <Maximize2 size={8} style={{ marginRight: 3 }} />
                VIEW
              </div>
            )}
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
      <Handle
        type="source"
        position={Position.Right}
        style={{
          background: TOKENS.success,
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
        title="User Message"
        content={content}
        timestamp={timestamp}
        messageType="user"
      />
    </div>
  );
};

export default UserNodeWithResend;
