/**
 * React hook for integrating with the Chat Pipeline Service
 * Manages pipeline state and provides handlers for chat flow
 */

import { useState, useEffect, useCallback } from 'react';
import { chatPipelineService, ChatPipelineState, AnalysisSummary, ResultFiles } from '../services/ChatPipelineService';
import { ChatMessage } from '../types/ChatMessage';

interface UseChatPipelineResult {
  pipelineState: ChatPipelineState;
  startChatPipeline: (message: string) => Promise<void>;
  retryLastStep: () => Promise<void>;
  isProcessing: boolean;
  error: string | null;
  addPipelineMessage: (message: ChatMessage) => void;
}

export function useChatPipeline(
  sessionId: string,
  onAddMessage: (message: ChatMessage) => void
): UseChatPipelineResult {
  const [pipelineState, setPipelineState] = useState<ChatPipelineState>(() =>
    chatPipelineService.getPipelineState(sessionId)
  );
  const [error, setError] = useState<string | null>(null);

  // Subscribe to pipeline events
  useEffect(() => {
    const unsubscribe = chatPipelineService.subscribe((event) => {
      if (event.data.sessionId !== sessionId) return;

      switch (event.type) {
        case 'state_change':
          setPipelineState(event.data);
          setError(null);
          break;

        case 'progress':
          handleProgressEvent(event.data);
          break;

        case 'analysis_summary':
          handleAnalysisSummary(event.data);
          break;

        case 'result_files':
          handleResultFiles(event.data);
          break;

        case 'error':
          setError(event.data.error);
          setPipelineState(event.data);
          break;
      }
    });

    return unsubscribe;
  }, [sessionId]);

  // Handle progress events by creating/updating progress message
  const handleProgressEvent = useCallback((data: any) => {
    const progressMessage: ChatMessage = {
      id: `progress-${sessionId}-${data.stage}`,
      type: 'system',
      messageType: 'analysis_progress',
      content: `Analyzing: ${data.stage}`,
      timestamp: new Date(),
      sessionId,
      metadata: {
        stage: data.stage,
        progress: data.progress,
        message: `Processing ${data.stage} stage...`
      }
    };

    onAddMessage(progressMessage);
  }, [sessionId, onAddMessage]);

  // Handle analysis summary by creating summary message
  const handleAnalysisSummary = useCallback((data: { sessionId: string; summary: AnalysisSummary }) => {
    const summaryMessage: ChatMessage = {
      id: `analysis-summary-${sessionId}-${Date.now()}`,
      type: 'system',
      messageType: 'analysis_summary',
      content: 'Analysis completed successfully',
      timestamp: new Date(),
      sessionId,
      metadata: {
        summary: data.summary
      }
    };

    onAddMessage(summaryMessage);
  }, [sessionId, onAddMessage]);

  // Handle result files by creating files message
  const handleResultFiles = useCallback((data: any) => {
    // Collect all files for this session
    const files = []; // This would be populated from the pipeline state
    
    const filesMessage: ChatMessage = {
      id: `result-files-${sessionId}-${Date.now()}`,
      type: 'system',
      messageType: 'result_files',
      content: 'Files are ready for download',
      timestamp: new Date(),
      sessionId,
      metadata: {
        files: [{
          artifactId: data.artifactId,
          filename: `${data.type}-${sessionId}.${data.type === 'bog' ? 'xml' : 'json'}`,
          size: 0, // Would be provided by the service
          sha256: '', // Would be provided by the service
          downloadUrl: data.downloadUrl,
          type: data.type
        }]
      }
    };

    onAddMessage(filesMessage);
  }, [sessionId, onAddMessage]);

  // Start chat pipeline
  const startChatPipeline = useCallback(async (message: string) => {
    try {
      setError(null);
      await chatPipelineService.startChatPipeline(sessionId, message);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to start chat pipeline';
      setError(errorMessage);
      console.error('[useChatPipeline] Failed to start pipeline:', err);
    }
  }, [sessionId]);

  // Retry last step
  const retryLastStep = useCallback(async () => {
    try {
      setError(null);
      await chatPipelineService.retryLastStep(sessionId);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to retry step';
      setError(errorMessage);
      console.error('[useChatPipeline] Failed to retry:', err);
    }
  }, [sessionId]);

  // Add pipeline message helper
  const addPipelineMessage = useCallback((message: ChatMessage) => {
    onAddMessage(message);
  }, [onAddMessage]);

  const isProcessing = ['chat', 'clarifying', 'analyzing', 'generating_bog'].includes(pipelineState.currentStep);

  return {
    pipelineState,
    startChatPipeline,
    retryLastStep,
    isProcessing,
    error,
    addPipelineMessage
  };
}