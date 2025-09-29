/**
 * Result Files Card Component
 * Displays downloadable artifacts following PyBOG neubrutalism design system
 */

import React, { useState } from 'react';
import { Handle, Position, NodeProps } from 'reactflow';
import { Package, Download, CheckCircle, AlertCircle, Loader2, BarChart3, Settings } from 'lucide-react';
import { TOKENS, STYLES, COMPONENTS } from '../../theme/neubrutalism';

interface FileArtifact {
  artifactId: string;
  filename: string;
  size: number;
  sha256: string;
  downloadUrl: string;
  type: 'analysis' | 'bog';
}

interface ResultFilesCardData {
  files: FileArtifact[];
  timestamp: Date;
  onDownload?: (artifactId: string) => void;
  onValidate?: () => void;
  validationEnabled?: boolean;
  validationStatus?: 'pending' | 'ok' | 'error';
}

const ResultFilesCard: React.FC<NodeProps<ResultFilesCardData>> = ({ data, id }) => {
  const { files, timestamp, onDownload, onValidate, validationEnabled, validationStatus } = data;
  const [downloading, setDownloading] = useState<string | null>(null);

  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  };

  const getFileIcon = (type: string) => {
    switch (type) {
      case 'analysis': return <BarChart3 size={16} />;
      case 'bog': return <Settings size={16} />;
      default: return <Package size={16} />;
    }
  };

  const getFileTypeLabel = (type: string): string => {
    switch (type) {
      case 'analysis': return 'Analysis Report';
      case 'bog': return 'BOG File';
      default: return 'File';
    }
  };

  const handleDownload = async (file: FileArtifact) => {
    if (downloading) return;
    
    setDownloading(file.artifactId);
    try {
      if (onDownload) {
        await onDownload(file.artifactId);
      } else {
        // Direct download via URL
        const link = document.createElement('a');
        link.href = file.downloadUrl;
        link.download = file.filename;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
      }
    } catch (error) {
      console.error('Download failed:', error);
    } finally {
      setDownloading(null);
    }
  };

  return (
    <div style={{
      ...COMPONENTS.message.base,
      minWidth: '360px',
      maxWidth: '450px',
      fontFamily: TOKENS.fontFamily,
    }}>
      {/* Input Port */}
      <Handle 
        type="target" 
        position={Position.Left}
        style={{ 
          background: TOKENS.warning,
          width: 10,
          height: 10,
          border: `2px solid ${TOKENS.black}`,
          left: -5
        }} 
      />
      
      {/* Header */}
      <div style={{
        ...COMPONENTS.message.header,
        background: TOKENS.nodeFooter,
        borderBottom: STYLES.border.solid,
      }}>
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: STYLES.spacing.sm,
        }}>
          <div style={{
            width: '20px',
            height: '20px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            background: TOKENS.white,
            borderRadius: STYLES.radius.small,
            color: TOKENS.warning
          }}>
            <Package size={14} />
          </div>
          <span>Files Ready</span>
        </div>
        <div style={{
          fontSize: STYLES.fontSize.xs,
          color: TOKENS.muted,
          fontWeight: STYLES.fontWeight.normal
        }}>
          {timestamp.toLocaleTimeString()}
        </div>
      </div>

      {/* Content */}
      <div style={{
        ...COMPONENTS.message.body,
        padding: STYLES.spacing.lg,
      }}>
        {/* Files List */}
        <div style={{
          display: 'flex',
          flexDirection: 'column',
          gap: STYLES.spacing.md,
          marginBottom: STYLES.spacing.lg,
        }}>
          {files.map((file) => (
            <div key={file.artifactId} style={{
              background: TOKENS.chip,
              border: STYLES.border.light,
              borderRadius: STYLES.radius.medium,
              padding: STYLES.spacing.md,
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              gap: STYLES.spacing.md,
            }}>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: STYLES.spacing.md,
                  marginBottom: STYLES.spacing.sm,
                }}>
                  <div style={{
                    color: file.type === 'analysis' ? TOKENS.info : TOKENS.success,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                  }}>
                    {getFileIcon(file.type)}
                  </div>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{
                      fontSize: STYLES.fontSize.sm,
                      fontWeight: STYLES.fontWeight.semibold,
                      color: TOKENS.text,
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap'
                    }}>
                      {file.filename}
                    </div>
                    <div style={{
                      display: 'flex',
                      gap: STYLES.spacing.md,
                      marginTop: '2px',
                    }}>
                      <span style={{
                        fontSize: STYLES.fontSize.xs,
                        color: TOKENS.muted,
                        fontWeight: STYLES.fontWeight.medium
                      }}>
                        {getFileTypeLabel(file.type)}
                      </span>
                      <span style={{
                        fontSize: STYLES.fontSize.xs,
                        color: TOKENS.muted,
                        fontWeight: STYLES.fontWeight.medium
                      }}>
                        {formatFileSize(file.size)}
                      </span>
                    </div>
                  </div>
                </div>
                
                {file.sha256 && (
                  <div style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: STYLES.spacing.sm,
                    fontSize: STYLES.fontSize.xs,
                    color: TOKENS.muted,
                  }}>
                    <span style={{ fontWeight: STYLES.fontWeight.semibold }}>SHA256:</span>
                    <span style={{ fontFamily: 'Monaco, Menlo, monospace' }}>
                      {file.sha256.substring(0, 16)}...
                    </span>
                  </div>
                )}
              </div>
              
              <button 
                onClick={() => handleDownload(file)}
                disabled={downloading === file.artifactId}
                style={{
                  ...COMPONENTS.button.base,
                  ...COMPONENTS.button.primary,
                  fontSize: STYLES.fontSize.sm,
                  display: 'flex',
                  alignItems: 'center',
                  gap: STYLES.spacing.xs,
                  flexShrink: 0,
                  ...(downloading === file.artifactId ? {
                    background: TOKENS.muted,
                    borderColor: TOKENS.muted,
                    cursor: 'not-allowed'
                  } : {})
                }}
                onMouseEnter={(e) => {
                  if (!downloading) {
                    e.currentTarget.style.transform = 'translateY(-1px)';
                    e.currentTarget.style.boxShadow = STYLES.shadow.sm;
                  }
                }}
                onMouseLeave={(e) => {
                  if (!downloading) {
                    e.currentTarget.style.transform = 'translateY(0)';
                    e.currentTarget.style.boxShadow = 'none';
                  }
                }}
              >
                {downloading === file.artifactId ? (
                  <>
                    <Loader2 size={14} className="animate-spin" />
                    Downloading...
                  </>
                ) : (
                  <>
                    <Download size={14} />
                    Download
                  </>
                )}
              </button>
            </div>
          ))}
        </div>

        {/* Validation Section */}
        {validationEnabled && (
          <div style={{
            background: TOKENS.awaitingApproval,
            border: STYLES.border.solid,
            borderColor: TOKENS.warning,
            borderRadius: STYLES.radius.medium,
            padding: STYLES.spacing.md,
            marginBottom: STYLES.spacing.lg,
          }}>
            <div style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              marginBottom: STYLES.spacing.sm,
            }}>
              <span style={{
                fontSize: STYLES.fontSize.sm,
                fontWeight: STYLES.fontWeight.semibold,
                color: TOKENS.text,
                textTransform: 'uppercase',
                letterSpacing: '0.5px',
              }}>Workbench Validation</span>
              {validationStatus && (
                <span style={{
                  fontSize: STYLES.fontSize.xs,
                  fontWeight: STYLES.fontWeight.semibold,
                  display: 'flex',
                  alignItems: 'center',
                  gap: STYLES.spacing.xs,
                  color: validationStatus === 'ok' ? TOKENS.success : 
                         validationStatus === 'error' ? TOKENS.error : TOKENS.warning
                }}>
                  {validationStatus === 'ok' && <><CheckCircle size={12} /> OK to import</>}
                  {validationStatus === 'error' && <><AlertCircle size={12} /> Validation failed</>}
                  {validationStatus === 'pending' && <><Loader2 size={12} className="animate-spin" /> Validating...</>}
                </span>
              )}
            </div>
            
            {onValidate && validationStatus !== 'pending' && (
              <button 
                onClick={onValidate}
                style={{
                  ...COMPONENTS.button.base,
                  ...COMPONENTS.button.warning,
                  fontSize: STYLES.fontSize.sm,
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
                Validate Files
              </button>
            )}
          </div>
        )}

        {/* Status */}
        <div style={{
          display: 'flex',
          justifyContent: 'flex-end',
          alignItems: 'center',
        }}>
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: STYLES.spacing.xs,
            fontSize: STYLES.fontSize.xs,
            fontWeight: STYLES.fontWeight.semibold,
            color: TOKENS.success,
            textTransform: 'uppercase',
            letterSpacing: '0.5px',
          }}>
            <CheckCircle size={12} />
            {files.length} file{files.length !== 1 ? 's' : ''} ready
          </div>
        </div>
      </div>

      {/* Output Port */}
      <Handle 
        type="source" 
        position={Position.Right}
        style={{ 
          background: TOKENS.success,
          width: 10,
          height: 10,
          border: `2px solid ${TOKENS.black}`,
          right: -5
        }} 
      />
    </div>
  );
};

export default ResultFilesCard;