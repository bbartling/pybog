/**
 * Chat Pipeline Service for PyBOG N4 Builder
 * Implements the complete chat → clarifiers → analysis → BOG → downloads flow
 * with idempotency, retry logic, and WebSocket progress tracking
 */

import { unifiedAPIService } from './UnifiedAPIService';
import websocketService from './websocketService';
import { generateIdempotencyKey } from '../utils/idempotency';

export interface ChatPipelineState {
  sessionId: string;
  currentStep: 'idle' | 'chat' | 'clarifying' | 'analyzing' | 'generating_bog' | 'complete' | 'error';
  lastIdempotencyKey?: string;
  analysisId?: string;
  artifactId?: string;
  error?: string;
  retryable?: boolean;
}

export interface AnalysisSummary {
  equipmentType: string;
  operatingModes: string[];
  schedules: Array<{
    name: string;
    type: string;
    schedule: string;
  }>;
  alarms: Array<{
    name: string;
    condition: string;
    action: string;
  }>;
  ioPoints: Array<{
    name: string;
    type: 'input' | 'output';
    dataType: string;
    description: string;
  }>;
  controlBlocks: Array<{
    name: string;
    type: string;
    description: string;
    complexity: number;
  }>;
  pseudoCode: string;
}

export interface ResultFiles {
  analysisFile: {
    artifactId: string;
    filename: string;
    size: number;
    sha256: string;
    downloadUrl: string;
  };
  bogFile: {
    artifactId: string;
    filename: string;
    size: number;
    sha256: string;
    downloadUrl: string;
  };
}

export type ChatPipelineEventHandler = (event: {
  type: 'state_change' | 'progress' | 'analysis_summary' | 'result_files' | 'error';
  data: any;
}) => void;

class ChatPipelineService {
  private handlers: Set<ChatPipelineEventHandler> = new Set();
  private pipelineStates: Map<string, ChatPipelineState> = new Map();

  constructor() {
    this.setupWebSocketListeners();
  }

  /**
   * Subscribe to pipeline events
   */
  subscribe(handler: ChatPipelineEventHandler): () => void {
    this.handlers.add(handler);
    return () => this.handlers.delete(handler);
  }

  /**
   * Get current pipeline state for a session
   */
  getPipelineState(sessionId: string): ChatPipelineState {
    return this.pipelineStates.get(sessionId) || {
      sessionId,
      currentStep: 'idle'
    };
  }

  /**
   * Start the chat pipeline with a user message
   */
  async startChatPipeline(sessionId: string, message: string): Promise<void> {
    const idempotencyKey = generateIdempotencyKey(sessionId, message);
    
    // Update pipeline state
    const state: ChatPipelineState = {
      sessionId,
      currentStep: 'chat',
      lastIdempotencyKey: idempotencyKey
    };
    this.pipelineStates.set(sessionId, state);
    this.emitEvent('state_change', state);

    try {
      // Ensure WebSocket connection is established before sending message
      const websocketService = (await import('./websocketService')).default;
      if (!websocketService.isConnected() || websocketService.getCurrentSessionId() !== sessionId) {
        console.log('[ChatPipeline] Establishing WebSocket connection for session:', sessionId);
        const connected = await websocketService.connect(sessionId);
        if (!connected) {
          throw new Error('Failed to establish WebSocket connection');
        }
        // Wait a moment for connection to stabilize
        await new Promise(resolve => setTimeout(resolve, 100));
      }

      // Send chat message with idempotency key
      const response = await fetch(`${this.getApiUrl()}/api/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Idempotency-Key': idempotencyKey
        },
        body: JSON.stringify({
          session_id: sessionId,
          text: message
        })
      });

      if (!response.ok) {
        throw new Error(`Chat request failed: ${response.status} ${response.statusText}`);
      }

      // Response is 202 Accepted - actual processing happens via WebSocket
      console.log('[ChatPipeline] Chat message sent, waiting for WebSocket events');
      
    } catch (error) {
      console.error('[ChatPipeline] Failed to start chat pipeline:', error);
      this.handleError(sessionId, error as Error, true);
    }
  }

  /**
   * Retry the last step with the same idempotency key
   */
  async retryLastStep(sessionId: string): Promise<void> {
    const state = this.pipelineStates.get(sessionId);
    if (!state || !state.lastIdempotencyKey) {
      throw new Error('No retryable step found');
    }

    console.log(`[ChatPipeline] Retrying step: ${state.currentStep}`);

    try {
      switch (state.currentStep) {
        case 'chat':
          // Retry chat with same idempotency key
          await this.retryChatStep(sessionId, state.lastIdempotencyKey);
          break;
        case 'analyzing':
          // Retry analysis
          await this.retryAnalysisStep(sessionId, state.lastIdempotencyKey);
          break;
        case 'generating_bog':
          // Retry BOG generation
          await this.retryBogStep(sessionId, state.lastIdempotencyKey);
          break;
        default:
          throw new Error(`Cannot retry step: ${state.currentStep}`);
      }
    } catch (error) {
      console.error('[ChatPipeline] Retry failed:', error);
      this.handleError(sessionId, error as Error, true);
    }
  }

  /**
   * Setup WebSocket listeners for pipeline events
   */
  private setupWebSocketListeners(): void {
    // Listen for analysis events
    websocketService.on('message', (event) => {
      const { data } = event;
      if (!data || !data.sessionId) return;

      const sessionId = data.sessionId;
      const state = this.pipelineStates.get(sessionId);
      if (!state) return;

      switch (data.type) {
        case 'analysis.started':
          this.handleAnalysisStarted(sessionId, data);
          break;
        case 'analysis.progress':
          this.handleAnalysisProgress(sessionId, data);
          break;
        case 'analysis.completed':
          this.handleAnalysisCompleted(sessionId, data);
          break;
        case 'analysis.failed':
          this.handleAnalysisFailed(sessionId, data);
          break;
        case 'bog.started':
          this.handleBogStarted(sessionId, data);
          break;
        case 'bog.completed':
          this.handleBogCompleted(sessionId, data);
          break;
        case 'bog.failed':
          this.handleBogFailed(sessionId, data);
          break;
        case 'artifact.available':
          this.handleArtifactAvailable(sessionId, data);
          break;
      }
    });
  }

  /**
   * Handle analysis started event
   */
  private handleAnalysisStarted(sessionId: string, data: any): void {
    const state = this.pipelineStates.get(sessionId);
    if (!state) return;

    const updatedState: ChatPipelineState = {
      ...state,
      currentStep: 'analyzing',
      analysisId: data.analysisId
    };
    this.pipelineStates.set(sessionId, updatedState);
    this.emitEvent('state_change', updatedState);
  }

  /**
   * Handle analysis progress event
   */
  private handleAnalysisProgress(sessionId: string, data: any): void {
    this.emitEvent('progress', {
      sessionId,
      stage: data.stage, // 'parse', 'normalize', 'synthesize'
      progress: data.progress
    });
  }

  /**
   * Handle analysis completed event
   */
  private handleAnalysisCompleted(sessionId: string, data: any): void {
    const state = this.pipelineStates.get(sessionId);
    if (!state) return;

    // Extract analysis summary from the event data
    const summary: AnalysisSummary = this.extractAnalysisSummary(data.summary);
    
    // Emit analysis summary event
    this.emitEvent('analysis_summary', {
      sessionId,
      summary
    });

    // Automatically trigger BOG generation
    this.startBogGeneration(sessionId, state.analysisId!);
  }

  /**
   * Handle analysis failed event
   */
  private handleAnalysisFailed(sessionId: string, data: any): void {
    this.handleError(sessionId, new Error(data.error), data.retryable);
  }

  /**
   * Handle BOG generation started event
   */
  private handleBogStarted(sessionId: string, data: any): void {
    const state = this.pipelineStates.get(sessionId);
    if (!state) return;

    const updatedState: ChatPipelineState = {
      ...state,
      currentStep: 'generating_bog'
    };
    this.pipelineStates.set(sessionId, updatedState);
    this.emitEvent('state_change', updatedState);
  }

  /**
   * Handle BOG generation completed event
   */
  private handleBogCompleted(sessionId: string, data: any): void {
    const state = this.pipelineStates.get(sessionId);
    if (!state) return;

    const updatedState: ChatPipelineState = {
      ...state,
      currentStep: 'complete',
      artifactId: data.artifactId
    };
    this.pipelineStates.set(sessionId, updatedState);
    this.emitEvent('state_change', updatedState);
  }

  /**
   * Handle BOG generation failed event
   */
  private handleBogFailed(sessionId: string, data: any): void {
    this.handleError(sessionId, new Error(data.error), data.retryable);
  }

  /**
   * Handle artifact available event
   */
  private handleArtifactAvailable(sessionId: string, data: any): void {
    // Emit result files event with download URLs
    this.emitEvent('result_files', {
      sessionId,
      artifactId: data.artifactId,
      type: data.type, // 'analysis' | 'bog'
      downloadUrl: data.downloadUrl
    });
  }

  /**
   * Start BOG generation
   */
  private async startBogGeneration(sessionId: string, analysisId: string): Promise<void> {
    const idempotencyKey = generateIdempotencyKey(sessionId, `bog-${analysisId}`);
    
    try {
      const response = await fetch(`${this.getApiUrl()}/api/bog`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Idempotency-Key': idempotencyKey
        },
        body: JSON.stringify({
          session_id: sessionId,
          analysis_id: analysisId
        })
      });

      if (!response.ok) {
        throw new Error(`BOG generation failed: ${response.status} ${response.statusText}`);
      }

      // Update state with BOG idempotency key for retry
      const state = this.pipelineStates.get(sessionId);
      if (state) {
        state.lastIdempotencyKey = idempotencyKey;
        this.pipelineStates.set(sessionId, state);
      }

    } catch (error) {
      console.error('[ChatPipeline] Failed to start BOG generation:', error);
      this.handleError(sessionId, error as Error, true);
    }
  }

  /**
   * Retry chat step
   */
  private async retryChatStep(sessionId: string, idempotencyKey: string): Promise<void> {
    // This would need the original message - for now, emit error
    throw new Error('Chat retry not implemented - original message needed');
  }

  /**
   * Retry analysis step
   */
  private async retryAnalysisStep(sessionId: string, idempotencyKey: string): Promise<void> {
    const response = await fetch(`${this.getApiUrl()}/api/analysis`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Idempotency-Key': idempotencyKey
      },
      body: JSON.stringify({
        session_id: sessionId
      })
    });

    if (!response.ok) {
      throw new Error(`Analysis retry failed: ${response.status} ${response.statusText}`);
    }
  }

  /**
   * Retry BOG generation step
   */
  private async retryBogStep(sessionId: string, idempotencyKey: string): Promise<void> {
    const state = this.pipelineStates.get(sessionId);
    if (!state?.analysisId) {
      throw new Error('No analysis ID available for BOG retry');
    }

    const response = await fetch(`${this.getApiUrl()}/api/bog`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Idempotency-Key': idempotencyKey
      },
      body: JSON.stringify({
        session_id: sessionId,
        analysis_id: state.analysisId
      })
    });

    if (!response.ok) {
      throw new Error(`BOG retry failed: ${response.status} ${response.statusText}`);
    }
  }

  /**
   * Handle pipeline errors
   */
  private handleError(sessionId: string, error: Error, retryable: boolean): void {
    const state = this.pipelineStates.get(sessionId);
    if (!state) return;

    const updatedState: ChatPipelineState = {
      ...state,
      currentStep: 'error',
      error: error.message,
      retryable
    };
    this.pipelineStates.set(sessionId, updatedState);
    
    this.emitEvent('error', {
      sessionId,
      error: error.message,
      retryable,
      step: state.currentStep
    });
  }

  /**
   * Extract analysis summary from WebSocket data
   */
  private extractAnalysisSummary(summaryData: any): AnalysisSummary {
    return {
      equipmentType: summaryData.equipmentType || 'Unknown',
      operatingModes: summaryData.operatingModes || [],
      schedules: summaryData.schedules || [],
      alarms: summaryData.alarms || [],
      ioPoints: summaryData.ioPoints || [],
      controlBlocks: summaryData.controlBlocks || [],
      pseudoCode: summaryData.pseudoCode || ''
    };
  }

  /**
   * Emit event to all subscribers
   */
  private emitEvent(type: string, data: any): void {
    this.handlers.forEach(handler => {
      try {
        handler({ type: type as any, data });
      } catch (error) {
        console.error('[ChatPipeline] Event handler error:', error);
      }
    });
  }

  /**
   * Get API URL from runtime config or environment
   */
  private getApiUrl(): string {
    const runtimeConfig = (window as any).RUNTIME_CONFIG;
    return runtimeConfig?.API_URL || process.env.REACT_APP_API_URL || 'http://localhost:8847';
  }
}

// Export singleton instance
export const chatPipelineService = new ChatPipelineService();
export default chatPipelineService;