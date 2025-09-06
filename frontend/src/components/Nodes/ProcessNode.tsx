import React from 'react';
import './ProcessNode.css';
import { Handle, Position } from 'reactflow';
import { Settings, CheckCircle, AlertCircle, Loader2, Zap } from 'lucide-react';

interface ProcessNodeData {
  stepKey: string;
  title: string;
  detail?: string;
  status: 'running' | 'ok' | 'error' | 'waiting';
  metrics?: Record<string, any>;
  timestamp?: string;
}

const ProcessNode: React.FC<{ data: ProcessNodeData }> = ({ data }) => {
  const getStatusIcon = () => {
    switch (data.status) {
      case 'running':
        return <Loader2 className="animate-spin" size={14} />;
      case 'ok':
        return <CheckCircle size={14} />;
      case 'error':
        return <AlertCircle size={14} />;
      default:
        return <Settings size={14} />;
    }
  };

  const getStatusColor = () => {
    switch (data.status) {
      case 'running':
        return '#f59e0b';
      case 'ok':
        return '#10b981';
      case 'error':
        return '#ef4444';
      default:
        return '#6b7280';
    }
  };

  return (
    <div
      style={{
        background: 'linear-gradient(135deg, #1e293b 0%, #334155 100%)',
        border: `2px solid ${getStatusColor()}`,
        borderRadius: '8px',
        padding: '8px 12px',
        minWidth: '200px',
        maxWidth: '280px',
        boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
        position: 'relative',
      }}
    >
      <Handle
        type="target"
        position={Position.Left}
        style={{
          background: getStatusColor(),
          width: 8,
          height: 8,
          border: '2px solid #fff',
        }}
      />
      
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
        <div style={{ color: getStatusColor() }}>
          {getStatusIcon()}
        </div>
        <div style={{ 
          color: '#f1f5f9', 
          fontSize: '13px', 
          fontWeight: 600,
          flex: 1,
        }}>
          {data.title}
        </div>
        <Zap size={12} style={{ color: '#64748b' }} />
      </div>
      
      {data.detail && (
        <div style={{ 
          color: '#cbd5e1', 
          fontSize: '11px',
          marginTop: '4px',
          lineHeight: '1.4',
        }}>
          {data.detail}
        </div>
      )}
      
      {data.metrics && Object.keys(data.metrics).length > 0 && (
        <div style={{
          marginTop: '6px',
          paddingTop: '6px',
          borderTop: '1px solid rgba(148, 163, 184, 0.2)',
          display: 'flex',
          gap: '12px',
          flexWrap: 'wrap',
        }}>
          {Object.entries(data.metrics).slice(0, 3).map(([key, value]) => (
            <div key={key} style={{ fontSize: '10px' }}>
              <span style={{ color: '#94a3b8' }}>{key}:</span>
              <span style={{ color: '#e2e8f0', marginLeft: '4px', fontWeight: 600 }}>
                {typeof value === 'number' ? value.toLocaleString() : String(value)}
              </span>
            </div>
          ))}
        </div>
      )}

      <Handle
        type="source"
        position={Position.Right}
        style={{
          background: getStatusColor(),
          width: 8,
          height: 8,
          border: '2px solid #fff',
        }}
      />
    </div>
  );
};

export default ProcessNode;
