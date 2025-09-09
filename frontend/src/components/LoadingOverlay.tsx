import React from 'react';
import { Loader2 } from 'lucide-react';

interface LoadingOverlayProps {
  isVisible: boolean;
  message?: string;
}

const LoadingOverlay: React.FC<LoadingOverlayProps> = ({ isVisible, message }) => {
  if (!isVisible) return null;

  return (
    <div style={{
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      backgroundColor: 'rgba(0, 0, 0, 0.5)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 9999,
      backdropFilter: 'blur(4px)',
    }}>
      <div style={{
        background: '#FFFFFF',
        border: '3px solid #3F3F4B',
        borderRadius: '16px',
        padding: '32px 48px',
        boxShadow: '8px 8px 0 0 rgba(63, 63, 75, 0.25)',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        gap: '20px',
        maxWidth: '400px',
      }}>
        <Loader2 
          size={48} 
          style={{ 
            color: '#569BFF',
            animation: 'spin 1s linear infinite'
          }} 
        />
        <div style={{
          fontSize: '18px',
          fontWeight: 600,
          color: '#3F3F4B',
          textAlign: 'center',
        }}>
          {message || 'Processing your request...'}
        </div>
        <div style={{
          fontSize: '14px',
          color: '#6B7280',
          textAlign: 'center',
        }}>
          Please wait while we analyze your input
        </div>
      </div>
      
      <style>{`
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
};

export default LoadingOverlay;
