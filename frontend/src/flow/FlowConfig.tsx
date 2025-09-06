import React from 'react';
import { Background, Controls, MiniMap, MarkerType, BackgroundVariant } from 'reactflow';

export const defaultEdgeOptions = {
  type: 'smoothstep',
  style: { strokeWidth: 1.25, stroke: 'rgba(100,116,139,0.9)' },
  markerEnd: { type: MarkerType.ArrowClosed, width: 14, height: 14, color: 'rgba(100,116,139,0.9)' },
} as const;

export function WorkbenchScaffolding() {
  return (
    <>
      <Background variant={BackgroundVariant.Lines} gap={18} color="rgba(0,0,0,0.06)" />
      <MiniMap position="top-right" pannable zoomable />
      <Controls position="top-right" />
    </>
  );
}
