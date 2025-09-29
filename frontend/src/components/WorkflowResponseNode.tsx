import React, { useState, useEffect } from 'react';
import {
  CheckCircle,
  XCircle,
  RefreshCw,
  Edit3,
  FileText,
  AlertTriangle,
  ChevronDown,
  ChevronUp,
  Zap,
  ThermometerSun,
  Wind,
  Gauge,
  Activity,
  BarChart3,
  Settings
} from 'lucide-react';
// import ReactMarkdown from 'react-markdown';
import './WorkflowResponseNode.css';

interface WorkflowResponseNodeProps {
  type: 'text_review' | 'analysis_review' | 'generation_confirmation';
  data: any;
  resumeUrl?: string;
  sessionId: string;
  onApprove: (data: any) => void;
  onReject?: (feedback: string) => void;
  onEdit?: (editedData: any) => void;
  onRetry?: () => void;
  onCancel?: () => void;
}

const WorkflowResponseNode: React.FC<WorkflowResponseNodeProps> = ({
  type,
  data,
  resumeUrl,
  sessionId,
  onApprove,
  onReject,
  onEdit,
  onRetry,
  onCancel
}) => {
  const [isExpanded, setIsExpanded] = useState(true);
  const [isEditing, setIsEditing] = useState(false);
  const [editedContent, setEditedContent] = useState('');
  const [feedback, setFeedback] = useState('');
  const [showFeedback, setShowFeedback] = useState(false);
  const [activeTab, setActiveTab] = useState<'inputs' | 'outputs' | 'logic'>('inputs');

  useEffect(() => {
    if (type === 'text_review' && data.extractedText) {
      setEditedContent(data.extractedText);
    }
  }, [type, data]);

  const getIcon = (pointType: string) => {
    const lower = pointType.toLowerCase();
    if (lower.includes('temp')) return <ThermometerSun size={14} />;
    if (lower.includes('flow') || lower.includes('cfm')) return <Wind size={14} />;
    if (lower.includes('pressure') || lower.includes('psi')) return <Gauge size={14} />;
    if (lower.includes('status')) return <Activity size={14} />;
    return <Settings size={14} />;
  };

  const renderTextReview = () => {
    const { extractedText, textQuality, qualityScore, qualityIssues, recommendations, hvacTermsFound } = data;
    
    return (
      <div className="response-content text-review">
        {/* Quality Indicator */}
        <div className="quality-indicator">
          <div className="quality-score" data-quality={textQuality?.toLowerCase() || 'unknown'}>
            <BarChart3 size={16} />
            <span>Quality: {textQuality || 'Unknown'}</span>
            {qualityScore && <span className="score-badge">{qualityScore}%</span>}
          </div>
          {hvacTermsFound > 0 && (
            <div className="hvac-terms">
              <Zap size={14} />
              <span>{hvacTermsFound} HVAC terms found</span>
            </div>
          )}
        </div>

        {/* Issues & Recommendations */}
        {qualityIssues && qualityIssues.length > 0 && (
          <div className="quality-issues">
            <div className="section-header">
              <AlertTriangle size={14} />
              <span>Quality Issues</span>
            </div>
            <ul>
              {qualityIssues.map((issue: string, idx: number) => (
                <li key={idx}>{issue}</li>
              ))}
            </ul>
          </div>
        )}

        {recommendations && recommendations.length > 0 && (
          <div className="recommendations">
            <div className="section-header">
              <FileText size={14} />
              <span>Recommendations</span>
            </div>
            <ul>
              {recommendations.map((rec: string, idx: number) => (
                <li key={idx}>{rec}</li>
              ))}
            </ul>
          </div>
        )}

        {/* Extracted Text */}
        <div className="extracted-text-container">
          <div className="section-header">
            <FileText size={14} />
            <span>Extracted Text</span>
            {!isEditing && (
              <button 
                className="edit-button"
                onClick={() => setIsEditing(true)}
                title="Edit extracted text"
              >
                <Edit3 size={14} />
              </button>
            )}
          </div>
          
          {isEditing ? (
            <div className="edit-mode">
              <textarea
                value={editedContent}
                onChange={(e) => setEditedContent(e.target.value)}
                className="text-editor"
                rows={10}
              />
              <div className="edit-actions">
                <button 
                  className="btn-save"
                  onClick={() => {
                    setIsEditing(false);
                    if (onEdit) onEdit({ ...data, extractedText: editedContent });
                  }}
                >
                  Save Changes
                </button>
                <button 
                  className="btn-cancel"
                  onClick={() => {
                    setIsEditing(false);
                    setEditedContent(extractedText);
                  }}
                >
                  Cancel
                </button>
              </div>
            </div>
          ) : (
            <div className="text-display">
              <pre>{extractedText}</pre>
            </div>
          )}
        </div>
      </div>
    );
  };

  const renderAnalysisReview = () => {
    const { analysis, summary } = data;
    
    if (!analysis) return null;
    
    const inputs = analysis.inputs || analysis.io_points?.inputs || [];
    const outputs = analysis.outputs || analysis.io_points?.outputs || [];
    const controlBlocks = analysis.control_blocks || [];
    const pseudocode = analysis.pseudocode || [];
    const issues = analysis.issues || [];

    return (
      <div className="response-content analysis-review">
        {/* Summary Stats */}
        {summary && (
          <div className="analysis-summary">
            <div className="stat-card">
              <span className="stat-value">{summary.totalInputs || 0}</span>
              <span className="stat-label">Inputs</span>
            </div>
            <div className="stat-card">
              <span className="stat-value">{summary.totalOutputs || 0}</span>
              <span className="stat-label">Outputs</span>
            </div>
            <div className="stat-card">
              <span className="stat-value">{summary.totalBlocks || 0}</span>
              <span className="stat-label">Blocks</span>
            </div>
            <div className="stat-card complexity" data-complexity={summary.complexity?.toLowerCase()}>
              <span className="stat-value">{summary.complexity || 'N/A'}</span>
              <span className="stat-label">Complexity</span>
            </div>
          </div>
        )}

        {/* Tabbed Content */}
        <div className="analysis-tabs">
          <div className="tab-header">
            <button 
              className={`tab-button ${activeTab === 'inputs' ? 'active' : ''}`}
              onClick={() => setActiveTab('inputs')}
            >
              Inputs ({inputs.length})
            </button>
            <button 
              className={`tab-button ${activeTab === 'outputs' ? 'active' : ''}`}
              onClick={() => setActiveTab('outputs')}
            >
              Outputs ({outputs.length})
            </button>
            <button 
              className={`tab-button ${activeTab === 'logic' ? 'active' : ''}`}
              onClick={() => setActiveTab('logic')}
            >
              Logic ({pseudocode.length})
            </button>
          </div>

          <div className="tab-content">
            {activeTab === 'inputs' && (
              <div className="io-points-list">
                {inputs.map((point: any, idx: number) => {
                  const name = typeof point === 'string' ? point : point.name;
                  const type = typeof point === 'object' ? point.type : 'Unknown';
                  return (
                    <div key={idx} className="io-point-item input">
                      {getIcon(name)}
                      <span className="point-name">{name}</span>
                      <span className="point-type">{type}</span>
                    </div>
                  );
                })}
              </div>
            )}

            {activeTab === 'outputs' && (
              <div className="io-points-list">
                {outputs.map((point: any, idx: number) => {
                  const name = typeof point === 'string' ? point : point.name;
                  const type = typeof point === 'object' ? point.type : 'Unknown';
                  return (
                    <div key={idx} className="io-point-item output">
                      {getIcon(name)}
                      <span className="point-name">{name}</span>
                      <span className="point-type">{type}</span>
                    </div>
                  );
                })}
              </div>
            )}

            {activeTab === 'logic' && (
              <div className="logic-blocks">
                {pseudocode.map((block: any, idx: number) => (
                  <div key={idx} className="logic-block">
                    <div className="block-header">
                      <Settings size={14} />
                      <span>{block.block || `Block ${idx + 1}`}</span>
                      {block.complexity && (
                        <span className="complexity-badge" data-level={block.complexity}>
                          Complexity: {block.complexity}
                        </span>
                      )}
                    </div>
                    <div className="block-logic">
                      {(block.logic || []).map((line: string, lineIdx: number) => (
                        <div key={lineIdx} className="logic-line">
                          <span className="line-number">{lineIdx + 1}</span>
                          <code>{line}</code>
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Issues */}
        {issues.length > 0 && (
          <div className="analysis-issues">
            <div className="section-header">
              <AlertTriangle size={14} />
              <span>Issues Found ({issues.length})</span>
            </div>
            <ul>
              {issues.map((issue: string, idx: number) => (
                <li key={idx}>{issue}</li>
              ))}
            </ul>
          </div>
        )}
      </div>
    );
  };

  const renderGenerationConfirmation = () => {
    const { bogFilePath, downloadUrl } = data;
    
    return (
      <div className="response-content generation-confirmation">
        <div className="success-message">
          <CheckCircle size={24} />
          <h3>BOG File Generated Successfully!</h3>
        </div>
        
        {bogFilePath && (
          <div className="file-info">
            <FileText size={16} />
            <span className="file-path">{bogFilePath}</span>
          </div>
        )}

        {downloadUrl && (
          <div className="download-section">
            <a 
              href={downloadUrl} 
              download 
              className="download-button"
              target="_blank"
              rel="noopener noreferrer"
            >
              <FileText size={16} />
              Download BOG File
            </a>
          </div>
        )}
      </div>
    );
  };

  const getContent = () => {
    switch (type) {
      case 'text_review':
        return renderTextReview();
      case 'analysis_review':
        return renderAnalysisReview();
      case 'generation_confirmation':
        return renderGenerationConfirmation();
      default:
        return null;
    }
  };

  const getTitle = () => {
    switch (type) {
      case 'text_review':
        return 'Text Extraction Review';
      case 'analysis_review':
        return 'HVAC Analysis Review';
      case 'generation_confirmation':
        return 'BOG Generation Complete';
      default:
        return 'Workflow Response';
    }
  };

  return (
    <div className="workflow-response-node" data-type={type}>
      {/* Header */}
      <div className="node-header" onClick={() => setIsExpanded(!isExpanded)}>
        <div className="header-left">
          <div className="node-icon">
            {type === 'text_review' && <FileText size={16} />}
            {type === 'analysis_review' && <BarChart3 size={16} />}
            {type === 'generation_confirmation' && <CheckCircle size={16} />}
          </div>
          <h3 className="node-title">{getTitle()}</h3>
        </div>
        <div className="header-right">
          <button className="expand-toggle">
            {isExpanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
          </button>
        </div>
      </div>

      {/* Content */}
      {isExpanded && (
        <>
          <div className="node-body">
            {getContent()}
          </div>

          {/* Actions */}
          <div className="node-actions">
            {/* Primary Approve/Generate buttons surfaced to keep UX simple */}
            {type === 'text_review' && (
              <>
                <button
                  className="action-button primary"
                  onClick={() => onApprove?.({ action: 'approve_text', text: editedContent || data.extractedText })}
                >
                  Approve & Continue
                </button>
                <button
                  className="action-button"
                  onClick={() => setIsEditing(true)}
                >
                  Edit Text
                </button>
              </>
            )}
            {type === 'analysis_review' && (
              <>
                <button
                  className="action-button primary"
                  onClick={() => onApprove?.({ action: 'approve_analysis' })}
                >
                  Approve Analysis
                </button>
                {onReject && (
                  <button
                    className="action-button"
                    onClick={() => onReject('refine_analysis')}
                  >
                    Request Changes
                  </button>
                )}
              </>
            )}
            {type === 'generation_confirmation' && data?.downloadUrl && (
              <a
                className="action-button primary"
                href={data.downloadUrl}
                target="_blank"
                rel="noopener noreferrer"
              >
                Download BOG
              </a>
            )}
            {/* Raw JSON toggle */}
            <details style={{ marginTop: 8 }}>
              <summary>Raw response</summary>
              <pre style={{ maxHeight: 240, overflow: 'auto' }}>{JSON.stringify(data, null, 2)}</pre>
            </details>

            {type === 'generation_confirmation' && (
              <>
                <button className="action-button primary" onClick={() => onApprove(data)}>
                  <CheckCircle size={16} />
                  Confirm
                </button>
                {onRetry && (
                  <button className="action-button secondary" onClick={onRetry}>
                    <RefreshCw size={16} />
                    Regenerate
                  </button>
                )}
                {onCancel && (
                  <button className="action-button danger" onClick={onCancel}>
                    <XCircle size={16} />
                    Cancel
                  </button>
                )}
              </>
            )}
          </div>
        </>
      )}
    </div>
  );
};

export default WorkflowResponseNode;
