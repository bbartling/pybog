import React, { useState } from 'react';
import { 
  CheckCircle, Edit3, AlertCircle, 
  Cpu, ArrowRight, ArrowLeft, Settings 
} from 'lucide-react';

// Using unified type from types/analysis.ts
import { AnalysisData } from '../types/analysis';

interface AnalysisBlockProps {
  analysis: AnalysisData;
  onApprove: () => void;
  onRequestChanges: (feedback: string) => void;
  status?: 'idle' | 'pending' | 'approved' | 'generating' | 'complete';
}

const AnalysisBlock: React.FC<AnalysisBlockProps> = ({
  analysis,
  onApprove,
  onRequestChanges,
  status = 'idle'
}) => {
  const [showFeedback, setShowFeedback] = useState(false);
  const [feedback, setFeedback] = useState('');
  const [expandedBlocks, setExpandedBlocks] = useState<Record<string, boolean>>({});

  const toggleBlock = (blockName: string) => {
    setExpandedBlocks(prev => ({
      ...prev,
      [blockName]: !prev[blockName]
    }));
  };

  const handleRequestChanges = () => {
    if (feedback.trim()) {
      onRequestChanges(feedback);
      setFeedback('');
      setShowFeedback(false);
    }
  };

  const getStatusColor = () => {
    switch (status) {
      case 'pending': return '#2563eb';
      case 'approved': return '#16a34a';
      case 'generating': return '#ea580c';
      case 'complete': return '#059669';
      default: return '#64748b';
    }
  };

  const getStatusText = () => {
    switch (status) {
      case 'pending': return 'READY FOR REVIEW';
      case 'approved': return 'APPROVED';
      case 'generating': return 'GENERATING BOG';
      case 'complete': return 'COMPLETE';
      default: return 'IDLE';
    }
  };

  return (
    <div className="analysis-block">
      <div className="analysis-header">
        <div className="analysis-title">
          <Cpu className="title-icon" />
          <span>HVAC Control Analysis</span>
          <div 
            className="status-indicator"
            style={{ backgroundColor: getStatusColor() }}
          >
            {getStatusText()}
          </div>
        </div>
      </div>

      <div className="analysis-content">
        {/* Input/Output Pins */}
        <div className="io-section">
          <div className="io-group">
            <div className="io-header">
              <ArrowRight className="io-icon" />
              <span>Inputs ({analysis.inputs.length})</span>
            </div>
            <div className="io-pins">
              {analysis.inputs.map((input, index) => (
                <div key={index} className="io-pin input-pin">
                  <div className="pin-connector"></div>
                  <span className="pin-label">{typeof input === 'string' ? input : input.name}</span>
                </div>
              ))}
            </div>
          </div>

          <div className="io-group">
            <div className="io-header">
              <ArrowLeft className="io-icon" />
              <span>Outputs ({analysis.outputs.length})</span>
            </div>
            <div className="io-pins">
              {analysis.outputs.map((output, index) => (
                <div key={index} className="io-pin output-pin">
                  <span className="pin-label">{typeof output === 'string' ? output : output.name}</span>
                  <div className="pin-connector"></div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Control Logic Blocks */}
        <div className="logic-section">
          <div className="section-header">
            <Settings className="section-icon" />
            <span>Control Logic Blocks ({analysis.blocks.length})</span>
          </div>
          
          {analysis.blocks.map((block, index) => (
            <div key={index} className="logic-block">
              <div 
                className="logic-block-header"
                onClick={() => toggleBlock(typeof block === 'string' ? block : block.name)}
              >
                <span className="block-name">{typeof block === 'string' ? block : block.name}</span>
                <div className={`expand-arrow ${expandedBlocks[typeof block === 'string' ? block : block.name] ? 'expanded' : ''}`}>
                  ▼
                </div>
              </div>
              
              {expandedBlocks[typeof block === 'string' ? block : block.name] && (
                <div className="logic-content">
                  <pre className="pseudocode">
                    {typeof block === 'string' ? 
                      analysis.pseudocode.join('\n') : 
                      (block.logic || 'No logic defined')}
                  </pre>
                </div>
              )}
            </div>
          ))}
        </div>

        {/* Action Buttons */}
        {status === 'pending' && (
          <div className="analysis-actions">
            {!showFeedback ? (
              <>
                <button
                  className="action-btn approve-btn"
                  onClick={onApprove}
                  disabled={status !== 'pending'}
                >
                  <CheckCircle className="btn-icon" />
                  {status === 'pending' ? 'Approve & Generate BOG' : 'Generating...'}
                </button>
                
                <button
                  className="action-btn changes-btn"
                  onClick={() => setShowFeedback(true)}
                  disabled={status !== 'pending'}
                >
                  <Edit3 className="btn-icon" />
                  Request Changes
                </button>
              </>
            ) : (
              <div className="feedback-section">
                <div className="feedback-header">
                  <AlertCircle className="feedback-icon" />
                  <span>Describe the changes you'd like:</span>
                </div>
                <textarea
                  className="feedback-input"
                  value={feedback}
                  onChange={(e) => setFeedback(e.target.value)}
                  placeholder="Please describe what changes you'd like to the analysis..."
                  rows={3}
                />
                <div className="feedback-actions">
                  <button
                    className="action-btn cancel-btn"
                    onClick={() => {
                      setShowFeedback(false);
                      setFeedback('');
                    }}
                  >
                    Cancel
                  </button>
                  <button
                    className="action-btn submit-btn"
                    onClick={handleRequestChanges}
                    disabled={!feedback.trim()}
                  >
                    Submit Changes
                  </button>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default AnalysisBlock;
