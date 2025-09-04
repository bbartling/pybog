import React from 'react';
import type { NodeProps } from 'reactflow';
import { Handle, Position } from 'reactflow';

interface UserData {
  content?: string;
  timestamp?: Date | string;
  files?: File[];
}

const UserNode: React.FC<NodeProps<UserData>> = ({ data }) => {
  const time = data?.timestamp ? new Date(data.timestamp) : null;
  return (
    <div className={data ? (data as any).processing ? 'rf-node-pulse' : '' : ''} style={{
      background: '#ffffff',
      padding: '0 0 10px 0',
      borderRadius: '10px',
      border: '2px solid #7e5bef',
      color: '#111827',
      fontFamily: 'system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif',
      position: 'relative'
    }}>
      <div style={{
        background: '#ede9fe',
        color: '#5b21b6',
        fontWeight: 700,
        padding: '6px 10px',
        borderTopLeftRadius: 8,
        borderTopRightRadius: 8,
        borderBottom: '1px solid #e9d5ff'
      }}>User</div>
      <div style={{ padding: '8px 12px', whiteSpace: 'pre-wrap' }}>{data?.content || ''}</div>
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
      <Handle type="target" position={Position.Left} style={{ background: '#7e5bef', width: 10, height: 10, border: '2px solid white' }} />
      <Handle type="source" position={Position.Right} style={{ background: '#7e5bef', width: 10, height: 10, border: '2px solid white' }} />
    </div>
  );
};

export default UserNode;

