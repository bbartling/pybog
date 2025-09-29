import React, { useState, useCallback, useEffect } from 'react';
import type { NodeProps } from 'reactflow';
import { Handle, Position } from 'reactflow';
import { 
  User, 
  FileText, 
  Download, 
  AlertCircle, 
  CheckCircle, 
  XCircle,
  RefreshCw,
  Eye,
  Upload,
  Trash2
} from 'lucide-react';
import { TOKENS, STYLES, COMPONENTS } from '../../theme/neubrutalism';
import enhancedFileStorageService, { StoredFile } from '../../services/enhancedFileStorageService';

interface EnhancedUserData {
  content: string;
  timestamp: Date | string;
  sessionId: string;
  messageId: string;
  files?: File[] | StoredFile[]; // Can be either File objects or StoredFile objects
  status?: 'sending' | 'sent' | 'failed';
  onResend?: (messageId: string) => void;
}

const EnhancedUserNode: React.FC<NodeProps<EnhancedUserData>> = ({ data }) => {
  const time = data?.timestamp ? new Date(data.timestamp) : new Date();
  const [storedFiles, setStoredFiles] = useState<StoredFile[]>([]);
  const [showFileModal, setShowFileModal] = useState(false);
  const [selectedFile, setSelectedFile] = useState<StoredFile | null>(null);
  const [resending, setResending] = useState(false);
  
  // Load stored files for this message
  useEffect(() => {
    if (data?.messageId) {
      const messageFiles = enhancedFileStorageService.getMessageFiles(data.messageId);
      setStoredFiles(messageFiles);
    }
  }, [data?.messageId]);
  
  // Status display
  const statusInfo = React.useMemo(() => {
    switch (data?.status) {
      case 'sending':
        return { 
          bg: TOKENS.running, 
          label: 'Sending…',
          icon: <RefreshCw size={12} className="animate-spin" />,
          pulse: true
        };
      case 'sent':
        return { 
          bg: '#D6F3D7', 
          label: 'Sent',
          icon: <CheckCircle size={12} />,
          pulse: false
        };
      case 'failed':
        return { 
          bg: '#FFD6D6', 
          label: 'Failed',
          icon: <XCircle size={12} />,
          pulse: true
        };
      default:
        return { 
          bg: '#E5E5E5', 
          label: 'Ready',
          icon: <User size={12} />,
          pulse: false
        };
    }
  }, [data?.status]);
  
  const handleResend = useCallback(async () => {
    if (!data?.onResend || !data?.messageId) return;
    
    setResending(true);
    try {
      // The parent component will handle the actual resend logic
      // including restoring files from storage
      data.onResend(data.messageId);
    } catch (error) {
      console.error('[EnhancedUserNode] Resend failed:', error);
    } finally {
      setResending(false);
    }
  }, [data?.onResend, data?.messageId]);
  
  const handleFilePreview = useCallback((file: StoredFile) => {
    setSelectedFile(file);
    setShowFileModal(true);
  }, []);
  
  const handleDeleteFile = useCallback((fileId: string) => {
    enhancedFileStorageService.deleteFile(fileId);
    setStoredFiles(prev => prev.filter(f => f.id !== fileId));
  }, []);
  
  const getFileIcon = (file: StoredFile) => {
    if (file.type.startsWith('image/')) return '🖼️';
    if (file.type.includes('pdf')) return '📄';
    if (file.type.includes('doc')) return '📝';
    if (file.type.includes('text')) return '📄';
    return '📁';
  };
  
  const renderFiles = () => {
    if (storedFiles.length === 0) return null;
    
    return (
      <div style={{
        marginTop: '12px',
        padding: '12px',
        background: TOKENS.white,
        border: STYLES.border.solid,
        borderRadius: STYLES.radius.small,
      }}>
        <h4 style={{ fontSize: '13px', fontWeight: 600, color: TOKENS.text, marginBottom: '8px', margin: 0 }}>
          <Upload size={14} style={{ display: 'inline', marginRight: '4px' }} />
          Files ({storedFiles.length})
        </h4>
        
        <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
          {storedFiles.map((file) => (
            <div key={file.id} style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              padding: '8px',
              background: file.status === 'error' ? '#FFE5E5' : '#F5F5F5',
              borderRadius: STYLES.radius.small,
              fontSize: '11px'
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flex: 1 }}>
                <span style={{ fontSize: '16px' }}>{getFileIcon(file)}</span>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ 
                    fontWeight: 600, 
                    color: TOKENS.text,
                    whiteSpace: 'nowrap',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis'
                  }}>
                    {file.name}
                  </div>
                  <div style={{ color: '#666', fontSize: '10px' }}>
                    {(file.size / 1024).toFixed(1)} KB
                    {file.status === 'processed' && file.metadata?.wordCount && 
                      ` • ${file.metadata.wordCount} words`
                    }
                    {file.status === 'error' && file.error &&
                      ` • Error: ${file.error}`
                    }
                  </div>
                </div>
              </div>
              
              <div style={{ display: 'flex', gap: '4px', alignItems: 'center' }}>
                {/* Status indicator */}
                {file.status === 'processing' && (
                  <RefreshCw size={12} className="animate-spin" style={{ color: TOKENS.info }} />
                )}
                {file.status === 'processed' && (
                  <CheckCircle size={12} style={{ color: TOKENS.success }} />
                )}
                {file.status === 'error' && (
                  <XCircle size={12} style={{ color: TOKENS.error }} />
                )}
                
                {/* Preview button */}
                {(file.base64Data || file.previewUrl) && (
                  <button
                    onClick={() => handleFilePreview(file)}
                    style={{
                      padding: '2px 6px',
                      fontSize: '10px',
                      background: TOKENS.white,
                      border: STYLES.border.solid,
                      borderRadius: STYLES.radius.small,
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '2px'
                    }}
                    title="Preview file"
                  >
                    <Eye size={10} />
                  </button>
                )}
                
                {/* Download button */}
                {file.downloadUrl && (
                  <a
                    href={file.downloadUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    style={{
                      padding: '2px 6px',
                      fontSize: '10px',
                      background: TOKENS.white,
                      border: STYLES.border.solid,
                      borderRadius: STYLES.radius.small,
                      color: TOKENS.primary,
                      textDecoration: 'none',
                      display: 'flex',
                      alignItems: 'center'
                    }}
                    title="Download file"
                  >
                    <Download size={10} />
                  </a>
                )}
                
                {/* Delete button */}
                <button
                  onClick={() => handleDeleteFile(file.id)}
                  style={{
                    padding: '2px 6px',
                    fontSize: '10px',
                    background: TOKENS.white,
                    border: STYLES.border.solid,
                    borderRadius: STYLES.radius.small,
                    cursor: 'pointer',
                    color: TOKENS.error
                  }}
                  title="Remove file"
                >
                  <Trash2 size={10} />
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  };
  
  const renderFileModal = () => {
    if (!showFileModal || !selectedFile) return null;
    
    const previewUrl = enhancedFileStorageService.getFilePreviewUrl(selectedFile.id);
    
    return (
      <div style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: 'rgba(0, 0, 0, 0.8)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 9999
      }}>
        <div style={{
          background: TOKENS.white,
          borderRadius: STYLES.radius.large,
          padding: '24px',
          maxWidth: '80vw',
          maxHeight: '80vh',
          overflow: 'auto',
          position: 'relative'
        }}>
          {/* Header */}
          <div style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            marginBottom: '16px',
            paddingBottom: '12px',
            borderBottom: STYLES.border.solid
          }}>
            <h3 style={{ margin: 0, fontSize: '16px', fontWeight: 600 }}>
              {selectedFile.name}
            </h3>
            <button
              onClick={() => setShowFileModal(false)}
              style={{
                background: 'none',
                border: 'none',
                fontSize: '20px',
                cursor: 'pointer',
                color: TOKENS.text
              }}
            >
              ×
            </button>
          </div>
          
          {/* File info */}
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'auto 1fr',
            gap: '8px 16px',
            marginBottom: '16px',
            fontSize: '12px'
          }}>
            <strong>Size:</strong>
            <span>{(selectedFile.size / 1024).toFixed(1)} KB</span>
            
            <strong>Type:</strong>
            <span>{selectedFile.type}</span>
            
            <strong>Uploaded:</strong>
            <span>{selectedFile.uploadedAt.toLocaleString()}</span>
            
            <strong>Status:</strong>
            <span style={{ 
              color: selectedFile.status === 'error' ? TOKENS.error : 
                     selectedFile.status === 'processed' ? TOKENS.success : 
                     TOKENS.text 
            }}>
              {selectedFile.status}
              {selectedFile.error && ` - ${selectedFile.error}`}
            </span>
          </div>
          
          {/* Preview */}
          {previewUrl && (
            <div style={{ textAlign: 'center' }}>
              {selectedFile.type.startsWith('image/') ? (
                <img 
                  src={previewUrl} 
                  alt={selectedFile.name}
                  style={{ 
                    maxWidth: '100%', 
                    maxHeight: '400px',
                    border: STYLES.border.solid,
                    borderRadius: STYLES.radius.small
                  }} 
                />
              ) : (
                <div style={{
                  padding: '24px',
                  background: '#F5F5F5',
                  border: STYLES.border.solid,
                  borderRadius: STYLES.radius.small,
                  color: TOKENS.muted
                }}>
                  Preview not available for this file type
                </div>
              )}
            </div>
          )}
          
          {/* Extracted text */}
          {selectedFile.metadata?.extractedText && (
            <div style={{ marginTop: '16px' }}>
              <h4 style={{ fontSize: '14px', fontWeight: 600, margin: '0 0 8px 0' }}>
                Extracted Text
              </h4>
              <div style={{
                maxHeight: '200px',
                overflow: 'auto',
                padding: '12px',
                background: '#F5F5F5',
                border: STYLES.border.solid,
                borderRadius: STYLES.radius.small,
                fontSize: '11px',
                fontFamily: 'monospace',
                whiteSpace: 'pre-wrap'
              }}>
                {selectedFile.metadata.extractedText}
              </div>
            </div>
          )}
          
          {/* Actions */}
          <div style={{
            marginTop: '16px',
            display: 'flex',
            gap: '12px',
            justifyContent: 'flex-end'
          }}>
            {selectedFile.downloadUrl && (
              <a
                href={selectedFile.downloadUrl}
                target="_blank"
                rel="noopener noreferrer"
                style={{
                  ...COMPONENTS.button.base,
                  ...COMPONENTS.button.secondary,
                  textDecoration: 'none',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px'
                }}
              >
                <Download size={14} />
                Download
              </a>
            )}
            <button
              onClick={() => setShowFileModal(false)}
              style={{
                ...COMPONENTS.button.base,
                ...COMPONENTS.button.primary
              }}
            >
              Close
            </button>
          </div>
        </div>
      </div>
    );
  };
  
  return (
    <>
      <div style={{
        background: TOKENS.white,
        border: STYLES.border.solid,
        borderRadius: STYLES.radius.medium,
        boxShadow: statusInfo.pulse ? STYLES.shadow.lg : STYLES.shadow.sm,
        minWidth: '280px',
        maxWidth: '400px',
        fontFamily: 'Inter, system-ui, -apple-system, Segoe UI, Roboto, sans-serif',
        position: 'relative',
        transition: 'box-shadow 0.3s ease'
      }}>
        {/* Node Header */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          padding: '8px 12px',
          background: TOKENS.userHeader,
          borderBottom: STYLES.border.solid,
          gap: '8px'
        }}>
          <div style={{
            width: '24px',
            height: '24px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            background: TOKENS.white,
            borderRadius: '4px',
            color: TOKENS.text
          }}>
            <User size={16} />
          </div>
          <div style={{
            flex: 1,
            fontSize: '13px',
            fontWeight: 600,
            color: TOKENS.text
          }}>
            Your Message
          </div>
          <div style={{
            padding: '2px 8px',
            borderRadius: STYLES.radius.pill,
            fontSize: '11px',
            fontWeight: 600,
            textTransform: 'uppercase',
            background: statusInfo.bg,
            border: STYLES.border.solid,
            color: TOKENS.text,
            display: 'flex',
            alignItems: 'center',
            gap: '4px'
          }}>
            {statusInfo.icon}
            {statusInfo.label}
          </div>
        </div>
        
        {/* Node Content */}
        <div style={{
          padding: '12px',
          background: TOKENS.userBody,
          borderRadius: '0 0 6px 6px'
        }}>
          {/* Message content */}
          <div style={{
            fontSize: '12px',
            lineHeight: '1.5',
            color: TOKENS.text,
            wordBreak: 'break-word',
            whiteSpace: 'pre-wrap',
            marginBottom: storedFiles.length > 0 ? '0' : '8px'
          }}>
            {data?.content || 'Message content'}
          </div>
          
          {/* Files */}
          {renderFiles()}
          
          {/* Resend button for failed messages */}
          {data?.status === 'failed' && data?.onResend && (
            <div style={{ marginTop: '12px' }}>
              <button
                onClick={handleResend}
                disabled={resending}
                style={{
                  ...COMPONENTS.button.base,
                  ...COMPONENTS.button.warning,
                  width: '100%',
                  fontWeight: 600
                }}
              >
                {resending ? (
                  <>
                    <RefreshCw size={14} className="animate-spin" style={{ marginRight: 6 }} />
                    Resending...
                  </>
                ) : (
                  <>
                    <RefreshCw size={14} style={{ marginRight: 6 }} />
                    Resend Message
                  </>
                )}
              </button>
            </div>
          )}
          
          {/* Timestamp */}
          <div style={{
            fontSize: '10px',
            color: '#666',
            textAlign: 'right',
            marginTop: '8px'
          }}>
            {time.toLocaleTimeString()}
          </div>
        </div>
        
        {/* Output Port */}
        <Handle 
          type="source" 
          position={Position.Right}
          style={{ 
            background: TOKENS.primary,
            width: 10,
            height: 10,
            border: `2px solid ${TOKENS.black}`,
            right: -5
          }} 
        />
      </div>
      
      {/* File modal */}
      {renderFileModal()}
    </>
  );
};

export default EnhancedUserNode;