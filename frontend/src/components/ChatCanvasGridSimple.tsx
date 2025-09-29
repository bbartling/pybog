import React, { useEffect, useMemo, useCallback } from 'react';
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

// Import our styled nodes
import UserNodeWithResend from './Nodes/UserNodeWithResend';
import SystemNodeNiagara from './Nodes/SystemNodeNiagara';
import AnalysisGridNode from './Nodes/AnalysisGridNode';
import ProcessNodeNiagara from './Nodes/ProcessNodeNiagara';
import ProgressNode from './Nodes/ProgressNode';
import AnalysisSummaryCard from './Nodes/AnalysisSummaryCard';
import ResultFilesCard from './Nodes/ResultFilesCard';
import AnalysisProgressCard from './Nodes/AnalysisProgressCard';
import BOGProgressNode from './Nodes/BOGProgressNode';
import BOGDownloadNode from './Nodes/BOGDownloadNode';
import AnalysisReviewNode from './Nodes/AnalysisReviewNode';
import TextReviewNode from './Nodes/TextReviewNode';

// Import theme
import { TOKENS } from '../theme/neubrutalism';
import { ChatMessage } from '../types/ChatMessage';

const nodeTypes = {
  userMessage: UserNodeWithResend,
  systemMessage: SystemNodeNiagara,
  analysisMessage: AnalysisGridNode,
  processMessage: ProcessNodeNiagara,
  progressMessage: ProgressNode,
  analysisSummary: AnalysisSummaryCard,
  resultFiles: ResultFilesCard,
  analysisProgress: AnalysisProgressCard,
  analysisReview: AnalysisReviewNode,
  bogProgress: BOGProgressNode,
  bogDownload: BOGDownloadNode,
  textReview: TextReviewNode,
};

interface ChatCanvasProps {
  messages: ChatMessage[];
  onApproveAnalysis: () => void;
  onRequestChanges: (feedback: string) => void;
  onApproveBOGGeneration?: (analysisData: any) => void;
  onRequestAnalysisChanges?: (feedback: string) => void;
  onViewAnalysisDetails?: (analysisData: any) => void;
  onResendMessage?: (message: ChatMessage) => void;

  // Text approval workflow callbacks
  onApproveText?: (approvedText: string) => void;
  onRequestTextChanges?: (feedback: string) => void;
  onViewTextDetails?: (text: string) => void;

  workflowState?: string;
  sessionId: string;
  focusMessageId?: string;
}

function ChatCanvasGridSimpleContent({
  messages,
  onApproveAnalysis,
  onRequestChanges,
  onApproveBOGGeneration,
  onRequestAnalysisChanges,
  onViewAnalysisDetails,
  onResendMessage,
  onApproveText,
  onRequestTextChanges,
  onViewTextDetails,
  workflowState,
  sessionId,
  focusMessageId,
}: ChatCanvasProps) {
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const { fitView } = useReactFlow();

  // Create stable callback references to prevent node recreation
  const handleResendMessage = useCallback((message: ChatMessage) => {
    if (onResendMessage) {
      onResendMessage(message);
    }
  }, [onResendMessage]);

  const handleExpand = useCallback((messageId: string) => {
    console.log('Expand details for:', messageId);
    // Could trigger a modal or detailed view here
  }, []);

  // BOG Generation workflow callbacks
  const handleApproveBOG = useCallback((analysisData: any) => {
    if (onApproveBOGGeneration) {
      onApproveBOGGeneration(analysisData);
    }
  }, [onApproveBOGGeneration]);

  const handleRequestAnalysisChanges = useCallback((feedback: string) => {
    if (onRequestAnalysisChanges) {
      onRequestAnalysisChanges(feedback);
    }
  }, [onRequestAnalysisChanges]);

  const handleViewAnalysisDetails = useCallback((analysisData: any) => {
    if (onViewAnalysisDetails) {
      onViewAnalysisDetails(analysisData);
    }
  }, [onViewAnalysisDetails]);

  // Handle node clicks for focus management
  const handleNodeClick = useCallback((event: any, node: Node) => {
    console.log('[ChatCanvas] Node clicked:', node.id);
    // Could set focus or trigger navigation
  }, []);

  // Handle node double-click for actions
  const handleNodeDoubleClick = useCallback((event: any, node: Node) => {
    console.log('[ChatCanvas] Node double-clicked:', node.id);
    handleExpand(node.id);
  }, [handleExpand]);

  // Create a stable callback map for onResend to prevent node recreation
  const resendCallbackMap = useMemo(() => {
    const map = new Map<string, () => void>();
    messages.forEach(message => {
      if (message.type === 'user' && message.status === 'failed' && typeof message.id === 'string') {
        map.set(message.id, () => handleResendMessage(message));
      }
    });
    return map;
  }, [messages, handleResendMessage]);

  // Conversational flow layout calculation
  const { flowNodes, flowEdges } = useMemo(() => {
    if (!messages || messages.length === 0) {
      return { flowNodes: [], flowEdges: [] };
    }

    const flowNodes: Node[] = [];
    const flowEdges: Edge[] = [];

    // Fixed conversation flow layout settings
    const nodeWidth = 340; // Standardized width
    const nodeHeight = 180; // Standardized height
    const horizontalGap = 100; // Clear horizontal spacing
    const verticalGap = 200; // Generous vertical gap between rows
    const padding = 60; // Standard padding from edges
    const maxNodesPerRow = 4; // Fixed at 4 nodes per row for consistency

    messages.forEach((message, index) => {
      const isUser = message.type === 'user';
      const isAssistant = message.type === 'assistant';
      const isSystem = message.type === 'system';
      const isAnalysis = message.metadata?.analysisData;
      const isProgress = message.messageType === 'progress' || message.messageType === 'status';
      const isProcess = message.messageType === 'processing';
      const isStreaming = typeof message.id === 'string' && message.id.startsWith('streaming-assistant-');

      // Enhanced node type determination with better fallbacks
      let nodeType = 'systemMessage'; // Default fallback

      if (isUser) {
        nodeType = 'userMessage';
      } else if (isProgress || isProcess) {
        nodeType = 'progressMessage';
      } else if (message.messageType === 'analysis_review') {
        nodeType = 'analysisReview';
      } else if (message.messageType === 'analysis_summary') {
        nodeType = 'analysisSummary';
      } else if (message.messageType === 'result_files') {
        nodeType = 'resultFiles';
      } else if (message.messageType === 'analysis_progress') {
        nodeType = 'analysisProgress';
      } else if (message.messageType === 'bog_progress') {
        nodeType = 'bogProgress';
      } else if (message.messageType === 'bog_download') {
        nodeType = 'bogDownload';
      } else if (message.messageType === 'text_review') {
        nodeType = 'textReview';
      } else if (isAnalysis) {
        nodeType = 'analysisMessage';
      } else if (isStreaming || isAssistant) {
        // Use system message for streaming/assistant responses
        nodeType = 'systemMessage';
      } else if (isSystem) {
        nodeType = 'systemMessage';
      }

      // Additional validation - ensure node type exists
      if (!nodeTypes[nodeType as keyof typeof nodeTypes]) {
        console.warn(`[ChatCanvas] Unknown node type: ${nodeType}, falling back to systemMessage`);
        nodeType = 'systemMessage';
      }

      // Conversational flow positioning
      const row = Math.floor(index / maxNodesPerRow);
      const col = index % maxNodesPerRow;

      // Calculate position for proper horizontal conversation flow
      const x = padding + col * (nodeWidth + horizontalGap);
      const y = padding + row * (nodeHeight + verticalGap);

      // Simplified positioning without offsets that break the flow
      // Add safety checks for NaN values
      const finalX = isNaN(x) ? padding : x;
      const finalY = isNaN(y) ? padding : y;

      const isFocused = focusMessageId === message.id;

      const node: Node = {
        id: typeof message.id === 'string' ? message.id : `message-${index}`,
        type: nodeType,
        position: { x: finalX, y: finalY },
        data: {
          // Core message data
          content: message.content,
          timestamp: message.timestamp,
          files: message.files,
          sessionId: sessionId,
          status: message.status,
          messageType: message.messageType,

          // Analysis-specific data
          analysis: message.metadata?.analysisData,
          summary: message.metadata?.summary,
          stage: message.metadata?.stage,

          // Progress/process-specific data
          progress: message.metadata?.progress,
          processStep: message.metadata?.processStep,
          message: message.metadata?.message,

          // Workflow actions - different callbacks for different node types
          onApprove: message.messageType === 'analysis_review'
            ? () => handleApproveBOG(message.metadata?.analysisData)
            : isAnalysis ? onApproveAnalysis : undefined,
          onRequestChanges: message.messageType === 'analysis_review'
            ? () => handleRequestAnalysisChanges('Request analysis refinement')
            : isAnalysis ? onRequestChanges : undefined,
          onViewDetails: message.messageType === 'analysis_review'
            ? () => handleViewAnalysisDetails(message.metadata?.analysisData)
            : undefined,

          // Text review workflow actions
          onApproveText: message.messageType === 'text_review' ? onApproveText : undefined,
          onRequestTextChanges: message.messageType === 'text_review' ? onRequestTextChanges : undefined,
          onViewTextDetails: message.messageType === 'text_review' ? onViewTextDetails : undefined,

          // Text review specific data
          extractedText: message.metadata?.extractedText,
          filename: message.metadata?.filename,
          file_id: message.metadata?.file_id,
          requiresApproval: message.metadata?.requiresApproval,
          onResend: typeof message.id === 'string' ? resendCallbackMap.get(message.id) : undefined,
          onExpand: typeof message.id === 'string' ? () => handleExpand(message.id) : undefined,

          // Additional metadata for node rendering
          isStreaming: isStreaming,
          isAnalysis: isAnalysis,
          isProgress: isProgress,
          isProcess: isProcess,
          isFocused: isFocused,
          metadata: message.metadata,
        },
        style: {
          width: nodeWidth,
          height: nodeHeight,
          ...(isFocused && {
            boxShadow: '0 0 0 3px #3b82f6',
            zIndex: 1000,
          }),
        },
        sourcePosition: Position.Right,
        targetPosition: Position.Left,
      };

      flowNodes.push(node);

      // Clean conversation flow edges
      if (index > 0) {
        const sourceNode = flowNodes[index - 1];
        const isLatestMessage = index === messages.length - 1;
        const isPreviousMessage = index === messages.length - 2;

        // Simplified edge styling
        let edgeColor = TOKENS.text;
        let edgeAnimation = false;
        let strokeDasharray = '0';
        let strokeWidth = 2;

        if (isLatestMessage) {
          edgeColor = TOKENS.primary;
          edgeAnimation = true;
          strokeDasharray = '8 4';
          strokeWidth = 3;
        } else if (isPreviousMessage) {
          edgeColor = TOKENS.success;
          strokeWidth = 2.5;
        } else {
          edgeColor = '#9ca3af'; // Gray-400
          strokeWidth = 2;
        }

        const edge: Edge = {
          id: `e-${sourceNode.id}-${node.id}`,
          source: sourceNode.id,
          target: node.id,
          type: ConnectionLineType.SmoothStep,
          animated: edgeAnimation,
          style: {
            stroke: edgeColor,
            strokeWidth: strokeWidth,
            strokeDasharray: strokeDasharray,
          },
          markerEnd: {
            type: 'arrow',
            width: 10,
            height: 10,
            color: edgeColor,
          },
          className: 'conversation-edge',
        };
        flowEdges.push(edge);
      }
    });

    return { flowNodes, flowEdges };
  }, [messages, sessionId, onApproveAnalysis, onRequestChanges, resendCallbackMap, handleExpand]);

  // Update nodes and edges with debug logging
  useEffect(() => {
    console.log('[ChatCanvas] Messages changed, updating React Flow nodes:', {
      messageCount: messages.length,
      nodeCount: flowNodes.length,
      sessionId,
      messageIds: messages.map(m => typeof m.id === 'string' ? m.id : 'invalid-id')
    });

    setNodes(flowNodes);
    setEdges(flowEdges);

    // Force a fitView after nodes update to ensure visibility
    setTimeout(() => {
      fitView({
        padding: 0.1,
        maxZoom: 1.0,
        duration: 100
      });
    }, 50);
  }, [flowNodes, flowEdges, setNodes, setEdges, fitView, messages.length, sessionId]);

  // Auto-fit view
  useEffect(() => {
    if (flowNodes.length > 0) {
      setTimeout(() => {
        fitView({ 
          padding: 0.1,
          maxZoom: 1.0,
          duration: 200
        });
      }, 100);
    }
  }, [flowNodes.length, fitView]);

  return (
    <div style={{ width: '100%', height: '100%', position: 'relative' }}>
      {/* CSS for interactive edges */}
      <style>{`
        .conversation-edge:hover {
          filter: brightness(1.3) !important;
          stroke-width: ${4}px !important;
        }

        .conversation-edge {
          cursor: pointer;
          transition: all 0.2s ease-in-out;
        }

        /* Animated dash movement for latest messages */
        @keyframes dashMove {
          0% { stroke-dashoffset: 0; }
          100% { stroke-dashoffset: 20; }
        }

        .react-flow__edge.react-flow__edge-smoothstep[data-animated="true"] {
          animation: dashMove 2s linear infinite;
        }
      `}</style>

      <ReactFlow
        key={`react-flow-${sessionId}-${messages.length}`}
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodeClick={handleNodeClick}
        onNodeDoubleClick={handleNodeDoubleClick}
        nodeTypes={nodeTypes}
        fitView
        fitViewOptions={{ padding: 0.05, maxZoom: 0.8, minZoom: 0.2 }}
        defaultViewport={{ x: 0, y: 0, zoom: 0.7 }}
        minZoom={0.2}
        maxZoom={1.2}
        nodesDraggable={true}
        nodesConnectable={false}
        elementsSelectable={true}
        selectNodesOnDrag={false}
        connectionLineType={ConnectionLineType.SmoothStep}
        panOnDrag={true}
        zoomOnScroll={true}
        zoomOnPinch={true}
      >
      <Background
        color={TOKENS.text}
        gap={24} // Larger grid for wiresheet feel
        variant={BackgroundVariant.Lines}
        size={1.5} // Slightly thicker grid lines
        style={{
          backgroundColor: TOKENS.bg,
          opacity: 0.15 // More subtle grid
        }}
      />
      <Controls
        showZoom
        showFitView
        showInteractive={false}
        position="top-right"
        style={{
          button: {
            backgroundColor: TOKENS.white,
            border: `2px solid ${TOKENS.text}`,
            borderRadius: '4px',
            color: TOKENS.text
          }
        }}
      />
      <MiniMap 
        position="bottom-right"
        style={{
          width: 200,
          height: 150,
        }}
        nodeColor={(n) => {
          if (n.type === 'userMessage') return '#007acc';
          if (n.type === 'analysisMessage') return '#28a745';
          if (n.type === 'progressMessage') return '#ffc107';
          return '#6c757d';
        }}
      />
    </ReactFlow>
    </div>
  );
}

const ChatCanvasGridSimple: React.FC<ChatCanvasProps> = (props) => {
  return (
    <div style={{ width: '100%', height: '100%', position: 'relative', background: TOKENS.bg }}>
      <ReactFlowProvider>
        <ChatCanvasGridSimpleContent {...props} />
      </ReactFlowProvider>
    </div>
  );
};

export default ChatCanvasGridSimple;