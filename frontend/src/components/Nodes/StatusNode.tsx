import React from 'react';
import { NodeProps } from 'reactflow';

export interface StatusNodeData {
  content: string;
  timestamp?: Date;
}

const StatusNode: React.FC<NodeProps<StatusNodeData>> = ({ data }) => {
  const { content } = data;
  
  // Determine status type from content
  const isError = content.toLowerCase().includes('error') || content.includes('❌');
  const isSuccess = content.toLowerCase().includes('success') || content.includes('✅');
  const isProcessing = content.toLowerCase().includes('processing') || content.toLowerCase().includes('analyzing');
  
  const bgGradient = isError ? 'linear-gradient(135deg, #fee2e2 0%, #fecaca 100%)' :
                     isSuccess ? 'linear-gradient(135deg, #dcfce7 0%, #bbf7d0 100%)' :
                     isProcessing ? 'linear-gradient(135deg, #fef3c7 0%, #fde68a 100%)' :
                     'linear-gradient(135deg, #f3f4f6 0%, #e5e7eb 100%)';
  
  const borderColor = isError ? '#ef4444' :
                      isSuccess ? '#10b981' :
                      isProcessing ? '#f59e0b' :
                      '#6b7280';
                      
  return (
    <div
      style={{
        background: bgGradient,
        border: `2px solid ${borderColor}`,
        borderRadius: 8,
        boxShadow: `0 2px 8px rgba(0, 0, 0, 0.1)`,
        padding: '12px 16px',
        minHeight: 60,
        position: 'relative',
      }}
    >
      <div style={{
        position: 'absolute',
        top: 4,
        left: 8,
        fontSize: 10,
        color: borderColor,
        fontWeight: 600,
        textTransform: 'uppercase',
        letterSpacing: '0.5px',
      }}>
        System
      </div>
      <div style={{
        color: '#1e293b',
        fontSize: 14,
        marginTop: 8,
        fontWeight: 500,
        whiteSpace: 'pre-wrap',
      }}>
        {content}
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
        border: `3px solid ${borderColor}`,
      }} />
      <div style={{
        position: 'absolute',
        right: -8,
        top: '50%',
        transform: 'translateY(-50%)',
        width: 16,
        height: 16,
        borderRadius: '50%',
        background: borderColor,
        border: '3px solid white',
      }} />
    </div>
  );
};

export default StatusNode;

