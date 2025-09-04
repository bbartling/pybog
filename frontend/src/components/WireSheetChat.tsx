import React, { useCallback, useRef, useEffect, useState } from 'react';
import ReactFlow, {
  Node,
  Edge,
  useNodesState,
  useEdgesState,
  addEdge,
  Connection,
  Controls,
  MiniMap,
  Background,
  Handle,
  Position,
  NodeProps,
  MarkerType,
} from 'reactflow';
import 'reactflow/dist/style.css';
import './WireSheetChat.css';

// Layout constants
const VIEWPORT_WIDTH = 1000;
const MESSAGE_WIDTH = 360;
const DIALOG_WIDTH = 380;
const V_SPACING = 20;
const MARGIN = 60;

interface ChatMessage {
  id: string;
  type: 'user' | 'system' | 'processing' | 'ai' | 'artifact' | 'error';
  content: string;
  timestamp?: Date;
  messageType?: string;
  metadata?: {
    analysisData?: any;
    downloadUrl?: string;
    status?: string;
  };
}

interface WireSheetChatProps {
  messages: ChatMessage[];
  embeddedMode?: boolean;
  onSendMessage?: (message: string) => void;
  onUpload?: (files: FileList) => void;
  onApprove?: () => void;
  onRequestChanges?: (feedback: string) => void;
  onDownload?: (messageId: string) => void;
}

// Custom node components
const DialogNode = ({ data }: NodeProps) => {
  const nodeClass = `ws-node ${data.isUserMessage ? 'ws-user' : 
                    data.type === 'ai' ? 'ws-ai' : 'ws-system'}`;
  
  return (
    <div className={nodeClass}>
      <Handle
        type="target"
        position={data.isUserMessage ? Position.Right : Position.Left}
        style={{
          background: '#4a9eff',
          width: 12,
          height: 12,
          border: '2px solid #fff',
          zIndex: 10
        }}
      />
      <div className="ws-node-header">
        <span className="ws-node-type">
          {data.isUserMessage ? 'User Input' : 
           data.type === 'ai' ? 'AI Analysis' :
           data.type === 'artifact' ? 'Final Artifact' :
           'System Response'}
        </span>
        <span className="ws-node-time">
          {data.timestamp ? new Date(data.timestamp).toLocaleTimeString([], {hour: '2-digit', minute: '2-digit'}) : ''}
        </span>
      </div>
      <div className="ws-node-content">
        {data.content}
      </div>
      {data.type === 'ai' && (
        <div className="ws-node-actions">
          <button className="ws-approve-btn" onClick={data.onApprove}>
            ✅ Approve
          </button>
          <button className="ws-changes-btn" onClick={() => data.onRequestChanges?.('Changes needed')}>
            ✏️ Request Changes
          </button>
        </div>
      )}
      {data.type === 'artifact' && data.metadata?.downloadUrl && (
        <div className="ws-node-actions">
          <button className="ws-download-btn" onClick={() => window.open(data.metadata?.downloadUrl, '_blank')}>
            📥 Download BOG
          </button>
        </div>
      )}
      <Handle
        type="source"
        position={data.isUserMessage ? Position.Left : Position.Right}
        style={{
          background: '#f59e0b',
          width: 12,
          height: 12,
          border: '2px solid #fff',
          zIndex: 10
        }}
      />
    </div>
  );
};

const CompactNode = ({ data }: NodeProps) => (
  <div className="ws-compact-node">
    <Handle
      type="target"
      position={Position.Left}
      style={{ background: '#4a9eff', width: 8, height: 8 }}
    />
    <div className="ws-compact-content">
      {data.content}
    </div>
    <Handle
      type="source"
      position={Position.Right}
      style={{ background: '#f59e0b', width: 8, height: 8 }}
    />
  </div>
);

const nodeTypes = {
  dialogNode: DialogNode,
  compactNode: CompactNode,
};

const WireSheetChat: React.FC<WireSheetChatProps> = ({
  messages,
  embeddedMode = false,
  onSendMessage,
  onUpload,
  onApprove,
  onRequestChanges,
  onDownload
}) => {
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [inputText, setInputText] = useState('');
  const reactFlowWrapper = useRef<HTMLDivElement>(null);

  const getZigzagLayout = useCallback((messages: ChatMessage[]) => {
    if (!messages.length) return { nodes: [], edges: [] };

    const nodePositions: { x: number; y: number }[] = [];
    const layoutedNodes: Node[] = [];
    const layoutedEdges: Edge[] = [];

    // Group messages into rows
    const rows: ChatMessage[][] = [];
    let currentRow: ChatMessage[] = [];
    let currentRowWidth = 0;

    messages.forEach((message) => {
      const isCompact = message.type === 'processing';
      const nodeWidth = isCompact ? 240 : DIALOG_WIDTH;
      
      if (isCompact && currentRowWidth + nodeWidth <= VIEWPORT_WIDTH - 200) {
        currentRow.push(message);
        currentRowWidth += nodeWidth + 40;
      } else {
        if (currentRow.length > 0) {
          rows.push(currentRow);
        }
        currentRow = [message];
        currentRowWidth = nodeWidth;
      }
    });
    
    if (currentRow.length > 0) {
      rows.push(currentRow);
    }

    let yOffset = 100;

    rows.forEach((row, rowIndex) => {
      const isLeftToRight = rowIndex % 2 === 0;
      let xOffset = isLeftToRight ? MARGIN : VIEWPORT_WIDTH - MARGIN;
      
      row.forEach((message, colIndex) => {
        const isCompact = message.type === 'processing';
        const nodeWidth = isCompact ? 240 : DIALOG_WIDTH;
        const nodeHeight = isCompact ? 80 : Math.min(200, 120 + (message.content.split('\n').length * 20));
        
        let x: number;
        if (row.length === 1 && !isCompact) {
          // Single dialog node - use zigzag positioning
          const isUserMessage = message.type === 'user';
          if (isUserMessage) {
            x = VIEWPORT_WIDTH - MESSAGE_WIDTH - MARGIN; // Right side for user
          } else {
            x = MARGIN; // Left side for system/ai
          }
        } else {
          // Compact nodes or multiple nodes in row
          if (isLeftToRight) {
            x = xOffset;
            xOffset += nodeWidth + 40;
          } else {
            x = xOffset - nodeWidth;
            xOffset -= nodeWidth + 40;
          }
        }

        const position = { x, y: yOffset };
        nodePositions.push(position);

        const nodeData = {
          ...message,
          content: message.content,
          timestamp: message.timestamp,
          isUserMessage: message.type === 'user',
          onApprove,
          onRequestChanges,
          onDownload
        };

        layoutedNodes.push({
          id: message.id,
          type: isCompact ? 'compactNode' : 'dialogNode',
          position,
          data: nodeData,
          style: {
            width: nodeWidth,
            height: nodeHeight,
          },
        });
      });

      yOffset += Math.max(...row.map(m => m.type === 'processing' ? 80 : 180)) + V_SPACING;
    });

    // Create edges
    for (let i = 0; i < layoutedNodes.length - 1; i++) {
      layoutedEdges.push({
        id: `e${i}-${i+1}`,
        source: layoutedNodes[i].id,
        target: layoutedNodes[i + 1].id,
        type: 'smoothstep',
        markerEnd: {
          type: MarkerType.ArrowClosed,
          width: 20,
          height: 20,
          color: '#4a9eff',
        },
        style: {
          stroke: '#4a9eff',
          strokeWidth: 2,
        },
      });
    }

    return { nodes: layoutedNodes, edges: layoutedEdges };
  }, [onApprove, onRequestChanges, onDownload]);

  useEffect(() => {
    const { nodes: layoutedNodes, edges: layoutedEdges } = getZigzagLayout(messages);
    setNodes(layoutedNodes);
    setEdges(layoutedEdges);
  }, [messages, getZigzagLayout, setNodes, setEdges]);

  const onConnect = useCallback(
    (params: Connection) => setEdges((eds) => addEdge(params, eds)),
    [setEdges]
  );

  const handleSend = () => {
    if (inputText.trim() && onSendMessage) {
      onSendMessage(inputText);
      setInputText('');
    }
  };

  return (
    <div className="wiresheet-chat-container" style={{ height: embeddedMode ? '100%' : 'calc(100vh - 120px)' }}>
      {!embeddedMode && (
        <div className="wiresheet-header">
          <h3>HVAC Control Logic Builder</h3>
        </div>
      )}
      
      <div className="wiresheet-canvas" style={{ height: embeddedMode ? '100%' : 'calc(100% - 60px)' }}>
        <ReactFlow
          ref={reactFlowWrapper}
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onConnect={onConnect}
          nodeTypes={nodeTypes}
          fitView
          fitViewOptions={{ 
            padding: 0.1,
            maxZoom: 1.0,
            minZoom: 0.5
          }}
          defaultViewport={{ x: 0, y: 0, zoom: 0.6 }}
        >
          <Background />
          <Controls />
          <MiniMap />
        </ReactFlow>
      </div>

      {!embeddedMode && (
        <div className="wiresheet-input">
          <input
            type="text"
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && handleSend()}
            placeholder="Describe HVAC control requirements..."
          />
          <button onClick={handleSend} disabled={!inputText.trim()}>
            Send
          </button>
        </div>
      )}
    </div>
  );
};

export default WireSheetChat;
