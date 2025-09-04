import React from 'react';
import type { NodeProps } from 'reactflow';
import { Handle, Position } from 'reactflow';
import { NodeChrome } from '../flow/Chrome';

interface ArtifactData {
  content?: string;
  timestamp?: Date | string;
  downloadUrl?: string;
  fileName?: string;
}

const ArtifactNode: React.FC<NodeProps<ArtifactData>> = ({ data }) => {
  const time = data?.timestamp ? new Date(data.timestamp) : null;
  return (
    <div className={(data as any)?.processing ? 'rf-node-pulse' : ''}>
      <NodeChrome title="Artifact" tone="tool">
        <div style={{ whiteSpace: 'pre-wrap' }}>{data?.content || 'Output artifact is ready.'}</div>
        {data?.downloadUrl && (
          <div style={{ marginTop: 10 }}>
            <a 
            href={data.downloadUrl} 
            target="_blank" 
            rel="noreferrer"
            style={{
              background: '#f59e0b',
              color: 'white',
              padding: '6px 10px',
              borderRadius: 6,
              textDecoration: 'none',
              fontWeight: 600,
            }}
          >
              Download {data.fileName || 'file'}
            </a>
          </div>
        )}
        {time && (
          <div style={{ marginTop: 8, fontSize: 12, color: '#6b7280' }}>
            {time.toLocaleString()}
          </div>
        )}
      </NodeChrome>
      <Handle type="target" position={Position.Left} style={{ background: '#f59e0b', width: 10, height: 10, border: '2px solid white' }} />
      <Handle type="source" position={Position.Right} style={{ background: '#f59e0b', width: 10, height: 10, border: '2px solid white' }} />
    </div>
  );
};

export default ArtifactNode;

