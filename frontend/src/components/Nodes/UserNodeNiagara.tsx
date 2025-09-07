import React from 'react';
import type { NodeProps } from 'reactflow';
import { Handle, Position } from 'reactflow';
import { Settings, User, Paperclip } from 'lucide-react';

interface UserData {
  content?: string;
  timestamp?: Date | string;
  files?: File[];
}

const UserNodeNiagara: React.FC<NodeProps<UserData>> = ({ data }) => {
  const time = data?.timestamp ? new Date(data.timestamp) : null;
  const hasFiles = data?.files && data.files.length > 0;
  
  return (
    <div style={{
      background: 'linear-gradient(135deg, #f3e8ff 0%, #ede9fe 100%)',
      border: '2px solid #8b5cf6',
      borderRadius: '6px',
      boxShadow: '0 2px 8px rgba(139, 92, 246, 0.15)',
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
        background: 'linear-gradient(180deg, #e8d5ff 0%, #ddd6fe 100%)',
        borderBottom: '1px solid #8b5cf6',
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
          color: '#8b5cf6'
        }}>
          <Settings size={16} style={{ animation: 'spin 8s linear infinite' }} />
        </div>
        <div style={{
          flex: 1,
          fontSize: '13px',
          fontWeight: 600,
          color: '#581c87'
        }}>
          User Input
        </div>
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '4px',
          padding: '2px 8px',
          borderRadius: '12px',
          fontSize: '11px',
          fontWeight: 600,
          textTransform: 'uppercase',
          background: '#e8d5ff',
          color: '#581c87'
        }}>
          <User size={12} />
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
          // Removed maxHeight to allow content to expand
          // Removed overflow: hidden
          // Removed WebkitLineClamp to show full content
          wordBreak: 'break-word',
          whiteSpace: 'pre-wrap',
          // Optional: Add max-width if needed to maintain bubble width
          maxWidth: '400px'
        }}>
          {data?.content || 'No content'}
        </div>
        
        {hasFiles && (
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '4px',
            marginTop: '8px',
            paddingTop: '8px',
            borderTop: '1px solid #e9d5ff',
            fontSize: '11px',
            color: '#6b7280'
          }}>
            <Paperclip size={12} />
            <span>{data.files!.length} file{data.files!.length > 1 ? 's' : ''}</span>
          </div>
        )}
        
        {time && (
          <div style={{
            marginTop: '4px',
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

export default UserNodeNiagara;
