import React, { useEffect } from 'react';
import ReactFlow, {
  Node,
  Edge,
  Controls,
  Background,
  MiniMap,
  useNodesState,
  useEdgesState,
  MarkerType,
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
import ProcessNodeNiagara from './Nodes/ProcessNodeNiagara';
import TextReviewNode from './Nodes/TextReviewNode';
import n8nWebhookService from '../services/n8nWebhookService';

// Import neubrutalism theme
import { TOKENS } from '../theme/neubrutalism';

const nodeTypes = {
  userMessage: UserNodeWithResend,
  systemMessage: SystemNodeNiagara,
  analysisMessage: AnalysisGridNode,
  processMessage: ProcessNodeNiagara,
  textReview: TextReviewNode,
};

export interface ChatMessage {
  id: string;
  type: 'user' | 'assistant' | 'system';
  messageType?: 'status' | 'analysis' | 'artifact' | 'user' | 'processing' | 'error';
  content: string;
  timestamp: Date;
  sessionId?: string;
  files?: File[];
  status?: 'sending' | 'sent' | 'failed';
  persisted?: boolean;
  metadata?: {
    analysisData?: any;
    downloadUrl?: string;
    fileName?: string;
    file_id?: string; // DB identifier for uploaded file
    previewUrl?: string; // server-provided preview URL (e.g., extracted text/image)
    bogFilePath?: string;
    status?: 'processing' | 'complete' | 'error' | 'awaiting_approval';
    processStep?: {
      stepKey: string;
      detail?: string;
      status: 'running' | 'ok' | 'error' | 'waiting';
      metrics?: Record<string, any>;
    };
    // Text review fields
    extractedText?: string;
    textQuality?: string;
    qualityScore?: number;
    qualityIssues?: string[];
    recommendations?: string[];
    hvacTermsFound?: number;
    // Analysis review fields
    analysisQuality?: string;
    summary?: any;
    actions?: any;
    progress?: {
      percentage: number;
      phase: string;
      description: string;
      eta: string;
    };
    resumeUrl?: string;
    workflowState?: {
      state: 'idle' | 'analyzing' | 'awaiting_approval' | 'generating' | 'complete';
      resumeUrl?: string;
      waitingData?: any;
    };
  };
}

interface ChatCanvasProps {
  messages: ChatMessage[];
  onApproveAnalysis: () => void;
  onRequestChanges: (feedback: string) => void;
  onResendMessage?: (message: ChatMessage) => void;
  workflowState?: 'idle' | 'analyzing' | 'awaiting_approval' | 'generating' | 'complete';
  sessionId: string;
  focusMessageId?: string;
}

// Grid layout configuration
const GRID_CONFIG = {
  NODE_WIDTH: 320,
  NODE_HEIGHT: 140,
  HORIZONTAL_GAP: 80,
  VERTICAL_GAP: 80,
  PADDING: 60,
  MAX_NODES_PER_ROW: 4,
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
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const { fitView, setCenter } = useReactFlow();

  useEffect(() => {
    console.log('[ChatCanvasGrid] Rendering with messages:', messages?.length || 0, messages);
    if (!messages || messages.length === 0) {
      console.log('[ChatCanvasGrid] No messages to display');
      return;
    }

    const flowNodes: Node[] = [];
    const flowEdges: Edge[] = [];

    // Calculate grid layout
    const calculatePosition = (index: number) => {
      const col = index % GRID_CONFIG.MAX_NODES_PER_ROW;
      const row = Math.floor(index / GRID_CONFIG.MAX_NODES_PER_ROW);
      
      const x = GRID_CONFIG.PADDING + col * (GRID_CONFIG.NODE_WIDTH + GRID_CONFIG.HORIZONTAL_GAP);
      const y = GRID_CONFIG.PADDING + row * (GRID_CONFIG.NODE_HEIGHT + GRID_CONFIG.VERTICAL_GAP);
      
      return { x, y };
    };

    // Precompute last user message index for optional resend affordance
    const lastUserIndex = (() => {
      let i = -1;
      for (let k = 0; k < messages.length; k++) if (messages[k].type === 'user') i = k;
      return i;
    })();

    // Create nodes
    messages.forEach((message, index) => {
      const position = calculatePosition(index);
      const isUser = message.type === 'user';
      const isProcess = message.metadata?.processStep !== undefined;
      const isAnalysis = message.metadata?.analysisData;
      
      const hasExtracted = Boolean(message.metadata?.extractedText || (message as any)?.metadata?.data?.extractedText || (message as any)?.metadata?.data?.fullText);
      const hasResume = Boolean(message.metadata?.resumeUrl || message.metadata?.workflowState?.resumeUrl);
      const isTextReview = hasExtracted && hasResume;

      let nodeType = 'systemMessage';
      if (isUser) nodeType = 'userMessage';
      else if (isProcess) nodeType = 'processMessage';
      else if (isTextReview) nodeType = 'textReview';
      else if (isAnalysis) nodeType = 'analysisMessage';

      const node: Node = {
        id: message.id,
        type: nodeType,
        position,
        data: (
          nodeType === 'textReview'
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
                  const url = (message as any)?.metadata?.resumeUrl || (message as any)?.metadata?.workflowState?.resumeUrl;
                  if (!url) return;
                  await n8nWebhookService.approveTextExtraction(sessionId, approvedText, url);
                },
                onEdit: async (editedText: string) => {
                  const url = (message as any)?.metadata?.resumeUrl || (message as any)?.metadata?.workflowState?.resumeUrl;
                  if (!url) return;
                  await n8nWebhookService.editExtractedText(sessionId, editedText, url);
                },
                onRetry: async () => {
                  const url = (message as any)?.metadata?.resumeUrl || (message as any)?.metadata?.workflowState?.resumeUrl;
                  if (!url) return;
                  await n8nWebhookService.retryExtraction(sessionId, url);
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
                onResend: isUser && onResendMessage && (message.status === 'failed' || index === lastUserIndex)
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
          width: GRID_CONFIG.NODE_WIDTH,
          border: nodeType === 'textReview' ? `2px solid ${TOKENS.warning}` : undefined,
        },
        sourcePosition: Position.Right,
        targetPosition: Position.Left,
      };

      flowNodes.push(node);

      // Create edges
      if (index > 0) {
        const sourceNode = flowNodes[index - 1];
        const targetNode = node;
        
        // Determine if nodes are on same row
        const sourceRow = Math.floor((index - 1) / GRID_CONFIG.MAX_NODES_PER_ROW);
        const targetRow = Math.floor(index / GRID_CONFIG.MAX_NODES_PER_ROW);
        // const sourceCol = (index - 1) % GRID_CONFIG.MAX_NODES_PER_ROW;
        // const targetCol = index % GRID_CONFIG.MAX_NODES_PER_ROW;
        
        // let edgeType: ConnectionLineType = ConnectionLineType.SmoothStep;
        
        // If wrapping to next row
        // if (targetRow > sourceRow) {
        //   edgeType = ConnectionLineType.Step;
        // }
        
        const targetStatus = message.metadata?.status || message.metadata?.workflowState?.state;
        const statusStr = String(targetStatus || '');
        const awaitingStatuses = ['awaiting_approval', 'awaiting_confirmation'];
        const isAwaiting = awaitingStatuses.includes(statusStr);
        const isError = statusStr === 'error';
        const edgeColor = isError ? TOKENS.error : (isAwaiting ? TOKENS.warning : TOKENS.border);
        const dash = (workflowState === 'analyzing' && index === messages.length - 1) || isAwaiting ? '8 6' : undefined;

        const edge: Edge = {
          id: `e-${sourceNode.id}-${targetNode.id}`,
          source: sourceNode.id,
          target: targetNode.id,
          type: 'smoothstep',
          animated: workflowState === 'analyzing' && index === messages.length - 1 && !isError,
          style: {
            stroke: edgeColor,
            strokeWidth: 2,
            strokeDasharray: dash,
          },
          markerEnd: {
            type: MarkerType.ArrowClosed,
            color: edgeColor,
            width: 20,
            height: 20,
          },
          pathOptions: {
            offset: targetRow > sourceRow ? 40 : 0,
          },
        };

        flowEdges.push(edge);
      }
    });

    setNodes(flowNodes);
    setEdges(flowEdges);

    // Auto-fit view with delay
    setTimeout(() => {
      fitView({ padding: 0.1, maxZoom: 1.2 });
    }, 50);
  }, [messages, workflowState, sessionId, onApproveAnalysis, onRequestChanges, onResendMessage, setNodes, setEdges, fitView]);

  // Focus on specific message
  useEffect(() => {
    if (!focusMessageId) return;
    const node = nodes.find((n) => n.id === focusMessageId);
    if (node) {
      setCenter(node.position.x + GRID_CONFIG.NODE_WIDTH / 2, node.position.y + GRID_CONFIG.NODE_HEIGHT / 2, {
        zoom: 1.2,
        duration: 500,
      });
    }
  }, [focusMessageId, nodes, setCenter]);

  return (
    <ReactFlow
      nodes={nodes}
      edges={edges}
      onNodesChange={onNodesChange}
      onEdgesChange={onEdgesChange}
      nodeTypes={nodeTypes}
      fitView
      fitViewOptions={{ padding: 0.15, maxZoom: 1.3 }}
      defaultViewport={{ x: 0, y: 0, zoom: 1 }}
      minZoom={0.2}
      maxZoom={2}
      nodesDraggable={false}
      nodesConnectable={false}
      elementsSelectable={true}
      connectionLineType={ConnectionLineType.SmoothStep}
    >
      <Background 
        color={TOKENS.grid}
        gap={16} 
        variant={BackgroundVariant.Lines} 
        size={1}
        style={{ backgroundColor: TOKENS.bg }}
      />
      <Controls 
        showZoom
        showFitView
        showInteractive={false}
        style={{
          background: TOKENS.white,
          border: `2px solid ${TOKENS.border}`,
          borderRadius: '8px',
        }}
      />
      <MiniMap 
        style={{
          background: TOKENS.white,
          border: `2px solid ${TOKENS.border}`,
          borderRadius: '8px',
        }}
        nodeColor={(n) => {
          if (n.type === 'userMessage') return TOKENS.userHeader;
          if (n.type === 'processMessage') return TOKENS.processHeader;
          if (n.type === 'analysisMessage') return TOKENS.ok;
          return TOKENS.systemHeader;
        }}
        maskColor="rgba(247, 248, 250, 0.8)"
      />
    </ReactFlow>
  );
}

const ChatCanvasGrid: React.FC<ChatCanvasProps> = (props) => {
  return (
    <div style={{ width: '100%', height: '100%', position: 'relative', background: TOKENS.bg }}>
      <ReactFlowProvider>
        <ChatCanvasGridContent {...props} />
      </ReactFlowProvider>
    </div>
  );
};

export default ChatCanvasGrid;
