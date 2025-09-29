// ExecutionStatusMonitor.tsx - Shows workflow execution status (no Tailwind; inline styles for consistency)
import React from 'react';
// Execution monitoring service removed - using unified backend
interface WorkflowExecution {
  id: string;
  workflowId: string;
  status: string;
  sessionId?: string;
  startedAt?: string;
  mode?: string;
}

const formatExecutionStatus = (execution: WorkflowExecution): string => execution.status;
const executionNeedsAttention = (execution: WorkflowExecution): boolean => execution.status === 'waiting';
import { AlertTriangle, Clock, CheckCircle, RefreshCw } from 'lucide-react';
import { TOKENS, STYLES } from '../theme/neubrutalism';

interface ExecutionStatusMonitorProps {
  executions: WorkflowExecution[];
  waitingExecutions: WorkflowExecution[];
  waitingCount: number;
  isLoading: boolean;
  error: string | null;
  onRefresh: () => void;
  sessionId?: string; // If provided, only show executions for this session
}

const boxStyle: React.CSSProperties = {
  background: TOKENS.white,
  // Avoid border shorthand to prevent collision with overrides of borderColor
  borderWidth: 1,
  borderStyle: 'solid',
  borderColor: '#E5E7EB',
  borderRadius: STYLES.radius.medium,
  padding: 12,
};

const rowStyle: React.CSSProperties = { display: 'flex', alignItems: 'center', justifyContent: 'space-between' };
const smallText: React.CSSProperties = { fontSize: 12, color: TOKENS.muted };
const labelText: React.CSSProperties = { fontSize: 12, fontWeight: 600, color: TOKENS.text };

const ExecutionStatusMonitor: React.FC<ExecutionStatusMonitorProps> = ({
  executions,
  waitingExecutions,
  waitingCount,
  isLoading,
  error,
  onRefresh,
  sessionId
}) => {
  // ENHANCED: Better session filtering and fallback logic
  const relevantExecutions = sessionId 
    ? executions.filter(exec => exec.sessionId === sessionId)
    : executions;
    
  const relevantWaitingExecutions = sessionId
    ? waitingExecutions.filter(exec => exec.sessionId === sessionId)
    : waitingExecutions;

  // Enhanced fallback: show cross-session waiting states when current session has no activity
  const hasSessionActivity = sessionId && relevantExecutions.length > 0;
  const hasGlobalWaiting = waitingExecutions.length > 0;
  const useGlobalFallback = Boolean(sessionId) && !hasSessionActivity && hasGlobalWaiting;
  
  const displayExecutions = useGlobalFallback ? executions : relevantExecutions;
  const displayWaitingExecutions = useGlobalFallback ? waitingExecutions : relevantWaitingExecutions;

  const needsAttentionCount = displayWaitingExecutions.filter(executionNeedsAttention).length;
  
  // Calculate cross-session stats for better context
  const crossSessionWaiting = sessionId ? waitingExecutions.filter(exec => exec.sessionId !== sessionId) : [];
  const totalGlobalWaiting = waitingExecutions.length;
  const sessionWaitingCount = relevantWaitingExecutions.length;

  if (error) {
    return (
      <div style={{ ...boxStyle, background: '#FEF2F2', borderColor: '#FECACA' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, color: '#B91C1C', fontWeight: 600 }}>
          <AlertTriangle size={14} />
          <span style={{ fontSize: 12 }}>Execution Monitor Error</span>
        </div>
        <div style={{ ...smallText, color: '#B91C1C', marginTop: 6 }}>{error}</div>
        <button 
          onClick={onRefresh}
          style={{ marginTop: 6, background: 'none', border: 'none', color: '#991B1B', textDecoration: 'underline', fontSize: 12, cursor: 'pointer' }}
        >
          Retry
        </button>
      </div>
    );
  }

  if (displayExecutions.length === 0 && !isLoading) {
    return (
      <div style={{ ...boxStyle, background: '#F9FAFB' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, color: TOKENS.muted }}>
          <CheckCircle size={14} />
          <span style={{ fontSize: 12 }}>No active executions</span>
        </div>
      </div>
    );
  }

  return (
    <div style={boxStyle}>
      {/* Header */}
      <div style={rowStyle}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          {needsAttentionCount > 0 ? (
            <AlertTriangle size={14} color={TOKENS.warning} />
          ) : waitingCount > 0 ? (
            <Clock size={14} color={TOKENS.info} />
          ) : (
            <CheckCircle size={14} color={TOKENS.ok} />
          )}
          <span style={labelText}>
            {useGlobalFallback 
              ? `All Workflows (${crossSessionWaiting.length} other sessions)` 
              : sessionId 
                ? `Session Workflows${crossSessionWaiting.length > 0 ? ` (+${crossSessionWaiting.length} others)` : ''}` 
                : 'All Workflows'
            }
          </span>
          {isLoading && (<RefreshCw size={12} color={TOKENS.muted} />)}
        </div>
        <button 
          onClick={onRefresh}
          disabled={isLoading}
          style={{ ...smallText, textDecoration: 'underline', background: 'none', border: 'none', cursor: 'pointer' }}
        >
          Refresh
        </button>
      </div>

      {/* Status Summary */}
      <div style={{ display: 'flex', gap: 12, marginTop: 8 }}>
        <div style={smallText}>Total: <span style={{ fontWeight: 600, color: TOKENS.text }}>{displayExecutions.length}</span></div>
        {displayWaitingExecutions.length > 0 && (
          <div style={{ ...smallText, color: TOKENS.warning }}>Waiting: <span style={{ fontWeight: 600 }}>{displayWaitingExecutions.length}</span></div>
        )}
        {needsAttentionCount > 0 && (
          <div style={{ ...smallText, color: TOKENS.error }}>Needs Attention: <span style={{ fontWeight: 600 }}>{needsAttentionCount}</span></div>
        )}
        {/* Show global context when viewing session-specific data */}
        {sessionId && !useGlobalFallback && totalGlobalWaiting > sessionWaitingCount && (
          <div style={{ ...smallText, color: TOKENS.info }}>Global: <span style={{ fontWeight: 600 }}>{totalGlobalWaiting}</span></div>
        )}
      </div>

      {/* Waiting Executions List */}
      {displayWaitingExecutions.length > 0 && (
        <div style={{ marginTop: 8, display: 'flex', flexDirection: 'column', gap: 8 }}>
          <div style={{ ...labelText, fontSize: 12, color: TOKENS.text }}>Waiting Workflows:</div>
          {displayWaitingExecutions.map(execution => (
            <div 
              key={execution.id} 
              style={{
                padding: 8,
                borderRadius: 8,
                // Avoid shorthand+longhand border collision warnings
                borderWidth: 1,
                borderStyle: 'solid',
                background: executionNeedsAttention(execution) ? '#FFF7ED' : '#EFF6FF',
                borderColor: executionNeedsAttention(execution) ? '#FED7AA' : '#BFDBFE',
                fontSize: 12
              }}
            >
              <div style={{ ...rowStyle, marginBottom: 4 }}>
                <span style={{ fontWeight: 600 }}>Execution #{execution.id.slice(-6)}</span>
                <span style={{
                  padding: '2px 6px',
                  borderRadius: 6,
                  background: executionNeedsAttention(execution) ? '#FED7AA' : '#DBEAFE',
                  color: '#1F2937',
                  fontSize: 11,
                  fontWeight: 600
                }}>
                  {formatExecutionStatus(execution)}
                </span>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 2, color: TOKENS.muted }}>
                {execution.sessionId && (
                  <div>Session: {execution.sessionId.slice(-8)}...</div>
                )}
                <div>Started: {execution.startedAt ? new Date(execution.startedAt).toLocaleTimeString() : 'Unknown'}</div>
                {execution.mode && (
                  <div>Mode: {execution.mode}</div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Recent Completed Executions */}
      {displayExecutions.length > displayWaitingExecutions.length && (
<div style={{ borderTopWidth: 1, borderTopStyle: 'solid', borderTopColor: '#E5E7EB', paddingTop: 8, marginTop: 8 }}>
          <div style={{ ...labelText, fontSize: 12, marginBottom: 4, color: TOKENS.text }}>Recent Activity:</div>
          <div style={{ ...smallText }}>
            {displayExecutions.length - displayWaitingExecutions.length} completed workflow(s)
          </div>
        </div>
      )}
    </div>
  );
};

export default ExecutionStatusMonitor;
