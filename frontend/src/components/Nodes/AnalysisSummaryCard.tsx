/**
 * Analysis Summary Card Component
 * Displays analysis results following PyBOG neubrutalism design system
 */

import React from 'react';
import { Handle, Position, NodeProps } from 'reactflow';
import { BarChart3, CheckCircle, Eye, Play } from 'lucide-react';
import { TOKENS, STYLES, COMPONENTS } from '../../theme/neubrutalism';
import { AnalysisSummary } from '../../services/ChatPipelineService';

interface AnalysisSummaryCardData {
  summary: AnalysisSummary;
  timestamp: Date;
  onExpand?: () => void;
  onApprove?: () => void;
}

const AnalysisSummaryCard: React.FC<NodeProps<AnalysisSummaryCardData>> = ({ data, id }) => {
  const { summary, timestamp, onExpand, onApprove } = data;

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
          background: TOKENS.success,
          width: 10,
          height: 10,
          border: `2px solid ${TOKENS.black}`,
          left: -5
        }} 
      />
      
      {/* Header */}
      <div style={{
        ...COMPONENTS.message.header,
        background: TOKENS.approved,
        borderBottom: STYLES.border.solid,
      }}>
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: STYLES.spacing.sm,
        }}>
          <div style={{
            width: '20px',
            height: '20px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            background: TOKENS.white,
            borderRadius: STYLES.radius.small,
            color: TOKENS.success
          }}>
            <BarChart3 size={14} />
          </div>
          <span>Analysis Complete</span>
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
        {/* Summary Grid */}
        <div style={{
          display: 'grid',
          gap: STYLES.spacing.sm,
          marginBottom: STYLES.spacing.lg,
        }}>
          <div style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            padding: `${STYLES.spacing.xs} 0`,
          }}>
            <span style={{
              fontSize: STYLES.fontSize.sm,
              fontWeight: STYLES.fontWeight.medium,
              color: TOKENS.text
            }}>Equipment:</span>
            <span style={{
              fontSize: STYLES.fontSize.sm,
              color: TOKENS.text,
              fontWeight: STYLES.fontWeight.semibold
            }}>{summary.equipmentType}</span>
          </div>
          
          <div style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            padding: `${STYLES.spacing.xs} 0`,
          }}>
            <span style={{
              fontSize: STYLES.fontSize.sm,
              fontWeight: STYLES.fontWeight.medium,
              color: TOKENS.text
            }}>Operating Modes:</span>
            <span style={{
              fontSize: STYLES.fontSize.sm,
              color: TOKENS.text,
              textAlign: 'right',
              maxWidth: '200px',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap'
            }}>{summary.operatingModes.join(', ')}</span>
          </div>
          
          <div style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            padding: `${STYLES.spacing.xs} 0`,
          }}>
            <span style={{
              fontSize: STYLES.fontSize.sm,
              fontWeight: STYLES.fontWeight.medium,
              color: TOKENS.text
            }}>I/O Points:</span>
            <span style={{
              ...COMPONENTS.badge.base,
              ...COMPONENTS.badge.info,
              fontSize: STYLES.fontSize.xs
            }}>{summary.ioPoints.length} points</span>
          </div>
          
          <div style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            padding: `${STYLES.spacing.xs} 0`,
          }}>
            <span style={{
              fontSize: STYLES.fontSize.sm,
              fontWeight: STYLES.fontWeight.medium,
              color: TOKENS.text
            }}>Control Blocks:</span>
            <span style={{
              ...COMPONENTS.badge.base,
              ...COMPONENTS.badge.info,
              fontSize: STYLES.fontSize.xs
            }}>{summary.controlBlocks.length} blocks</span>
          </div>
          
          <div style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            padding: `${STYLES.spacing.xs} 0`,
          }}>
            <span style={{
              fontSize: STYLES.fontSize.sm,
              fontWeight: STYLES.fontWeight.medium,
              color: TOKENS.text
            }}>Schedules:</span>
            <span style={{
              ...COMPONENTS.badge.base,
              ...COMPONENTS.badge.default,
              fontSize: STYLES.fontSize.xs
            }}>{summary.schedules.length} schedules</span>
          </div>
          
          <div style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            padding: `${STYLES.spacing.xs} 0`,
          }}>
            <span style={{
              fontSize: STYLES.fontSize.sm,
              fontWeight: STYLES.fontWeight.medium,
              color: TOKENS.text
            }}>Alarms:</span>
            <span style={{
              ...COMPONENTS.badge.base,
              ...COMPONENTS.badge.warning,
              fontSize: STYLES.fontSize.xs
            }}>{summary.alarms.length} alarms</span>
          </div>
        </div>

        {/* Pseudocode Preview */}
        {summary.pseudoCode && (
          <div style={{
            background: TOKENS.chip,
            border: STYLES.border.light,
            borderRadius: STYLES.radius.medium,
            padding: STYLES.spacing.md,
            marginBottom: STYLES.spacing.lg,
          }}>
            <div style={{
              fontSize: STYLES.fontSize.xs,
              fontWeight: STYLES.fontWeight.semibold,
              color: TOKENS.muted,
              textTransform: 'uppercase',
              letterSpacing: '0.5px',
              marginBottom: STYLES.spacing.sm,
            }}>Control Logic Preview:</div>
            <div style={{
              fontFamily: 'Monaco, Menlo, monospace',
              fontSize: STYLES.fontSize.xs,
              color: TOKENS.text,
              lineHeight: '1.4',
              whiteSpace: 'pre-wrap',
            }}>
              {summary.pseudoCode.substring(0, 200)}
              {summary.pseudoCode.length > 200 && '...'}
            </div>
          </div>
        )}

        {/* Actions */}
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          gap: STYLES.spacing.md,
        }}>
          <div style={{
            display: 'flex',
            gap: STYLES.spacing.sm,
          }}>
            {onExpand && (
              <button
                onClick={onExpand}
                style={{
                  ...COMPONENTS.button.base,
                  ...COMPONENTS.button.secondary,
                  fontSize: STYLES.fontSize.sm,
                  display: 'flex',
                  alignItems: 'center',
                  gap: STYLES.spacing.xs,
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
                <Eye size={12} />
                View Details
              </button>
            )}

            {onApprove && (
              <button
                onClick={onApprove}
                style={{
                  ...COMPONENTS.button.base,
                  background: TOKENS.success,
                  borderColor: TOKENS.success,
                  color: TOKENS.white,
                  fontSize: STYLES.fontSize.sm,
                  display: 'flex',
                  alignItems: 'center',
                  gap: STYLES.spacing.xs,
                  fontWeight: STYLES.fontWeight.bold,
                  textTransform: 'uppercase',
                  letterSpacing: '0.5px',
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.transform = 'translateY(-2px)';
                  e.currentTarget.style.boxShadow = `4px 4px 0 ${TOKENS.black}`;
                  e.currentTarget.style.background = TOKENS.approved;
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.transform = 'translateY(0)';
                  e.currentTarget.style.boxShadow = `2px 2px 0 ${TOKENS.black}`;
                  e.currentTarget.style.background = TOKENS.success;
                }}
              >
                <Play size={12} />
                Approve & Generate BOG
              </button>
            )}
          </div>

          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: STYLES.spacing.xs,
            fontSize: STYLES.fontSize.xs,
            fontWeight: STYLES.fontWeight.semibold,
            color: TOKENS.success,
            textTransform: 'uppercase',
            letterSpacing: '0.5px',
          }}>
            <CheckCircle size={12} />
            Analysis Ready
          </div>
        </div>
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
          right: -5
        }} 
      />
    </div>
  );
};

export default AnalysisSummaryCard;