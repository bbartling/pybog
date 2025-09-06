import React, { useState } from 'react';
import { Handle, Position } from 'reactflow';
import { 
  FileText, 
  CheckCircle, 
  AlertCircle, 
  Edit3, 
  RefreshCw,
  TrendingUp,
  X 
} from 'lucide-react';
import './NodeStyles.css';

interface TextReviewNodeData {
  sessionId: string;
  extractedText: string;
  fileCount: number;
  totalCharacters: number;
  estimatedTokens?: number;
  textQuality: 'excellent' | 'good' | 'fair' | 'warning' | 'poor';
  qualityScore: number;
  qualityIssues: string[];
  recommendations: string[];
  hvacTermsFound?: number;
  currentStep?: number;
  totalSteps?: number;
  progress?: {
    percentage: number;
    phase: string;
    description: string;
    eta: string;
  };
  actions?: {
    [key: string]: {
      label: string;
      action: string;
      description: string;
      recommended: boolean;
      confidence: number;
    };
  };
  onApprove: (extractedText: string) => void;
  onEdit: (extractedText: string) => void;
  onRetry: () => void;
  onCancel?: () => void;
}

const TextReviewNode: React.FC<{ data: TextReviewNodeData }> = ({ data }) => {
  const [isExpanded, setIsExpanded] = useState(true);
  const [editedText, setEditedText] = useState(data.extractedText);
  const [isEditing, setIsEditing] = useState(false);

  const getQualityColor = () => {
    switch (data.textQuality) {
      case 'excellent': return '#10b981';
      case 'good': return '#3b82f6';
      case 'fair': return '#f59e0b';
      case 'warning': return '#ef4444';
      case 'poor': return '#991b1b';
      default: return '#6b7280';
    }
  };

  const handleApprove = () => {
    data.onApprove(isEditing ? editedText : data.extractedText);
  };

  const handleSaveEdit = () => {
    data.onEdit(editedText);
    setIsEditing(false);
  };

  const handleCancelEdit = () => {
    setEditedText(data.extractedText);
    setIsEditing(false);
  };

  return (
    <div 
      className="text-review-node"
      style={{
        background: 'linear-gradient(135deg, #ffffff 0%, #f9fafb 100%)',
        border: `2px solid ${getQualityColor()}`,
        borderRadius: '12px',
        padding: '16px',
        width: '480px',
        boxShadow: '0 4px 12px rgba(0,0,0,0.1)',
      }}
    >
      <Handle type="target" position={Position.Top} />
      
      {/* Header with quality indicator */}
      <div style={{ 
        display: 'flex', 
        justifyContent: 'space-between', 
        alignItems: 'center',
        marginBottom: '12px',
        borderBottom: '1px solid #e5e7eb',
        paddingBottom: '12px'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <FileText size={20} color={getQualityColor()} />
          <h3 style={{ margin: 0, fontSize: '16px', fontWeight: 600 }}>
            Text Extraction Review
          </h3>
          {data.currentStep && data.totalSteps && (
            <span style={{ 
              fontSize: '12px', 
              color: '#6b7280',
              background: '#f3f4f6',
              padding: '2px 8px',
              borderRadius: '4px'
            }}>
              Step {data.currentStep}/{data.totalSteps}
            </span>
          )}
        </div>
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          style={{
            background: 'none',
            border: 'none',
            cursor: 'pointer',
            padding: '4px'
          }}
        >
          {isExpanded ? '−' : '+'}
        </button>
      </div>

      {isExpanded && (
        <>
          {/* Progress Bar */}
          {data.progress && (
            <div style={{ marginBottom: '16px' }}>
              <div style={{ 
                display: 'flex', 
                justifyContent: 'space-between',
                fontSize: '12px',
                color: '#6b7280',
                marginBottom: '4px'
              }}>
                <span>{data.progress.phase}</span>
                <span>{data.progress.percentage}%</span>
              </div>
              <div style={{
                width: '100%',
                height: '6px',
                background: '#e5e7eb',
                borderRadius: '3px',
                overflow: 'hidden'
              }}>
                <div style={{
                  width: `${data.progress.percentage}%`,
                  height: '100%',
                  background: getQualityColor(),
                  transition: 'width 0.3s ease'
                }} />
              </div>
              <div style={{ 
                fontSize: '11px', 
                color: '#9ca3af',
                marginTop: '2px'
              }}>
                {data.progress.description}
              </div>
            </div>
          )}

          {/* Quality Assessment */}
          <div style={{
            background: '#f9fafb',
            borderRadius: '8px',
            padding: '12px',
            marginBottom: '12px'
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
              <span style={{ fontSize: '13px', fontWeight: 500 }}>Text Quality</span>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <TrendingUp size={14} color={getQualityColor()} />
                <span style={{ 
                  color: getQualityColor(), 
                  fontWeight: 600,
                  fontSize: '13px'
                }}>
                  {data.textQuality.toUpperCase()} ({data.qualityScore}%)
                </span>
              </div>
            </div>

            {/* File Stats */}
            <div style={{ 
              display: 'grid', 
              gridTemplateColumns: '1fr 1fr 1fr',
              gap: '8px',
              marginBottom: '8px'
            }}>
              <div style={{ textAlign: 'center' }}>
                <div style={{ fontSize: '18px', fontWeight: 600 }}>{data.fileCount}</div>
                <div style={{ fontSize: '11px', color: '#6b7280' }}>Files</div>
              </div>
              <div style={{ textAlign: 'center' }}>
                <div style={{ fontSize: '18px', fontWeight: 600 }}>
                  {(data.totalCharacters / 1000).toFixed(1)}k
                </div>
                <div style={{ fontSize: '11px', color: '#6b7280' }}>Characters</div>
              </div>
              <div style={{ textAlign: 'center' }}>
                <div style={{ fontSize: '18px', fontWeight: 600 }}>
                  {data.hvacTermsFound || 0}
                </div>
                <div style={{ fontSize: '11px', color: '#6b7280' }}>HVAC Terms</div>
              </div>
            </div>

            {/* Issues & Recommendations */}
            {data.qualityIssues.length > 0 && (
              <div style={{ marginBottom: '8px' }}>
                <div style={{ 
                  display: 'flex', 
                  alignItems: 'center', 
                  gap: '4px',
                  marginBottom: '4px'
                }}>
                  <AlertCircle size={12} color="#ef4444" />
                  <span style={{ fontSize: '12px', fontWeight: 500, color: '#ef4444' }}>
                    Issues:
                  </span>
                </div>
                <ul style={{ 
                  margin: '0 0 0 16px', 
                  padding: 0,
                  fontSize: '11px',
                  color: '#6b7280'
                }}>
                  {data.qualityIssues.map((issue, idx) => (
                    <li key={idx}>{issue}</li>
                  ))}
                </ul>
              </div>
            )}

            {data.recommendations.length > 0 && (
              <div>
                <div style={{ 
                  display: 'flex', 
                  alignItems: 'center', 
                  gap: '4px',
                  marginBottom: '4px'
                }}>
                  <CheckCircle size={12} color="#10b981" />
                  <span style={{ fontSize: '12px', fontWeight: 500, color: '#10b981' }}>
                    Recommendations:
                  </span>
                </div>
                <ul style={{ 
                  margin: '0 0 0 16px', 
                  padding: 0,
                  fontSize: '11px',
                  color: '#6b7280'
                }}>
                  {data.recommendations.map((rec, idx) => (
                    <li key={idx}>{rec}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>

          {/* Text Preview/Edit Area */}
          <div style={{
            background: '#ffffff',
            border: '1px solid #e5e7eb',
            borderRadius: '8px',
            padding: '12px',
            marginBottom: '12px',
            maxHeight: '200px',
            overflow: 'auto'
          }}>
            <div style={{ 
              display: 'flex', 
              justifyContent: 'space-between',
              marginBottom: '8px'
            }}>
              <span style={{ fontSize: '12px', fontWeight: 500, color: '#6b7280' }}>
                Extracted Text {isEditing && '(Editing)'}
              </span>
              {!isEditing && (
                <button
                  onClick={() => setIsEditing(true)}
                  style={{
                    background: 'none',
                    border: 'none',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '4px',
                    fontSize: '11px',
                    color: '#3b82f6'
                  }}
                >
                  <Edit3 size={12} />
                  Edit
                </button>
              )}
            </div>
            
            {isEditing ? (
              <textarea
                value={editedText}
                onChange={(e) => setEditedText(e.target.value)}
                style={{
                  width: '100%',
                  minHeight: '120px',
                  border: '1px solid #3b82f6',
                  borderRadius: '4px',
                  padding: '8px',
                  fontSize: '12px',
                  fontFamily: 'monospace',
                  resize: 'vertical'
                }}
              />
            ) : (
              <pre style={{
                margin: 0,
                fontSize: '11px',
                fontFamily: 'monospace',
                whiteSpace: 'pre-wrap',
                color: '#374151',
                lineHeight: 1.5
              }}>
                {data.extractedText.substring(0, 500)}
                {data.extractedText.length > 500 && '...'}
              </pre>
            )}
          </div>

          {/* Action Buttons */}
          <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
            {isEditing ? (
              <>
                <button
                  onClick={handleSaveEdit}
                  style={{
                    flex: 1,
                    padding: '8px 12px',
                    background: '#3b82f6',
                    color: '#ffffff',
                    border: 'none',
                    borderRadius: '6px',
                    fontSize: '13px',
                    fontWeight: 500,
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: '6px'
                  }}
                >
                  <CheckCircle size={14} />
                  Save & Continue
                </button>
                <button
                  onClick={handleCancelEdit}
                  style={{
                    padding: '8px 12px',
                    background: '#f3f4f6',
                    color: '#6b7280',
                    border: 'none',
                    borderRadius: '6px',
                    fontSize: '13px',
                    cursor: 'pointer'
                  }}
                >
                  Cancel
                </button>
              </>
            ) : (
              <>
                {/* Approve button - highlighted if recommended */}
                {data.actions?.approve_text && (
                  <button
                    onClick={handleApprove}
                    style={{
                      flex: data.actions.approve_text.recommended ? 2 : 1,
                      padding: '8px 12px',
                      background: data.actions.approve_text.recommended ? '#10b981' : '#3b82f6',
                      color: '#ffffff',
                      border: 'none',
                      borderRadius: '6px',
                      fontSize: '13px',
                      fontWeight: data.actions.approve_text.recommended ? 600 : 500,
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      gap: '6px',
                      boxShadow: data.actions.approve_text.recommended ? 
                        '0 2px 8px rgba(16,185,129,0.3)' : 'none'
                    }}
                  >
                    <CheckCircle size={14} />
                    {data.actions.approve_text.label}
                    {data.actions.approve_text.recommended && ' ✓'}
                  </button>
                )}

                {/* Retry button */}
                {data.actions?.retry_extraction && (
                  <button
                    onClick={data.onRetry}
                    style={{
                      flex: 1,
                      padding: '8px 12px',
                      background: data.actions.retry_extraction.recommended ? '#f59e0b' : '#f3f4f6',
                      color: data.actions.retry_extraction.recommended ? '#ffffff' : '#6b7280',
                      border: 'none',
                      borderRadius: '6px',
                      fontSize: '13px',
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      gap: '6px'
                    }}
                  >
                    <RefreshCw size={14} />
                    {data.actions.retry_extraction.label}
                  </button>
                )}
              </>
            )}
          </div>

          {/* Action Descriptions */}
          {data.actions && !isEditing && (
            <div style={{
              marginTop: '8px',
              padding: '8px',
              background: '#f9fafb',
              borderRadius: '6px',
              fontSize: '11px',
              color: '#6b7280'
            }}>
              {Object.entries(data.actions)
                .filter(([_, action]) => action.recommended)
                .map(([key, action]) => (
                  <div key={key} style={{ marginBottom: '4px' }}>
                    <strong>{action.label}:</strong> {action.description}
                    {action.confidence && (
                      <span style={{ marginLeft: '4px', color: '#9ca3af' }}>
                        ({action.confidence}% confidence)
                      </span>
                    )}
                  </div>
                ))
              }
            </div>
          )}
        </>
      )}
      
      <Handle type="source" position={Position.Bottom} />
    </div>
  );
};

export default TextReviewNode;
