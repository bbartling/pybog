/**
 * Analysis Review Node Component
 * Shows analysis results with approval actions - matches the n8n workflow pattern
 */

import React from 'react';
import { Handle, Position, NodeProps } from 'reactflow';
import { CheckCircle, XCircle, Eye, AlertTriangle, Clock, BarChart3 } from 'lucide-react';
import { TOKENS, STYLES, COMPONENTS } from '../../theme/neubrutalism';

interface AnalysisReviewData {
  sessionId: string;
  analysis: {
    io_points: {
      inputs: string[];
      outputs: string[];
    };
    control_blocks: string[];
    pseudocode: Array<{
      block: string;
      logic: string[];
      complexity?: number;
    }>;
    issues: string[];
  };
  summary: {
    totalInputs: number;
    totalOutputs: number;
    totalBlocks: number;
    complexity: 'Low' | 'Medium' | 'High';
  };
  analysisQuality: 'poor' | 'fair' | 'good' | 'excellent';
  timestamp: Date;
  onApprove: () => void;
  onRequestChanges: () => void;
  onViewDetails: () => void;
}

const AnalysisReviewNode: React.FC<NodeProps<AnalysisReviewData>> = ({ data, id }) => {
  const { sessionId, analysis, summary, analysisQuality, timestamp, onApprove, onRequestChanges, onViewDetails } = data;

  const getQualityColor = () => {
    switch (analysisQuality) {
      case 'excellent': return TOKENS.success;
      case 'good': return TOKENS.approved;
      case 'fair': return TOKENS.warning;
      case 'poor': return TOKENS.error;
      default: return TOKENS.muted;
    }
  };

  const getQualityIcon = () => {
    switch (analysisQuality) {
      case 'excellent': return <CheckCircle size={16} />;
      case 'good': return <CheckCircle size={16} />;
      case 'fair': return <AlertTriangle size={16} />;
      case 'poor': return <XCircle size={16} />;
      default: return <Clock size={16} />;
    }
  };

  const getComplexityColor = () => {
    switch (summary.complexity) {
      case 'High': return TOKENS.error;
      case 'Medium': return TOKENS.warning;
      case 'Low': return TOKENS.success;
      default: return TOKENS.muted;
    }
  };

  return (
    <div style={{
      ...COMPONENTS.message.base,
      minWidth: '420px',
      maxWidth: '480px',
      fontFamily: TOKENS.fontFamily,
      background: `linear-gradient(135deg, ${TOKENS.white} 0%, #f8fafc 100%)`,
      border: `4px solid ${getQualityColor()}`,
      boxShadow: `8px 8px 0 ${TOKENS.text}`,
    }}>
      {/* Input Port */}
      <Handle
        type="target"
        position={Position.Left}
        style={{
          background: TOKENS.primary,
          width: 12,
          height: 12,
          border: `2px solid ${TOKENS.text}`,
          left: -6
        }}
      />

      {/* Header - Analysis Review */}
      <div style={{
        background: `linear-gradient(135deg, ${getQualityColor()} 0%, ${getQualityColor()}dd 100%)`,
        padding: `${STYLES.spacing.lg} ${STYLES.spacing.xl}`,
        borderBottom: `4px solid ${TOKENS.text}`,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
      }}>
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: STYLES.spacing.md,
        }}>
          <div style={{
            width: '32px',
            height: '32px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            background: TOKENS.white,
            borderRadius: '8px',
            border: `3px solid ${TOKENS.text}`,
            color: getQualityColor()
          }}>
            <BarChart3 size={18} />
          </div>
          <div>
            <div style={{
              fontWeight: 800,
              color: TOKENS.white,
              fontSize: '16px',
              textTransform: 'uppercase',
              letterSpacing: '0.5px',
              textShadow: `2px 2px 0 ${TOKENS.text}`,
            }}>
              ANALYSIS COMPLETE
            </div>
            <div style={{
              fontSize: STYLES.fontSize.xs,
              color: 'rgba(255,255,255,0.9)',
              fontWeight: STYLES.fontWeight.normal,
              marginTop: '2px',
            }}>
              Review & Approve for BOG Generation
            </div>
          </div>
        </div>

        {/* Quality Badge */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: STYLES.spacing.xs,
          background: TOKENS.white,
          padding: '8px 12px',
          borderRadius: '6px',
          border: `2px solid ${TOKENS.text}`,
          boxShadow: `2px 2px 0 ${TOKENS.text}`,
        }}>
          <span style={{ color: getQualityColor() }}>
            {getQualityIcon()}
          </span>
          <span style={{
            fontSize: STYLES.fontSize.xs,
            fontWeight: STYLES.fontWeight.bold,
            color: TOKENS.text,
            textTransform: 'uppercase',
          }}>
            {analysisQuality}
          </span>
        </div>
      </div>

      {/* Progress Bar */}
      <div style={{
        background: TOKENS.chip,
        padding: `${STYLES.spacing.md} ${STYLES.spacing.xl}`,
        borderBottom: `2px solid ${TOKENS.text}`,
      }}>
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: STYLES.spacing.sm,
        }}>
          <span style={{
            fontSize: STYLES.fontSize.xs,
            fontWeight: STYLES.fontWeight.bold,
            color: TOKENS.text,
            textTransform: 'uppercase',
            letterSpacing: '0.5px',
          }}>
            Step 4 of 5 - Awaiting Approval
          </span>
          <span style={{
            fontSize: STYLES.fontSize.xs,
            fontWeight: STYLES.fontWeight.bold,
            color: TOKENS.primary,
          }}>
            80%
          </span>
        </div>
        <div style={{
          width: '100%',
          height: '8px',
          background: TOKENS.white,
          border: `2px solid ${TOKENS.text}`,
          borderRadius: '4px',
          overflow: 'hidden',
        }}>
          <div style={{
            width: '80%',
            height: '100%',
            background: `linear-gradient(90deg, ${TOKENS.primary} 0%, ${TOKENS.success} 100%)`,
            transition: 'width 0.3s ease',
          }} />
        </div>
      </div>

      {/* Analysis Summary Grid */}
      <div style={{
        padding: STYLES.spacing.xl,
      }}>
        <div style={{
          display: 'grid',
          gridTemplateColumns: '1fr 1fr',
          gap: STYLES.spacing.md,
          marginBottom: STYLES.spacing.lg,
        }}>
          {/* I/O Points */}
          <div style={{
            background: `linear-gradient(135deg, ${TOKENS.primary}15 0%, ${TOKENS.primary}05 100%)`,
            border: `3px solid ${TOKENS.text}`,
            borderLeft: `6px solid ${TOKENS.primary}`,
            borderRadius: '8px',
            padding: STYLES.spacing.md,
            textAlign: 'center',
          }}>
            <div style={{
              fontSize: '24px',
              fontWeight: 900,
              color: TOKENS.primary,
              lineHeight: 1,
            }}>
              {summary.totalInputs + summary.totalOutputs}
            </div>
            <div style={{
              fontSize: STYLES.fontSize.xs,
              color: TOKENS.text,
              fontWeight: STYLES.fontWeight.bold,
              textTransform: 'uppercase',
              marginTop: '4px',
            }}>
              I/O Points
            </div>
          </div>

          {/* Control Blocks */}
          <div style={{
            background: `linear-gradient(135deg, ${TOKENS.success}15 0%, ${TOKENS.success}05 100%)`,
            border: `3px solid ${TOKENS.text}`,
            borderLeft: `6px solid ${TOKENS.success}`,
            borderRadius: '8px',
            padding: STYLES.spacing.md,
            textAlign: 'center',
          }}>
            <div style={{
              fontSize: '24px',
              fontWeight: 900,
              color: TOKENS.success,
              lineHeight: 1,
            }}>
              {summary.totalBlocks}
            </div>
            <div style={{
              fontSize: STYLES.fontSize.xs,
              color: TOKENS.text,
              fontWeight: STYLES.fontWeight.bold,
              textTransform: 'uppercase',
              marginTop: '4px',
            }}>
              Control Blocks
            </div>
          </div>
        </div>

        {/* Complexity Indicator */}
        <div style={{
          background: `linear-gradient(135deg, ${getComplexityColor()}15 0%, ${getComplexityColor()}05 100%)`,
          border: `3px solid ${TOKENS.text}`,
          borderLeft: `6px solid ${getComplexityColor()}`,
          borderRadius: '8px',
          padding: STYLES.spacing.md,
          marginBottom: STYLES.spacing.lg,
          display: 'flex',
          alignItems: 'center',
          gap: STYLES.spacing.md,
        }}>
          <div style={{
            background: getComplexityColor(),
            color: TOKENS.white,
            border: `2px solid ${TOKENS.text}`,
            borderRadius: '50%',
            width: '32px',
            height: '32px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: '14px',
            fontWeight: 800,
          }}>
            {summary.complexity[0]}
          </div>
          <div>
            <div style={{
              fontSize: STYLES.fontSize.sm,
              fontWeight: STYLES.fontWeight.bold,
              color: TOKENS.text,
            }}>
              {summary.complexity} Complexity
            </div>
            <div style={{
              fontSize: STYLES.fontSize.xs,
              color: TOKENS.muted,
            }}>
              {summary.totalInputs} inputs, {summary.totalOutputs} outputs detected
            </div>
          </div>
        </div>

        {/* Issues Warning (if any) */}
        {analysis.issues && analysis.issues.length > 0 && (
          <div style={{
            background: `linear-gradient(135deg, ${TOKENS.warning}15 0%, ${TOKENS.warning}05 100%)`,
            border: `3px solid ${TOKENS.text}`,
            borderLeft: `6px solid ${TOKENS.warning}`,
            borderRadius: '8px',
            padding: STYLES.spacing.md,
            marginBottom: STYLES.spacing.lg,
          }}>
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: STYLES.spacing.xs,
              marginBottom: STYLES.spacing.xs,
            }}>
              <AlertTriangle size={16} color={TOKENS.warning} />
              <span style={{
                fontSize: STYLES.fontSize.sm,
                fontWeight: STYLES.fontWeight.bold,
                color: TOKENS.text,
              }}>
                {analysis.issues.length} Issue{analysis.issues.length > 1 ? 's' : ''} Noted
              </span>
            </div>
            <div style={{
              fontSize: STYLES.fontSize.xs,
              color: TOKENS.muted,
            }}>
              Review recommended before approval
            </div>
          </div>
        )}

        {/* Action Buttons */}
        <div style={{
          display: 'flex',
          gap: STYLES.spacing.md,
          marginTop: STYLES.spacing.lg,
        }}>
          <button
            onClick={onViewDetails}
            style={{
              ...COMPONENTS.button.base,
              ...COMPONENTS.button.secondary,
              fontSize: STYLES.fontSize.sm,
              display: 'flex',
              alignItems: 'center',
              gap: STYLES.spacing.xs,
              flex: 1,
              justifyContent: 'center',
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
            <Eye size={14} />
            View Details
          </button>

          <button
            onClick={onRequestChanges}
            style={{
              ...COMPONENTS.button.base,
              background: TOKENS.warning,
              borderColor: TOKENS.warning,
              color: TOKENS.white,
              fontSize: STYLES.fontSize.sm,
              display: 'flex',
              alignItems: 'center',
              gap: STYLES.spacing.xs,
              flex: 1,
              justifyContent: 'center',
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.transform = 'translateY(-1px)';
              e.currentTarget.style.boxShadow = `4px 4px 0 ${TOKENS.text}`;
              e.currentTarget.style.background = TOKENS.error;
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.transform = 'translateY(0)';
              e.currentTarget.style.boxShadow = `2px 2px 0 ${TOKENS.text}`;
              e.currentTarget.style.background = TOKENS.warning;
            }}
          >
            <XCircle size={14} />
            Request Changes
          </button>
        </div>

        {/* Primary Approval Button */}
        <button
          onClick={onApprove}
          style={{
            ...COMPONENTS.button.base,
            background: `linear-gradient(135deg, ${TOKENS.success} 0%, ${TOKENS.approved} 100%)`,
            borderColor: TOKENS.success,
            color: TOKENS.white,
            fontSize: STYLES.fontSize.base,
            display: 'flex',
            alignItems: 'center',
            gap: STYLES.spacing.sm,
            fontWeight: STYLES.fontWeight.bold,
            textTransform: 'uppercase',
            letterSpacing: '0.5px',
            width: '100%',
            justifyContent: 'center',
            marginTop: STYLES.spacing.md,
            padding: '16px 24px',
            boxShadow: `4px 4px 0 ${TOKENS.text}`,
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.transform = 'translateY(-3px)';
            e.currentTarget.style.boxShadow = `6px 6px 0 ${TOKENS.text}`;
            e.currentTarget.style.background = `linear-gradient(135deg, ${TOKENS.approved} 0%, ${TOKENS.success} 100%)`;
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.transform = 'translateY(0)';
            e.currentTarget.style.boxShadow = `4px 4px 0 ${TOKENS.text}`;
            e.currentTarget.style.background = `linear-gradient(135deg, ${TOKENS.success} 0%, ${TOKENS.approved} 100%)`;
          }}
        >
          <CheckCircle size={18} />
          Approve & Generate BOG File
        </button>
      </div>

      {/* Output Port - Only show when approved */}
      <Handle
        type="source"
        position={Position.Right}
        style={{
          background: TOKENS.success,
          width: 12,
          height: 12,
          border: `2px solid ${TOKENS.text}`,
          right: -6
        }}
      />

      {/* Timestamp */}
      <div style={{
        position: 'absolute',
        bottom: '8px',
        right: '12px',
        fontSize: STYLES.fontSize.xs,
        color: TOKENS.muted,
        fontWeight: STYLES.fontWeight.normal,
      }}>
        {timestamp.toLocaleTimeString()}
      </div>
    </div>
  );
};

export default AnalysisReviewNode;