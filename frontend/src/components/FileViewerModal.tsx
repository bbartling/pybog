import React, { useEffect, useMemo, useState } from 'react';
import { X, Download, ExternalLink, FileText, FileCode, FileType } from 'lucide-react';
import { TOKENS, STYLES, COMPONENTS } from '../theme/neubrutalism';

export interface FileToView {
  name: string;
  url: string;
  type?: 'pdf' | 'text' | 'json' | 'docx' | 'unknown';
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

  const fileType = useMemo(() => {
    if (!file) return 'unknown';
    return file.type || deriveType(file.name, file.url) || 'unknown';
  }, [file]);

  useEffect(() => {
    if (!isOpen || !file) return;
    setTextContent('');
    setError(null);

    const load = async () => {
      try {
        if (fileType === 'text' || fileType === 'json') {
          const resp = await fetch(file.url);
          const txt = await resp.text();
          setTextContent(txt);
        }
      } catch (e: any) {
        setError(e?.message || 'Failed to load content');
      }
    };

    load();
  }, [isOpen, file, fileType]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    if (isOpen) window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [isOpen, onClose]);

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
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <a href={file.url} target="_blank" rel="noreferrer" style={{
              ...COMPONENTS.button.base, ...COMPONENTS.button.primary, textDecoration: 'none'
            }}>
              <ExternalLink size={14} style={{ marginRight: 6 }} /> Open
            </a>
            <a href={file.url} download style={{
              ...COMPONENTS.button.base, ...COMPONENTS.button.success, textDecoration: 'none'
            }}>
              <Download size={14} style={{ marginRight: 6 }} /> Download
            </a>
            <button onClick={onClose} style={{ ...COMPONENTS.button.base }}>
              <X size={14} />
            </button>
          </div>
        </div>

        {/* Body */}
        <div style={{ flex: 1, background: TOKENS.bg, padding: 12, overflow: 'hidden' }}>
          {/* Viewers */}
          {error && (
            <div style={{ color: TOKENS.error, fontWeight: 600 }}>{error}</div>
          )}

          {!error && fileType === 'pdf' && (
            <iframe title={file.name} src={file.url} style={{
              width: '100%', height: '100%', border: 'none', background: TOKENS.white
            }} />
          )}

          {!error && (fileType === 'text' || fileType === 'json') && (
            <div style={{
              width: '100%', height: '100%', background: TOKENS.white,
              border: STYLES.border.solid, borderRadius: STYLES.radius.medium,
              overflow: 'auto', padding: 12, fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace',
              fontSize: 12, whiteSpace: 'pre-wrap', wordBreak: 'break-word'
            }}>
              {textContent || 'Loading...'}
            </div>
          )}

          {!error && fileType === 'docx' && (
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
                <a href={file.url} target="_blank" rel="noreferrer" style={{ ...COMPONENTS.button.base, ...COMPONENTS.button.primary, textDecoration: 'none' }}>
                  <ExternalLink size={14} style={{ marginRight: 6 }} /> Open in new tab
                </a>
                <a href={file.url} download style={{ ...COMPONENTS.button.base, ...COMPONENTS.button.success, textDecoration: 'none', marginLeft: 8 }}>
                  <Download size={14} style={{ marginRight: 6 }} /> Download
                </a>
              </div>
            </div>
          )}

          {!error && fileType === 'unknown' && (
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
                <a href={file.url} target="_blank" rel="noreferrer" style={{ ...COMPONENTS.button.base, ...COMPONENTS.button.primary, textDecoration: 'none' }}>
                  <ExternalLink size={14} style={{ marginRight: 6 }} /> Open in new tab
                </a>
                <a href={file.url} download style={{ ...COMPONENTS.button.base, ...COMPONENTS.button.success, textDecoration: 'none', marginLeft: 8 }}>
                  <Download size={14} style={{ marginRight: 6 }} /> Download
                </a>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default FileViewerModal;

