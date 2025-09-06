import React from 'react';
import { Handle, Position } from 'reactflow';
import { CheckCircle, AlertCircle, Loader2, Zap, Activity } from 'lucide-react';
import './NiagaraNodes.css';

interface ProcessNodeData {
  stepKey: string;
  title: string;
  detail?: string;
  status: 'running' | 'ok' | 'error' | 'waiting';
  metrics?: Record<string, any>;
  timestamp?: string;
}

const ProcessNodeNiagara: React.FC<{ data: ProcessNodeData }> = ({ data }) => {
  const getStatusIcon = () => {
    switch (data.status) {
      case 'running':
        return <Loader2 className="animate-spin" size={14} />;
      case 'ok':
        return <CheckCircle size={14} />;
      case 'error':
        return <AlertCircle size={14} />;
      default:
        return <Activity size={14} />;
    }
  };

  const getStatusClass = () => {
    switch (data.status) {
      case 'running':
        return 'running';
      case 'ok':
        return 'ok';
      case 'error':
        return 'alarm';
      default:
        return 'fault';
    }
  };

  const isProcessing = data.status === 'running';

  return (
    <div className={`niagara-node process-node ${isProcessing ? 'processing' : ''}`}>
      {/* Input Port */}
      <Handle
        type="target"
        position={Position.Left}
        className="niagara-port input-port"
        style={{
          background: '#22d3ee',
          width: 10,
          height: 10,
          border: '2px solid #0f172a',
          left: -5
        }}
      />
      
      {/* Node Header */}
      <div className="niagara-node-header">
        <div className="node-icon">
          <Zap size={14} />
        </div>
        <div className="node-title">{data.stepKey || 'Process'}</div>
        <div className={`node-status ${getStatusClass()}`}>
          {getStatusIcon()}
        </div>
      </div>
      
      {/* Node Content */}
      <div className="niagara-node-content">
        <div className="node-value-display" style={{ fontSize: '11px' }}>
          {data.title}
        </div>
        
        {data.detail && (
          <div style={{ 
            marginTop: '4px',
            fontSize: '10px',
            color: '#94a3b8',
            fontStyle: 'italic'
          }}>
            {data.detail}
          </div>
        )}
        
        {data.metrics && Object.keys(data.metrics).length > 0 && (
          <div className="process-metrics">
            {Object.entries(data.metrics).slice(0, 3).map(([key, value]) => (
              <div key={key} className="metric-item">
                <span className="metric-label">{key}</span>
                <span className="metric-value">
                  {typeof value === 'number' ? value.toLocaleString() : String(value)}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
      
      {/* Output Port */}
      <Handle
        type="source"
        position={Position.Right}
        className="niagara-port output-port"
        style={{
          background: '#fb923c',
          width: 10,
          height: 10,
          border: '2px solid #0f172a',
          right: -5
        }}
      />
    </div>
  );
};

export default ProcessNodeNiagara;
