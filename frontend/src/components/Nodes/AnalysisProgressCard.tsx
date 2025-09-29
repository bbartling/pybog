/**
 * Analysis Progress Card Component
 * Shows progress through analysis stages following PyBOG neubrutalism design system
 */

import React from 'react';
import { Handle, Position, NodeProps } from 'reactflow';
import { Search, Settings, Brain, Loader2 } from 'lucide-react';
import { TOKENS, STYLES, COMPONENTS } from '../../theme/neubrutalism';

interface AnalysisProgressCardData {
  stage: 'parse' | 'normalize' | 'synthesize';
  progress: number; // 0-1
  timestamp: Date;
  message?: string;
}

const AnalysisProgressCard: React.FC<NodeProps<AnalysisProgressCardData>> = ({ data, id }) => {
  const { stage, progress, timestamp, message } = data;

  const getStageInfo = (currentStage: string) => {
    const stages = {
      parse: { 
        label: 'Parsing', 
        icon: <Search size={16} />, 
        description: 'Extracting HVAC components',
        color: TOKENS.info
      },
      normalize: { 
        label: 'Normalizing', 
        icon: <Settings size={16} />, 
        description: 'Standardizing data format',
        color: TOKENS.warning
      },
      synthesize: { 
        label: 'Synthesizing', 
        icon: <Brain size={16} />, 
        description: 'Generating control logic',
        color: TOKENS.success
      }
    };
    return stages[currentStage as keyof typeof stages] || stages.parse;
  };

  const stageInfo = getStageInfo(stage);
  const progressPercent = Math.round(progress * 100);

  return (
    <div style={{
      ...COMPONENTS.message.base,
      minWidth: '320px',
      maxWidth: '400px',
      fontFamily: TOKENS.fontFamily,
      border: `2px solid ${stageInfo.color}`,
      position: 'relative',
      overflow: 'hidden'
    }}>
      {/* Animated shimmer overlay */}
      <div style={{
        position: 'absolute',
        top: 0,
        left: '-100%',
        width: '100%',
        height: '100%',
        background: `linear-gradient(90deg, transparent, ${stageInfo.color}20, transparent)`,
        animation: 'shimmer 2s infinite',
        pointerEvents: 'none'
      }} />
      
      {/* Input Port */}
      <Handle 
        type="target" 
        position={Position.Left}
        style={{ 
          background: stageInfo.color,
          width: 10,
          height: 10,
          border: `2px solid ${TOKENS.black}`,
          left: -5
        }} 
      />
      
      {/* Header */}
      <div style={{
        ...COMPONENTS.message.header,
        background: TOKENS.running,
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
            color: stageInfo.color,
            animation: 'pulse 2s infinite'
          }}>
            {stageInfo.icon}
          </div>
          <span>Analysis in Progress</span>
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
        position: 'relative',
        zIndex: 1,
      }}>
        {/* Current Stage Info */}
        <div style={{
          textAlign: 'center',
          marginBottom: STYLES.spacing.xl,
        }}>
          <div style={{
            fontSize: STYLES.fontSize.lg,
            fontWeight: STYLES.fontWeight.bold,
            color: stageInfo.color,
            marginBottom: STYLES.spacing.xs,
          }}>
            {stageInfo.label}
          </div>
          <div style={{
            fontSize: STYLES.fontSize.sm,
            color: TOKENS.muted,
            fontWeight: STYLES.fontWeight.medium
          }}>
            {stageInfo.description}
          </div>
        </div>

        {/* Progress Bar */}
        <div style={{
          marginBottom: STYLES.spacing.xl,
        }}>
          <div style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            marginBottom: STYLES.spacing.sm,
          }}>
            <span style={{
              fontSize: STYLES.fontSize.sm,
              fontWeight: STYLES.fontWeight.semibold,
              color: TOKENS.text
            }}>Progress</span>
            <span style={{
              fontSize: STYLES.fontSize.sm,
              fontWeight: STYLES.fontWeight.bold,
              color: stageInfo.color
            }}>{progressPercent}%</span>
          </div>
          
          <div style={{
            width: '100%',
            height: '8px',
            background: TOKENS.chip,
            borderRadius: STYLES.radius.small,
            overflow: 'hidden',
            border: STYLES.border.light,
            position: 'relative'
          }}>
            <div style={{
              height: '100%',
              background: `linear-gradient(90deg, ${stageInfo.color}, ${stageInfo.color}dd)`,
              borderRadius: STYLES.radius.small,
              transition: STYLES.transition.base,
              width: `${progressPercent}%`,
              position: 'relative'
            }}>
              {/* Animated progress shimmer */}
              <div style={{
                position: 'absolute',
                top: 0,
                left: 0,
                right: 0,
                bottom: 0,
                background: 'linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.3), transparent)',
                animation: 'progress-shimmer 1.5s infinite',
              }} />
            </div>
          </div>
        </div>

        {/* Status Message */}
        {message && (
          <div style={{
            background: TOKENS.processBody,
            border: STYLES.border.light,
            borderRadius: STYLES.radius.medium,
            padding: STYLES.spacing.md,
            marginBottom: STYLES.spacing.lg,
            fontSize: STYLES.fontSize.sm,
            color: TOKENS.text,
            textAlign: 'center',
            fontWeight: STYLES.fontWeight.medium
          }}>
            {message}
          </div>
        )}

        {/* Stage Indicators */}
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          gap: STYLES.spacing.sm,
        }}>
          {['parse', 'normalize', 'synthesize'].map((stageName, index) => {
            const isActive = stage === stageName;
            const isComplete = progress > (index + 1) / 3;
            const isPending = !isActive && !isComplete;
            
            return (
              <div key={stageName} style={{
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                gap: STYLES.spacing.xs,
                flex: 1,
              }}>
                <div style={{
                  width: '12px',
                  height: '12px',
                  borderRadius: '50%',
                  border: `2px solid ${isPending ? TOKENS.grid : isActive ? stageInfo.color : TOKENS.success}`,
                  background: isPending ? TOKENS.white : isActive ? stageInfo.color : TOKENS.success,
                  transition: STYLES.transition.base,
                  ...(isActive ? {
                    animation: 'pulse-dot 1.5s infinite',
                    boxShadow: `0 0 0 4px ${stageInfo.color}33`
                  } : {})
                }} />
                <span style={{
                  fontSize: STYLES.fontSize.xs,
                  fontWeight: STYLES.fontWeight.semibold,
                  textTransform: 'uppercase',
                  letterSpacing: '0.5px',
                  color: isPending ? TOKENS.muted : isActive ? stageInfo.color : TOKENS.success,
                  transition: STYLES.transition.base
                }}>
                  {stageName}
                </span>
              </div>
            );
          })}
        </div>
      </div>

      {/* Output Port */}
      <Handle 
        type="source" 
        position={Position.Right}
        style={{ 
          background: stageInfo.color,
          width: 10,
          height: 10,
          border: `2px solid ${TOKENS.black}`,
          right: -5
        }} 
      />


    </div>
  );
};

export default AnalysisProgressCard;