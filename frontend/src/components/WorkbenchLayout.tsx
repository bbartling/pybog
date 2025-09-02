import React, { useState, useRef, useEffect } from 'react';
import { 
  Send, Upload, Download, Loader2, 
  MessageCircle, Code, Database, ChevronRight, ChevronDown, User, Bot, 
  Activity, Cpu, Folder, Package, Menu, AlertCircle, Grid, FolderOpen, Box
} from 'lucide-react';
import './WorkbenchTheme.css';

interface WorkbenchMessage {
  id: string;
  type: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: Date;
  component?: 'string-writable' | 'enum-writable' | 'folder' | 'bool-writable';
}

interface BogFile {
  id: string;
  name: string;
  size: number;
  timestamp: Date;
  status: 'ready' | 'generating';
}

interface TreeNode {
  id: string;
  label: string;
  icon?: React.ReactNode;
  children?: TreeNode[];
  expanded?: boolean;
  type?: 'folder' | 'file' | 'component';
}

interface WorkbenchLayoutProps {
  messages: WorkbenchMessage[];
  bogFiles: BogFile[];
  onSendMessage: (text: string) => void;
  onDownloadBog: (id: string) => void;
  isLoading?: boolean;
}

const WorkbenchLayout: React.FC<WorkbenchLayoutProps> = ({
  messages,
  bogFiles,
  onSendMessage,
  onDownloadBog,
  isLoading = false
}) => {
  const [inputText, setInputText] = useState('');
  const [selectedTab, setSelectedTab] = useState('bog-files');
  const [treeNodes, setTreeNodes] = useState<TreeNode[]>([
    {
      id: 'nav',
      label: 'Nav',
      icon: <Grid size={14} />,
      expanded: true,
      children: [
        {
          id: 'drivers',
          label: 'Drivers',
          icon: <Folder size={14} />,
          children: []
        },
        {
          id: 'points',
          label: 'points',
          icon: <Database size={14} />,
          expanded: true,
          children: messages.slice(0, 5).map((msg, idx) => ({
            id: `point-${idx}`,
            label: `Message_${idx + 1}`,
            icon: <MessageCircle size={14} />,
            type: 'component' as const
          }))
        }
      ]
    }
  ]);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const wiresheetRef = useRef<HTMLDivElement>(null);
  const [wireConnections, setWireConnections] = useState<any[]>([]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    updateWireConnections();
  }, [messages]);

  const updateWireConnections = () => {
    if (!wiresheetRef.current) return;
    
    const components = wiresheetRef.current.querySelectorAll('.wb-component');
    const connections: any[] = [];
    
    for (let i = 0; i < components.length - 1; i++) {
      const from = components[i].getBoundingClientRect();
      const to = components[i + 1].getBoundingClientRect();
      const containerRect = wiresheetRef.current.getBoundingClientRect();
      
      connections.push({
        x1: from.right - containerRect.left,
        y1: from.top + from.height / 2 - containerRect.top,
        x2: to.left - containerRect.left,
        y2: to.top + to.height / 2 - containerRect.top
      });
    }
    
    setWireConnections(connections);
  };

  const toggleTreeNode = (nodeId: string) => {
    const toggleNode = (nodes: TreeNode[]): TreeNode[] => {
      return nodes.map(node => {
        if (node.id === nodeId) {
          return { ...node, expanded: !node.expanded };
        }
        if (node.children) {
          return { ...node, children: toggleNode(node.children) };
        }
        return node;
      });
    };
    setTreeNodes(toggleNode(treeNodes));
  };

  const renderTreeNode = (node: TreeNode, depth: number = 0) => {
    const hasChildren = node.children && node.children.length > 0;
    
    return (
      <div key={node.id}>
        <div 
          className={`tree-node ${node.type === 'component' ? 'selected' : ''}`}
          onClick={() => hasChildren && toggleTreeNode(node.id)}
          style={{ paddingLeft: `${depth * 16 + 4}px` }}
        >
          {hasChildren && (
            <span className="tree-expand">
              {node.expanded ? <ChevronDown size={10} /> : <ChevronRight size={10} />}
            </span>
          )}
          <span className="tree-icon">
            {node.expanded && hasChildren ? <FolderOpen size={14} /> : node.icon}
          </span>
          <span className="tree-label">{node.label}</span>
        </div>
        {node.expanded && node.children && (
          <div>
            {node.children.map(child => renderTreeNode(child, depth + 1))}
          </div>
        )}
      </div>
    );
  };

  const renderWiresheetComponent = (message: WorkbenchMessage, index: number) => {
    const isUser = message.type === 'user';
    const componentType = message.component || 'enum-writable';
    
    return (
      <div 
        key={message.id}
        className={`wb-component message-component ${message.type}`}
        style={{
          position: 'absolute',
          left: isUser ? '60%' : '20%',
          top: `${index * 80 + 20}px`
        }}
      >
        {/* Input Pins */}
        <div className="wb-pins input">
          <div className="wb-pin input" title="In">
            <span className="wb-pin-label">In</span>
          </div>
        </div>
        
        {/* Output Pins */}
        <div className="wb-pins output">
          <div className="wb-pin output" title="Out">
            <span className="wb-pin-label">Out</span>
          </div>
        </div>

        <div className="wb-component-header">
          <span className="wb-component-title">
            {componentType === 'string-writable' && 'String Writable'}
            {componentType === 'enum-writable' && 'Enum Writable'}
            {componentType === 'folder' && 'Folder'}
            {componentType === 'bool-writable' && 'Boolean Writable'}
          </span>
          <Box size={12} className="wb-component-icon" />
        </div>
        
        <div className="wb-component-body">
          <div className="wb-property">
            <span className="wb-property-label">Out:</span>
            <span className="wb-property-value">
              {message.content.substring(0, 30)}...
            </span>
          </div>
          <div className="wb-property">
            <span className="wb-property-label">Status:</span>
            <span className="wb-property-value">
              {message.type === 'user' ? '[null]' : 'true [ok]'}
            </span>
          </div>
        </div>
      </div>
    );
  };

  const handleSend = () => {
    if (inputText.trim()) {
      onSendMessage(inputText);
      setInputText('');
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="workbench-container">
      {/* Header */}
      <div className="workbench-header">
        <div className="wb-logo">
          <Cpu size={14} />
          <span>PyBOG - HVAC Control Builder</span>
        </div>
        <div className="wb-status-bar">
          <div className="wb-status-item">
            <div className="wb-status-dot" />
            <span>N8N Connected</span>
          </div>
          <div className="wb-status-item">
            <Activity size={10} />
            <span>{isLoading ? 'Processing...' : 'Ready'}</span>
          </div>
        </div>
      </div>

      <div className="workbench-layout">
        {/* Sidebar Navigation */}
        <div className="workbench-nav">
          <div className="nav-header">
            Nav
          </div>
          <div className="nav-tree">
            {treeNodes.map(node => renderTreeNode(node))}
          </div>
        </div>

        {/* Main Canvas */}
        <div className="workbench-canvas">
          {/* Wire Sheet */}
          <div className="wiresheet-container" ref={wiresheetRef}>
            <div className="wiresheet-grid" />
            
            {/* Wire Connections SVG */}
            <svg className="wiresheet-wires">
              {wireConnections.map((conn, idx) => (
                <path
                  key={idx}
                  className="wire-path animated"
                  d={`M ${conn.x1} ${conn.y1} 
                      C ${conn.x1 + 50} ${conn.y1}, 
                        ${conn.x2 - 50} ${conn.y2}, 
                        ${conn.x2} ${conn.y2}`}
                />
              ))}
            </svg>

            {/* Components */}
            <div className="wiresheet-content">
              {messages.map((msg, idx) => renderWiresheetComponent(msg, idx))}
              <div ref={messagesEndRef} style={{ height: 100 }} />
            </div>
          </div>

          {/* Chat Input */}
          <div className="chat-input-panel">
            <button className="chat-button">
              <Upload size={12} />
              Upload
            </button>
            <textarea
              className="chat-input-field"
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Describe HVAC control requirements..."
              rows={2}
            />
            <button 
              className="chat-button primary"
              onClick={handleSend}
              disabled={!inputText.trim() || isLoading}
            >
              <Send size={12} />
              Send
            </button>
          </div>
        </div>
      </div>

      {/* Bottom Panel */}
      <div className="workbench-bottom">
        <div className="bottom-tabs">
          <div 
            className={`bottom-tab ${selectedTab === 'bog-files' ? 'active' : ''}`}
            onClick={() => setSelectedTab('bog-files')}
          >
            BOG Files
          </div>
          <div 
            className={`bottom-tab ${selectedTab === 'console' ? 'active' : ''}`}
            onClick={() => setSelectedTab('console')}
          >
            Console
          </div>
          <div 
            className={`bottom-tab ${selectedTab === 'properties' ? 'active' : ''}`}
            onClick={() => setSelectedTab('properties')}
          >
            Properties
          </div>
        </div>
        
        <div className="bottom-content">
          {selectedTab === 'bog-files' && (
            <div className="bog-list">
              {bogFiles.length === 0 ? (
                <div style={{ color: '#666', fontStyle: 'italic' }}>
                  No BOG files generated yet
                </div>
              ) : (
                bogFiles.map(bog => (
                  <div 
                    key={bog.id} 
                    className="bog-item"
                    onClick={() => onDownloadBog(bog.id)}
                  >
                    <Code size={16} className="bog-item-icon" />
                    <span className="bog-item-name">{bog.name}</span>
                    <span className="bog-item-size">
                      {(bog.size / 1024).toFixed(1)} KB
                    </span>
                    <Download size={12} />
                  </div>
                ))
              )}
            </div>
          )}
          
          {selectedTab === 'console' && (
            <div style={{ fontFamily: 'monospace', fontSize: '10px', color: '#666' }}>
              [System] Ready for HVAC control sequence analysis...<br/>
              [N8N] Workflow connected<br/>
              {isLoading && '[Processing] Analyzing control logic...'}
            </div>
          )}
          
          {selectedTab === 'properties' && (
            <div>
              <div className="wb-property">
                <span className="wb-property-label">Session:</span>
                <span className="wb-property-value">Active</span>
              </div>
              <div className="wb-property">
                <span className="wb-property-label">Messages:</span>
                <span className="wb-property-value">{messages.length}</span>
              </div>
              <div className="wb-property">
                <span className="wb-property-label">BOG Files:</span>
                <span className="wb-property-value">{bogFiles.length}</span>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default WorkbenchLayout;
