import React from 'react';
import { LANES } from '../../flow/lanes';

export function Swimlanes() {
  return (
    <div className="pointer-events-none" style={{ position: 'absolute', inset: 0 }}>
      {Object.entries(LANES).map(([key, x]) => (
        <div key={key} style={{ position: 'absolute', top: 0, bottom: 0, left: x - 190, width: 380 }}>
          <div style={{ height: '100%', borderLeft: '1px solid rgba(0,0,0,0.08)', borderRight: '1px solid rgba(0,0,0,0.08)' }} />
          <div style={{ position: 'absolute', top: 6, left: 8, fontSize: 11, textTransform: 'uppercase', letterSpacing: 1, color: 'rgba(0,0,0,0.45)' }}>
            {key}
          </div>
        </div>
      ))}
    </div>
  );
}
