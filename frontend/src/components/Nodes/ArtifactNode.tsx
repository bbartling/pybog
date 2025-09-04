import React from 'react';
import { NodeProps } from 'reactflow';

export interface ArtifactNodeData {
  fileName: string;
  downloadUrl: string;
}

const ArtifactNode: React.FC<NodeProps<ArtifactNodeData>> = ({ data }) => {
  const { fileName, downloadUrl } = data;
  return (
    <div
      style={{
        background: 'linear-gradient(135deg, #fef3c7 0%, #fde68a 100%)',
        border: '2px solid #f59e0b',
        borderRadius: 8,
        boxShadow: '0 3px 10px rgba(245, 158, 11, 0.25)',
        padding: '14px 16px',
        position: 'relative',
        minHeight: 100,
      }}
    >
      <div style={{
        position: 'absolute',
        top: 4,
        left: 8,
        fontSize: 10,
        color: '#d97706',
        fontWeight: 700,
        textTransform: 'uppercase',
        letterSpacing: '0.5px',
      }}>
        🎆 Generated Output
      </div>
      
      <div style={{
        marginTop: 20,
        display: 'flex',
        alignItems: 'center',
        gap: 12,
      }}>
        <div style={{
          width: 48,
          height: 48,
          borderRadius: 8,
          background: 'white',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontSize: 24,
        }}>
          📁
        </div>
        <div style={{ flex: 1 }}>
          <div style={{ 
            fontWeight: 700, 
            color: '#92400e',
            fontSize: 14,
            marginBottom: 4,
          }}>
            {fileName || 'control_logic.bog'}
          </div>
          <div style={{ fontSize: 11, color: '#78350f' }}>
            Ready for Niagara Workbench Import
          </div>
        </div>
      </div>
      
      <button
        onClick={() => {
          if (downloadUrl) window.open(downloadUrl, '_blank');
        }}
        style={{
          width: '100%',
          marginTop: 12,
          background: '#f59e0b',
          color: 'white',
          border: 'none',
          borderRadius: 6,
          padding: '10px 12px',
          fontWeight: 600,
          cursor: 'pointer',
          fontSize: 13,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          gap: 6,
          transition: 'all 0.2s',
        }}
        onMouseEnter={(e) => {
          e.currentTarget.style.background = '#d97706';
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.background = '#f59e0b';
        }}
      >
        📥 Download BOG File
      </button>
      
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
        border: '3px solid #f59e0b',
      }} />
    </div>
  );
};
export default ArtifactNode;

