import React, { useCallback, useEffect } from 'react';
import ReactFlow, {
  Node,
  Edge,
  Controls,
  Background,
  useNodesState,
  useEdgesState,
  addEdge,
  Connection,
  MarkerType,
  Position,
  BackgroundVariant,
  useReactFlow,
} from 'reactflow';
import 'reactflow/dist/style.css';

// Import our custom nodes
import UserNode from './Nodes/UserNode';
import StatusNode from './Nodes/StatusNode';
import AnalysisNode from './Nodes/AnalysisNode';
import ArtifactNode from './Nodes/ArtifactNode';

// Define node types for ReactFlow
const nodeTypes = {
  userMessage: UserNode,
  statusMessage: StatusNode,
  analysisMessage: AnalysisNode,
  artifactMessage: ArtifactNode,
};

export interface ChatMessage {
  id: string;
  type: 'user' | 'assistant' | 'system';
  messageType?: 'status' | 'analysis' | 'artifact' | 'user' | 'processing' | 'error';
  content: string;
  timestamp: Date;
  files?: File[];
  metadata?: {
    analysisData?: any;
    downloadUrl?: string;
    status?: 'processing' | 'complete' | 'error' | 'awaiting_approval';
  };
}

interface HighlightTarget {
  kind: 'analysis' | 'block' | 'input' | 'output';
  label?: string;
}

interface ChatCanvasProps {
  messages: ChatMessage[];
  onApproveAnalysis: () => void;
  onRequestChanges: (feedback: string) => void;
  workflowState?: 'idle' | 'analyzing' | 'awaiting_approval' | 'generating' | 'complete';
  sessionId: string;
  focusMessageId?: string;
  highlightTarget?: HighlightTarget;
}

const ChatCanvas: React.FC<ChatCanvasProps> = ({
  messages,
  onApproveAnalysis,
  onRequestChanges,
  workflowState,
  sessionId,
  focusMessageId,
  highlightTarget,
}) => {
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const { setCenter } = useReactFlow();
  const HIGHLIGHT_MS = 1200;

  // Convert messages to ReactFlow nodes with zigzag pattern
  useEffect(() => {
    const flowNodes: Node[] = [];
    const flowEdges: Edge[] = [];
    
    // Calculate viewport width for proper spacing
    const viewportWidth = window.innerWidth - 300; // Subtract sidebar width
    const nodeWidth = 320;
    const horizontalSpacing = (viewportWidth - nodeWidth) / 2;
    
    messages.forEach((message, index) => {
      const yPosition = 120 + (index * 160); // Vertical spacing
      const isUser = message.type === 'user';
      const isAnalysis = message.metadata?.analysisData;
      const isArtifact = message.metadata?.downloadUrl;
      
      // Zigzag pattern: user right, system left, analysis/artifacts center
      let xPosition: number;
      if (isAnalysis || isArtifact) {
        xPosition = horizontalSpacing; // Center
      } else if (isUser) {
        xPosition = viewportWidth - nodeWidth - 100; // Right side
      } else {
        xPosition = 100; // Left side (system/assistant)
      }
      
      // Determine node type based on message
      let nodeType = 'statusMessage';
      if (message.type === 'user') {
        nodeType = 'userMessage';
      } else if (message.metadata?.analysisData) {
        nodeType = 'analysisMessage';
      } else if (message.metadata?.downloadUrl) {
        nodeType = 'artifactMessage';
      }
      
      // Create the node with wiresheet styling
      const node: Node = {
        id: message.id,
        type: nodeType,
        position: { x: xPosition, y: yPosition },
        data: {
          content: message.content,
          timestamp: message.timestamp,
          files: message.files,
          // For analysis nodes
          sessionId: sessionId,
          analysis: message.metadata?.analysisData,
          onApprove: nodeType === 'analysisMessage' ? onApproveAnalysis : undefined,
          onRequestChanges: nodeType === 'analysisMessage' ? onRequestChanges : undefined,
          approving: workflowState === 'generating',
          processing: workflowState === 'analyzing' || workflowState === 'generating',
          // For artifact nodes
          downloadUrl: message.metadata?.downloadUrl,
          fileName: message.metadata?.downloadUrl ? 'bog_output.json' : undefined,
        },
        sourcePosition: isUser ? Position.Left : Position.Right,
        targetPosition: isUser ? Position.Right : Position.Left,
        style: {
          width: nodeWidth,
          borderRadius: '12px',
          border: '2px solid',
          borderColor: isUser ? '#7e5bef' : (isAnalysis ? '#3ccf8e' : (isArtifact ? '#f59e0b' : '#4a9eff')),
          boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
          background: '#ffffff',
          color: '#111827',
        },
        draggable: false,
      };
      
      flowNodes.push(node);

      // If analysis, render mini nodes for I/O and blocks
      if (nodeType === 'analysisMessage' && message.metadata?.analysisData) {
        const analysis = message.metadata.analysisData as any;
        const inputsRaw = analysis.inputs || analysis.io_points?.inputs || [];
        const outputsRaw = analysis.outputs || analysis.io_points?.outputs || [];
        const blocksRaw = analysis.blocks || analysis.functional_blocks || analysis.controlBlocks || [];

        const norm = (arr: any[]) => arr.map((e: any) => typeof e === 'string' ? e : (e?.name || ''))
                                        .filter((s: string) => !!s);
        const inputs = norm(inputsRaw).slice(0, 10);
        const outputs = norm(outputsRaw).slice(0, 10);
        const blocks = (Array.isArray(blocksRaw) ? blocksRaw : []).map((b:any)=> typeof b==='string'?b:(b?.name||'Block')).slice(0, 8);

        const colGap = 12;
        const miniW = 220;
        const miniH = 48;

        // place inputs to the left stack
        inputs.forEach((name, i) => {
          const id = `${message.id}-in-${i}`;
          const mini: Node = {
            id,
            type: 'statusMessage',
            position: { x: xPosition - (miniW + 40), y: yPosition + i * (miniH + colGap) },
            data: { content: name, kind: 'input' },
            sourcePosition: Position.Right,
            targetPosition: Position.Left,
            style: { width: miniW, border: '2px solid #93c5fd', borderRadius: '10px', background: '#fff', color: '#1e3a8a' },
            draggable: false,
          };
          flowNodes.push(mini);
          flowEdges.push({
            id: `e-${message.id}-${id}`,
            source: message.id,
            target: id,
            type: 'smoothstep',
            animated: false,
            style: { stroke: '#93c5fd', strokeWidth: 2 },
            markerEnd: { type: MarkerType.ArrowClosed, color: '#93c5fd', width: 12, height: 12 },
          } as Edge);
        });

        // place outputs to the right stack
        outputs.forEach((name, i) => {
          const id = `${message.id}-out-${i}`;
          const mini: Node = {
            id,
            type: 'statusMessage',
            position: { x: xPosition + nodeWidth + 40, y: yPosition + i * (miniH + colGap) },
            data: { content: name, kind: 'output' },
            sourcePosition: Position.Right,
            targetPosition: Position.Left,
            style: { width: miniW, border: '2px solid #86efac', borderRadius: '10px', background: '#fff', color: '#14532d' },
            draggable: false,
          };
          flowNodes.push(mini);
          flowEdges.push({
            id: `e-${message.id}-${id}`,
            source: message.id,
            target: id,
            type: 'smoothstep',
            animated: false,
            style: { stroke: '#86efac', strokeWidth: 2 },
            markerEnd: { type: MarkerType.ArrowClosed, color: '#86efac', width: 12, height: 12 },
          } as Edge);
        });

        // place blocks below analysis node
        blocks.forEach((name, i) => {
          const rowSize = 3;
          const id = `${message.id}-blk-${i}`;
          const col = i % rowSize;
          const row = Math.floor(i / rowSize);
          const miniX = xPosition + col * (miniW + 20) - (rowSize-1)*(miniW+20)/2 + nodeWidth/2 - miniW/2;
          const miniY = yPosition + 120 + row * (miniH + colGap);
          const mini: Node = {
            id,
            type: 'statusMessage',
            position: { x: miniX, y: miniY },
            data: { content: name, kind: 'block' },
            sourcePosition: Position.Right,
            targetPosition: Position.Left,
            style: { width: miniW, border: '2px solid #f59e0b', borderRadius: '10px', background: '#fff', color: '#7c2d12' },
            draggable: false,
          };
          flowNodes.push(mini);
          flowEdges.push({
            id: `e-${message.id}-${id}`,
            source: message.id,
            target: id,
            type: 'smoothstep',
            animated: false,
            style: { stroke: '#f59e0b', strokeWidth: 2 },
            markerEnd: { type: MarkerType.ArrowClosed, color: '#f59e0b', width: 12, height: 12 },
          } as Edge);
        });
      }
      
      // Create curved edge to previous message for zigzag flow
      if (index > 0) {
        const isLastLink = index === messages.length - 1;
        const edge: Edge = {
          id: `e${messages[index - 1].id}-${message.id}`,
          source: messages[index - 1].id,
          target: message.id,
          type: 'smoothstep',
          animated: isLastLink && (workflowState === 'analyzing' || workflowState === 'generating'),
          style: {
            stroke: workflowState === 'analyzing' ? '#f59e0b' : 
                   workflowState === 'generating' ? '#10b981' : '#64748b',
            strokeWidth: 2,
            strokeDasharray: workflowState === 'idle' ? '6,6' : '0',
          },
          markerEnd: {
            type: MarkerType.ArrowClosed,
            color: '#64748b',
            width: 16,
            height: 16,
          },
          labelStyle: { fill: '#6b7280', fontWeight: 700 },
          labelBgStyle: { fill: '#f3f4f6', fillOpacity: 0.8 },
        };
        flowEdges.push(edge);
      }
    });
    
    setNodes(flowNodes);
    setEdges(flowEdges);
  }, [messages, workflowState, sessionId, onApproveAnalysis, onRequestChanges, setNodes, setEdges]);

  const onConnect = useCallback(
    (params: Edge | Connection) => setEdges((eds) => addEdge(params, eds)),
    [setEdges]
  );

  // Focus viewport on a specific message/node when requested
  useEffect(() => {
    if (!focusMessageId) return;
    const node = nodes.find((n) => n.id === focusMessageId);
    if (node) {
      const centerX = node.position.x + 160;
      const centerY = node.position.y + 80;
      setCenter(centerX, centerY, { zoom: 1.1, duration: 500 });
    }
  }, [focusMessageId, nodes, setCenter]);

  // Highlight node by tree item; fallback to analysis node
  useEffect(() => {
    if (!highlightTarget) return;

    const targetNode = nodes.find((n) => (n.data as any)?.kind === highlightTarget.kind && (n.data as any)?.content === highlightTarget.label)
      || nodes.find((n) => n.type === 'analysisMessage');
    if (!targetNode) return;

    const centerX = targetNode.position.x + 160;
    const centerY = targetNode.position.y + 80;
    setCenter(centerX, centerY, { zoom: 1.1, duration: 400 });

    setNodes((nds) => nds.map(n => n.id === targetNode.id ? {
      ...n,
      data: { ...(n.data as any), processing: true, highlightLabel: highlightTarget.label }
    } : n));

    const t = setTimeout(() => {
      setNodes((nds) => nds.map(n => n.id === targetNode.id ? {
        ...n,
        data: { ...(n.data as any), processing: false, highlightLabel: undefined }
      } : n));
    }, HIGHLIGHT_MS);

    return () => clearTimeout(t);
  }, [highlightTarget, setCenter, setNodes, nodes]);

  return (
    <div style={{ width: '100%', height: '100%' }}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        nodeTypes={nodeTypes}
        fitView
        fitViewOptions={{ padding: 0.1, maxZoom: 1.2 }}
        defaultViewport={{ x: 0, y: 0, zoom: 0.9 }}
        minZoom={0.5}
        maxZoom={1.5}
        attributionPosition="bottom-left"
      >
        <Background 
          variant={BackgroundVariant.Lines} 
          gap={24} 
          size={1}
          color="#ededed"
        />
        <Controls showInteractive={false} />
      </ReactFlow>
    </div>
  );
};

export default ChatCanvas;
