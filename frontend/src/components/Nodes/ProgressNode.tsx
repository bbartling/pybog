import React from 'react';
import { Handle, Position } from 'reactflow';
import { TOKENS } from '../../theme/neubrutalism';
import TextTruncatePopup from '../TextTruncatePopup';

interface ProgressNodeProps {
  data: {
    content: string;
    timestamp: Date;
    sessionId: string;
    progressState: 'queued' | 'processing' | 'finalizing' | 'complete' | 'failed';
    progressPercent?: number;
    progressMessage?: string;
    operation?: 'analyze' | 'generate_bog' | 'cancel';
    analysis_id?: number;
    file_id?: number;
    onCancel?: () => void;
  };
}

const ProgressNode: React.FC<ProgressNodeProps> = ({ data }) => {
  const {
    content,
    timestamp,
    progressState,
    progressPercent,
    progressMessage,
    operation,
    onCancel
  } = data;

  // Determine colors and icons based on state
  const getStateConfig = (state: string) => {
    switch (state) {
      case 'queued':
        return {
          color: TOKENS.info,
          bgColor: `${TOKENS.info}20`,
          icon: '⏳',
          label: 'Queued'
        };
      case 'processing':
        return {
          color: TOKENS.primary,
          bgColor: `${TOKENS.primary}20`,
          icon: '⚙️',
          label: 'Processing'
        };
      case 'finalizing':
        return {
          color: TOKENS.warning,
          bgColor: `${TOKENS.warning}20`,
          icon: '🔄',
          label: 'Finalizing'
        };
      case 'complete':
        return {
          color: TOKENS.success,
          bgColor: `${TOKENS.success}20`,
          icon: '✅',
          label: 'Complete'
        };
      case 'failed':
        return {
          color: TOKENS.error,
          bgColor: `${TOKENS.error}20`,
          icon: '❌',
          label: 'Failed'
        };
      default:
        return {
          color: TOKENS.text,
          bgColor: `${TOKENS.text}10`,
          icon: '❓',
          label: 'Unknown'
        };
    }
  };

  const stateConfig = getStateConfig(progressState);
  const isActive = ['processing', 'finalizing'].includes(progressState);
  const canCancel = isActive && onCancel;

  return (
    <div
      style={{
        background: TOKENS.surface,
        border: `3px solid ${stateConfig.color}`,
        borderRadius: '8px',
        padding: '16px',
        minWidth: '280px',
        maxWidth: '320px',
        boxShadow: `4px 4px 0px ${stateConfig.color}`,
        fontFamily: TOKENS.fontFamily,
      }}
    >
      <Handle
        type="target"
        position={Position.Left}
        style={{
          background: stateConfig.color,
          border: `2px solid ${TOKENS.surface}`,
          width: '12px',
          height: '12px',
        }}
      />

      {/* Header */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          marginBottom: '12px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ fontSize: '16px' }}>{stateConfig.icon}</span>
          <span
            style={{
              fontWeight: 'bold',
              color: stateConfig.color,
              fontSize: '14px',
            }}
          >
            {stateConfig.label}
          </span>
        </div>
        
        {canCancel && (
          <button
            onClick={onCancel}
            style={{
              background: TOKENS.error,
              color: TOKENS.surface,
              border: `2px solid ${TOKENS.text}`,
              borderRadius: '4px',
              padding: '4px 8px',
              fontSize: '12px',
              fontWeight: 'bold',
              cursor: 'pointer',
              fontFamily: TOKENS.fontFamily,
            }}
            onMouseOver={(e) => {
              e.currentTarget.style.transform = 'translate(-2px, -2px)';
              e.currentTarget.style.boxShadow = `2px 2px 0px ${TOKENS.text}`;
            }}
            onMouseOut={(e) => {
              e.currentTarget.style.transform = 'none';
              e.currentTarget.style.boxShadow = 'none';
            }}
          >
            Cancel
          </button>
        )}
      </div>

      {/* Operation type */}
      {operation && (
        <div
          style={{
            fontSize: '12px',
            color: TOKENS.textSecondary,
            marginBottom: '8px',
            textTransform: 'capitalize',
          }}
        >
          Operation: {operation.replace('_', ' ')}
        </div>
      )}

      {/* Progress bar */}
      {progressPercent !== undefined && (
        <div
          style={{
            marginBottom: '12px',
          }}
        >
          <div
            style={{
              background: `${stateConfig.color}20`,
              border: `2px solid ${stateConfig.color}`,
              borderRadius: '4px',
              height: '20px',
              position: 'relative',
              overflow: 'hidden',
            }}
          >
            <div
              style={{
                background: stateConfig.color,
                height: '100%',
                width: `${Math.max(0, Math.min(100, progressPercent))}%`,
                transition: 'width 0.3s ease',
                position: 'relative',
              }}
            >
              {isActive && (
                <div
                  style={{
                    position: 'absolute',
                    top: 0,
                    left: 0,
                    right: 0,
                    bottom: 0,
                    background: `linear-gradient(90deg, transparent, ${TOKENS.surface}40, transparent)`,
                    animation: 'shimmer 2s infinite',
                  }}
                />
              )}
            </div>
            <div
              style={{
                position: 'absolute',
                top: '50%',
                left: '50%',
                transform: 'translate(-50%, -50%)',
                fontSize: '11px',
                fontWeight: 'bold',
                color: progressPercent > 50 ? TOKENS.surface : stateConfig.color,
                textShadow: progressPercent > 50 ? `1px 1px 0px ${stateConfig.color}` : `1px 1px 0px ${TOKENS.surface}`,
              }}
            >
              {Math.round(progressPercent)}%
            </div>
          </div>
        </div>
      )}

      {/* Progress message */}
      {progressMessage && (
        <div
          style={{
            fontSize: '13px',
            color: TOKENS.text,
            marginBottom: '8px',
            fontStyle: 'italic',
          }}
        >
          {progressMessage}
        </div>
      )}

      {/* Main content */}
      <TextTruncatePopup
        text={content}
        maxLength={150}
        maxLines={3}
        style={{
          fontSize: '14px',
          color: TOKENS.text,
          lineHeight: '1.4',
          marginBottom: '8px',
        }}
      />

      {/* Timestamp */}
      <div
        style={{
          fontSize: '11px',
          color: TOKENS.textSecondary,
          textAlign: 'right',
        }}
      >
        {timestamp.toLocaleTimeString()}
      </div>

      <Handle
        type="source"
        position={Position.Right}
        style={{
          background: stateConfig.color,
          border: `2px solid ${TOKENS.surface}`,
          width: '12px',
          height: '12px',
        }}
      />

      <style>
        {`
          @keyframes shimmer {
            0% { transform: translateX(-100%); }
            100% { transform: translateX(100%); }
          }
        `}
      </style>
    </div>
  );
};

export default ProgressNode;