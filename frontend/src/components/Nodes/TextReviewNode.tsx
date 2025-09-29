/**
 * Text Review Node Component
 * Shows extracted document text with approval actions for analysis workflow
 */

import React, { useState } from 'react';
import { Handle, Position, NodeProps } from 'reactflow';
import { CheckCircle, XCircle, Eye, FileText, Edit3, AlertTriangle } from 'lucide-react';
import { TOKENS, STYLES, COMPONENTS } from '../../theme/neubrutalism';
import TextExpansionModal from '../TextExpansionModal';

interface TextReviewData {
  extractedText: string;
  filename: string;
  file_id: string;
  requiresApproval: boolean;
  stage: string;
  onApproveText?: (approvedText: string) => void;
  onRequestTextChanges?: (feedback: string) => void;
  onViewTextDetails?: (text: string) => void;
}

const TextReviewNode: React.FC<NodeProps<TextReviewData>> = ({ data, id }) => {
  const { extractedText, filename, file_id, requiresApproval, onApproveText, onRequestTextChanges, onViewTextDetails } = data;
  const [isEditing, setIsEditing] = useState(false);
  const [editedText, setEditedText] = useState(extractedText || '');
  const [feedback, setFeedback] = useState('');
  const [showFeedback, setShowFeedback] = useState(false);
  const [showModal, setShowModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);

  const handleApprove = () => {
    if (onApproveText) {
      onApproveText(isEditing ? editedText : extractedText);
    }
  };

  const handleRequestChanges = () => {
    if (onRequestTextChanges && feedback.trim()) {
      onRequestTextChanges(feedback);
      setShowFeedback(false);
      setFeedback('');
    }
  };

  const handleReExtract = () => {
    if (onRequestTextChanges) {
      onRequestTextChanges(`Please re-extract text from file ID: ${file_id} (${filename})`);
    }
  };

  const handleViewDetails = () => {
    setShowModal(true);
  };

  const handleEditToggle = () => {
    setShowEditModal(true);
  };

  const handleSaveEdit = (newText: string) => {
    setEditedText(newText);
    setIsEditing(true);
    setShowEditModal(false);
  };

  const handleCancelEdit = () => {
    setEditedText(extractedText); // Reset changes
    setIsEditing(false);
    setShowEditModal(false);
  };

  const previewText = (isEditing ? editedText : extractedText) || '';
  const truncatedText = previewText.length > 300 ? previewText.substring(0, 300) + '...' : previewText;

  return (
    <div style={{
      ...COMPONENTS.message.base,
      minWidth: '600px',
      maxWidth: '650px',
      fontFamily: TOKENS.fontFamily,
      background: TOKENS.white,
      border: STYLES.border.solid,
      borderRadius: STYLES.radius.large,
      position: 'relative',
    }}>
      {/* Input Port */}
      <Handle
        type="target"
        position={Position.Left}
        style={{
          background: TOKENS.port,
          width: 12,
          height: 12,
          border: STYLES.border.solid,
          left: -6
        }}
      />

      {/* Header - Text Review */}
      <div style={{
        ...COMPONENTS.message.header,
        background: TOKENS.nodeHeader,
        borderBottom: STYLES.border.solid,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
      }}>
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: STYLES.spacing.md,
        }}>
          <FileText size={18} color={TOKENS.text} />
          <div>
            <div style={{
              fontWeight: STYLES.fontWeight.semibold,
              color: TOKENS.text,
              fontSize: STYLES.fontSize.lg,
            }}>
              Text Extracted
            </div>
            <div style={{
              fontSize: STYLES.fontSize.xs,
              color: TOKENS.muted,
              fontWeight: STYLES.fontWeight.normal,
            }}>
              Review before analysis
            </div>
          </div>
        </div>

        {/* Status Badge */}
        <div style={{
          ...COMPONENTS.badge.base,
          ...COMPONENTS.badge.warning,
        }}>
          <AlertTriangle size={14} color={TOKENS.text} />
          <span>Awaiting Review</span>
        </div>
      </div>

      {/* Progress Bar */}
      <div style={{
        background: TOKENS.chip,
        padding: STYLES.spacing.md,
        borderBottom: STYLES.border.solid,
      }}>
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: STYLES.spacing.sm,
        }}>
          <span style={{
            fontSize: STYLES.fontSize.xs,
            fontWeight: STYLES.fontWeight.bold,
            color: TOKENS.text,
            textTransform: 'uppercase',
            letterSpacing: '0.5px',
          }}>
            Step 2 of 5 - Text Review
          </span>
          <span style={{
            fontSize: STYLES.fontSize.xs,
            fontWeight: STYLES.fontWeight.bold,
            color: TOKENS.primary,
          }}>
            40%
          </span>
        </div>
        <div style={{
          width: '100%',
          height: '8px',
          background: TOKENS.white,
          border: STYLES.border.solid,
          borderRadius: STYLES.radius.small,
          overflow: 'hidden',
        }}>
          <div style={{
            width: '40%',
            height: '100%',
            background: TOKENS.primary,
            transition: STYLES.transition.base,
          }} />
        </div>
      </div>

      {/* Content */}
      <div style={{
        ...COMPONENTS.message.body,
      }}>
        {/* File Info */}
        <div style={{
          background: TOKENS.chip,
          border: STYLES.border.solid,
          borderRadius: STYLES.radius.medium,
          padding: STYLES.spacing.md,
          marginBottom: STYLES.spacing.lg,
        }}>
          <div style={{
            fontSize: STYLES.fontSize.sm,
            fontWeight: STYLES.fontWeight.bold,
            color: TOKENS.text,
            marginBottom: STYLES.spacing.xs,
          }}>
            Document: {filename}
          </div>
          <div style={{
            fontSize: STYLES.fontSize.xs,
            color: TOKENS.muted,
          }}>
            {previewText.length} characters extracted
          </div>
        </div>

        {/* Text Preview/Editor */}
        <div style={{
          background: TOKENS.white,
          border: STYLES.border.solid,
          borderRadius: STYLES.radius.medium,
          padding: STYLES.spacing.md,
          marginBottom: STYLES.spacing.lg,
          minHeight: '120px',
          maxHeight: '200px',
          overflow: 'auto',
        }}>
          {isEditing ? (
            <textarea
              value={editedText}
              onChange={(e) => setEditedText(e.target.value)}
              style={{
                width: '100%',
                height: '150px',
                border: 'none',
                outline: 'none',
                fontSize: STYLES.fontSize.sm,
                fontFamily: TOKENS.fontFamily,
                color: TOKENS.text,
                background: 'transparent',
                resize: 'none',
              }}
              placeholder="Edit extracted text..."
            />
          ) : (
            <div style={{
              fontSize: STYLES.fontSize.sm,
              color: TOKENS.text,
              lineHeight: 1.5,
              whiteSpace: 'pre-wrap',
            }}>
              {truncatedText}
              {previewText.length > 300 && (
                <button
                  onClick={handleViewDetails}
                  style={{
                    background: 'none',
                    border: 'none',
                    color: TOKENS.primary,
                    cursor: 'pointer',
                    textDecoration: 'underline',
                    fontSize: STYLES.fontSize.sm,
                    padding: 0,
                    marginLeft: STYLES.spacing.sm,
                  }}
                >
                  View Full Text
                </button>
              )}
            </div>
          )}
        </div>

        {/* Feedback Section */}
        {showFeedback && (
          <div style={{
            background: TOKENS.changesRequested,
            border: STYLES.border.solid,
            borderRadius: STYLES.radius.medium,
            padding: STYLES.spacing.md,
            marginBottom: STYLES.spacing.lg,
          }}>
            <textarea
              value={feedback}
              onChange={(e) => setFeedback(e.target.value)}
              placeholder="Describe what changes are needed..."
              style={{
                ...COMPONENTS.input.base,
                width: '100%',
                height: '80px',
                resize: 'none',
              }}
            />
          </div>
        )}

        {/* Action Buttons */}
        <div style={{
          display: 'flex',
          gap: STYLES.spacing.sm,
          marginBottom: STYLES.spacing.md,
        }}>
          <button
            onClick={handleViewDetails}
            style={{
              ...COMPONENTS.button.base,
              ...COMPONENTS.button.secondary,
              fontSize: STYLES.fontSize.sm,
              display: 'flex',
              alignItems: 'center',
              gap: STYLES.spacing.xs,
              flex: 1,
              justifyContent: 'center',
            }}
          >
            <Eye size={14} />
            View Full
          </button>

          <button
            onClick={handleEditToggle}
            style={{
              ...COMPONENTS.button.base,
              ...COMPONENTS.button.secondary,
              fontSize: STYLES.fontSize.sm,
              display: 'flex',
              alignItems: 'center',
              gap: STYLES.spacing.xs,
              flex: 1,
              justifyContent: 'center',
            }}
          >
            <Edit3 size={14} />
            {isEditing ? 'Edit More' : 'Edit'}
          </button>

          <button
            onClick={handleReExtract}
            style={{
              ...COMPONENTS.button.base,
              ...COMPONENTS.button.warning,
              fontSize: STYLES.fontSize.sm,
              display: 'flex',
              alignItems: 'center',
              gap: STYLES.spacing.xs,
              flex: 1,
              justifyContent: 'center',
            }}
          >
            <XCircle size={14} />
            Re-extract
          </button>
        </div>

        {/* Feedback Submit Button */}
        {showFeedback && (
          <button
            onClick={handleRequestChanges}
            disabled={!feedback.trim()}
            style={{
              ...COMPONENTS.button.base,
              ...COMPONENTS.button.danger,
              ...(feedback.trim() ? {} : COMPONENTS.button.disabled),
              fontSize: STYLES.fontSize.sm,
              display: 'flex',
              alignItems: 'center',
              gap: STYLES.spacing.sm,
              width: '100%',
              justifyContent: 'center',
              marginBottom: STYLES.spacing.md,
            }}
          >
            <XCircle size={16} />
            Request Re-extraction
          </button>
        )}

        {/* Primary Approval Button */}
        <button
          onClick={handleApprove}
          style={{
            ...COMPONENTS.button.base,
            ...COMPONENTS.button.success,
            fontSize: STYLES.fontSize.lg,
            display: 'flex',
            alignItems: 'center',
            gap: STYLES.spacing.sm,
            fontWeight: STYLES.fontWeight.bold,
            width: '100%',
            justifyContent: 'center',
            padding: `${STYLES.spacing.lg} ${STYLES.spacing.xxl}`,
          }}
        >
          <CheckCircle size={18} />
          Approve Text & Start Analysis
        </button>
      </div>

      {/* Output Port - Only show when approved */}
      <Handle
        type="source"
        position={Position.Right}
        style={{
          background: TOKENS.port,
          width: 12,
          height: 12,
          border: STYLES.border.solid,
          right: -6
        }}
      />

      {/* Text Expansion Modal */}
      <TextExpansionModal
        isOpen={showModal}
        onClose={() => setShowModal(false)}
        title={`Extracted Text - ${filename}`}
        content={extractedText || 'No text extracted'}
        messageType="system"
        showActions={true}
      />

      {/* Text Edit Modal */}
      {showEditModal && (
        <div
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: 'rgba(0, 0, 0, 0.6)',
            zIndex: 50000,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '20px',
          }}
          onClick={(e) => {
            if (e.target === e.currentTarget) {
              handleCancelEdit();
            }
          }}
        >
          <div
            style={{
              background: TOKENS.white,
              border: STYLES.border.solid,
              borderRadius: STYLES.radius.large,
              width: '80vw',
              maxWidth: '1200px',
              height: '80vh',
              display: 'flex',
              flexDirection: 'column',
              overflow: 'hidden',
              fontFamily: TOKENS.fontFamily,
            }}
            onClick={(e) => e.stopPropagation()}
          >
            {/* Header */}
            <div style={{
              ...COMPONENTS.message.header,
              background: TOKENS.nodeHeader,
              borderBottom: STYLES.border.solid,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
            }}>
              <div style={{
                display: 'flex',
                alignItems: 'center',
                gap: STYLES.spacing.md,
              }}>
                <Edit3 size={18} color={TOKENS.text} />
                <div style={{
                  fontWeight: STYLES.fontWeight.semibold,
                  color: TOKENS.text,
                  fontSize: STYLES.fontSize.lg,
                }}>
                  Edit Extracted Text - {filename}
                </div>
              </div>
            </div>

            {/* Edit Area */}
            <div style={{
              flex: 1,
              padding: STYLES.spacing.lg,
              display: 'flex',
              flexDirection: 'column',
            }}>
              <textarea
                value={editedText}
                onChange={(e) => setEditedText(e.target.value)}
                style={{
                  ...COMPONENTS.input.base,
                  width: '100%',
                  height: '100%',
                  resize: 'none',
                  fontSize: STYLES.fontSize.base,
                  lineHeight: 1.6,
                }}
                placeholder="Edit the extracted text..."
              />
            </div>

            {/* Footer */}
            <div style={{
              padding: STYLES.spacing.lg,
              borderTop: STYLES.border.solid,
              display: 'flex',
              gap: STYLES.spacing.sm,
              justifyContent: 'flex-end',
            }}>
              <button
                onClick={handleCancelEdit}
                style={{
                  ...COMPONENTS.button.base,
                  ...COMPONENTS.button.secondary,
                }}
              >
                Cancel
              </button>
              <button
                onClick={() => handleSaveEdit(editedText)}
                style={{
                  ...COMPONENTS.button.base,
                  ...COMPONENTS.button.primary,
                }}
              >
                Save Changes
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default TextReviewNode;