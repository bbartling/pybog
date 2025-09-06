import React, { useCallback, useEffect, useRef } from 'react';
import ReactFlow, {
  Node,
  Edge,
  Controls,
  Background,
  MiniMap,
  useNodesState,
  useEdgesState,
  addEdge,
  Connection,
  MarkerType,
  Position,
  BackgroundVariant,
  useReactFlow,
} from 'reactflow';
import ConversationSwimlanes from './flow/ConversationSwimlanes';
import './flow/canvas.css';
import { SmartStepEdge } from '@tisoap/react-flow-smart-edge';
import 'reactflow/dist/style.css';
import { graphlib as dagreGraphLib, layout as dagreLayout } from '@dagrejs/dagre';

// Import our custom nodes
import UserNode from './Nodes/UserNode';
import StatusNode from './Nodes/StatusNode';
import AnalysisGridNode from './Nodes/AnalysisGridNode';
import ArtifactNode from './Nodes/ArtifactNode';
import ProcessNode from './Nodes/ProcessNode';

// Define node types for ReactFlow
const nodeTypes = {
  userMessage: UserNode,
  statusMessage: StatusNode,
  analysisMessage: AnalysisGridNode,
  artifactMessage: ArtifactNode,
  processMessage: ProcessNode,
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
    processStep?: {
      stepKey: string;
      detail?: string;
      status: 'running' | 'ok' | 'error' | 'waiting';
      metrics?: Record<string, any>;
    };
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

const edgeTypes = { smart: SmartStepEdge } as const;

const defaultEdgeOptions = {
  type: 'smart',
  style: { strokeWidth: 1.5, stroke: '#22d3ee' }, // Niagara cyan for default chat edges
  markerEnd: { type: MarkerType.ArrowClosed, width: 14, height: 14, color: '#22d3ee' },
} as const;

// Standard width for node cards used in layout math for mini nodes
const nodeWidth = 340;

// Dagre graph for auto-layout with Niagara lanes
const dagreGraph = new dagreGraphLib.Graph();
dagreGraph.setGraph({ rankdir: 'TB', nodesep: 80, ranksep: 120, edgesep: 50 });
dagreGraph.setDefaultEdgeLabel(() => ({}));

function laneOffset(lane: 'left' | 'center' | 'right') {
  switch (lane) {
    case 'left':
      return -220;
    case 'center':
      return 0;
    case 'right':
      return 220;
  }
}

function layoutWithDagre(nodes: Node[], edges: Edge[]) {
  // Seed dagre nodes with width/height
  nodes.forEach((n) => {
    const w = (n as any).width || nodeWidth;
    const h = (n as any).height || 100;
    dagreGraph.setNode(n.id, { width: w, height: h });
  });
  edges.forEach((e) => dagreGraph.setEdge(e.source, e.target));
  dagreLayout(dagreGraph);

  const laid = nodes.map((n) => {
    const pos = dagreGraph.node(n.id);
    const lane = ((n.data as any)?.lane as 'left' | 'center' | 'right') || 'center';
    const x = pos.x + laneOffset(lane);
    const y = pos.y;
    const w = (n as any).width || nodeWidth;
    const h = (n as any).height || 100;
    return { ...n, position: { x: x - w / 2, y: y - h / 2 } };
  });

  // reset graph
  dagreGraph.nodes().forEach((id) => dagreGraph.removeNode(id));
  return laid;
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
  const { setCenter, fitView, screenToFlowPosition } = useReactFlow();
  // Ephemeral nodes/edges created via drag-drop from the navigator
  const extraNodesRef = useRef<Node[]>([]);
  const extraEdgesRef = useRef<Edge[]>([]);
  const HIGHLIGHT_MS = 1200;

  // Convert messages to ReactFlow nodes with clear conversation flow
  useEffect(() => {
    const flowNodes: Node[] = [];
    const flowEdges: Edge[] = [];

    // Conversation flow parameters
    const CANVAS_WIDTH = 1400;
    const NODE_WIDTH = 340;
    const PROCESS_NODE_WIDTH = 240;
    const VERTICAL_GAP = 120;
    const TOP_PADDING = 100;
    
    // Track conversation pairs and process groups
    let currentY = TOP_PADDING;
    let lastUserNode: Node | null = null;
    let processNodeGroup: Node[] = [];
    
    messages.forEach((message, index) => {
      const isUser = message.type === 'user';
      const isAssistant = message.type === 'assistant';
      const isProcess = message.metadata?.processStep !== undefined;
      const isAnalysis = message.metadata?.analysisData;
      const isArtifact = message.metadata?.downloadUrl;
      const isStatus = message.messageType === 'status' && !isProcess;
      
      // Handle process step nodes (small, in middle)
      if (isProcess) {
        const processData = message.metadata!.processStep!;
        const processNode: Node = {
          id: message.id,
          type: 'processMessage',
          position: {
            x: CANVAS_WIDTH / 2 - PROCESS_NODE_WIDTH / 2,
            y: currentY
          },
          data: {
            lane: 'center',
            stepKey: processData.stepKey,
            title: message.content,
            detail: processData.detail,
            status: processData.status,
            metrics: processData.metrics,
            timestamp: message.timestamp.toISOString(),
          },
          width: PROCESS_NODE_WIDTH as any,
          height: 90 as any,
          draggable: false,
        };
        
        flowNodes.push(processNode);
        processNodeGroup.push(processNode);
        
        // Don't increment Y for process nodes, they stack horizontally
        if (processNodeGroup.length > 1) {
          // Arrange process nodes in a row
          processNodeGroup.forEach((pn, idx) => {
            pn.position.x = CANVAS_WIDTH / 2 - (processNodeGroup.length * (PROCESS_NODE_WIDTH + 20)) / 2 + idx * (PROCESS_NODE_WIDTH + 20);
          });
        }
        
        // Connect process nodes to each other
        if (processNodeGroup.length > 1) {
          const prevProcess = processNodeGroup[processNodeGroup.length - 2];
          flowEdges.push({
            id: `e-process-${prevProcess.id}-${processNode.id}`,
            source: prevProcess.id,
            target: processNode.id,
            type: 'smoothstep',
            animated: processData.status === 'running',
            style: { stroke: '#64748b', strokeWidth: 1.5, strokeDasharray: processData.status === 'running' ? '5 3' : '0' },
          });
        }
        
        // Connect from last user to first process
        if (lastUserNode && processNodeGroup.length === 1) {
            flowEdges.push({
              id: `e-user-to-process-${lastUserNode.id}-${processNode.id}`,
              source: lastUserNode.id,
              target: processNode.id,
              type: 'smoothstep',
              animated: true,
              style: { stroke: '#2dd4bf', strokeWidth: 2, strokeDasharray: '5 3' }, // teal dashed into process
              markerEnd: { type: MarkerType.ArrowClosed, color: '#2dd4bf', width: 12, height: 12 },
            });
        }
        
        return; // Don't create main conversation node
      }
      
      // Clear process group when we hit a non-process message
      if (processNodeGroup.length > 0 && !isProcess) {
        currentY += VERTICAL_GAP / 2; // Add space after process group
        processNodeGroup = [];
      }
      
      // Determine node type and position
      let nodeType = 'statusMessage';
      let xPosition = CANVAS_WIDTH / 2 - NODE_WIDTH / 2; // Default center
      let alignment: 'left' | 'right' | 'center' = 'center';
      
      if (isUser) {
        nodeType = 'userMessage';
        xPosition = 200; // Left side for user
        alignment = 'left';
      } else if (isAnalysis) {
        nodeType = 'analysisMessage';
        xPosition = CANVAS_WIDTH - NODE_WIDTH - 200; // Right side for analysis
        alignment = 'right';
      } else if (isArtifact) {
        nodeType = 'artifactMessage';
        xPosition = CANVAS_WIDTH - NODE_WIDTH - 200; // Right side for artifacts
        alignment = 'right';
      } else if (isAssistant) {
        xPosition = CANVAS_WIDTH - NODE_WIDTH - 200; // Right side for assistant
        alignment = 'right';
      } else if (isStatus) {
        // Treat status messages as system-side updates (right aligned)
        xPosition = CANVAS_WIDTH - NODE_WIDTH - 200;
        alignment = 'right';
      }
      
      // Create the main conversation node
      const node: Node = {
        id: message.id,
        type: nodeType,
        position: { x: xPosition, y: currentY },
        data: {
          lane: alignment,
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
        sourcePosition: alignment === 'left' ? Position.Right : alignment === 'right' ? Position.Left : Position.Bottom,
        targetPosition: alignment === 'left' ? Position.Left : alignment === 'right' ? Position.Right : Position.Top,
        style: {
          width: NODE_WIDTH,
          borderRadius: '12px',
          border: '2px solid',
          borderColor: isUser ? '#8b5cf6' : (isAnalysis ? '#10b981' : (isArtifact ? '#f59e0b' : (isAssistant ? '#3b82f6' : '#64748b'))),
          boxShadow: '0 4px 12px rgba(0,0,0,0.1)',
          background: isUser ? 'linear-gradient(135deg, #f3e8ff 0%, #ede9fe 100%)' : '#ffffff',
        },
        width: (nodeType === 'analysisMessage' ? 560 : NODE_WIDTH) as any,
        height: (nodeType === 'analysisMessage' ? 320 : 120) as any,
        draggable: false,
      };
      
      flowNodes.push(node);
      
      // Track last user node for connecting to processes
      if (isUser) {
        lastUserNode = node;
      }
      
      // Move Y position down for next message
      currentY += VERTICAL_GAP;

      // Create conversation flow edges
      if (index > 0 && !isProcess) {
        const prevMessage = messages[index - 1];
        const isPrevProcess = prevMessage.metadata?.processStep !== undefined;
        
        if (isPrevProcess) {
          // Connect from last process node to this message
          const lastProcess = processNodeGroup[processNodeGroup.length - 1] || flowNodes.find(n => n.id === prevMessage.id);
          if (lastProcess) {
            flowEdges.push({
              id: `e-process-to-msg-${lastProcess.id}-${node.id}`,
              source: lastProcess.id,
              target: node.id,
              type: 'smoothstep',
              animated: false,
              style: { stroke: '#22d3ee', strokeWidth: 1.5 }, // cyan out of process to system/user
              markerEnd: { type: MarkerType.ArrowClosed, color: '#22d3ee', width: 10, height: 10 },
            });
          }
        } else {
          // Normal conversation flow edge
          const prevNode = flowNodes.find(n => n.id === prevMessage.id);
          if (prevNode) {
            const isConversationPair = 
              (prevMessage.type === 'user' && message.type === 'assistant') ||
              (prevMessage.type === 'assistant' && message.type === 'user');
            
            flowEdges.push({
              id: `e-${prevMessage.id}-${message.id}`,
              source: prevMessage.id,
              target: message.id,
              type: 'smoothstep',
              animated: workflowState === 'analyzing' && index === messages.length - 1,
              style: {
                stroke: isConversationPair ? '#22d3ee' : '#94a3b8', // cyan for chat pair
                strokeWidth: isConversationPair ? 2 : 1.5,
                strokeDasharray: workflowState === 'analyzing' && index === messages.length - 1 ? '5 3' : '0',
              },
              markerEnd: {
                type: MarkerType.ArrowClosed,
                color: isConversationPair ? '#22d3ee' : '#94a3b8',
                width: 12,
                height: 12,
              },
            });
          }
        }
      }
    });
    
    // Merge ephemeral nodes/edges and layout together
    const allNodes = [...flowNodes, ...extraNodesRef.current];
    const allEdges = [...flowEdges, ...extraEdgesRef.current];

    const layouted = layoutWithDagre(allNodes, allEdges);
    setNodes(layouted);
    setEdges(allEdges);
  }, [messages, workflowState, sessionId, onApproveAnalysis, onRequestChanges, setNodes, setEdges]);

  const onConnect = useCallback(
    (params: Edge | Connection) => setEdges((eds) => addEdge(params, eds)),
    [setEdges]
  );

  // Drag & Drop from NiagaraTreeNavigator
  const onDragOver = useCallback((evt: React.DragEvent) => {
    evt.preventDefault();
    evt.dataTransfer.dropEffect = 'move';
  }, []);

  const onDrop = useCallback((evt: React.DragEvent) => {
    evt.preventDefault();
    const raw = evt.dataTransfer.getData('application/reactflow');
    if (!raw) return;
    const payload = JSON.parse(raw);
    const pos = screenToFlowPosition({ x: evt.clientX, y: evt.clientY });

    const makeId = (prefix: string) => `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;

    if (payload.type === 'message') {
      const id = makeId('extra-msg');
      const isUser = payload.role === 'user';
      const lane = isUser ? 'left' : 'right';
      const node: Node = {
        id,
        type: isUser ? 'userMessage' : 'statusMessage',
        position: pos,
        data: { lane, content: payload.text, timestamp: new Date() },
        width: 340 as any,
        height: 120 as any,
        draggable: false,
      };
      extraNodesRef.current = [...extraNodesRef.current, node];
    }

    if (payload.type === 'file') {
      const id = makeId('extra-file');
      const node: Node = {
        id,
        type: 'statusMessage',
        position: pos,
        data: { lane: 'right', content: `File: ${payload.name}`, timestamp: new Date() },
        width: 340 as any,
        height: 120 as any,
        draggable: false,
      };
      extraNodesRef.current = [...extraNodesRef.current, node];
    }

    if (payload.type === 'analysis-point') {
      const id = makeId('extra-anl');
      const analysis = payload.slot === 'OUT' ? { inputs: [], outputs: [payload.name] } : { inputs: [payload.name], outputs: [] };
      const node: Node = {
        id,
        type: 'analysisMessage',
        position: pos,
        data: {
          lane: 'right',
          sessionId,
          analysis,
          approving: false,
          processing: false,
        },
        width: 560 as any,
        height: 320 as any,
        draggable: false,
      };
      extraNodesRef.current = [...extraNodesRef.current, node];
    }

    if (payload.type === 'sequence') {
      const id = makeId('extra-seq');
      const node: Node = {
        id,
        type: 'statusMessage',
        position: pos,
        data: { lane: 'right', content: `Sequence: ${payload.name}`, timestamp: new Date() },
        width: 340 as any,
        height: 120 as any,
        draggable: false,
      };
      extraNodesRef.current = [...extraNodesRef.current, node];
    }

    // Re-layout including new nodes
    setNodes((prev) => layoutWithDagre([...prev, ...extraNodesRef.current.filter(n => !prev.find(p => p.id === n.id))], edges));
  }, [edges, screenToFlowPosition, sessionId, setNodes]);

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

  // Fit the most recent 4 conversation nodes to keep context in view
  useEffect(() => {
    if (!messages || messages.length === 0) return;
    const recentIds = messages.slice(-4).map(m => m.id);
    const targets = nodes.filter(n => recentIds.includes(n.id));
    if (targets.length > 0) {
      try {
        // Prefer native fitView over manual centering
        fitView({ nodes: targets, padding: 0.15, maxZoom: 1.2, duration: 500 });
      } catch {
        // Fallback: center on last node if fitView signature differs
        const last = targets[targets.length - 1];
        const cx = last.position.x + 160;
        const cy = last.position.y + 80;
        setCenter(cx, cy, { zoom: 1.0, duration: 450 });
      }
    }
  }, [messages, nodes, fitView, setCenter]);

  // During processing, nudge zoom slightly and keep the recent context visible
  useEffect(() => {
    if (!messages || messages.length === 0) return;
    if (workflowState === 'analyzing' || workflowState === 'generating') {
      const recentIds = messages.slice(-4).map(m => m.id);
      const targets = nodes.filter(n => recentIds.includes(n.id));
      if (targets.length > 0) {
        try { fitView({ nodes: targets, padding: 0.18, maxZoom: 1.2, duration: 380 }); }
        catch {}
      }
    }
  }, [workflowState, messages, nodes, fitView]);

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
    <div style={{ width: '100%', height: '100%', position: 'relative' }}>
      <ConversationSwimlanes />
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        nodeTypes={nodeTypes}
        edgeTypes={edgeTypes}
        defaultEdgeOptions={defaultEdgeOptions}
        fitView
        fitViewOptions={{ padding: 0.08, maxZoom: 1.3 }}
        defaultViewport={{ x: 0, y: 0, zoom: 1.0 }}
        minZoom={0.5}
        maxZoom={1.6}
        panOnScroll
        panOnDrag
        zoomOnPinch
        nodesDraggable={false}
        nodesConnectable={false}
        elementsSelectable={false}
        attributionPosition="bottom-left"
        onDragOver={onDragOver}
        onDrop={onDrop}
      >
        <Background 
          variant={BackgroundVariant.Lines} 
          gap={24} 
          size={1}
          color="#ededed"
        />
        <MiniMap position="top-right" style={{ height: 120, width: 180 }} zoomable pannable />
        <Controls showInteractive={true} />
      </ReactFlow>
    </div>
  );
};

export default ChatCanvas;
