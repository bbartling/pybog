import React, { useState, useEffect, useRef } from 'react';
import { Terminal, X, Trash2, Download, ChevronUp, ChevronDown } from 'lucide-react';

export interface ConsoleMessage {
  id: string;
  timestamp: Date;
  level: 'info' | 'warn' | 'error' | 'success' | 'debug';
  source: string;
  message: string;
  details?: any;
  container?: string; // New: for Docker logs
}

interface ConsolePanelProps {
  isOpen: boolean;
  onClose: () => void;
  messages: ConsoleMessage[];
  onClear: () => void;
}

const ConsolePanel: React.FC<ConsolePanelProps> = ({
  isOpen,
  onClose,
  messages,
  onClear
}) => {
  const [filter, setFilter] = useState<'all' | 'info' | 'warn' | 'error' | 'docker'>('all');
  const [containerFilter, setContainerFilter] = useState<string>('all');
  const [isMinimized, setIsMinimized] = useState(false);
  const [dockerLogs, setDockerLogs] = useState<ConsoleMessage[]>([]);
  const [wsConnected, setWsConnected] = useState(false);
  const consoleEndRef = useRef<HTMLDivElement>(null);
  const wsRef = useRef<WebSocket | null>(null);
  
  // Connect to Docker logs WebSocket
  useEffect(() => {
    if (!isOpen) return;
    
    const cfg = (window as any).RUNTIME_CONFIG || {};
    const apiBase = cfg.API_URL || process.env.REACT_APP_API_URL || 'http://localhost:8847';
    const wsUrl = apiBase.replace(/^http/, 'ws') + '/ws/logs';
    
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;
    
    ws.onopen = () => setWsConnected(true);
    
    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === 'docker_log' && data.data) {
          const logMessage: ConsoleMessage = {
            id: `docker-${Date.now()}-${Math.random()}`,
            timestamp: new Date(data.data.timestamp),
            level: data.data.level || 'info',
            source: 'Docker',
            message: data.data.message,
            container: data.data.container
          };
          setDockerLogs(prev => [...prev.slice(-999), logMessage]);
        }
      } catch (e) {
        console.error('Failed to parse Docker log message:', e);
      }
    };
    
    ws.onclose = () => setWsConnected(false);
    ws.onerror = () => setWsConnected(false);
    
    return () => {
      ws.close();
      wsRef.current = null;
    };
  }, [isOpen]);
  
  useEffect(() => {
    if (consoleEndRef.current) {
      consoleEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages]);
  
  const getLevelColor = (level: ConsoleMessage['level']) => {
    switch (level) {
      case 'error': return '#ef4444';
      case 'warn': return '#f59e0b';
      case 'success': return '#10b981';
      case 'debug': return '#6b7280';
      default: return '#3b82f6';
    }
  };
  
  const getLevelIcon = (level: ConsoleMessage['level']) => {
    switch (level) {
      case 'error': return '❌';
      case 'warn': return '⚠️';
      case 'success': return '✅';
      case 'debug': return '🐛';
      default: return 'ℹ️';
    }
  };
  
  // Combine system messages and Docker logs
  const allMessages = [...messages, ...dockerLogs].sort(
    (a, b) => a.timestamp.getTime() - b.timestamp.getTime()
  );
  
  const filteredMessages = allMessages.filter(msg => {
    const levelMatch = filter === 'all' || 
                     (filter === 'docker' && msg.source === 'Docker') ||
                     (filter !== 'docker' && msg.level === filter);
    
    const containerMatch = containerFilter === 'all' || 
                          !msg.container || 
                          msg.container === containerFilter;
                          
    return levelMatch && containerMatch;
  });
  
  // Get unique containers for filter
  const containers = Array.from(new Set(
    dockerLogs.map(log => log.container).filter(Boolean)
  )).sort();
  
  const exportLogs = () => {
    const logContent = allMessages.map(msg => {
      const container = msg.container ? ` [${msg.container}]` : '';
      return `[${msg.timestamp.toISOString()}] [${msg.level.toUpperCase()}] [${msg.source}]${container} ${msg.message}${
        msg.details ? '\n  Details: ' + JSON.stringify(msg.details, null, 2) : ''
      }`;
    }).join('\n');
    
    const blob = new Blob([logContent], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `pybog-console-${new Date().toISOString()}.log`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };
  
  if (!isOpen) return null;
  
  return (
    <div style={{
      position: 'fixed',
      bottom: 0,
      left: 0,
      right: 0,
      height: isMinimized ? 40 : 300,
      background: '#1a1a1a',
      borderTop: '2px solid #374151',
      boxShadow: '0 -4px 12px rgba(0,0,0,0.2)',
      zIndex: 999,
      display: 'flex',
      flexDirection: 'column',
      transition: 'height 0.3s ease',
    }}>
      {/* Header */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        padding: '8px 12px',
        background: '#0f0f0f',
        borderBottom: '1px solid #374151',
        minHeight: 40,
      }}>
        <Terminal size={16} style={{ color: '#10b981', marginRight: 8 }} />
        <span style={{ color: '#e5e7eb', fontSize: 12, fontWeight: 600 }}>
          Console Output
        </span>
        
        {/* Connection status */}
        <span style={{ 
          color: wsConnected ? '#10b981' : '#6b7280', 
          fontSize: 11,
          background: '#1f2937',
          padding: '2px 8px',
          borderRadius: 4,
        }}>
          Docker: {wsConnected ? 'Connected' : 'Disconnected'}
        </span>
        
        <span style={{ 
          color: '#6b7280', 
          fontSize: 11, 
          marginLeft: 12,
          background: '#1f2937',
          padding: '2px 8px',
          borderRadius: 4,
        }}>
          {allMessages.length} messages
        </span>
        
        {/* Filter buttons */}
        <div style={{ marginLeft: 24, display: 'flex', gap: 8 }}>
          {(['all', 'docker', 'info', 'warn', 'error'] as const).map(level => (
            <button
              key={level}
              onClick={() => setFilter(level)}
              style={{
                padding: '2px 8px',
                fontSize: 11,
                background: filter === level ? '#374151' : 'transparent',
                color: filter === level ? '#e5e7eb' : '#6b7280',
                border: '1px solid #374151',
                borderRadius: 4,
                cursor: 'pointer',
                textTransform: 'capitalize',
              }}
            >
              {level}
            </button>
          ))}
        </div>
        
        {/* Container filter */}
        {containers.length > 0 && (
          <select
            value={containerFilter}
            onChange={(e) => setContainerFilter(e.target.value)}
            style={{
              background: '#1f2937',
              color: '#e5e7eb',
              border: '1px solid #374151',
              borderRadius: 4,
              padding: '2px 8px',
              fontSize: 11,
            }}
          >
            <option value="all">All Containers</option>
            {containers.map(container => (
              <option key={container} value={container}>
                {container?.replace('pybog-', '') || 'Unknown'}
              </option>
            ))}
          </select>
        )}
        
        {/* Actions */}
        <div style={{ marginLeft: 'auto', display: 'flex', gap: 8 }}>
          <button
            onClick={exportLogs}
            style={{
              background: 'transparent',
              border: 'none',
              color: '#6b7280',
              cursor: 'pointer',
              padding: 4,
            }}
            title="Export logs"
          >
            <Download size={16} />
          </button>
          <button
            onClick={() => {
              onClear();
              setDockerLogs([]);
            }}
            style={{
              background: 'transparent',
              border: 'none',
              color: '#6b7280',
              cursor: 'pointer',
              padding: 4,
            }}
            title="Clear console"
          >
            <Trash2 size={16} />
          </button>
          <button
            onClick={() => setIsMinimized(!isMinimized)}
            style={{
              background: 'transparent',
              border: 'none',
              color: '#6b7280',
              cursor: 'pointer',
              padding: 4,
            }}
            title={isMinimized ? "Expand" : "Minimize"}
          >
            {isMinimized ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
          </button>
          <button
            onClick={onClose}
            style={{
              background: 'transparent',
              border: 'none',
              color: '#6b7280',
              cursor: 'pointer',
              padding: 4,
            }}
            title="Close console"
          >
            <X size={16} />
          </button>
        </div>
      </div>
      
      {/* Console content */}
      {!isMinimized && (
        <div style={{
          flex: 1,
          overflow: 'auto',
          padding: '8px 12px',
          fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace',
          fontSize: 11,
        }}>
          {filteredMessages.length === 0 ? (
            <div style={{ color: '#4b5563', fontStyle: 'italic', padding: '12px 0' }}>
              No console messages...
            </div>
          ) : (
            filteredMessages.map((msg) => (
              <div 
                key={msg.id}
                style={{ 
                  marginBottom: 4,
                  display: 'flex',
                  alignItems: 'flex-start',
                  gap: 8,
                }}
              >
                <span style={{ color: '#4b5563', fontSize: 10, minWidth: 60 }}>
                  {msg.timestamp.toLocaleTimeString()}
                </span>
                <span style={{ fontSize: 12 }}>{getLevelIcon(msg.level)}</span>
                <span style={{ 
                  color: '#6b7280', 
                  fontSize: 10,
                  background: '#1f2937',
                  padding: '0 4px',
                  borderRadius: 2,
                  minWidth: 60,
                  textAlign: 'center',
                }}>
                  {msg.source}
                </span>
                {msg.container && (
                  <span style={{ 
                    color: '#3b82f6', 
                    fontSize: 10,
                    background: '#1e3a8a',
                    padding: '0 4px',
                    borderRadius: 2,
                    minWidth: 80,
                    textAlign: 'center',
                  }}>
                    {msg.container.replace('pybog-', '')}
                  </span>
                )}
                <span style={{ color: getLevelColor(msg.level), flex: 1 }}>
                  {msg.message}
                </span>
                {msg.details && (
                  <details style={{ color: '#6b7280', marginLeft: 12 }}>
                    <summary style={{ cursor: 'pointer', fontSize: 10 }}>Details</summary>
                    <pre style={{ 
                      fontSize: 10, 
                      background: '#0f0f0f',
                      padding: 4,
                      borderRadius: 4,
                      marginTop: 4,
                    }}>
                      {JSON.stringify(msg.details, null, 2)}
                    </pre>
                  </details>
                )}
              </div>
            ))
          )}
          <div ref={consoleEndRef} />
        </div>
      )}
    </div>
  );
};

export default ConsolePanel;
