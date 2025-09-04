import React from 'react';
import type { NodeProps } from 'reactflow';
import { Handle, Position } from 'reactflow';

interface StatusData {
  content?: string;
  timestamp?: Date | string;
}

const StatusNode: React.FC<NodeProps<StatusData>> = ({ data }) => {
  const time = data?.timestamp ? new Date(data.timestamp) : null;
  return (
    <div className={(data as any)?.processing ? 'rf-node-pulse' : ''} style={{
      background: '#f8fbff',
      padding: '0 0 10px 0',
      borderRadius: '10px',
      border: '2px solid #4a9eff',
      color: '#0f172a',
      fontFamily: 'system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif',
      position: 'relative'
    }}>
      <div style={{
        background: '#dbeafe',
        color: '#1d4ed8',
        fontWeight: 700,
        padding: '6px 10px',
        borderTopLeftRadius: 8,
        borderTopRightRadius: 8,
        borderBottom: '1px solid #bfdbfe'
      }}>System</div>
      <div style={{ padding: '8px 12px', whiteSpace: 'pre-wrap' }}>{data?.content || ''}</div>
      {time && (
        <div style={{ marginTop: 8, fontSize: 12, color: '#6b7280' }}>
          {time.toLocaleString()}
        </div>
      )}
      <Handle type="target" position={Position.Left} style={{ background: '#4a9eff', width: 10, height: 10, border: '2px solid white' }} />
      <Handle type="source" position={Position.Right} style={{ background: '#4a9eff', width: 10, height: 10, border: '2px solid white' }} />
    </div>
  );
};

export default StatusNode;

