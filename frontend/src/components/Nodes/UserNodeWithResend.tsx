import React from 'react';
import { Handle, Position } from 'reactflow';
import { User, RefreshCw, AlertCircle } from 'lucide-react';

interface UserNodeProps {
  data: {
    content: string;
    timestamp?: Date;
    files?: File[];
    status?: 'sending' | 'sent' | 'failed';
    onResend?: () => void;
  };
}

const UserNodeWithResend: React.FC<UserNodeProps> = ({ data }) => {
  const { content, timestamp, files, status, onResend } = data;
  const isFailed = status === 'failed';
  const isSending = status === 'sending';

  return (
    <div 
      className={`niagara-node user-node ${isFailed ? 'error' : ''} ${isSending ? 'sending' : ''}`}
      style={{
        background: isFailed ? '#fee2e2' : '#e0e7ff',
        border: `2px solid ${isFailed ? '#dc2626' : '#6366f1'}`,
        borderRadius: '8px',
        padding: '12px',
        minWidth: '280px',
        maxWidth: '400px',
        opacity: isSending ? 0.7 : 1,
      }}
    >
      <Handle type="target" position={Position.Left} />
      
      <div style={{ 
        display: 'flex', 
        alignItems: 'flex-start', 
        gap: '10px',
        marginBottom: '8px' 
      }}>
        <div style={{
          background: isFailed ? '#dc2626' : '#6366f1',
          borderRadius: '50%',
          padding: '6px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center'
        }}>
          <User size={16} color="white" />
        </div>
        
        <div style={{ flex: 1 }}>
          <div style={{ 
            fontWeight: 500, 
            color: isFailed ? '#991b1b' : '#312e81',
            marginBottom: '4px',
            display: 'flex',
            alignItems: 'center',
            gap: '8px'
          }}>
            User
            {isFailed && (
              <>
                <AlertCircle size={14} color="#dc2626" />
                <span style={{ fontSize: '12px', color: '#dc2626' }}>Failed to send</span>
              </>
            )}
            {isSending && (
              <span style={{ fontSize: '12px', color: '#6366f1' }}>Sending...</span>
            )}
          </div>
          
          <div style={{ 
            fontSize: '13px', 
            color: '#1f2937',
            lineHeight: '1.4',
            wordBreak: 'break-word'
          }}>
            {content}
          </div>
          
          {files && files.length > 0 && (
            <div style={{ 
              marginTop: '6px', 
              fontSize: '11px', 
              color: '#6b7280' 
            }}>
              📎 {files.length} file(s) attached
            </div>
          )}
          
          <div style={{ 
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            marginTop: '6px'
          }}>
            {timestamp && (
              <div style={{ 
                fontSize: '11px', 
                color: '#9ca3af' 
              }}>
                {(timestamp instanceof Date ? timestamp : new Date(timestamp)).toLocaleTimeString()}
              </div>
            )}
            
            {isFailed && onResend && (
              <button
                onClick={onResend}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '4px',
                  padding: '2px 8px',
                  fontSize: '11px',
                  color: '#dc2626',
                  background: 'white',
                  border: '1px solid #dc2626',
                  borderRadius: '4px',
                  cursor: 'pointer',
                  transition: 'all 0.2s'
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.background = '#dc2626';
                  e.currentTarget.style.color = 'white';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.background = 'white';
                  e.currentTarget.style.color = '#dc2626';
                }}
              >
                <RefreshCw size={12} />
                Resend
              </button>
            )}
          </div>
        </div>
      </div>
      
      <Handle type="source" position={Position.Right} />
    </div>
  );
};

export default UserNodeWithResend;
