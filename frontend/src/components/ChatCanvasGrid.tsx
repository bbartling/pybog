import React, { useEffect, useMemo } from 'react';
import ReactFlow, {
  Node,
  Edge,
  Controls,
  Background,
  MiniMap,
  useNodesState,
  useEdgesState,
  Position,
  BackgroundVariant,
  useReactFlow,
  ReactFlowProvider,
  ConnectionLineType,
} from 'reactflow';
import 'reactflow/dist/style.css';

// Import our styled nodes - use neubrutalism if available, fallback to originals
import UserNodeWithResend from './Nodes/UserNodeWithResend';
import SystemNodeNiagara from './Nodes/SystemNodeNiagara';
import AnalysisGridNode from './Nodes/AnalysisGridNode';
import AnalysisReviewNode from './Nodes/AnalysisReviewNode';
import ProcessNodeNiagara from './Nodes/ProcessNodeNiagara';
import TextReviewNode from './Nodes/TextReviewNode';
import ProgressNode from './Nodes/ProgressNode';
import { unifiedAPIService } from '../services/UnifiedAPIService';

// Import neubrutalism theme
import { TOKENS } from '../theme/neubrutalism';
import { ChatMessage } from '../types/ChatMessage';

// Import layout engine and edge styling
import { NodeLayoutEngine, DEFAULT_LAYOUT_CONFIG, LayoutConfig } from '../utils/nodeLayoutEngine';
import { EdgeStyleEngine, createStyledEdge } from '../utils/edgeStyleEngine';
import { useResponsiveLayout } from '../hooks/useResponsiveLayout';
// import { useRenderTracker } from '../utils/performanceMonitor';

const nodeTypes = {
  userMessage: UserNodeWithResend,
  systemMessage: SystemNodeNiagara,
  analysisMessage: AnalysisGridNode,
  analysisReview: AnalysisReviewNode,
  processMessage: ProcessNodeNiagara,
  textReview: TextReviewNode,
  progressMessage: ProgressNode,
};

interface ChatCanvasProps {
  messages: ChatMessage[];
  onApproveAnalysis: () => void;
  onRequestChanges: (feedback: string) => void;
  onResendMessage?: (message: ChatMessage) => void;
  workflowState?: 'idle' | 'analyzing' | 'awaiting_approval' | 'generating' | 'complete' | 'awaiting_analysis_review';
  sessionId: string;
  focusMessageId?: string;
}

// Professional layout configuration - restored original settings
const ENHANCED_LAYOUT_CONFIG: LayoutConfig = {
  ...DEFAULT_LAYOUT_CONFIG,
  maxNodesPerRow: 3,
  horizontalGap: 120,
  verticalGap: 100,
  padding: 80,
  adaptiveRowHeight: false, // Disable for consistent professional layout
};

function ChatCanvasGridContent({
  messages,
  onApproveAnalysis,
  onRequestChanges,
  onResendMessage,
  workflowState,
  sessionId,
  focusMessageId,
}: ChatCanvasProps) {
  // Performance monitoring disabled to prevent render loops
  // useRenderTracker('ChatCanvasGridContent', { 
  //   messageCount: messages?.length, 
  //   workflowState, 
  //   sessionId 
  // });

  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const { fitView, setCenter } = useReactFlow();

  // Use static layout configuration to prevent re-renders
  // const { layoutConfig } = useResponsiveLayout({
  //   ...ENHANCED_LAYOUT_CONFIG,
  //   adaptiveRowHeight: false, // Consistent professional layout
  // });

  // Use a stable layout engine instance
  const layoutEngine = useMemo(() => {
    return new NodeLayoutEngine(ENHANCED_LAYOUT_CONFIG);
  }, []); // No dependencies - use static config

  // Memoize node data preparation for layout calculation - remove callback dependencies
  const nodeLayoutData = useMemo(() => {
    if (!messages || messages.length === 0) return [];

    return messages.map((message, index) => {
      const isUser = message.type === 'user';
      const isProcess = message.metadata?.processStep !== undefined;
      const isAnalysis = message.metadata?.analysisData;
      const isProgress = message.messageType === 'progress' || message.metadata?.progressState;
      
      const hasExtracted = Boolean(message.metadata?.extractedText || (message as any)?.metadata?.data?.extractedText || (message as any)?.metadata?.data?.fullText);
      const hasResume = Boolean(message.metadata?.resumeUrl || message.metadata?.workflowState?.resumeUrl);
      const isTextReview = hasExtracted && hasResume;
      const isAnalysisReview = message.metadata?.workflowState?.state === 'awaiting_analysis_review' || 
                              message.metadata?.status === 'awaiting_analysis_review' ||
                              message.messageType === 'analysis_review';

      let nodeType = 'systemMessage';
      if (isUser) nodeType = 'userMessage';
      else if (isProgress) nodeType = 'progressMessage';
      else if (isProcess) nodeType = 'processMessage';
      else if (isTextReview) nodeType = 'textReview';
      else if (isAnalysisReview) nodeType = 'analysisReview';
      else if (isAnalysis) nodeType = 'analysisMessage';

      // Determine node features for layout calculation - check for callback existence without depending on them
      const hasActions = Boolean(
        isAnalysis ||
        message.metadata?.actions ||
        (isUser && (message.status === 'failed' || index === messages.length - 1))
      );
      const hasProgressBar = isProgress && message.metadata?.progressPercent !== undefined;
      const hasFiles = Boolean(message.files && message.files.length > 0);

      return {
        id: message.id,
        type: nodeType,
        content: message.content || '',
        hasActions,
        hasProgress: hasProgressBar,
        hasFiles,
        priority: isUser ? 1 : isAnalysis ? 3 : isProgress ? 2 : 0, // Priority for better positioning
        originalMessage: message,
        index
      };
    });
  }, [messages]); // Only depend on messages, not callbacks

  // Calculate optimal layout using the layout engine
  const layoutNodes = useMemo(() => {
    if (nodeLayoutData.length === 0) return [];
    return layoutEngine.layoutNodes(nodeLayoutData);
  }, [nodeLayoutData]); // Remove layoutEngine dependency

  // Simple grid layout to prevent render loops
  const { flowNodes, flowEdges } = useMemo(() => {
    if (!messages || messages.length === 0) {
      return { flowNodes: [], flowEdges: [] };
    }

    const flowNodes: Node[] = [];
    const flowEdges: Edge[] = [];

    // Simple grid layout - 3 columns, consistent spacing
    const nodeWidth = 320;
    const nodeHeight = 160;
    const horizontalGap = 120;
    const verticalGap = 100;
    const padding = 80;
    const maxNodesPerRow = 3;

    // Create nodes with simple grid positioning
    messages.forEach((message, index) => {
      const isUser = message.type === 'user';
      const isProcess = message.metadata?.processStep !== undefined;
      const isAnalysis = message.metadata?.analysisData;
      const isProgress = message.messageType === 'progress' || message.metadata?.progressState;
      
      // Determine node type
      let nodeType = 'systemMessage';
      if (isUser) nodeType = 'userMessage';
      else if (isProgress) nodeType = 'progressMessage';
      else if (isProcess) nodeType = 'processMessage';
      else if (isAnalysis) nodeType = 'analysisMessage';

      // Simple grid positioning
      const row = Math.floor(index / maxNodesPerRow);
      const col = index % maxNodesPerRow;
      const x = padding + col * (nodeWidth + horizontalGap);
      const y = padding + row * (nodeHeight + verticalGap);

      const node: Node = {
        id: message.id,
        type: nodeType,
        position: { x, y },
        data: (
          nodeType === 'progressMessage'
            ? {
                content: message.content,
                timestamp: message.timestamp,
                sessionId,
                progressState: message.metadata?.progressState || 'queued',
                progressPercent: message.metadata?.progressPercent,
                progressMessage: message.metadata?.progressMessage,
                operation: message.metadata?.operation,
                analysis_id: message.metadata?.analysis_id,
                file_id: message.metadata?.file_id,
                onCancel: message.metadata?.analysis_id ? async () => {
                  try {
                    await unifiedAPIService.cancelAnalysis(sessionId, message.metadata?.analysis_id);
                  } catch (error) {
                    console.error('Failed to cancel analysis:', error);
                  }
                } : undefined,
              }
            : nodeType === 'analysisReview'
            ? {
                sessionId,
                analysisId: message.metadata?.analysis_id || 1,
                qualityScore: message.metadata?.qualityScore || message.metadata?.analysisData?.quality_score || 0.8,
                completenessScore: message.metadata?.completenessScore || 0.85,
                ioPointsCount: message.metadata?.analysisData?.io_points?.length || 0,
                controlBlocksCount: message.metadata?.analysisData?.control_blocks?.length || 0,
                pseudocodeStepsCount: message.metadata?.analysisData?.pseudocode?.length || 0,
                issues: message.metadata?.analysisData?.issues || [],
                recommendations: message.metadata?.analysisData?.metadata?.recommendations || [],
                confidenceLevel: message.metadata?.analysisData?.metadata?.confidence || 0.8,
                analysisData: message.metadata?.analysisData || {
                  io_points: [],
                  control_blocks: [],
                  pseudocode: [],
                  metadata: { document_type: 'unknown', confidence: 0.8, recommendations: [] }
                },
                onApprove: async () => {
                  try {
                    await fetch(`${process.env.REACT_APP_API_URL || 'http://localhost:8847'}/api/workflow/review/${sessionId}`, {
                      method: 'POST',
                      headers: { 'Content-Type': 'application/json' },
                      body: JSON.stringify({
                        review_id: message.metadata?.review_id || `analysis_review_${message.id}`,
                        decision: 'approve'
                      })
                    });
                  } catch (error) {
                    console.error('Failed to approve analysis:', error);
                  }
                },
                onRequestChanges: async (feedback: string) => {
                  try {
                    await fetch(`${process.env.REACT_APP_API_URL || 'http://localhost:8847'}/api/workflow/review/${sessionId}`, {
                      method: 'POST',
                      headers: { 'Content-Type': 'application/json' },
                      body: JSON.stringify({
                        review_id: message.metadata?.review_id || `analysis_review_${message.id}`,
                        decision: 'request_changes',
                        feedback
                      })
                    });
                  } catch (error) {
                    console.error('Failed to request changes:', error);
                  }
                },
                onRetry: async () => {
                  try {
                    await fetch(`${process.env.REACT_APP_API_URL || 'http://localhost:8847'}/api/workflow/review/${sessionId}`, {
                      method: 'POST',
                      headers: { 'Content-Type': 'application/json' },
                      body: JSON.stringify({
                        review_id: message.metadata?.review_id || `analysis_review_${message.id}`,
                        decision: 'retry'
                      })
                    });
                  } catch (error) {
                    console.error('Failed to retry analysis:', error);
                  }
                }
              }
            : nodeType === 'textReview'
            ? {
                sessionId,
                extractedText:
                  (message as any)?.metadata?.data?.fullText ||
                  (message as any)?.metadata?.data?.extractedText ||
                  message.metadata?.extractedText || '',
                fileCount: (message as any)?.metadata?.fileCount || 1,
                totalCharacters:
                  (message as any)?.metadata?.totalCharacters ||
                  ((message as any)?.metadata?.data?.fullText?.length || (message as any)?.metadata?.data?.extractedText?.length || message.metadata?.extractedText?.length || 0),
                textQuality: (message as any)?.metadata?.textQuality || 'good',
                qualityScore: (message as any)?.metadata?.qualityScore || 100,
                qualityIssues: (message as any)?.metadata?.qualityIssues || [],
                recommendations: (message as any)?.metadata?.recommendations || [],
                hvacTermsFound: (message as any)?.metadata?.hvacTermsFound || 0,
                currentStep: (message as any)?.metadata?.currentStep,
                totalSteps: (message as any)?.metadata?.totalSteps,
                progress: (message as any)?.metadata?.progress,
                actions: (message as any)?.metadata?.actions,
                onApprove: async (approvedText: string) => {
                  try {
                    await unifiedAPIService.submitReview(
                      sessionId,
                      message.metadata?.review_id || `text_review_${message.id}`,
                      'approve',
                      undefined,
                      { approved_text: approvedText }
                    );
                  } catch (error) {
                    console.error('Failed to approve text:', error);
                  }
                },
                onEdit: async (editedText: string) => {
                  try {
                    await unifiedAPIService.submitReview(
                      sessionId,
                      message.metadata?.review_id || `text_review_${message.id}`,
                      'approve',
                      'Text edited by user',
                      { approved_text: editedText }
                    );
                  } catch (error) {
                    console.error('Failed to submit edited text:', error);
                  }
                },
                onRetry: async () => {
                  try {
                    await unifiedAPIService.submitReview(
                      sessionId,
                      message.metadata?.review_id || `text_review_${message.id}`,
                      'retry'
                    );
                  } catch (error) {
                    console.error('Failed to retry extraction:', error);
                  }
                },
              }
            : {
                content: message.content,
                timestamp: message.timestamp,
                files: message.files,
                sessionId: sessionId,
                status: message.status,
                analysis: message.metadata?.analysisData,
                onApprove: isAnalysis ? onApproveAnalysis : undefined,
                onRequestChanges: isAnalysis ? onRequestChanges : undefined,
                // Resend is offered if message is failed OR it's the latest user message (quick retry)
                onResend: isUser && onResendMessage && (message.status === 'failed' || index === messages.length - 1)
                  ? () => onResendMessage(message) : undefined,
                stepKey: message.metadata?.processStep?.stepKey,
                title: isProcess ? message.content : undefined,
                detail: message.metadata?.processStep?.detail,
                processStatus: message.metadata?.processStep?.status,
                metrics: message.metadata?.processStep?.metrics,
                // Option B: pass action set and resume URL for system nodes
                actions: message.metadata?.actions,
                resumeUrl: message.metadata?.workflowState?.resumeUrl || message.metadata?.resumeUrl,
                workflowStatus: message.metadata?.status || message.metadata?.workflowState?.state,
              }
        ),
        style: {
          width: nodeWidth,
          height: nodeHeight,
        },
        sourcePosition: Position.Right,
        targetPosition: Position.Left,
      };

      flowNodes.push(node);

      // Create simple edges
      if (index > 0) {
        const sourceNode = flowNodes[index - 1];
        const edge: Edge = {
          id: `e-${sourceNode.id}-${node.id}`,
          source: sourceNode.id,
          target: node.id,
          type: ConnectionLineType.Step,
          animated: false,
          style: { stroke: '#666', strokeWidth: 2 },
        };
        flowEdges.push(edge);
      }
    });

    return { flowNodes, flowEdges };
  }, [messages, sessionId, onApproveAnalysis, onRequestChanges, onResendMessage]);

  // Separate effect for setting nodes/edges to prevent render loops
  useEffect(() => {
    setNodes(flowNodes);
    setEdges(flowEdges);
  }, [flowNodes, flowEdges, setNodes, setEdges]);

  // Separate effect for viewport fitting
  useEffect(() => {
    if (flowNodes.length > 0) {
      const timeoutId = setTimeout(() => {
        fitView({ 
          padding: 0.1,
          maxZoom: 1.0,
          minZoom: 0.4,
          duration: 200
        });
      }, 50);
      return () => clearTimeout(timeoutId);
    }
  }, [flowNodes.length, fitView]);

  // Focus on specific message with dynamic node dimensions
  useEffect(() => {
    if (!focusMessageId) return;
    const node = nodes.find((n) => n.id === focusMessageId);
    const layoutNode = layoutNodes.find((n) => n.id === focusMessageId);
    if (node && layoutNode) {
      setCenter(
        node.position.x + layoutNode.dimensions.width / 2, 
        node.position.y + layoutNode.dimensions.height / 2, 
        {
          zoom: 1.2,
          duration: 500,
        }
      );
    }
  }, [focusMessageId, nodes, layoutNodes, setCenter]);

  return (
    <ReactFlow
      nodes={nodes}
      edges={edges}
      onNodesChange={onNodesChange}
      onEdgesChange={onEdgesChange}
      nodeTypes={nodeTypes}
      fitView
      fitViewOptions={{ padding: 0.1, maxZoom: 1.0 }}
      defaultViewport={{ x: 0, y: 0, zoom: 0.9 }}
      minZoom={0.3}
      maxZoom={1.5}
      nodesDraggable={false}
      nodesConnectable={false}
      elementsSelectable={true}
      connectionLineType={ConnectionLineType.SmoothStep}
      panOnScroll={true}
      panOnScrollSpeed={0.5}
      zoomOnScroll={true}
      zoomOnPinch={true}
      preventScrolling={false}
      attributionPosition="bottom-left"
    >
      <Background 
        color={TOKENS.grid}
        gap={20} 
        variant={BackgroundVariant.Lines} 
        size={1}
        style={{ 
          backgroundColor: TOKENS.bg,
          opacity: 0.6 
        }}
      />
      <Controls 
        showZoom
        showFitView
        showInteractive={false}
        position="top-right"
        style={{
          background: TOKENS.white,
          border: `3px solid ${TOKENS.border}`,
          borderRadius: '12px',
          boxShadow: '4px 4px 0px rgba(0,0,0,0.1)',
        }}
      />
      <MiniMap 
        position="bottom-right"
        style={{
          background: TOKENS.white,
          border: `3px solid ${TOKENS.border}`,
          borderRadius: '12px',
          boxShadow: '4px 4px 0px rgba(0,0,0,0.1)',
          width: 200,
          height: 150,
        }}
        nodeColor={(n) => {
          if (n.type === 'userMessage') return TOKENS.userHeader;
          if (n.type === 'processMessage') return TOKENS.processHeader;
          if (n.type === 'analysisMessage') return TOKENS.success;
          if (n.type === 'progressMessage') return TOKENS.primary;
          if (n.type === 'textReview') return TOKENS.warning;
          if (n.type === 'analysisReview') return TOKENS.info;
          return TOKENS.systemHeader;
        }}
        nodeStrokeColor={TOKENS.border}
        nodeStrokeWidth={2}
        maskColor="rgba(247, 248, 250, 0.7)"
        pannable={true}
        zoomable={true}
      />
    </ReactFlow>
  );
}

const ChatCanvasGrid: React.FC<ChatCanvasProps> = (props) => {
  // Inject edge animation CSS
  React.useEffect(() => {
    const styleId = 'chat-canvas-edge-animations';
    if (!document.getElementById(styleId)) {
      const style = document.createElement('style');
      style.id = styleId;
      style.textContent = EdgeStyleEngine.getEdgeAnimationCSS();
      document.head.appendChild(style);
    }
  }, []);

  return (
    <div style={{ width: '100%', height: '100%', position: 'relative', background: TOKENS.bg }}>
      <ReactFlowProvider>
        <ChatCanvasGridContent {...props} />
      </ReactFlowProvider>
    </div>
  );
};

export default ChatCanvasGrid;
