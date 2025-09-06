import React from 'react';
import type { NodeProps } from 'reactflow';
import { Handle, Position } from 'reactflow';
import { Database, CheckCircle } from 'lucide-react';

interface SystemData {
  content?: string;
  timestamp?: Date | string;
  analysis?: any;
  downloadUrl?: string;
}

const SystemNodeNiagara: React.FC<NodeProps<SystemData>> = ({ data }) => {
  const time = data?.timestamp ? new Date(data.timestamp) : null;
  
  return (
    <div style={{
      background: 'linear-gradient(135deg, #dbeafe 0%, #bfdbfe 100%)',
      border: '2px solid #3b82f6',
      borderRadius: '6px',
      boxShadow: '0 2px 8px rgba(59, 130, 246, 0.15)',
      minWidth: '280px',
      fontFamily: 'Segoe UI, Tahoma, Geneva, Verdana, sans-serif',
      position: 'relative'
    }}>
      {/* Input Port */}
      <Handle 
        type="target" 
        position={Position.Left}
        style={{ 
          background: '#22d3ee',
          width: 10,
          height: 10,
          border: '2px solid #ffffff',
          left: -5
        }} 
      />
      
      {/* Node Header */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        padding: '8px 12px',
        background: 'linear-gradient(180deg, #93c5fd 0%, #60a5fa 100%)',
        borderBottom: '1px solid #3b82f6',
        gap: '8px'
      }}>
        <div style={{
          width: '24px',
          height: '24px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          background: '#ffffff',
          borderRadius: '4px',
          color: '#3b82f6'
        }}>
          <Database size={16} />
        </div>
        <div style={{
          flex: 1,
          fontSize: '13px',
          fontWeight: 600,
          color: '#1e3a8a'
        }}>
          System Response
        </div>
        <div style={{
          padding: '2px 8px',
          borderRadius: '12px',
          fontSize: '11px',
          fontWeight: 600,
          textTransform: 'uppercase',
          background: '#dcfce7',
          color: '#166534'
        }}>
          <CheckCircle size={12} style={{ display: 'inline', marginRight: '2px' }} />
          OK
        </div>
      </div>
      
      {/* Node Content */}
      <div style={{
        padding: '12px',
        background: '#ffffff',
        borderRadius: '0 0 4px 4px'
      }}>
        <div style={{
          fontSize: '12px',
          lineHeight: '1.5',
          color: '#374151',
          maxHeight: '80px',
          overflow: 'hidden',
          textOverflow: 'ellipsis',
          display: '-webkit-box',
          WebkitLineClamp: 4,
          WebkitBoxOrient: 'vertical',
          wordBreak: 'break-word'
        }}>
          {data?.content && data.content.length > 150 
            ? data.content.substring(0, 150) + '...' 
            : data?.content || 'No content'}
        </div>
        
        {time && (
          <div style={{
            marginTop: '8px',
            paddingTop: '8px',
            borderTop: '1px solid #e5e7eb',
            fontSize: '10px',
            color: '#6b7280',
            fontStyle: 'italic'
          }}>
            {time.toLocaleTimeString()}
          </div>
        )}
      </div>
      
      {/* Output Port */}
      <Handle 
        type="source" 
        position={Position.Right}
        style={{ 
          background: '#f59e0b',
          width: 10,
          height: 10,
          border: '2px solid #ffffff',
          right: -5
        }} 
      />
    </div>
  );
};

export default SystemNodeNiagara;
