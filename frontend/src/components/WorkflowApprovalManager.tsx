/**
 * WorkflowApprovalManager Component
 * Fetches and displays waiting workflow executions that need user approval
 */

import React, { useState, useEffect } from 'react';
import { WorkflowApproval } from './WorkflowApproval';

interface ApprovalData {
  id: string;
  executionId: string;
  sessionId: string;
  status: string;
  category: string;
  waitNode: any;
  timestamp: string;
  workflowId: string;
}

interface WorkflowApprovalManagerProps {
  sessionId?: string; // If provided, only show approvals for this session
  onApprovalComplete?: (executionId: string, action: string, success: boolean) => void;
  // Optional top-level wiring hooks (not required by internal list rendering)
  onApprove?: () => void;
  onReject?: (feedback: string) => void;
}

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8847';

export const WorkflowApprovalManager: React.FC<WorkflowApprovalManagerProps> = ({
  sessionId,
  onApprovalComplete,
}) => {
  const [approvals, setApprovals] = useState<ApprovalData[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastFetch, setLastFetch] = useState<Date | null>(null);

  const fetchApprovals = async () => {
    setLoading(true);
    setError(null);

    try {
      // Workflow approvals now handled through unified API service
      const response = await fetch(`${API_BASE_URL}/api/workflow/approvals`);
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const data = await response.json();
      
      if (data.success) {
        let fetchedApprovals = data.approvals || [];
        
        // Filter by session ID if provided
        if (sessionId) {
          fetchedApprovals = fetchedApprovals.filter(
            (approval: ApprovalData) => approval.sessionId === sessionId
          );
        }
        
        setApprovals(fetchedApprovals);
        setLastFetch(new Date());
        console.log(`[WorkflowApprovalManager] Fetched ${fetchedApprovals.length} approval(s)`);
      } else {
        setError(data.error || 'Failed to fetch approvals');
      }
    } catch (err: any) {
      setError(err.message || 'Failed to fetch approvals');
      console.error('[WorkflowApprovalManager] Fetch error:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleApprovalComplete = async (action: string, success: boolean, executionId: string) => {
    console.log(`[WorkflowApprovalManager] Approval completed: ${action} (${success ? 'success' : 'failed'}) for execution ${executionId}`);
    
    if (success) {
      // Remove the completed approval from the list
      setApprovals(prev => prev.filter(approval => approval.executionId !== executionId));
    }
    
    // Notify parent component
    onApprovalComplete?.(executionId, action, success);
    
    // Refresh the list after a short delay
    setTimeout(() => {
      fetchApprovals();
    }, 1000);
  };

  // Auto-fetch on mount and set up polling
  useEffect(() => {
    fetchApprovals();
    
    // Poll every 10 seconds for new approvals
    const pollInterval = setInterval(fetchApprovals, 10000);

    // Also listen for window focus to immediately refresh when user returns
    const onFocus = () => fetchApprovals();
    window.addEventListener('focus', onFocus);
    
    return () => {
      clearInterval(pollInterval);
      window.removeEventListener('focus', onFocus);
    };
  }, [sessionId]);

  if (loading && approvals.length === 0) {
    return (
      <div style={{ padding: 16, textAlign: 'center', color: '#666' }}>
        Loading workflow approvals...
      </div>
    );
  }

  if (error && approvals.length === 0) {
    return (
      <div style={{ 
        padding: 16, 
        background: '#FEF2F2', 
        border: '1px solid #FECACA', 
        borderRadius: 8,
        color: '#B91C1C' 
      }}>
        <div style={{ fontWeight: 600, marginBottom: 8 }}>Error Loading Approvals</div>
        <div style={{ fontSize: '0.875rem' }}>{error}</div>
        <button 
          onClick={fetchApprovals}
          style={{
            marginTop: 8,
            padding: '4px 12px',
            background: 'none',
            border: '1px solid #B91C1C',
            borderRadius: 4,
            color: '#B91C1C',
            cursor: 'pointer',
            fontSize: '0.875rem'
          }}
        >
          Retry
        </button>
      </div>
    );
  }

  if (approvals.length === 0) {
    return (
      <div style={{ 
        padding: 16, 
        textAlign: 'center', 
        color: '#666',
        background: '#F9FAFB',
        borderRadius: 8,
        border: '1px solid #E5E7EB'
      }}>
        <div style={{ fontWeight: 600 }}>No pending approvals</div>
        <div style={{ fontSize: '0.875rem', marginTop: 4 }}>
          All workflows are running smoothly
        </div>
        {lastFetch && (
          <div style={{ fontSize: '0.75rem', marginTop: 8, color: '#9CA3AF' }}>
            Last checked: {lastFetch.toLocaleTimeString()}
          </div>
        )}
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      <div style={{ 
        display: 'flex', 
        justifyContent: 'space-between', 
        alignItems: 'center',
        padding: '12px 0',
        borderBottom: '1px solid #E5E7EB'
      }}>
        <h3 style={{ margin: 0, color: '#1F2937' }}>
          Workflow Approvals ({approvals.length})
        </h3>
        <button
          onClick={fetchApprovals}
          disabled={loading}
          style={{
            padding: '6px 12px',
            background: loading ? '#F3F4F6' : '#EBF8FF',
            border: '1px solid #BFDBFE',
            borderRadius: 6,
            color: loading ? '#9CA3AF' : '#1D4ED8',
            cursor: loading ? 'default' : 'pointer',
            fontSize: '0.875rem'
          }}
        >
          {loading ? 'Refreshing...' : 'Refresh'}
        </button>
      </div>
      
      {approvals.map((approval) => {
        // Transform approval data into message format expected by WorkflowApproval
        const message: any = {
          id: approval.id,
          messageId: approval.id,
          type: 'system',
          content: '',
          metadata: {
            status: approval.status,
            category: approval.category,
            waitNode: approval.waitNode,
          },
          timestamp: approval.timestamp,
          sessionId: approval.sessionId,
        };

        return (
          <WorkflowApproval
            key={approval.id}
            message={message}
            sessionId={approval.sessionId || ''}
            onActionComplete={(action: string, success: boolean) => 
              handleApprovalComplete(action, success, approval.executionId)
            }
          />
        );
      })}
      
      {error && (
        <div style={{ 
          padding: 12, 
          background: '#FEF2F2', 
          border: '1px solid #FECACA', 
          borderRadius: 6,
          color: '#B91C1C',
          fontSize: '0.875rem'
        }}>
          Warning: {error}
        </div>
      )}
      
      {lastFetch && (
        <div style={{ 
          fontSize: '0.75rem', 
          color: '#9CA3AF', 
          textAlign: 'center',
          paddingTop: 8
        }}>
          Last updated: {lastFetch.toLocaleTimeString()}
        </div>
      )}
    </div>
  );
};

export default WorkflowApprovalManager;