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

// Import our styled nodes
import UserNodeWithResend from './Nodes/UserNodeWithResend';
import SystemNodeNiagara from './Nodes/SystemNodeNiagara';
import AnalysisGridNode from './Nodes/AnalysisGridNode';
import ProcessNodeNiagara from './Nodes/ProcessNodeNiagara';

const nodeTypes = {
  userMessage: UserNodeWithResend,
  systemMessage: SystemNodeNiagara,
  analysisMessage: AnalysisGridNode,
  processMessage: ProcessNodeNiagara,
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
    if (!messages || messages.length === 0) return;

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

    // Create nodes
    messages.forEach((message, index) => {
      const position = calculatePosition(index);
      const isUser = message.type === 'user';
      const isProcess = message.metadata?.processStep !== undefined;
      const isAnalysis = message.metadata?.analysisData;
      
      let nodeType = 'systemMessage';
      if (isUser) nodeType = 'userMessage';
      else if (isProcess) nodeType = 'processMessage';
      else if (isAnalysis) nodeType = 'analysisMessage';

      const node: Node = {
        id: message.id,
        type: nodeType,
        position,
        data: {
          content: message.content,
          timestamp: message.timestamp,
          files: message.files,
          sessionId: sessionId,
          status: message.status,
          analysis: message.metadata?.analysisData,
          onApprove: isAnalysis ? onApproveAnalysis : undefined,
          onRequestChanges: isAnalysis ? onRequestChanges : undefined,
          onResend: isUser && message.status === 'failed' && onResendMessage ? 
            () => onResendMessage(message) : undefined,
          stepKey: message.metadata?.processStep?.stepKey,
          title: isProcess ? message.content : undefined,
          detail: message.metadata?.processStep?.detail,
          processStatus: message.metadata?.processStep?.status,
          metrics: message.metadata?.processStep?.metrics,
        },
        style: {
          width: GRID_CONFIG.NODE_WIDTH,
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
        
        const edge: Edge = {
          id: `e-${sourceNode.id}-${targetNode.id}`,
          source: sourceNode.id,
          target: targetNode.id,
          type: 'smoothstep',
          animated: workflowState === 'analyzing' && index === messages.length - 1,
          style: {
            stroke: isUser ? '#8b5cf6' : '#22d3ee',
            strokeWidth: 2,
          },
          markerEnd: {
            type: MarkerType.ArrowClosed,
            color: isUser ? '#8b5cf6' : '#22d3ee',
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
        color="#e5e7eb" 
        gap={20} 
        variant={BackgroundVariant.Lines} 
        size={1}
        style={{ backgroundColor: '#ffffff' }}
      />
      <Controls 
        showZoom
        showFitView
        showInteractive={false}
        style={{
          background: '#ffffff',
          border: '1px solid #e5e7eb',
          borderRadius: '8px',
        }}
      />
      <MiniMap 
        style={{
          background: '#ffffff',
          border: '1px solid #e5e7eb',
        }}
        nodeColor={(n) => {
          if (n.type === 'userMessage') return '#8b5cf6';
          if (n.type === 'processMessage') return '#22d3ee';
          if (n.type === 'analysisMessage') return '#10b981';
          return '#3b82f6';
        }}
        maskColor="rgba(255, 255, 255, 0.8)"
      />
    </ReactFlow>
  );
}

const ChatCanvasGrid: React.FC<ChatCanvasProps> = (props) => {
  return (
    <div style={{ width: '100%', height: '100%', position: 'relative', background: '#ffffff' }}>
      <ReactFlowProvider>
        <ChatCanvasGridContent {...props} />
      </ReactFlowProvider>
    </div>
  );
};

export default ChatCanvasGrid;
