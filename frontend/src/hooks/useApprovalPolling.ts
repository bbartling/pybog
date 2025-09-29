import { useState, useEffect, useCallback } from 'react';
import { ChatMessage } from '../types/ChatMessage';

interface ApprovalMessage {
  message_id: string;
  type: 'system';
  messageCategory: 'approval';
  content: string;
  timestamp: string;
  metadata: any;
}

interface ApprovalPollingConfig {
  sessionId: string;
  enabled?: boolean;
  interval?: number; // in milliseconds, default 10 seconds
}

export const useApprovalPolling = ({ sessionId, enabled = true, interval = 10000 }: ApprovalPollingConfig) => {
  const [approvalMessages, setApprovalMessages] = useState<ChatMessage[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastPoll, setLastPoll] = useState<Date | null>(null);

  const pollApprovals = useCallback(async () => {
    if (!sessionId || !enabled) return;

    setLoading(true);
    setError(null);

    try {
      const response = await fetch(`/api/sessions/${sessionId}/approval-messages`);
      
      if (!response.ok) {
        throw new Error(`Failed to fetch approvals: ${response.statusText}`);
      }

      const data = await response.json();

      if (data.success) {
        // Convert approval messages to ChatMessage format
        const chatMessages: ChatMessage[] = data.messages.map((msg: ApprovalMessage) => ({
          id: msg.message_id,
          type: 'system' as const,
          messageType: 'approval' as const,
          content: msg.content,
          timestamp: new Date(msg.timestamp),
          sessionId: sessionId,
          metadata: {
            ...msg.metadata,
            // Ensure compatibility with existing ChatMessage interface
            status: msg.metadata.status || 'awaiting_approval',
            workflowState: {
              state: 'awaiting_approval' as const,
              resumeUrl: msg.metadata.resumeUrl,
              waitingData: msg.metadata.waitNode
            }
          }
        }));

        setApprovalMessages(chatMessages);
      } else {
        setError(data.error || 'Failed to fetch approval messages');
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error occurred';
      setError(errorMessage);
      console.error('Approval polling failed:', err);
    } finally {
      setLoading(false);
      setLastPoll(new Date());
    }
  }, [sessionId, enabled]);

  // Initial poll and set up interval
  useEffect(() => {
    if (!enabled || !sessionId) {
      setApprovalMessages([]);
      return;
    }

    // Initial poll
    pollApprovals();

    // Set up polling interval
    const pollInterval = setInterval(pollApprovals, interval);

    return () => {
      clearInterval(pollInterval);
    };
  }, [sessionId, enabled, interval, pollApprovals]);

  // Manual refresh function
  const refreshApprovals = useCallback(() => {
    pollApprovals();
  }, [pollApprovals]);

  // Clear approvals (useful when workflows complete)
  const clearApprovals = useCallback(() => {
    setApprovalMessages([]);
  }, []);

  return {
    approvalMessages,
    loading,
    error,
    lastPoll,
    refreshApprovals,
    clearApprovals,
    isPolling: enabled
  };
};