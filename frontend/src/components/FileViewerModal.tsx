import React, { useEffect, useMemo, useState, useCallback } from 'react';
import { X, Download, ExternalLink, FileText, FileCode, FileType, ZoomIn, ZoomOut, Maximize2, Info } from 'lucide-react';
import { TOKENS, STYLES, COMPONENTS } from '../theme/neubrutalism';
import { unifiedAPIService } from '../services/UnifiedAPIService';

// Use runtime config if available, fallback to build-time env vars
const runtimeConfig = (window as any).RUNTIME_CONFIG;
const API_BASE_URL = runtimeConfig?.API_URL || process.env.REACT_APP_API_URL || 'http://localhost:8847';

export interface FileToView {
  name: string;
  url: string;
  type?: 'pdf' | 'text' | 'json' | 'docx' | 'unknown';
  file_id?: string;
  file_size?: number;
  mime_type?: string;
  created_at?: string;
  state?: string;
}

interface FileViewerModalProps {
  isOpen: boolean;
  file: FileToView | null;
  onClose: () => void;
}

function deriveType(name?: string, url?: string): FileToView['type'] {
  const source = `${name || ''} ${url || ''}`.toLowerCase();
  if (/\.pdf(\b|$)/.test(source)) return 'pdf';
  if (/\.(txt|md|log)(\b|$)/.test(source)) return 'text';
  if (/\.json(\b|$)/.test(source)) return 'json';
  if (/\.(docx|doc)(\b|$)/.test(source)) return 'docx';
  return 'unknown';
}

const FileViewerModal: React.FC<FileViewerModalProps> = ({ isOpen, file, onClose }) => {
  const [textContent, setTextContent] = useState<string>('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [fileMetadata, setFileMetadata] = useState<any>(null);
  const [zoom, setZoom] = useState<number>(100);
  const [showMetadata, setShowMetadata] = useState<boolean>(false);

  const fileType = useMemo(() => {
    if (!file) return 'unknown';
    return file.type || deriveType(file.name, file.url) || 'unknown';
  }, [file]);

  const loadFileContent = useCallback(async () => {
    if (!file) return;
    
    setLoading(true);
    setError(null);
    setTextContent('');
    
    try {
      // If we have a file_id, use the backend API
      if (file.file_id) {
        // Get file metadata
        const metadata = await unifiedAPIService.getFile(Number(file.file_id));
        setFileMetadata(metadata);
        
        // Load content for text files
        if (fileType === 'text' || fileType === 'json') {
          const contentResponse = await fetch(`${API_BASE_URL}/api/files/${file.file_id}/content`);
          if (contentResponse.ok) {
            const contentData = await contentResponse.json();
            setTextContent(contentData.content || '');
          } else {
            throw new Error('Failed to load file content');
          }
        }
      } else {
        // Fallback to direct URL fetch
        if (fileType === 'text' || fileType === 'json') {
          const resp = await fetch(file.url);
          const txt = await resp.text();
          setTextContent(txt);
        }
      }
    } catch (e: any) {
      setError(e?.message || 'Failed to load content');
    } finally {
      setLoading(false);
    }
  }, [file, fileType]);

  useEffect(() => {
    if (!isOpen || !file) return;
    loadFileContent();
  }, [isOpen, file, loadFileContent]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { 
      if (e.key === 'Escape') onClose();
      if (e.key === '+' || e.key === '=') handleZoomIn();
      if (e.key === '-') handleZoomOut();
      if (e.key === '0') setZoom(100);
    };
    if (isOpen) window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [isOpen, onClose]);

  const handleZoomIn = () => setZoom(prev => Math.min(prev + 25, 300));
  const handleZoomOut = () => setZoom(prev => Math.max(prev - 25, 25));
  const handleZoomReset = () => setZoom(100);

  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const formatDate = (dateString: string): string => {
    return new Date(dateString).toLocaleString();
  };

  if (!isOpen || !file) return null;

  return (
    <div style={{
      position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.35)',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      zIndex: 10000,
    }}>
      <div style={{
        width: '88vw', height: '88vh', background: TOKENS.white,
        border: STYLES.border.solid, borderRadius: STYLES.radius.large,
        boxShadow: STYLES.shadow.lg, display: 'flex', flexDirection: 'column',
      }}>
        {/* Header */}
        <div style={{
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          padding: '10px 14px', borderBottom: STYLES.border.solid,
          background: TOKENS.systemHeader,
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            {fileType === 'pdf' && <FileType size={16} />}
            {(fileType === 'text' || fileType === 'json') && <FileText size={16} />}
            {fileType === 'docx' && <FileCode size={16} />}
            <div style={{ fontWeight: 700, color: TOKENS.text, fontSize: 13 }}>{file.name}</div>
            <div style={{ ...COMPONENTS.badge.base, ...COMPONENTS.badge.info }}>{fileType?.toUpperCase()}</div>
            {fileMetadata?.state && (
              <div style={{ 
                ...COMPONENTS.badge.base, 
                ...(fileMetadata.state === 'complete' ? COMPONENTS.badge.success : 
                   fileMetadata.state === 'failed' ? COMPONENTS.badge.error : 
                   COMPONENTS.badge.warning)
              }}>
                {fileMetadata.state.toUpperCase()}
              </div>
            )}
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            {/* Zoom controls for PDFs and images */}
            {fileType === 'pdf' && (
              <>
                <button onClick={handleZoomOut} style={{ ...COMPONENTS.button.base }} title="Zoom Out (-)">
                  <ZoomOut size={14} />
                </button>
                <span style={{ fontSize: 12, color: TOKENS.text, minWidth: 40, textAlign: 'center' }}>
                  {zoom}%
                </span>
                <button onClick={handleZoomIn} style={{ ...COMPONENTS.button.base }} title="Zoom In (+)">
                  <ZoomIn size={14} />
                </button>
                <button onClick={handleZoomReset} style={{ ...COMPONENTS.button.base }} title="Reset Zoom (0)">
                  <Maximize2 size={14} />
                </button>
              </>
            )}
            
            {/* Metadata toggle */}
            <button 
              onClick={() => setShowMetadata(!showMetadata)} 
              style={{ 
                ...COMPONENTS.button.base, 
                ...(showMetadata ? COMPONENTS.button.primary : {})
              }}
              title="File Info"
            >
              <Info size={14} />
            </button>
            
            {/* Download button - use backend endpoint if file_id available */}
            <a 
              href={file.file_id ? 
`${API_BASE_URL}/api/files/${file.file_id}/download` : 
                file.url
              } 
              target="_blank" 
              rel="noreferrer" 
              style={{
                ...COMPONENTS.button.base, ...COMPONENTS.button.primary, textDecoration: 'none'
              }}
            >
              <ExternalLink size={14} style={{ marginRight: 6 }} /> Open
            </a>
            <a 
              href={file.file_id ? 
`${API_BASE_URL}/api/files/${file.file_id}/download` : 
                file.url
              } 
              download 
              style={{
                ...COMPONENTS.button.base, ...COMPONENTS.button.success, textDecoration: 'none'
              }}
            >
              <Download size={14} style={{ marginRight: 6 }} /> Download
            </a>
            <button onClick={onClose} style={{ ...COMPONENTS.button.base }}>
              <X size={14} />
            </button>
          </div>
        </div>

        {/* Body */}
        <div style={{ flex: 1, background: TOKENS.bg, display: 'flex', overflow: 'hidden' }}>
          {/* Main content area */}
          <div style={{ flex: 1, padding: 12, overflow: 'hidden' }}>
            {/* Loading state */}
            {loading && (
              <div style={{ 
                display: 'flex', alignItems: 'center', justifyContent: 'center', 
                height: '100%', color: TOKENS.text, fontSize: 14 
              }}>
                Loading file content...
              </div>
            )}

            {/* Error state */}
            {error && !loading && (
              <div style={{
                background: TOKENS.white, border: STYLES.border.solid, borderRadius: STYLES.radius.medium,
                padding: 16, color: TOKENS.error
              }}>
                <div style={{ fontWeight: 700, marginBottom: 8 }}>Error loading file</div>
                <div style={{ fontSize: 13, marginBottom: 12 }}>{error}</div>
                <button 
                  onClick={loadFileContent}
                  style={{ ...COMPONENTS.button.base, ...COMPONENTS.button.primary }}
                >
                  Retry
                </button>
              </div>
            )}

            {/* PDF Viewer */}
            {!error && !loading && fileType === 'pdf' && (
              <div style={{ width: '100%', height: '100%', position: 'relative' }}>
                <iframe
                  title={file.name}
                  src={file.file_id ?
                    `${API_BASE_URL}/api/files/${file.file_id}/preview` :
                    file.url
                  }
                  style={{
                    width: '100%',
                    height: '100%',
                    border: 'none',
                    background: TOKENS.white,
                    borderRadius: STYLES.radius.medium,
                    transform: `scale(${zoom / 100})`,
                    transformOrigin: 'top left'
                  }}
                  onLoad={() => {
                    console.log('[FileViewer] PDF loaded successfully');
                    setError(null);
                  }}
                  onError={(e) => {
                    console.error('[FileViewer] PDF load error:', e);
                    setError('Failed to load PDF preview. Try downloading the file.');
                  }}
                />
              </div>
            )}

            {/* Text/JSON Viewer */}
            {!error && !loading && (fileType === 'text' || fileType === 'json') && (
              <div style={{
                width: '100%', height: '100%', background: TOKENS.white,
                border: STYLES.border.solid, borderRadius: STYLES.radius.medium,
                overflow: 'auto', padding: 12, 
                fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace',
                fontSize: 12, whiteSpace: 'pre-wrap', wordBreak: 'break-word'
              }}>
                {textContent || 'No content available'}
              </div>
            )}

            {/* DOCX Viewer */}
            {!error && !loading && fileType === 'docx' && (
              <div style={{
                width: '100%', height: '100%', background: TOKENS.white,
                border: STYLES.border.solid, borderRadius: STYLES.radius.medium,
                padding: 16, color: TOKENS.text
              }}>
                <div style={{ fontWeight: 700, marginBottom: 8 }}>DOCX preview not available inline</div>
                <div style={{ fontSize: 13, color: TOKENS.muted, marginBottom: 12 }}>
                  Browser-native inline viewing of .docx is limited. Use Open or Download.
                </div>
                <div>
                  <a 
                    href={file.file_id ? 
  `${API_BASE_URL}/api/files/${file.file_id}/preview` : 
                      file.url
                    } 
                    target="_blank" 
                    rel="noreferrer" 
                    style={{ ...COMPONENTS.button.base, ...COMPONENTS.button.primary, textDecoration: 'none' }}
                  >
                    <ExternalLink size={14} style={{ marginRight: 6 }} /> Open in new tab
                  </a>
                  <a 
                    href={file.file_id ? 
      `${API_BASE_URL}/api/files/${file.file_id}/download` : 
                      file.url
                    } 
                    download 
                    style={{ ...COMPONENTS.button.base, ...COMPONENTS.button.success, textDecoration: 'none', marginLeft: 8 }}
                  >
                    <Download size={14} style={{ marginRight: 6 }} /> Download
                  </a>
                </div>
              </div>
            )}

            {/* Unknown file type */}
            {!error && !loading && fileType === 'unknown' && (
              <div style={{
                width: '100%', height: '100%', background: TOKENS.white,
                border: STYLES.border.solid, borderRadius: STYLES.radius.medium,
                padding: 16, color: TOKENS.text
              }}>
                <div style={{ fontWeight: 700, marginBottom: 8 }}>Preview not available</div>
                <div style={{ fontSize: 13, color: TOKENS.muted, marginBottom: 12 }}>
                  This file type is not supported for inline preview. Try Open or Download.
                </div>
                <div>
                  <a 
                    href={file.file_id ? 
  `${API_BASE_URL}/api/files/${file.file_id}/preview` : 
                      file.url
                    } 
                    target="_blank" 
                    rel="noreferrer" 
                    style={{ ...COMPONENTS.button.base, ...COMPONENTS.button.primary, textDecoration: 'none' }}
                  >
                    <ExternalLink size={14} style={{ marginRight: 6 }} /> Open in new tab
                  </a>
                  <a 
                    href={file.file_id ? 
      `${API_BASE_URL}/api/files/${file.file_id}/download` : 
                      file.url
                    } 
                    download 
                    style={{ ...COMPONENTS.button.base, ...COMPONENTS.button.success, textDecoration: 'none', marginLeft: 8 }}
                  >
                    <Download size={14} style={{ marginRight: 6 }} /> Download
                  </a>
                </div>
              </div>
            )}
          </div>

          {/* Metadata sidebar */}
          {showMetadata && (
            <div style={{
              width: 300, borderLeft: STYLES.border.solid, background: TOKENS.white,
              padding: 16, overflow: 'auto'
            }}>
              <div style={{ fontWeight: 700, marginBottom: 12, color: TOKENS.text }}>File Information</div>
              
              <div style={{ fontSize: 12, color: TOKENS.text }}>
                <div style={{ marginBottom: 8 }}>
                  <strong>Name:</strong> {file.name}
                </div>
                
                {fileMetadata && (
                  <>
                    <div style={{ marginBottom: 8 }}>
                      <strong>Size:</strong> {formatFileSize(fileMetadata.file_size || file.file_size || 0)}
                    </div>
                    
                    <div style={{ marginBottom: 8 }}>
                      <strong>Type:</strong> {fileMetadata.mime_type || file.mime_type || 'Unknown'}
                    </div>
                    
                    <div style={{ marginBottom: 8 }}>
                      <strong>Status:</strong> {fileMetadata.state || file.state || 'Unknown'}
                    </div>
                    
                    {fileMetadata.created_at && (
                      <div style={{ marginBottom: 8 }}>
                        <strong>Created:</strong> {formatDate(fileMetadata.created_at)}
                      </div>
                    )}
                    
                    {fileMetadata.file_type && (
                      <div style={{ marginBottom: 8 }}>
                        <strong>Category:</strong> {fileMetadata.file_type}
                      </div>
                    )}
                  </>
                )}
                
                {file.file_id && (
                  <div style={{ marginBottom: 8 }}>
                    <strong>File ID:</strong> {file.file_id}
                  </div>
                )}
              </div>
              
              {/* Keyboard shortcuts */}
              <div style={{ marginTop: 16, paddingTop: 16, borderTop: STYLES.border.solid }}>
                <div style={{ fontWeight: 700, marginBottom: 8, fontSize: 12 }}>Keyboard Shortcuts</div>
                <div style={{ fontSize: 11, color: TOKENS.muted }}>
                  <div>ESC - Close viewer</div>
                  {fileType === 'pdf' && (
                    <>
                      <div>+ - Zoom in</div>
                      <div>- - Zoom out</div>
                      <div>0 - Reset zoom</div>
                    </>
                  )}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default FileViewerModal;

