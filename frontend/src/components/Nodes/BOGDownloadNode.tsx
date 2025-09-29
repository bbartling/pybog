/**
 * BOG Download Node Component
 * Final node showing completed BOG file with download options
 */

import React from 'react';
import { Handle, Position, NodeProps } from 'reactflow';
import { Download, FileCode, CheckCircle, Eye, Zap } from 'lucide-react';
import { TOKENS, STYLES, COMPONENTS } from '../../theme/neubrutalism';

interface BOGDownloadData {
  filename: string;
  fileSize: string;
  generatedAt: Date;
  downloadUrl: string;
  previewUrl?: string;
  stats: {
    ioPoints: number;
    controlBlocks: number;
    schedules: number;
    alarms: number;
  };
}

const BOGDownloadNode: React.FC<NodeProps<BOGDownloadData>> = ({ data, id }) => {
  const { filename, fileSize, generatedAt, downloadUrl, previewUrl, stats } = data;

  const handleDownload = () => {
    // Create download link
    const link = document.createElement('a');
    link.href = downloadUrl;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const handlePreview = () => {
    if (previewUrl) {
      window.open(previewUrl, '_blank');
    }
  };

  return (
    <div style={{
      ...COMPONENTS.message.base,
      minWidth: '360px',
      maxWidth: '420px',
      fontFamily: TOKENS.fontFamily,
    }}>
      {/* Input Port */}
      <Handle
        type="target"
        position={Position.Left}
        style={{
          background: TOKENS.success,
          width: 10,
          height: 10,
          border: `2px solid ${TOKENS.black}`,
          left: -5
        }}
      />

      {/* Header */}
      <div style={{
        ...COMPONENTS.message.header,
        background: TOKENS.success,
        borderBottom: STYLES.border.solid,
      }}>
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: STYLES.spacing.sm,
        }}>
          <div style={{
            width: '24px',
            height: '24px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            background: TOKENS.white,
            borderRadius: STYLES.radius.small,
            color: TOKENS.success
          }}>
            <CheckCircle size={16} />
          </div>
          <span style={{
            fontWeight: STYLES.fontWeight.bold,
            textTransform: 'uppercase',
            letterSpacing: '0.5px',
            color: TOKENS.white,
          }}>BOG FILE READY</span>
        </div>
        <div style={{
          fontSize: STYLES.fontSize.xs,
          color: 'rgba(255,255,255,0.8)',
          fontWeight: STYLES.fontWeight.normal
        }}>
          {generatedAt.toLocaleString()}
        </div>
      </div>

      {/* Content */}
      <div style={{
        ...COMPONENTS.message.body,
        padding: STYLES.spacing.lg,
      }}>
        {/* File Info */}
        <div style={{
          background: `linear-gradient(135deg, ${TOKENS.success}15 0%, ${TOKENS.success}05 100%)`,
          border: `2px solid ${TOKENS.success}`,
          borderRadius: STYLES.radius.medium,
          padding: STYLES.spacing.md,
          marginBottom: STYLES.spacing.lg,
        }}>
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: STYLES.spacing.sm,
            marginBottom: STYLES.spacing.sm,
          }}>
            <FileCode size={20} color={TOKENS.success} />
            <div>
              <div style={{
                fontSize: STYLES.fontSize.base,
                fontWeight: STYLES.fontWeight.bold,
                color: TOKENS.text,
                lineHeight: 1.2,
              }}>
                {filename}
              </div>
              <div style={{
                fontSize: STYLES.fontSize.xs,
                color: TOKENS.muted,
              }}>
                {fileSize} • Niagara BOG File
              </div>
            </div>
          </div>

          {/* File Stats */}
          <div style={{
            display: 'grid',
            gridTemplateColumns: '1fr 1fr',
            gap: STYLES.spacing.sm,
            marginTop: STYLES.spacing.md,
          }}>
            <div style={{
              display: 'flex',
              justifyContent: 'space-between',
              fontSize: STYLES.fontSize.xs,
              color: TOKENS.text,
            }}>
              <span>I/O Points:</span>
              <span style={{ fontWeight: STYLES.fontWeight.bold }}>{stats.ioPoints}</span>
            </div>
            <div style={{
              display: 'flex',
              justifyContent: 'space-between',
              fontSize: STYLES.fontSize.xs,
              color: TOKENS.text,
            }}>
              <span>Control Blocks:</span>
              <span style={{ fontWeight: STYLES.fontWeight.bold }}>{stats.controlBlocks}</span>
            </div>
            <div style={{
              display: 'flex',
              justifyContent: 'space-between',
              fontSize: STYLES.fontSize.xs,
              color: TOKENS.text,
            }}>
              <span>Schedules:</span>
              <span style={{ fontWeight: STYLES.fontWeight.bold }}>{stats.schedules}</span>
            </div>
            <div style={{
              display: 'flex',
              justifyContent: 'space-between',
              fontSize: STYLES.fontSize.xs,
              color: TOKENS.text,
            }}>
              <span>Alarms:</span>
              <span style={{ fontWeight: STYLES.fontWeight.bold }}>{stats.alarms}</span>
            </div>
          </div>
        </div>

        {/* Success Message */}
        <div style={{
          background: TOKENS.chip,
          border: STYLES.border.light,
          borderRadius: STYLES.radius.medium,
          padding: STYLES.spacing.md,
          marginBottom: STYLES.spacing.lg,
          textAlign: 'center',
        }}>
          <div style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: STYLES.spacing.xs,
            marginBottom: STYLES.spacing.xs,
          }}>
            <Zap size={16} color={TOKENS.success} />
            <span style={{
              fontSize: STYLES.fontSize.sm,
              fontWeight: STYLES.fontWeight.bold,
              color: TOKENS.success,
              textTransform: 'uppercase',
              letterSpacing: '0.5px',
            }}>
              Ready for Niagara Workbench
            </span>
          </div>
          <div style={{
            fontSize: STYLES.fontSize.xs,
            color: TOKENS.muted,
            lineHeight: 1.4,
          }}>
            Your BOG file has been successfully generated and is ready to import into Niagara Workbench
          </div>
        </div>

        {/* Action Buttons */}
        <div style={{
          display: 'flex',
          gap: STYLES.spacing.sm,
        }}>
          <button
            onClick={handleDownload}
            style={{
              ...COMPONENTS.button.base,
              background: TOKENS.success,
              borderColor: TOKENS.success,
              color: TOKENS.white,
              fontSize: STYLES.fontSize.sm,
              display: 'flex',
              alignItems: 'center',
              gap: STYLES.spacing.xs,
              fontWeight: STYLES.fontWeight.bold,
              textTransform: 'uppercase',
              letterSpacing: '0.5px',
              flex: 1,
              justifyContent: 'center',
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.transform = 'translateY(-2px)';
              e.currentTarget.style.boxShadow = `4px 4px 0 ${TOKENS.black}`;
              e.currentTarget.style.background = TOKENS.approved;
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.transform = 'translateY(0)';
              e.currentTarget.style.boxShadow = `2px 2px 0 ${TOKENS.black}`;
              e.currentTarget.style.background = TOKENS.success;
            }}
          >
            <Download size={14} />
            Download BOG
          </button>

          {previewUrl && (
            <button
              onClick={handlePreview}
              style={{
                ...COMPONENTS.button.base,
                ...COMPONENTS.button.secondary,
                fontSize: STYLES.fontSize.sm,
                display: 'flex',
                alignItems: 'center',
                gap: STYLES.spacing.xs,
                minWidth: '100px',
                justifyContent: 'center',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.transform = 'translateY(-1px)';
                e.currentTarget.style.boxShadow = STYLES.shadow.sm;
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.transform = 'translateY(0)';
                e.currentTarget.style.boxShadow = 'none';
              }}
            >
              <Eye size={12} />
              Preview
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

export default BOGDownloadNode;