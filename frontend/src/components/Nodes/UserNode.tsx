import React from 'react';
import { NodeProps } from 'reactflow';

export interface UserNodeData {
  content: string;
  timestamp?: Date;
  files?: File[];
}

const UserNode: React.FC<NodeProps<UserNodeData>> = ({ data }) => {
  const { content, files } = data;
  return (
    <div
      style={{
        background: 'linear-gradient(135deg, #e0e7ff 0%, #c7d2fe 100%)',
        border: '2px solid #6366f1',
        borderRadius: 8,
        boxShadow: '0 2px 8px rgba(99, 102, 241, 0.3)',
        padding: '12px 16px',
        minHeight: 60,
        position: 'relative',
      }}
    >
      <div style={{
        position: 'absolute',
        top: 4,
        right: 8,
        fontSize: 10,
        color: '#6366f1',
        fontWeight: 600,
        textTransform: 'uppercase',
        letterSpacing: '0.5px',
      }}>
        User Input
      </div>
      <div style={{
        color: '#1e293b',
        fontSize: 14,
        marginTop: 8,
        fontWeight: 500,
      }}>
        {content}
      </div>
      {files && files.length > 0 && (
        <div style={{
          marginTop: 8,
          paddingTop: 8,
          borderTop: '1px solid #c7d2fe',
        }}>
          <div style={{ fontSize: 11, color: '#6366f1', marginBottom: 4 }}>Attachments:</div>
          {files.map((file, idx) => (
            <div key={idx} style={{
              display: 'inline-block',
              padding: '2px 6px',
              background: '#6366f1',
              color: 'white',
              borderRadius: 4,
              fontSize: 11,
              marginRight: 4,
            }}>
              📎 {file.name}
            </div>
          ))}
        </div>
      )}
      {/* Socket indicators */}
      <div style={{
        position: 'absolute',
        left: -8,
        top: '50%',
        transform: 'translateY(-50%)',
        width: 16,
        height: 16,
        borderRadius: '50%',
        background: '#6366f1',
        border: '3px solid white',
      }} />
      <div style={{
        position: 'absolute',
        right: -8,
        top: '50%',
        transform: 'translateY(-50%)',
        width: 16,
        height: 16,
        borderRadius: '50%',
        background: 'white',
        border: '3px solid #6366f1',
      }} />
    </div>
  );
};

export default UserNode;

