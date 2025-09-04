import React from 'react';
import type { NodeProps } from 'reactflow';
import { Handle, Position } from 'reactflow';
import { NodeChrome } from '../flow/Chrome';

interface StatusData {
  content?: string;
  timestamp?: Date | string;
}

const StatusNode: React.FC<NodeProps<StatusData>> = ({ data }) => {
  const time = data?.timestamp ? new Date(data.timestamp) : null;
  return (
    <div className={(data as any)?.processing ? 'rf-node-pulse' : ''}>
      <NodeChrome title="System" tone="system">
        <div style={{ whiteSpace: 'pre-wrap' }}>{data?.content || ''}</div>
        {time && (
          <div style={{ marginTop: 8, fontSize: 12, color: '#6b7280' }}>
            {time.toLocaleString()}
          </div>
        )}
      </NodeChrome>
      <Handle type="target" position={Position.Left} style={{ background: '#4a9eff', width: 10, height: 10, border: '2px solid white' }} />
      <Handle type="source" position={Position.Right} style={{ background: '#4a9eff', width: 10, height: 10, border: '2px solid white' }} />
    </div>
  );
};

export default StatusNode;

