import React, { useState, memo } from 'react';
import { NodeProps, Handle, Position } from 'reactflow';
import {
  Database, ChevronDown, ChevronRight, CheckCircle, 
  XCircle, Edit3, Download, Thermometer, Gauge, 
  Wind, Droplets, ToggleLeft, Sliders, GitBranch,
  AlertCircle, Loader2
} from 'lucide-react';
import './AnalysisNodeEnhanced.css';

interface IOPoint {
  name: string;
  type?: string;
  units?: string;
  range?: string;
  description?: string;
}

interface ControlSequence {
  name: string;
  type?: string;
  description?: string;
  components?: string[];
}

interface AnalysisNodeData {
  sessionId: string;
  analysis: {
    inputs?: (string | IOPoint)[];
    outputs?: (string | IOPoint)[];
    control_sequences?: ControlSequence[];
    pseudocode?: string[];
    setpoints?: Record<string, any>;
    alarms?: any[];
    io_summary?: {
      total_inputs: number;
      total_outputs: number;
      has_errors?: boolean;
    };
  };
  onApprove?: () => void;
  onRequestChanges?: (feedback: string) => void;
  approving?: boolean;
  processing?: boolean;
  timestamp?: Date;
}

const AnalysisNodeEnhanced: React.FC<NodeProps<AnalysisNodeData>> = ({ data }) => {
  const [expandedSections, setExpandedSections] = useState({
    inputs: true,
    outputs: true,
    sequences: false,
    pseudocode: false,
    setpoints: false
  });
  const [feedback, setFeedback] = useState('');
  const [showFeedback, setShowFeedback] = useState(false);

  const toggleSection = (section: keyof typeof expandedSections) => {
    setExpandedSections(prev => ({ ...prev, [section]: !prev[section] }));
  };

  const getPointIcon = (point: string | IOPoint) => {
    const name = typeof point === 'string' ? point : point.name;
    const nameLower = name.toLowerCase();
    
    if (nameLower.includes('temp')) return <Thermometer size={12} className="point-icon" />;
    if (nameLower.includes('pressure')) return <Gauge size={12} className="point-icon" />;
    if (nameLower.includes('flow') || nameLower.includes('cfm')) return <Wind size={12} className="point-icon" />;
    if (nameLower.includes('humid')) return <Droplets size={12} className="point-icon" />;
    if (nameLower.includes('status')) return <ToggleLeft size={12} className="point-icon" />;
    if (nameLower.includes('setpoint')) return <Sliders size={12} className="point-icon" />;
    return <Database size={12} className="point-icon" />;
  };

  const getPointType = (point: string | IOPoint): string => {
    if (typeof point === 'object' && point.type) return point.type;
    const name = typeof point === 'string' ? point : point.name;
    const nameLower = name.toLowerCase();
    
    if (nameLower.includes('temp') || nameLower.includes('pressure')) return 'AI';
    if (nameLower.includes('status') || nameLower.includes('enable')) return 'BI';
    if (nameLower.includes('command') || nameLower.includes('valve')) return 'BO';
    if (nameLower.includes('setpoint') || nameLower.includes('output')) return 'AO';
    return 'AI';
  };

  const handleApprove = () => {
    if (!data.approving && data.onApprove) {
      data.onApprove();
    }
  };

  const handleRequestChanges = () => {
    if (feedback.trim() && data.onRequestChanges) {
      data.onRequestChanges(feedback);
      setFeedback('');
      setShowFeedback(false);
    }
  };

  const { analysis } = data;
  const inputCount = analysis.inputs?.length || 0;
  const outputCount = analysis.outputs?.length || 0;
  const sequenceCount = analysis.control_sequences?.length || 0;

  return (
    <div className="analysis-node-enhanced">
      <Handle type="target" position={Position.Top} />
      
      {/* Header */}
      <div className="analysis-header">
        <div className="analysis-title">
          <Database size={16} />
          <span>HVAC Analysis Results</span>
        </div>
        <div className="analysis-stats">
          <span className="stat">
            <span className="stat-value">{inputCount}</span>
            <span className="stat-label">IN</span>
          </span>
          <span className="stat">
            <span className="stat-value">{outputCount}</span>
            <span className="stat-label">OUT</span>
          </span>
          <span className="stat">
            <span className="stat-value">{sequenceCount}</span>
            <span className="stat-label">SEQ</span>
          </span>
        </div>
      </div>

      {/* I/O Points Section */}
      <div className="analysis-section">
        {/* Inputs */}
        <div className="section-header" onClick={() => toggleSection('inputs')}>
          {expandedSections.inputs ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
          <span className="section-title">Input Points</span>
          <span className="section-count">{inputCount}</span>
        </div>
        
        {expandedSections.inputs && analysis.inputs && (
          <div className="io-table">
            <div className="io-table-header">
              <div className="io-col-icon"></div>
              <div className="io-col-name">Name</div>
              <div className="io-col-type">Type</div>
              <div className="io-col-status">Status</div>
            </div>
            {analysis.inputs.slice(0, 10).map((input, idx) => {
              const name = typeof input === 'string' ? input : input.name;
              const type = getPointType(input);
              return (
                <div key={idx} className="io-row input">
                  <div className="io-col-icon">{getPointIcon(input)}</div>
                  <div className="io-col-name">{name}</div>
                  <div className="io-col-type">
                    <span className={`type-badge ${type}`}>{type}</span>
                  </div>
                  <div className="io-col-status">
                    <span className="status-indicator ok">OK</span>
                  </div>
                </div>
              );
            })}
            {inputCount > 10 && (
              <div className="io-more">+{inputCount - 10} more inputs...</div>
            )}
          </div>
        )}

        {/* Outputs */}
        <div className="section-header" onClick={() => toggleSection('outputs')}>
          {expandedSections.outputs ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
          <span className="section-title">Output Points</span>
          <span className="section-count">{outputCount}</span>
        </div>
        
        {expandedSections.outputs && analysis.outputs && (
          <div className="io-table">
            <div className="io-table-header">
              <div className="io-col-icon"></div>
              <div className="io-col-name">Name</div>
              <div className="io-col-type">Type</div>
              <div className="io-col-status">Status</div>
            </div>
            {analysis.outputs.slice(0, 10).map((output, idx) => {
              const name = typeof output === 'string' ? output : output.name;
              const type = getPointType(output);
              return (
                <div key={idx} className="io-row output">
                  <div className="io-col-icon">{getPointIcon(output)}</div>
                  <div className="io-col-name">{name}</div>
                  <div className="io-col-type">
                    <span className={`type-badge ${type}`}>{type}</span>
                  </div>
                  <div className="io-col-status">
                    <span className="status-indicator ok">OK</span>
                  </div>
                </div>
              );
            })}
            {outputCount > 10 && (
              <div className="io-more">+{outputCount - 10} more outputs...</div>
            )}
          </div>
        )}
      </div>

      {/* Control Sequences */}
      {analysis.control_sequences && analysis.control_sequences.length > 0 && (
        <div className="analysis-section">
          <div className="section-header" onClick={() => toggleSection('sequences')}>
            {expandedSections.sequences ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
            <span className="section-title">Control Sequences</span>
            <span className="section-count">{sequenceCount}</span>
          </div>
          
          {expandedSections.sequences && (
            <div className="sequences-list">
              {analysis.control_sequences.map((seq, idx) => (
                <div key={idx} className="sequence-item">
                  <GitBranch size={14} className="sequence-icon" />
                  <div className="sequence-content">
                    <div className="sequence-name">{seq.name}</div>
                    {seq.description && (
                      <div className="sequence-desc">{seq.description}</div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Pseudocode */}
      {analysis.pseudocode && analysis.pseudocode.length > 0 && (
        <div className="analysis-section">
          <div className="section-header" onClick={() => toggleSection('pseudocode')}>
            {expandedSections.pseudocode ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
            <span className="section-title">Control Logic</span>
          </div>
          
          {expandedSections.pseudocode && (
            <div className="pseudocode-block">
              <pre>{analysis.pseudocode.join('\n')}</pre>
            </div>
          )}
        </div>
      )}

      {/* Approval Section */}
      <div className="approval-section">
        {data.processing ? (
          <div className="processing-indicator">
            <Loader2 className="animate-spin" size={16} />
            <span>Processing...</span>
          </div>
        ) : (
          <>
            <button 
              className="approve-btn"
              onClick={handleApprove}
              disabled={data.approving}
            >
              {data.approving ? (
                <>
                  <Loader2 className="animate-spin" size={14} />
                  <span>Generating BOG...</span>
                </>
              ) : (
                <>
                  <CheckCircle size={14} />
                  <span>Approve & Generate</span>
                </>
              )}
            </button>
            
            <button 
              className="changes-btn"
              onClick={() => setShowFeedback(!showFeedback)}
            >
              <Edit3 size={14} />
              <span>Request Changes</span>
            </button>
          </>
        )}
      </div>

      {/* Feedback Input */}
      {showFeedback && (
        <div className="feedback-section">
          <textarea
            className="feedback-input"
            placeholder="Describe the changes you need..."
            value={feedback}
            onChange={(e) => setFeedback(e.target.value)}
            rows={3}
          />
          <div className="feedback-actions">
            <button 
              className="feedback-submit"
              onClick={handleRequestChanges}
              disabled={!feedback.trim()}
            >
              Send Feedback
            </button>
            <button 
              className="feedback-cancel"
              onClick={() => {
                setShowFeedback(false);
                setFeedback('');
              }}
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* Error Indicator */}
      {analysis.io_summary?.has_errors && (
        <div className="error-indicator">
          <AlertCircle size={14} />
          <span>Validation errors detected</span>
        </div>
      )}

      <Handle type="source" position={Position.Bottom} />
    </div>
  );
};

export default memo(AnalysisNodeEnhanced);
