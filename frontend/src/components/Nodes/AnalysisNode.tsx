import React from 'react';
import type { NodeProps } from 'reactflow';
import { Handle, Position } from 'reactflow';

interface AnalysisData {
  content?: string;
  timestamp?: Date | string;
  analysis?: any;
  approving?: boolean;
  onApprove?: () => void;
  onRequestChanges?: (feedback: string) => void;
}

const AnalysisNode: React.FC<NodeProps<AnalysisData>> = ({ data }) => {
  const time = data?.timestamp ? new Date(data.timestamp) : null;
  const summary = data?.analysis ? (
    <pre style={{
      background: '#f0fdf4',
      padding: 8,
      borderRadius: 8,
      border: '1px solid #bbf7d0',
      maxHeight: 200,
      overflow: 'auto',
      fontSize: 12
    }}>{JSON.stringify(
      {
        components: data.analysis.component_count ?? undefined,
        inputs: data.analysis.io_summary?.total_inputs ?? undefined,
        outputs: data.analysis.io_summary?.total_outputs ?? undefined,
      },
      null,
      2
    )}</pre>
  ) : null;

  const handleRequestChanges = () => {
    data?.onRequestChanges?.('Please refine the analysis.');
  };

  return (
    <div className={(data as any)?.approving || (data as any)?.processing ? 'rf-node-pulse' : ''} style={{
      background: '#f8fffb',
      padding: '0 0 10px 0',
      borderRadius: '10px',
      border: '2px solid #3ccf8e',
      color: '#064e3b',
      fontFamily: 'system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif',
      position: 'relative'
    }}>
      <div style={{
        background: '#d1fae5',
        color: '#065f46',
        fontWeight: 800,
        padding: '6px 10px',
        borderTopLeftRadius: 8,
        borderTopRightRadius: 8,
        borderBottom: '1px solid #a7f3d0'
      }}>Analysis</div>
      <div style={{ padding: '8px 12px', whiteSpace: 'pre-wrap', marginBottom: 8 }}>{data?.content || 'Analysis results available.'}</div>
      {summary}
      <div style={{ display: 'flex', gap: 8, marginTop: 10 }}>
        <button
          onClick={data?.onApprove}
          disabled={!!data?.approving}
          style={{
            background: '#10b981',
            border: 'none',
            color: 'white',
            padding: '6px 10px',
            borderRadius: 6,
            cursor: data?.approving ? 'not-allowed' : 'pointer',
            fontWeight: 600,
          }}
        >
          {data?.approving ? 'Approving…' : 'Approve'}
        </button>
        <button
          onClick={handleRequestChanges}
          disabled={!!data?.approving}
          style={{
            background: '#fde68a',
            border: '1px solid #f59e0b',
            color: '#92400e',
            padding: '6px 10px',
            borderRadius: 6,
            cursor: data?.approving ? 'not-allowed' : 'pointer',
            fontWeight: 600,
          }}
        >
          Request changes
        </button>
      </div>
      {time && (
        <div style={{ marginTop: 8, fontSize: 12, color: '#6b7280' }}>
          {time.toLocaleString()}
        </div>
      )}
      <Handle type="target" position={Position.Left} style={{ background: '#10b981', width: 10, height: 10, border: '2px solid white' }} />
      <Handle type="source" position={Position.Right} style={{ background: '#10b981', width: 10, height: 10, border: '2px solid white' }} />
    </div>
  );
};

export default AnalysisNode;

