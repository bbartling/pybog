/**
 * Enhanced Edge Styling Engine for ChatCanvasGrid
 * Provides dynamic edge styling based on workflow states and node relationships
 */

import { Edge, MarkerType, ConnectionLineType } from 'reactflow';
import { TOKENS } from '../theme/neubrutalism';

export interface EdgeStyleConfig {
  workflowState?: 'idle' | 'analyzing' | 'awaiting_approval' | 'generating' | 'complete' | 'awaiting_analysis_review';
  sourceNodeType: string;
  targetNodeType: string;
  targetStatus?: string;
  isLastEdge?: boolean;
  isError?: boolean;
  isProcessing?: boolean;
  isComplete?: boolean;
  isAwaiting?: boolean;
}

export interface StyledEdgeResult {
  type: ConnectionLineType;
  animated: boolean;
  style: {
    stroke: string;
    strokeWidth: number;
    strokeDasharray?: string;
    opacity?: number;
  };
  markerEnd: {
    type: MarkerType;
    color: string;
    width: number;
    height: number;
  };
  pathOptions?: {
    offset?: number;
    borderRadius?: number;
  };
  className?: string;
}

export class EdgeStyleEngine {
  /**
   * Get enhanced edge styling based on workflow context - restored professional routing
   */
  static getEdgeStyle(config: EdgeStyleConfig): StyledEdgeResult {
    const {
      workflowState,
      sourceNodeType,
      targetNodeType,
      targetStatus,
      isLastEdge,
      isError,
      isProcessing,
      isComplete,
      isAwaiting
    } = config;

    // Professional edge routing with right angles
    let edgeType: ConnectionLineType = ConnectionLineType.Step;
    
    // Use consistent step edges for professional appearance
    if (sourceNodeType === 'userMessage') {
      edgeType = ConnectionLineType.Step;
    } else if (targetNodeType === 'analysisMessage' || targetNodeType === 'analysisReview') {
      edgeType = ConnectionLineType.Step;
    } else if (targetNodeType === 'progressMessage') {
      edgeType = ConnectionLineType.Step;
    }

    // Determine edge color based on status
    let strokeColor = TOKENS.border;
    let strokeWidth = 2;
    let opacity = 1;

    if (isError) {
      strokeColor = TOKENS.error;
      strokeWidth = 3;
    } else if (isComplete) {
      strokeColor = TOKENS.success;
      strokeWidth = 2.5;
    } else if (isProcessing) {
      strokeColor = TOKENS.primary;
      strokeWidth = 2.5;
      opacity = 0.8;
    } else if (isAwaiting) {
      strokeColor = TOKENS.warning;
      strokeWidth = 2;
    }

    // Special styling for workflow states
    if (workflowState === 'analyzing' && isLastEdge) {
      strokeColor = TOKENS.primary;
      strokeWidth = 3;
      opacity = 0.9;
    } else if (workflowState === 'awaiting_approval') {
      strokeColor = TOKENS.warning;
      strokeWidth = 2.5;
    } else if (workflowState === 'generating') {
      strokeColor = TOKENS.info;
      strokeWidth = 2.5;
    }

    // Determine dash pattern
    let strokeDasharray: string | undefined;
    if (isProcessing || (workflowState === 'analyzing' && isLastEdge)) {
      strokeDasharray = '8 6';
    } else if (isAwaiting) {
      strokeDasharray = '12 4';
    } else if (isError) {
      strokeDasharray = '4 4';
    }

    // Determine animation
    const animated = Boolean(
      isProcessing || 
      (workflowState === 'analyzing' && isLastEdge && !isError) ||
      workflowState === 'generating'
    );

    // Marker styling
    const markerWidth = isError ? 24 : isProcessing ? 22 : 20;
    const markerHeight = markerWidth;

    // Path options for professional right-angle edges
    const pathOptions = {
      offset: 30, // Consistent offset for professional routing
      borderRadius: 4, // Minimal radius for sharp corners
    };

    // CSS class for additional animations
    let className: string | undefined;
    if (animated && isProcessing) {
      className = 'edge-processing';
    } else if (animated && workflowState === 'analyzing') {
      className = 'edge-analyzing';
    } else if (isError) {
      className = 'edge-error';
    }

    return {
      type: edgeType,
      animated,
      style: {
        stroke: strokeColor,
        strokeWidth,
        strokeDasharray,
        opacity,
      },
      markerEnd: {
        type: MarkerType.ArrowClosed,
        color: strokeColor,
        width: markerWidth,
        height: markerHeight,
      },
      pathOptions,
      className,
    };
  }

  /**
   * Get status-specific edge styling
   */
  static getStatusEdgeStyle(status: string): Partial<StyledEdgeResult> {
    const statusMap: Record<string, Partial<StyledEdgeResult>> = {
      'queued': {
        style: {
          stroke: TOKENS.info,
          strokeWidth: 2,
          strokeDasharray: '8 6',
          opacity: 0.7,
        },
        animated: false,
      },
      'processing': {
        style: {
          stroke: TOKENS.primary,
          strokeWidth: 2.5,
          strokeDasharray: '8 6',
          opacity: 0.9,
        },
        animated: true,
        className: 'edge-processing',
      },
      'finalizing': {
        style: {
          stroke: TOKENS.warning,
          strokeWidth: 2.5,
          strokeDasharray: '12 4',
          opacity: 0.8,
        },
        animated: true,
      },
      'complete': {
        style: {
          stroke: TOKENS.success,
          strokeWidth: 2,
          opacity: 1,
        },
        animated: false,
      },
      'failed': {
        style: {
          stroke: TOKENS.error,
          strokeWidth: 3,
          strokeDasharray: '4 4',
          opacity: 1,
        },
        animated: false,
        className: 'edge-error',
      },
      'awaiting_approval': {
        style: {
          stroke: TOKENS.warning,
          strokeWidth: 2.5,
          strokeDasharray: '12 4',
          opacity: 0.9,
        },
        animated: false,
      },
    };

    return statusMap[status] || {};
  }

  /**
   * Create CSS animations for enhanced edge effects
   */
  static getEdgeAnimationCSS(): string {
    return `
      .edge-processing {
        animation: edge-pulse 2s ease-in-out infinite;
      }
      
      .edge-analyzing {
        animation: edge-flow 3s linear infinite;
      }
      
      .edge-error {
        animation: edge-error-flash 1s ease-in-out infinite alternate;
      }
      
      @keyframes edge-pulse {
        0%, 100% { opacity: 0.7; }
        50% { opacity: 1; }
      }
      
      @keyframes edge-flow {
        0% { stroke-dashoffset: 0; }
        100% { stroke-dashoffset: -20; }
      }
      
      @keyframes edge-error-flash {
        0% { opacity: 1; }
        100% { opacity: 0.6; }
      }
      
      /* Enhanced ReactFlow edge styling */
      .react-flow__edge-path {
        transition: all 0.3s ease;
      }
      
      .react-flow__edge:hover .react-flow__edge-path {
        stroke-width: 3;
        filter: drop-shadow(0 0 4px currentColor);
      }
      
      .react-flow__edge.selected .react-flow__edge-path {
        stroke-width: 4;
        filter: drop-shadow(0 0 6px currentColor);
      }
    `;
  }
}

/**
 * Helper function to create enhanced edges with proper styling
 */
export function createStyledEdge(
  id: string,
  source: string,
  target: string,
  config: EdgeStyleConfig
): Edge {
  const styling = EdgeStyleEngine.getEdgeStyle(config);
  
  const edge: Edge = {
    id,
    source,
    target,
    type: styling.type,
    animated: styling.animated,
    style: styling.style,
    markerEnd: styling.markerEnd,
  };

  // Add className if provided
  if (styling.className) {
    (edge as any).className = styling.className;
  }

  return edge;
}