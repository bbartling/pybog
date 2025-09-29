/**
 * BOG Progress Node Component
 * Shows real-time progress of BOG file generation
 */

import React from 'react';
import { Handle, Position, NodeProps } from 'reactflow';
import { Loader2, Cog, FileText, CheckCircle } from 'lucide-react';
import { TOKENS, STYLES, COMPONENTS } from '../../theme/neubrutalism';

interface BOGProgressData {
  stage: 'preparing' | 'analyzing' | 'generating' | 'completed' | 'failed';
  progress: number; // 0-100
  message: string;
  timestamp: Date;
  details?: string[];
}

const BOGProgressNode: React.FC<NodeProps<BOGProgressData>> = ({ data, id }) => {
  const { stage, progress, message, timestamp, details } = data;

  const getStageIcon = () => {
    switch (stage) {
      case 'preparing':
        return <Cog size={16} className="animate-spin" />;
      case 'analyzing':
        return <Loader2 size={16} className="animate-spin" />;
      case 'generating':
        return <FileText size={16} />;
      case 'completed':
        return <CheckCircle size={16} />;
      case 'failed':
        return <span style={{ color: TOKENS.error }}>⚠</span>;
      default:
        return <Loader2 size={16} className="animate-spin" />;
    }
  };

  const getStageColor = () => {
    switch (stage) {
      case 'preparing':
        return TOKENS.warning;
      case 'analyzing':
        return TOKENS.primary;
      case 'generating':
        return TOKENS.info;
      case 'completed':
        return TOKENS.success;
      case 'failed':
        return TOKENS.error;
      default:
        return TOKENS.primary;
    }
  };

  const getStageText = () => {
    switch (stage) {
      case 'preparing':
        return 'Preparing BOG Generation';
      case 'analyzing':
        return 'Analyzing Control Logic';
      case 'generating':
        return 'Generating BOG File';
      case 'completed':
        return 'BOG Generation Complete';
      case 'failed':
        return 'Generation Failed';
      default:
        return 'Processing...';
    }
  };

  return (
    <div style={{
      ...COMPONENTS.message.base,
      minWidth: '320px',
      maxWidth: '400px',
      fontFamily: TOKENS.fontFamily,
    }}>
      {/* Input Port */}
      <Handle
        type="target"
        position={Position.Left}
        style={{
          background: TOKENS.primary,
          width: 10,
          height: 10,
          border: `2px solid ${TOKENS.black}`,
          left: -5
        }}
      />

      {/* Header */}
      <div style={{
        ...COMPONENTS.message.header,
        background: getStageColor(),
        borderBottom: STYLES.border.solid,
      }}>
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: STYLES.spacing.sm,
        }}>
          <div style={{
            width: '24px',
            height: '24px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            background: TOKENS.white,
            borderRadius: STYLES.radius.small,
            color: getStageColor()
          }}>
            {getStageIcon()}
          </div>
          <span style={{
            fontWeight: STYLES.fontWeight.bold,
            textTransform: 'uppercase',
            letterSpacing: '0.5px',
          }}>{getStageText()}</span>
        </div>
        <div style={{
          fontSize: STYLES.fontSize.xs,
          color: TOKENS.muted,
          fontWeight: STYLES.fontWeight.normal
        }}>
          {timestamp.toLocaleTimeString()}
        </div>
      </div>

      {/* Content */}
      <div style={{
        ...COMPONENTS.message.body,
        padding: STYLES.spacing.lg,
      }}>
        {/* Progress Bar */}
        <div style={{
          marginBottom: STYLES.spacing.lg,
        }}>
          <div style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            marginBottom: STYLES.spacing.sm,
          }}>
            <span style={{
              fontSize: STYLES.fontSize.sm,
              fontWeight: STYLES.fontWeight.medium,
              color: TOKENS.text
            }}>Progress</span>
            <span style={{
              fontSize: STYLES.fontSize.sm,
              fontWeight: STYLES.fontWeight.bold,
              color: getStageColor()
            }}>{progress}%</span>
          </div>

          <div style={{
            width: '100%',
            height: '12px',
            background: TOKENS.chip,
            border: `2px solid ${TOKENS.black}`,
            borderRadius: STYLES.radius.small,
            overflow: 'hidden',
            position: 'relative',
          }}>
            <div style={{
              width: `${progress}%`,
              height: '100%',
              background: `linear-gradient(90deg, ${getStageColor()} 0%, ${getStageColor()}dd 100%)`,
              transition: 'width 0.3s ease-in-out',
              position: 'relative',
            }}>
              {/* Animated stripe effect for active progress */}
              {stage !== 'completed' && stage !== 'failed' && (
                <div style={{
                  position: 'absolute',
                  top: 0,
                  left: 0,
                  right: 0,
                  bottom: 0,
                  background: `repeating-linear-gradient(
                    45deg,
                    transparent,
                    transparent 4px,
                    rgba(255,255,255,0.2) 4px,
                    rgba(255,255,255,0.2) 8px
                  )`,
                  animation: 'progress-stripes 1s linear infinite',
                }} />
              )}
            </div>
          </div>
        </div>

        {/* Current Message */}
        <div style={{
          background: TOKENS.chip,
          border: STYLES.border.light,
          borderRadius: STYLES.radius.medium,
          padding: STYLES.spacing.md,
          marginBottom: details && details.length > 0 ? STYLES.spacing.md : 0,
        }}>
          <div style={{
            fontSize: STYLES.fontSize.sm,
            color: TOKENS.text,
            lineHeight: '1.4',
            fontWeight: STYLES.fontWeight.medium,
          }}>
            {message}
          </div>
        </div>

        {/* Details */}
        {details && details.length > 0 && (
          <div style={{
            background: TOKENS.white,
            border: STYLES.border.light,
            borderRadius: STYLES.radius.medium,
            padding: STYLES.spacing.md,
          }}>
            <div style={{
              fontSize: STYLES.fontSize.xs,
              fontWeight: STYLES.fontWeight.semibold,
              color: TOKENS.muted,
              textTransform: 'uppercase',
              letterSpacing: '0.5px',
              marginBottom: STYLES.spacing.sm,
            }}>Recent Activity:</div>
            <div style={{
              maxHeight: '120px',
              overflowY: 'auto',
            }}>
              {details.map((detail, index) => (
                <div key={index} style={{
                  fontSize: STYLES.fontSize.xs,
                  color: TOKENS.text,
                  lineHeight: '1.4',
                  marginBottom: index < details.length - 1 ? STYLES.spacing.xs : 0,
                  paddingLeft: STYLES.spacing.sm,
                  borderLeft: `2px solid ${getStageColor()}`,
                }}>
                  {detail}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Output Port - Only show when completed */}
      {stage === 'completed' && (
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
      )}

      {/* CSS for animations */}
      <style>{`
        @keyframes progress-stripes {
          0% { transform: translateX(-16px); }
          100% { transform: translateX(0); }
        }

        .animate-spin {
          animation: spin 1s linear infinite;
        }

        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
};

export default BOGProgressNode;