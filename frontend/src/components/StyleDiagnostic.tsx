import React from 'react';

const StyleDiagnostic: React.FC = () => {
  return (
    <div style={{
      position: 'fixed',
      bottom: '20px',
      right: '20px',
      width: '300px',
      padding: '16px',
      background: 'white',
      border: '2px solid #3F3F4B',
      borderRadius: '12px',
      boxShadow: '4px 4px 0 0 #3F3F4B',
      zIndex: 9999,
      fontFamily: 'Inter, system-ui, -apple-system, sans-serif'
    }}>
      <h3 style={{
        margin: '0 0 12px 0',
        fontSize: '14px',
        fontWeight: 700,
        color: '#3F3F4B',
        textTransform: 'uppercase',
        letterSpacing: '0.05em'
      }}>
        Style Diagnostic
      </h3>
      
      <div style={{ fontSize: '12px', color: '#6B7280', lineHeight: '1.6' }}>
        <div style={{ marginBottom: '8px' }}>
          <strong>CSS Variables Check:</strong>
        </div>
        
        <div style={{ 
          display: 'grid', 
          gridTemplateColumns: '1fr 1fr',
          gap: '8px',
          marginBottom: '12px'
        }}>
          <div style={{
            padding: '8px',
            background: 'var(--neubrutalism-bg-primary, #F7F8FA)',
            border: '1px solid var(--neubrutalism-border-color, #3F3F4B)',
            borderRadius: '6px',
            fontSize: '11px'
          }}>
            Primary BG
          </div>
          <div style={{
            padding: '8px',
            background: 'var(--neubrutalism-bg-secondary, #FFFFFF)',
            border: '1px solid var(--neubrutalism-border-color, #3F3F4B)',
            borderRadius: '6px',
            fontSize: '11px'
          }}>
            Secondary BG
          </div>
          <div style={{
            padding: '8px',
            background: 'var(--neubrutalism-accent-blue, #569BFF)',
            color: 'white',
            border: '1px solid var(--neubrutalism-border-color, #3F3F4B)',
            borderRadius: '6px',
            fontSize: '11px'
          }}>
            Accent Blue
          </div>
          <div style={{
            padding: '8px',
            background: 'var(--neubrutalism-accent-green, #86EFAC)',
            border: '1px solid var(--neubrutalism-border-color, #3F3F4B)',
            borderRadius: '6px',
            fontSize: '11px'
          }}>
            Accent Green
          </div>
        </div>
        
        <div style={{
          padding: '8px',
          background: '#F0F9FF',
          border: '1px solid #569BFF',
          borderRadius: '6px',
          fontSize: '11px',
          color: '#1E40AF'
        }}>
          ✓ Neubrutalism styles are {
            getComputedStyle(document.documentElement)
              .getPropertyValue('--neubrutalism-border-color') ? 'loaded' : 'not loaded'
          }
        </div>
      </div>
      
      <button
        onClick={() => {
          // Force reload CSS
          const link = document.querySelector('link[href*="neubrutalism.css"]');
          if (link) {
            const href = link.getAttribute('href');
            link.setAttribute('href', href + '?t=' + Date.now());
          }
          window.location.reload();
        }}
        style={{
          marginTop: '12px',
          width: '100%',
          padding: '8px',
          background: '#3F3F4B',
          color: 'white',
          border: 'none',
          borderRadius: '6px',
          fontSize: '12px',
          fontWeight: 600,
          cursor: 'pointer'
        }}
      >
        Force Reload Styles
      </button>
    </div>
  );
};

export default StyleDiagnostic;
