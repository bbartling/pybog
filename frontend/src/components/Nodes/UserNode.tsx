import React from 'react';
import type { NodeProps } from 'reactflow';
import { Handle, Position } from 'reactflow';
import { NodeChrome } from '../flow/Chrome';

interface UserData {
  content?: string;
  timestamp?: Date | string;
  files?: File[];
}

const UserNode: React.FC<NodeProps<UserData>> = ({ data }) => {
  const time = data?.timestamp ? new Date(data.timestamp) : null;
  return (
    <div className={data ? (data as any).processing ? 'rf-node-pulse' : '' : ''}>
      <NodeChrome title="User" tone="user">
        <div style={{ whiteSpace: 'pre-wrap' }}>{data?.content || ''}</div>
        {data?.files && data.files.length > 0 && (
          <div style={{ marginTop: 8, fontSize: 12, color: '#6b7280' }}>
            {data.files.length} file{data.files.length > 1 ? 's' : ''} attached
          </div>
        )}
        {time && (
          <div style={{ marginTop: 8, fontSize: 12, color: '#6b7280' }}>
            {time.toLocaleString()}
          </div>
        )}
      </NodeChrome>
      <Handle type="target" position={Position.Left} style={{ background: '#7e5bef', width: 10, height: 10, border: '2px solid white' }} />
      <Handle type="source" position={Position.Right} style={{ background: '#7e5bef', width: 10, height: 10, border: '2px solid white' }} />
    </div>
  );
};

export default UserNode;

