import React from 'react';
import { createPortal } from 'react-dom';
import { X, Copy, Download, FileText } from 'lucide-react';
import { TOKENS, STYLES, COMPONENTS } from '../theme/neubrutalism';

interface TextExpansionModalProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  content: string;
  timestamp?: Date | string;
  messageType?: 'user' | 'assistant' | 'system';
  showActions?: boolean;
}

const TextExpansionModal: React.FC<TextExpansionModalProps> = ({
  isOpen,
  onClose,
  title,
  content,
  timestamp,
  messageType = 'assistant',
  showActions = true,
}) => {
  // Handle ESC key closing
  React.useEffect(() => {
    const handleEscapeKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        onClose();
      }
    };

    if (isOpen) {
      document.addEventListener('keydown', handleEscapeKey);
      // Prevent background scrolling when modal is open
      document.body.style.overflow = 'hidden';
    }

    return () => {
      document.removeEventListener('keydown', handleEscapeKey);
      document.body.style.overflow = 'unset';
    };
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  // Force cache refresh

  // Handle backdrop click
  const handleBackdropClick = (e: React.MouseEvent) => {
    if (e.target === e.currentTarget) {
      onClose();
    }
  };

  const handleCopyText = () => {
    navigator.clipboard.writeText(content);
  };

  const handleDownloadText = () => {
    const blob = new Blob([content], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `message-${Date.now()}.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const formatContent = (text: string) => {
    // Simplified but robust formatting that preserves line breaks and enhances readability
    const lines = text.split('\n');
    const elements: JSX.Element[] = [];
    let i = 0;

    while (i < lines.length) {
      const line = lines[i];

      // Code blocks (```...```)
      if (line.trim().startsWith('```')) {
        const codeLines: string[] = [];
        i++; // Skip the opening ```
        while (i < lines.length && !lines[i].trim().startsWith('```')) {
          codeLines.push(lines[i]);
          i++;
        }
        i++; // Skip the closing ```

        elements.push(
          <div key={`code-${elements.length}`} style={{
            background: 'linear-gradient(135deg, #0a0c10 0%, #1a1d24 100%)',
            border: `4px solid ${TOKENS.text}`,
            borderRadius: '12px',
            padding: '24px',
            margin: '20px 0',
            fontFamily: "'JetBrains Mono', 'Fira Code', 'SF Mono', Consolas, monospace",
            fontSize: '14px',
            color: '#e6edf3',
            overflow: 'auto',
            boxShadow: `6px 6px 0px ${TOKENS.text}`,
            position: 'relative',
            maxHeight: '500px',
          }}>
            <button
              onClick={() => navigator.clipboard.writeText(codeLines.join('\n'))}
              style={{
                position: 'absolute',
                top: '12px',
                right: '12px',
                background: TOKENS.success,
                border: `2px solid ${TOKENS.text}`,
                borderRadius: '6px',
                color: TOKENS.white,
                padding: '6px 10px',
                fontSize: '10px',
                fontWeight: 700,
                cursor: 'pointer',
                zIndex: 10,
                boxShadow: `2px 2px 0 ${TOKENS.text}`,
              }}
              title="Copy code block"
            >
              COPY
            </button>
            <pre style={{
              margin: 0,
              whiteSpace: 'pre-wrap',
              lineHeight: 1.6,
              paddingRight: '80px',
              fontSize: '14px',
            }}>
              {codeLines.join('\n')}
            </pre>
          </div>
        );
        continue;
      }

      // Headers (## or **)
      if (line.trim().startsWith('##') || (line.trim().startsWith('**') && line.trim().endsWith('**'))) {
        const headerText = line.trim().startsWith('##')
          ? line.replace(/^#+\s*/, '')
          : line.replace(/^\*\*|\*\*$/g, '');

        elements.push(
          <div key={`header-${elements.length}`} style={{
            fontWeight: 800,
            color: TOKENS.white,
            marginBottom: '16px',
            marginTop: elements.length > 0 ? '32px' : '0',
            fontSize: '18px',
            textTransform: 'uppercase',
            letterSpacing: '0.5px',
            padding: '16px 24px',
            background: `linear-gradient(135deg, ${TOKENS.primary} 0%, #3b82f6 100%)`,
            border: `4px solid ${TOKENS.text}`,
            borderRadius: '8px',
            boxShadow: `4px 4px 0 ${TOKENS.text}`,
          }}>
            🔥 {headerText}
          </div>
        );
        i++;
        continue;
      }

      // Bullet points - improved to handle multi-line content
      if (line.trim().startsWith('•') || line.trim().startsWith('-') || line.trim().startsWith('*')) {
        const bulletText = line.replace(/^[\s•\-\*]+/, '').trim();

        // Check for continued content on next lines (indented)
        let fullContent = bulletText;
        let nextIndex = i + 1;

        while (nextIndex < lines.length) {
          const nextLine = lines[nextIndex];
          // If next line is indented or continues the list item
          if (nextLine.match(/^\s{2,}/) && !nextLine.match(/^\s*\d+\./) && !nextLine.match(/^\s*[\*\-\•]/)) {
            fullContent += '\n' + nextLine.trim();
            nextIndex++;
          } else {
            break;
          }
        }

        elements.push(
          <div key={`bullet-${elements.length}`} style={{
            marginLeft: '24px',
            marginBottom: '16px',
            padding: '16px 20px',
            background: `linear-gradient(135deg, ${TOKENS.white} 0%, #f0fdf4 100%)`,
            border: `3px solid ${TOKENS.text}`,
            borderLeft: `6px solid ${TOKENS.success}`,
            borderRadius: '8px',
            boxShadow: `4px 4px 0 ${TOKENS.text}`,
            color: TOKENS.text,
            fontSize: '15px',
            display: 'flex',
            alignItems: 'flex-start',
            gap: '16px',
            lineHeight: 1.6,
          }}>
            <span style={{
              color: TOKENS.success,
              fontWeight: 800,
              fontSize: '16px',
              marginTop: '2px',
              flexShrink: 0,
            }}>▶</span>
            <div style={{
              flex: 1,
              whiteSpace: 'pre-wrap',
              lineHeight: 1.7,
              fontWeight: 500,
            }}>
              {fullContent}
            </div>
          </div>
        );

        i = nextIndex;
        continue;
      }

      // Numbered lists - improved to handle multi-line content
      if (/^\s*\d+\./.test(line)) {
        const match = line.match(/^\s*(\d+)\.\s*(.*)/);
        if (match) {
          const [, number, listText] = match;

          // Check for continued content on next lines (indented)
          let fullContent = listText;
          let nextIndex = i + 1;

          while (nextIndex < lines.length) {
            const nextLine = lines[nextIndex];
            // If next line is indented or continues the list item
            if (nextLine.match(/^\s{2,}/) && !nextLine.match(/^\s*\d+\./) && !nextLine.match(/^\s*[\*\-\•]/)) {
              fullContent += '\n' + nextLine.trim();
              nextIndex++;
            } else {
              break;
            }
          }

          elements.push(
            <div key={`number-${elements.length}`} style={{
              marginLeft: '24px',
              marginBottom: '16px',
              padding: '16px 20px',
              background: `linear-gradient(135deg, ${TOKENS.white} 0%, #f8f9fa 100%)`,
              border: `3px solid ${TOKENS.text}`,
              borderLeft: `6px solid ${TOKENS.primary}`,
              borderRadius: '8px',
              boxShadow: `4px 4px 0 ${TOKENS.text}`,
              color: TOKENS.text,
              fontSize: '15px',
              display: 'flex',
              alignItems: 'flex-start',
              gap: '16px',
              lineHeight: 1.6,
            }}>
              <span style={{
                background: `linear-gradient(135deg, ${TOKENS.primary} 0%, #2563eb 100%)`,
                color: TOKENS.white,
                border: `3px solid ${TOKENS.text}`,
                borderRadius: '50%',
                width: '28px',
                height: '28px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: '12px',
                fontWeight: 800,
                flexShrink: 0,
                boxShadow: `2px 2px 0 ${TOKENS.text}`,
              }}>
                {number}
              </span>
              <div style={{
                flex: 1,
                whiteSpace: 'pre-wrap',
                lineHeight: 1.7,
                fontWeight: 500,
              }}>
                {fullContent}
              </div>
            </div>
          );

          i = nextIndex;
          continue;
        }
      }

      // Regular text lines with inline formatting
      if (line.trim()) {
        // Process inline formatting like **bold** and *italic*
        const processInlineFormatting = (text: string): React.ReactNode[] => {
          const parts: React.ReactNode[] = [];
          let remaining = text;
          let key = 0;

          while (remaining.length > 0) {
            // Match **bold** text
            const boldMatch = remaining.match(/^(.*?)\*\*(.*?)\*\*(.*)/);
            if (boldMatch) {
              const [, before, boldText, after] = boldMatch;
              if (before) parts.push(<span key={key++}>{before}</span>);
              parts.push(
                <strong key={key++} style={{
                  fontWeight: 800,
                  color: TOKENS.text,
                  background: `linear-gradient(135deg, ${TOKENS.primary}15 0%, ${TOKENS.primary}05 100%)`,
                  padding: '2px 6px',
                  borderRadius: '4px',
                }}>
                  {boldText}
                </strong>
              );
              remaining = after;
              continue;
            }

            // Match *italic* text
            const italicMatch = remaining.match(/^(.*?)\*(.*?)\*(.*)/);
            if (italicMatch) {
              const [, before, italicText, after] = italicMatch;
              if (before) parts.push(<span key={key++}>{before}</span>);
              parts.push(
                <em key={key++} style={{
                  fontStyle: 'italic',
                  color: TOKENS.primary,
                  fontWeight: 600,
                }}>
                  {italicText}
                </em>
              );
              remaining = after;
              continue;
            }

            // No more formatting, add remaining text
            parts.push(<span key={key++}>{remaining}</span>);
            break;
          }

          return parts;
        };

        elements.push(
          <div key={`text-${elements.length}`} style={{
            marginBottom: '16px',
            color: TOKENS.text,
            lineHeight: 1.8,
            fontSize: '16px',
            padding: '12px 0',
            whiteSpace: 'pre-wrap',
            userSelect: 'text',
            fontWeight: 500,
          }}>
            {processInlineFormatting(line)}
          </div>
        );
      } else {
        // Empty line spacing
        elements.push(
          <div key={`space-${elements.length}`} style={{ height: '16px' }} />
        );
      }

      i++;
    }

    return elements.length > 0 ? elements : [
      <div key="fallback" style={{
        color: TOKENS.text,
        fontSize: '16px',
        lineHeight: 1.7,
        whiteSpace: 'pre-wrap',
        padding: '16px',
        background: TOKENS.white,
        border: `3px solid ${TOKENS.text}`,
        borderRadius: '8px',
        boxShadow: `3px 3px 0 ${TOKENS.text}`,
      }}>
        {text}
      </div>
    ];
  };

  return createPortal(
    <div
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: 'rgba(0, 0, 0, 0.6)', // Darker backdrop like PDF viewer for better focus
        zIndex: 50000, // Very high z-index to ensure it's completely detached and above everything
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '20px',
        backdropFilter: 'blur(1px)', // Subtle blur to keep context visible
        cursor: 'pointer', // Indicate clickable backdrop
      }}
      onClick={handleBackdropClick}
    >
      <div
        style={{
          background: TOKENS.white,
          border: `6px solid ${TOKENS.text}`, // Thick Neo-Brutalism border
          borderRadius: '12px', // Clean rounded corners
          boxShadow: `12px 12px 0 ${TOKENS.text}`, // Strong but not overwhelming shadow
          width: '85vw', // Much larger like PDF viewer - 85% of viewport
          maxWidth: '1400px', // Significantly larger max width for better content visibility
          height: '85vh', // Much taller - 85% of viewport height
          maxHeight: '85vh',
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
          fontFamily: "'Inter', 'SF Pro Display', system-ui, sans-serif",
          position: 'relative',
          transform: 'translateZ(0)',
          animation: 'modalSlideIn 0.3s cubic-bezier(0.4, 0.0, 0.2, 1)', // Smooth entrance animation
          cursor: 'default', // Reset cursor for modal content
        }}
        onClick={(e) => e.stopPropagation()} // Prevent backdrop click when clicking modal content
      >
        {/* Header */}
        <div style={{
          background: messageType === 'user' ? TOKENS.userHeader :
                     messageType === 'system' ? TOKENS.systemHeader :
                     TOKENS.systemHeader,
          padding: `${STYLES.spacing.xl} ${STYLES.spacing.xxl}`,
          borderBottom: `6px solid ${TOKENS.text}`, // Thicker bottom border
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          boxShadow: `0 6px 0 ${TOKENS.text}`, // Inset shadow for depth
          position: 'relative',
          // Neo-Brutalism gradient overlay
          backgroundImage: `linear-gradient(135deg,
            ${messageType === 'user' ? TOKENS.userHeader : TOKENS.systemHeader} 0%,
            ${messageType === 'user' ? TOKENS.userBody : TOKENS.systemBody} 100%)`,
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: STYLES.spacing.lg }}>
            {/* Enhanced icon with Neo-Brutalism styling */}
            <div style={{
              background: TOKENS.white,
              border: `4px solid ${TOKENS.text}`,
              borderRadius: '8px',
              padding: '12px',
              boxShadow: `4px 4px 0 ${TOKENS.text}`,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}>
              <FileText size={24} color={TOKENS.text} />
            </div>
            <div>
              <div style={{
                fontWeight: 800,
                color: TOKENS.text,
                fontSize: '20px', // Larger title
                textTransform: 'uppercase',
                letterSpacing: '0.5px',
                textShadow: `2px 2px 0 ${TOKENS.white}`,
                marginBottom: '4px',
              }}>
                {title}
              </div>
              {timestamp && (
                <div style={{
                  fontSize: STYLES.fontSize.sm,
                  color: TOKENS.muted,
                  marginTop: 2
                }}>
                  {new Date(timestamp).toLocaleString()}
                </div>
              )}
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: STYLES.spacing.md }}>
            {showActions && (
              <>
                {/* Copy Button with Neo-Brutalism styling */}
                <button
                  onClick={handleCopyText}
                  style={{
                    background: TOKENS.success,
                    border: `4px solid ${TOKENS.text}`,
                    borderRadius: '8px',
                    padding: '12px 16px',
                    color: TOKENS.white,
                    fontWeight: 700,
                    fontSize: '12px',
                    textTransform: 'uppercase',
                    letterSpacing: '0.5px',
                    cursor: 'pointer',
                    boxShadow: `4px 4px 0 ${TOKENS.text}`,
                    transition: 'all 0.1s ease',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px',
                  }}
                  title="Copy full text"
                  onMouseEnter={(e) => {
                    e.currentTarget.style.transform = 'translate(-2px, -2px)';
                    e.currentTarget.style.boxShadow = `6px 6px 0 ${TOKENS.text}`;
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.transform = 'translate(0, 0)';
                    e.currentTarget.style.boxShadow = `4px 4px 0 ${TOKENS.text}`;
                  }}
                >
                  <Copy size={16} />
                  COPY
                </button>
                {/* Download Button */}
                <button
                  onClick={handleDownloadText}
                  style={{
                    background: TOKENS.primary,
                    border: `4px solid ${TOKENS.text}`,
                    borderRadius: '8px',
                    padding: '12px 16px',
                    color: TOKENS.white,
                    fontWeight: 700,
                    fontSize: '12px',
                    textTransform: 'uppercase',
                    letterSpacing: '0.5px',
                    cursor: 'pointer',
                    boxShadow: `4px 4px 0 ${TOKENS.text}`,
                    transition: 'all 0.1s ease',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px',
                  }}
                  title="Download as text file"
                  onMouseEnter={(e) => {
                    e.currentTarget.style.transform = 'translate(-2px, -2px)';
                    e.currentTarget.style.boxShadow = `6px 6px 0 ${TOKENS.text}`;
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.transform = 'translate(0, 0)';
                    e.currentTarget.style.boxShadow = `4px 4px 0 ${TOKENS.text}`;
                  }}
                >
                  <Download size={16} />
                  SAVE
                </button>
              </>
            )}
            {/* Close Button */}
            <button
              onClick={onClose}
              style={{
                background: TOKENS.error,
                border: `4px solid ${TOKENS.text}`,
                borderRadius: '8px',
                padding: '12px 16px',
                color: TOKENS.white,
                fontWeight: 700,
                fontSize: '12px',
                textTransform: 'uppercase',
                letterSpacing: '0.5px',
                cursor: 'pointer',
                boxShadow: `4px 4px 0 ${TOKENS.text}`,
                transition: 'all 0.1s ease',
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
              }}
              title="Close modal"
              onMouseEnter={(e) => {
                e.currentTarget.style.transform = 'translate(-2px, -2px)';
                e.currentTarget.style.boxShadow = `6px 6px 0 ${TOKENS.text}`;
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.transform = 'translate(0, 0)';
                e.currentTarget.style.boxShadow = `4px 4px 0 ${TOKENS.text}`;
              }}
            >
              <X size={16} />
              CLOSE
            </button>
          </div>
        </div>

        {/* Enhanced Content Area with Neo-Brutalism styling */}
        <div style={{
          flex: 1,
          overflow: 'auto',
          padding: `${STYLES.spacing.xxl} ${STYLES.spacing.xxl}`,
          background: `linear-gradient(135deg, ${TOKENS.bg} 0%, #FAFBFC 100%)`, // Subtle gradient
          fontFamily: "'Inter', 'SF Pro Display', system-ui, -apple-system, sans-serif",
          fontSize: '16px', // Even larger base font for excellent readability
          lineHeight: 1.8, // Spacious line height for easy reading
          color: TOKENS.text,
          position: 'relative',
          // Enhanced scrollbar for Neo-Brutalism style
          scrollbarWidth: 'thick',
          scrollbarColor: `${TOKENS.primary} ${TOKENS.bg}`,
        }}>
          <style>{`
            /* Enhanced Neo-Brutalism scrollbar */
            .modal-content::-webkit-scrollbar {
              width: 16px;
            }
            .modal-content::-webkit-scrollbar-track {
              background: ${TOKENS.bg};
              border: 4px solid ${TOKENS.text};
              border-radius: 8px;
              margin: 4px;
            }
            .modal-content::-webkit-scrollbar-thumb {
              background: ${TOKENS.primary};
              border: 3px solid ${TOKENS.text};
              border-radius: 8px;
              box-shadow: 2px 2px 0 ${TOKENS.text};
            }
            .modal-content::-webkit-scrollbar-thumb:hover {
              background: ${TOKENS.success};
              transform: scale(1.1);
            }
            .modal-content::-webkit-scrollbar-corner {
              background: ${TOKENS.bg};
            }

            /* Modal entrance animation */
            @keyframes modalSlideIn {
              0% {
                opacity: 0;
                transform: scale(0.9) translateY(-20px);
              }
              100% {
                opacity: 1;
                transform: scale(1) translateY(0);
              }
            }

            /* Typography enhancements */
            .modal-content h1, .modal-content h2, .modal-content h3 {
              border-left: 6px solid ${TOKENS.primary};
              padding-left: 16px;
              margin: 24px 0 16px 0;
              background: ${TOKENS.white};
              padding: 12px 16px;
              border-radius: 8px;
              box-shadow: 3px 3px 0 ${TOKENS.text};
            }
          `}</style>
          <div className="modal-content" style={{ height: '100%', overflow: 'auto' }}>
            {formatContent(content)}
          </div>
        </div>
      </div>
    </div>,
    document.body
  );
};

export default TextExpansionModal;