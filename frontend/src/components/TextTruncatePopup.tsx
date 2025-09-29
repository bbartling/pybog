import React, { useState, useRef, useEffect } from 'react';
import { createPortal } from 'react-dom';
import { TOKENS, STYLES, COMPONENTS } from '../theme/neubrutalism';

interface TextTruncatePopupProps {
  text: string;
  maxLength?: number;
  maxLines?: number;
  className?: string;
  style?: React.CSSProperties;
}

const TextTruncatePopup: React.FC<TextTruncatePopupProps> = ({
  text,
  maxLength = 150,
  maxLines = 3,
  className,
  style
}) => {
  const [showPopup, setShowPopup] = useState(false);
  const [isClickedOpen, setIsClickedOpen] = useState(false);
  const [popupPosition, setPopupPosition] = useState({ x: 0, y: 0 });
  const textRef = useRef<HTMLDivElement>(null);
  const popupRef = useRef<HTMLDivElement>(null);

  const shouldTruncate = text.length > maxLength;
  const truncatedText = shouldTruncate ? text.slice(0, maxLength) + '...' : text;

  const calculatePopupPosition = (event: React.MouseEvent) => {
    const rect = event.currentTarget.getBoundingClientRect();
    const viewportWidth = window.innerWidth;
    const viewportHeight = window.innerHeight;

    // Much larger popup dimensions
    const popupWidth = Math.min(800, viewportWidth - 40);
    const popupHeight = Math.min(600, viewportHeight - 40);

    // Center the popup in viewport
    let x = viewportWidth / 2;
    let y = viewportHeight / 2;

    setPopupPosition({ x, y });
  };

  const handleMouseEnter = (event: React.MouseEvent) => {
    if (!shouldTruncate || isClickedOpen) return;
    calculatePopupPosition(event);
    setShowPopup(true);
  };

  const handleMouseLeave = () => {
    if (!isClickedOpen) {
      setShowPopup(false);
    }
  };

  const handleClick = (event: React.MouseEvent) => {
    if (!shouldTruncate) return;
    event.stopPropagation();
    calculatePopupPosition(event);
    setIsClickedOpen(true);
    setShowPopup(true);
  };

  const handleClosePopup = () => {
    setShowPopup(false);
    setIsClickedOpen(false);
  };

  // Close popup when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (popupRef.current && !popupRef.current.contains(event.target as Node)) {
        handleClosePopup();
      }
    };

    const handleEscapeKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        handleClosePopup();
      }
    };

    if (showPopup) {
      document.addEventListener('mousedown', handleClickOutside);
      document.addEventListener('keydown', handleEscapeKey);
      return () => {
        document.removeEventListener('mousedown', handleClickOutside);
        document.removeEventListener('keydown', handleEscapeKey);
      };
    }
  }, [showPopup]);

  // Format HVAC analysis content for better display
  const formatAnalysisContent = (content: string) => {
    // Check if this looks like HVAC analysis content
    const hasHvacTerms = /(?:temperature|sensor|actuator|damper|valve|fan|control|hvac|i\/o|point|block)/i.test(content);

    if (hasHvacTerms) {
      return content
        .replace(/(\*\*.*?\*\*)/g, '<strong>$1</strong>') // Bold markdown
        .replace(/^(#{1,6})\s*(.+)$/gm, '<h$1.length class="analysis-header">$2</h$1.length>') // Headers
        .replace(/^[-•]\s*(.+)$/gm, '<li class="analysis-item">$1</li>') // List items
        .replace(/(\d+\.\s*.+?)(?=\n|$)/g, '<div class="analysis-step">$1</div>') // Numbered items
        .replace(/\n\n/g, '<br><br>'); // Line breaks
    }

    return content.replace(/\n/g, '<br>');
  };

  const viewportWidth = window.innerWidth;
  const viewportHeight = window.innerHeight;
  const popupWidth = Math.min(800, viewportWidth - 40);
  const popupHeight = Math.min(600, viewportHeight - 40);

  const popupContent = showPopup && shouldTruncate && (
    <>
      {/* Backdrop */}
      <div
        style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: 'rgba(0, 0, 0, 0.4)',
          zIndex: 9999,
          backdropFilter: 'blur(2px)',
        }}
        onClick={handleClosePopup}
      />

      {/* Modal */}
      <div
        ref={popupRef}
        style={{
          position: 'fixed',
          left: '50%',
          top: '50%',
          transform: 'translate(-50%, -50%)',
          width: `${popupWidth}px`,
          maxHeight: `${popupHeight}px`,
          background: TOKENS.white,
          border: `4px solid ${TOKENS.primary}`,
          borderRadius: STYLES.radius.large,
          boxShadow: `8px 8px 0px ${TOKENS.primary}`,
          zIndex: 10000,
          display: 'flex',
          flexDirection: 'column',
          fontFamily: TOKENS.fontFamily,
        }}
      >
        {/* Header */}
        <div
          style={{
            padding: STYLES.spacing.lg,
            borderBottom: `3px solid ${TOKENS.primary}`,
            background: TOKENS.primary,
            color: TOKENS.white,
            fontWeight: STYLES.fontWeight.bold,
            fontSize: STYLES.fontSize.lg,
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
          }}
        >
          <div>🔍 Analysis Results</div>
          <button
            onClick={handleClosePopup}
            style={{
              background: 'transparent',
              border: 'none',
              color: TOKENS.white,
              fontSize: '24px',
              cursor: 'pointer',
              padding: '0 8px',
              lineHeight: '1',
            }}
          >
            ×
          </button>
        </div>

        {/* Content */}
        <div
          style={{
            flex: 1,
            padding: STYLES.spacing.lg,
            overflow: 'auto',
            fontSize: STYLES.fontSize.base,
            lineHeight: '1.6',
            color: TOKENS.text,
          }}
        >
          <div
            dangerouslySetInnerHTML={{
              __html: formatAnalysisContent(text),
            }}
            style={{
              whiteSpace: 'pre-wrap',
              wordBreak: 'break-word',
            }}
          />
        </div>

        {/* Footer */}
        <div
          style={{
            padding: STYLES.spacing.md,
            borderTop: `2px solid ${TOKENS.border}`,
            background: TOKENS.bg,
            fontSize: STYLES.fontSize.sm,
            color: TOKENS.muted,
            textAlign: 'center',
          }}
        >
          {text.length} characters • Press ESC or click outside to close • {isClickedOpen ? 'Pinned open' : 'Hover mode'}
        </div>
      </div>
    </>
  );

  return (
    <>
      <div
        ref={textRef}
        className={className}
        style={{
          ...style,
          cursor: shouldTruncate ? 'pointer' : 'default',
          position: 'relative',
          display: '-webkit-box',
          WebkitLineClamp: maxLines,
          WebkitBoxOrient: 'vertical',
          overflow: 'hidden',
          lineHeight: '1.4',
          wordBreak: 'break-word',
        }}
        onMouseEnter={handleMouseEnter}
        onMouseLeave={handleMouseLeave}
        title={shouldTruncate ? 'Click to view full text' : undefined}
      >
        {shouldTruncate ? (
          <>
            {truncatedText}
            <span
              style={{
                color: TOKENS.primary,
                fontWeight: STYLES.fontWeight.medium,
                marginLeft: STYLES.spacing.xs,
              }}
            >
              (click to expand)
            </span>
          </>
        ) : (
          text
        )}
      </div>
      {showPopup && createPortal(popupContent, document.body)}
    </>
  );
};

export default TextTruncatePopup;