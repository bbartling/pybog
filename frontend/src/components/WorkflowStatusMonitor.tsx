import { useEffect, useState } from 'react';

interface WorkflowStatus {
  sessionId: string;
  currentStep: string;
  status: 'idle' | 'processing' | 'waiting' | 'complete' | 'error';
  progress?: number;
  message?: string;
  lastUpdate: string;
  error?: string;
}

interface WorkflowMonitorProps {
  sessionId: string;
  onStatusChange?: (status: WorkflowStatus) => void;
}

export const WorkflowStatusMonitor: React.FC<WorkflowMonitorProps> = ({ 
  sessionId, 
  onStatusChange 
}) => {
  const [status, setStatus] = useState<WorkflowStatus>({
    sessionId,
    currentStep: 'idle',
    status: 'idle',
    lastUpdate: new Date().toISOString()
  });
  const [isPolling, setIsPolling] = useState(false);

  // Poll for workflow status updates
  useEffect(() => {
    if (!sessionId || isPolling) return;

    const pollInterval = setInterval(async () => {
      try {
        console.log('[WorkflowMonitor] Polling status for session:', sessionId);
        
        // Check session for new messages and workflow state
        const response = await fetch(`http://localhost:8847/api/sessions/${sessionId}/full`);
        if (!response.ok) return;

        const sessionData = await response.json();
        const messages = sessionData.messages || [];
        const latestMessage = messages[messages.length - 1];

        if (latestMessage && latestMessage.timestamp !== status.lastUpdate) {
          const newStatus: WorkflowStatus = {
            sessionId,
            currentStep: latestMessage.metadata?.step || 'unknown',
            status: deriveStatusFromMessage(latestMessage),
            progress: latestMessage.metadata?.progress?.percentage,
            message: latestMessage.content,
            lastUpdate: latestMessage.timestamp,
            error: latestMessage.type === 'error' ? latestMessage.content : undefined
          };

          console.log('[WorkflowMonitor] Status update:', newStatus);
          setStatus(newStatus);
          onStatusChange?.(newStatus);
        }
      } catch (error) {
        console.error('[WorkflowMonitor] Polling error:', error);
      }
    }, 2000); // Poll every 2 seconds

    setIsPolling(true);

    return () => {
      clearInterval(pollInterval);
      setIsPolling(false);
    };
  }, [sessionId, status.lastUpdate, onStatusChange, isPolling]);

  return (
    <div className="workflow-status-monitor" style={{
      position: 'fixed',
      top: '10px',
      right: '10px',
      background: 'white',
      border: '1px solid #ccc',
      borderRadius: '8px',
      padding: '12px',
      boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
      minWidth: '300px',
      zIndex: 1000
    }}>
      <div style={{ fontWeight: 'bold', marginBottom: '8px' }}>
        Workflow Status
      </div>
      
      <div style={{ marginBottom: '4px' }}>
        <strong>Step:</strong> {status.currentStep}
      </div>
      
      <div style={{ marginBottom: '4px' }}>
        <strong>Status:</strong> 
        <span style={{ 
          color: getStatusColor(status.status),
          marginLeft: '8px',
          fontWeight: 'bold'
        }}>
          {status.status.toUpperCase()}
        </span>
      </div>

      {status.progress && (
        <div style={{ marginBottom: '8px' }}>
          <div style={{ fontSize: '12px', marginBottom: '2px' }}>
            Progress: {status.progress}%
          </div>
          <div style={{
            width: '100%',
            height: '4px',
            background: '#f0f0f0',
            borderRadius: '2px'
          }}>
            <div style={{
              width: `${status.progress}%`,
              height: '100%',
              background: getStatusColor(status.status),
              borderRadius: '2px',
              transition: 'width 0.3s ease'
            }} />
          </div>
        </div>
      )}

      {status.message && (
        <div style={{ 
          fontSize: '12px',
          color: '#666',
          marginBottom: '8px',
          maxHeight: '60px',
          overflow: 'auto'
        }}>
          {status.message}
        </div>
      )}

      {status.error && (
        <div style={{
          background: '#fee',
          color: '#c00',
          padding: '8px',
          borderRadius: '4px',
          fontSize: '12px'
        }}>
          <strong>Error:</strong> {status.error}
        </div>
      )}

      <div style={{ fontSize: '10px', color: '#999' }}>
        Last update: {new Date(status.lastUpdate).toLocaleTimeString()}
      </div>
    </div>
  );
};

function deriveStatusFromMessage(message: any): WorkflowStatus['status'] {
  if (message.type === 'error') return 'error';
  
  const step = message.metadata?.step;
  const workflow = message.metadata?.workflow;
  
  if (step === 'text_approved' || workflow === 'analysis') return 'processing';
  if (step === 'analysis_complete') return 'waiting';
  if (step === 'analysis_handoff') return 'complete';
  
  return 'processing';
}

function getStatusColor(status: WorkflowStatus['status']): string {
  switch (status) {
    case 'processing': return '#2563eb';
    case 'waiting': return '#f59e0b';
    case 'complete': return '#10b981';
    case 'error': return '#ef4444';
    case 'idle': return '#6b7280';
    default: return '#6b7280';
  }
}

export default WorkflowStatusMonitor;
