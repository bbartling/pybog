import React, { useState } from 'react';
import { Handle, Position, NodeProps } from 'reactflow';
import { FileText, Eye, Download, X, FileImage, File } from 'lucide-react';
import FileViewerModal from './FileViewerModal';

interface FileMessageData {
  content: string;
  timestamp?: Date;
  files?: File[];
  metadata?: {
    fileName?: string;
    file_id?: string;
    preview_url?: string;
    previewUrl?: string;
    fileType?: string;
    fileSize?: number;
  };
}

const FileMessageNode: React.FC<NodeProps<FileMessageData>> = ({ data }) => {
  const { content, timestamp, files, metadata } = data;
  const [viewerOpen, setViewerOpen] = useState(false);
  const [selectedFile, setSelectedFile] = useState<{ 
    name: string; 
    url: string; 
    type?: string;
    file_id?: number;
    file_size?: number;
    mime_type?: string;
    state?: string;
  } | null>(null);

  const formatFileSize = (bytes?: number) => {
    if (!bytes) return '';
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const getFileIcon = (fileName?: string, fileType?: string) => {
    const name = fileName?.toLowerCase() || '';
    const type = fileType?.toLowerCase() || '';
    
    if (name.endsWith('.pdf') || type.includes('pdf')) {
      return <FileText size={20} style={{ color: '#DC2626' }} />;
    }
    if (name.match(/\.(jpg|jpeg|png|gif|webp)$/) || type.includes('image')) {
      return <FileImage size={20} style={{ color: '#2563EB' }} />;
    }
    if (name.match(/\.(doc|docx)$/) || type.includes('word')) {
      return <FileText size={20} style={{ color: '#2563EB' }} />;
    }
    return <File size={20} style={{ color: '#6B7280' }} />;
  };

  const getFileType = (fileName?: string, mimeType?: string): 'pdf' | 'text' | 'json' | 'docx' | 'unknown' => {
    const name = fileName?.toLowerCase() || '';
    const mime = mimeType?.toLowerCase() || '';
    
    if (name.endsWith('.pdf') || mime.includes('pdf')) return 'pdf';
    if (name.endsWith('.txt') || mime.includes('text/plain')) return 'text';
    if (name.endsWith('.json') || mime.includes('json')) return 'json';
    if (name.endsWith('.docx') || mime.includes('word')) return 'docx';
    return 'unknown';
  };

  const handleViewFile = () => {
    const fileName = metadata?.fileName || 'File';
    const previewUrl = metadata?.preview_url || metadata?.previewUrl;
    
    if (previewUrl) {
      const fileType = getFileType(fileName, metadata?.fileType);
      setSelectedFile({ 
        name: fileName, 
        url: previewUrl,
        type: fileType,
        file_id: metadata?.file_id ? parseInt(metadata.file_id) : undefined,
        file_size: metadata?.fileSize,
        mime_type: metadata?.fileType,
        state: 'complete' // Assume complete if we can view it
      });
      setViewerOpen(true);
    }
  };

  const fileName = metadata?.fileName || (files && files[0]?.name) || 'Unknown File';
  const fileSize = metadata?.fileSize || (files && files[0]?.size);
  const previewUrl = metadata?.preview_url || metadata?.previewUrl;

  return (
    <>
      <Handle type="target" position={Position.Left} />
      
      <div style={{
        background: '#FFFFFF',
        border: '2px solid #3F3F4B',
        borderRadius: '12px',
        padding: '16px',
        minWidth: '300px',
        maxWidth: '400px',
        boxShadow: '4px 4px 0 0 rgba(63, 63, 75, 0.15)',
      }}>
        {/* Header */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          marginBottom: '12px',
          paddingBottom: '12px',
          borderBottom: '2px solid #E5E7EB',
        }}>
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            color: '#6B7280',
            fontSize: '12px',
            fontWeight: 600,
            textTransform: 'uppercase',
            letterSpacing: '0.05em',
          }}>
            <FileText size={14} />
            <span>File Upload</span>
          </div>
          {timestamp && (
            <span style={{ 
              fontSize: '11px', 
              color: '#9CA3AF',
              fontFamily: 'Monaco, monospace',
            }}>
              {new Date(timestamp).toLocaleTimeString()}
            </span>
          )}
        </div>

        {/* File Card */}
        <div style={{
          background: '#F9FAFB',
          border: '2px solid #E5E7EB',
          borderRadius: '8px',
          padding: '12px',
          display: 'flex',
          alignItems: 'center',
          gap: '12px',
          transition: 'all 0.2s ease',
          cursor: previewUrl ? 'pointer' : 'default',
        }}
        onMouseEnter={(e) => {
          if (previewUrl) {
            e.currentTarget.style.borderColor = '#569BFF';
            e.currentTarget.style.background = '#F0F9FF';
          }
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.borderColor = '#E5E7EB';
          e.currentTarget.style.background = '#F9FAFB';
        }}
        onClick={previewUrl ? handleViewFile : undefined}
        >
          {/* File Icon */}
          <div style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            width: '40px',
            height: '40px',
            background: '#FFFFFF',
            border: '2px solid #E5E7EB',
            borderRadius: '8px',
            flexShrink: 0,
          }}>
            {getFileIcon(fileName, metadata?.fileType)}
          </div>

          {/* File Info */}
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{
              fontWeight: 600,
              fontSize: '13px',
              color: '#3F3F4B',
              marginBottom: '4px',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap',
            }}>
              {fileName}
            </div>
            <div style={{
              fontSize: '11px',
              color: '#6B7280',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
            }}>
              {fileSize && <span>{formatFileSize(fileSize)}</span>}
              {metadata?.file_id && (
                <>
                  <span>•</span>
                  <span>ID: {metadata.file_id.substring(0, 8)}...</span>
                </>
              )}
            </div>
          </div>

          {/* Actions */}
          {previewUrl && (
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
            }}>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  handleViewFile();
                }}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  width: '32px',
                  height: '32px',
                  background: '#569BFF',
                  color: '#FFFFFF',
                  border: '2px solid #3F3F4B',
                  borderRadius: '6px',
                  cursor: 'pointer',
                  transition: 'all 0.2s ease',
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.background = '#3B82F6';
                  e.currentTarget.style.transform = 'translateY(-1px)';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.background = '#569BFF';
                  e.currentTarget.style.transform = 'translateY(0)';
                }}
                title="View file"
              >
                <Eye size={14} />
              </button>
              
              <a
                href={previewUrl}
                download={fileName}
                onClick={(e) => e.stopPropagation()}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  width: '32px',
                  height: '32px',
                  background: '#10B981',
                  color: '#FFFFFF',
                  border: '2px solid #3F3F4B',
                  borderRadius: '6px',
                  cursor: 'pointer',
                  transition: 'all 0.2s ease',
                  textDecoration: 'none',
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.background = '#059669';
                  e.currentTarget.style.transform = 'translateY(-1px)';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.background = '#10B981';
                  e.currentTarget.style.transform = 'translateY(0)';
                }}
                title="Download file"
              >
                <Download size={14} />
              </a>
            </div>
          )}
        </div>

        {/* Status Message */}
        {content && content !== `File uploaded: ${fileName}` && (
          <div style={{
            marginTop: '12px',
            padding: '8px 12px',
            background: '#F0FDF4',
            border: '2px solid #10B981',
            borderRadius: '6px',
            fontSize: '12px',
            color: '#065F46',
            fontWeight: 500,
          }}>
            {content}
          </div>
        )}
      </div>

      <Handle type="source" position={Position.Right} />

      {/* File Viewer Modal */}
      {viewerOpen && selectedFile && (
        <FileViewerModal
          isOpen={viewerOpen}
          onClose={() => {
            setViewerOpen(false);
            setSelectedFile(null);
          }}
          file={{ 
            name: selectedFile.name, 
            url: selectedFile.url, 
            type: selectedFile.type as any,
            file_id: selectedFile.file_id?.toString(),
            file_size: selectedFile.file_size,
            mime_type: selectedFile.mime_type,
            state: selectedFile.state
          }}
        />
      )}
    </>
  );
};

export default FileMessageNode;
