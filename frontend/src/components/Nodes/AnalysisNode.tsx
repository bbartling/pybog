import React from 'react';
import { NodeProps } from 'reactflow';

// Using unified AnalysisData type

import { NodeAnalysisData as AnalysisNodeData } from '../../types/analysis';

const chip: React.CSSProperties = {
  display: 'inline-flex',
  alignItems: 'center',
  padding: '3px 10px',
  borderRadius: 6,
  background: '#f3f4f6',
  border: '1px solid #e5e7eb',
  color: '#374151',
  fontSize: 11,
  fontWeight: 600,
};

// Wrapper component that handles both ReactFlow node props and direct props
const AnalysisNode: React.FC<NodeProps<AnalysisNodeData> | AnalysisNodeData | any> = (props) => {
  // Determine if this is being used as a ReactFlow node or a standalone component
  const isNodeProps = 'data' in props && props.type === 'analysis';
  const {
    sessionId,
    analysis,
    onApprove,
    onRequestChanges,
    approving,
    className,
  } = isNodeProps ? props.data : props.data || props;
  return (
    <div
      className={className}
      style={{
        background: 'linear-gradient(135deg, #f0fdf4 0%, #dcfce7 100%)',
        border: '2px solid #10b981',
        borderRadius: 10,
        boxShadow: '0 4px 12px rgba(16, 185, 129, 0.2)',
        padding: 16,
        position: 'relative',
        minHeight: 200,
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 12 }}>
        <div style={{ 
          fontSize: 11, 
          color: '#10b981', 
          fontWeight: 700,
          textTransform: 'uppercase',
          letterSpacing: '0.5px'
        }}>
          ⚡ Analysis Complete
        </div>
        <div style={{ fontSize: 10, color: '#6b7280' }}>ID: {sessionId.slice(-8)}</div>
      </div>

      <div style={{ marginBottom: 14 }}>
        <div style={{ fontWeight: 700, color: '#047857', marginBottom: 8, fontSize: 15 }}>
          {analysis.component_name || 'HVAC Control Logic'}
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
          <div>
            <div style={{ fontSize: 11, color: '#6b7280', marginBottom: 6, fontWeight: 600 }}>📥 INPUTS</div>
            <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
              {(analysis.inputs || []).map((i: any, idx: number) => (
                <span key={idx} style={{ 
                  ...chip, 
                  background: '#dbeafe',
                  borderColor: '#93c5fd',
                  color: '#1e40af' 
                }}>
                  {typeof i === 'string' ? i : i.name}
                </span>
              ))}
            </div>
          </div>
          <div>
            <div style={{ fontSize: 11, color: '#6b7280', marginBottom: 6, fontWeight: 600 }}>📤 OUTPUTS</div>
            <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
              {(analysis.outputs || []).map((o: any, idx: number) => (
                <span key={idx} style={{ 
                  ...chip,
                  background: '#fef3c7',
                  borderColor: '#fde68a',
                  color: '#92400e'
                }}>
                  {typeof o === 'string' ? o : o.name}
                </span>
              ))}
            </div>
          </div>
        </div>
      </div>

      <div style={{ fontSize: 11, color: '#6b7280', marginBottom: 6, fontWeight: 600 }}>📋 CONTROL LOGIC</div>
      <div
        style={{
          background: 'white',
          border: '1px solid #d1d5db',
          borderRadius: 6,
          padding: 10,
          fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace',
          fontSize: 11,
          color: '#1f2937',
          maxHeight: 120,
          overflow: 'auto',
        }}
      >
        {(analysis.pseudocode || []).slice(0, 3).map((b: any, i: number) => (
          <div key={i} style={{ marginBottom: 6 }}>
            <div style={{ color: '#059669', fontWeight: 600, marginBottom: 2 }}>
              {(b.block || b.name || `Block ${i + 1}`)}
            </div>
            <div style={{ paddingLeft: 12 }}>
              {Array.isArray(b.logic) ? (
                b.logic.slice(0, 2).map((line: string, j: number) => (
                  <div key={j} style={{ color: '#4b5563' }}>{line}</div>
                ))
              ) : (
                <div style={{ color: '#4b5563' }}>{String(b).slice(0, 50)}...</div>
              )}
            </div>
          </div>
        ))}
      </div>

      <div style={{ display: 'flex', gap: 8, marginTop: 14 }}>
        <button
          onClick={() => onApprove?.()}
          disabled={approving}
          style={{
            flex: 1,
            background: '#10b981',
            color: 'white',
            border: 'none',
            borderRadius: 6,
            padding: '10px 12px',
            fontWeight: 600,
            cursor: approving ? 'wait' : 'pointer',
            fontSize: 13,
            opacity: approving ? 0.6 : 1,
            transition: 'all 0.2s',
          }}
        >
          {approving ? '⏳ Generating...' : '✅ Approve & Generate'}
        </button>
        <button
          onClick={() => {
            const fb = prompt('Describe what changes are needed:') || '';
            if (fb) onRequestChanges?.(fb);
          }}
          style={{
            background: 'white',
            color: '#374151',
            border: '2px solid #d1d5db',
            borderRadius: 6,
            padding: '10px 12px',
            fontWeight: 600,
            cursor: 'pointer',
            fontSize: 13,
            transition: 'all 0.2s',
          }}
        >
          ✏️ Revise
        </button>
      </div>
      {/* Socket indicators */}
      <div style={{
        position: 'absolute',
        left: -8,
        top: '50%',
        transform: 'translateY(-50%)',
        width: 16,
        height: 16,
        borderRadius: '50%',
        background: 'white',
        border: '3px solid #10b981',
      }} />
      <div style={{
        position: 'absolute',
        right: -8,
        top: '50%',
        transform: 'translateY(-50%)',
        width: 16,
        height: 16,
        borderRadius: '50%',
        background: '#10b981',
        border: '3px solid white',
      }} />
    </div>
  );
};

export default AnalysisNode;

