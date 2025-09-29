/**
 * Advanced Node Layout Engine for ChatCanvasGrid
 * Handles dynamic sizing, collision detection, and optimal positioning
 */

export interface NodeDimensions {
  width: number;
  height: number;
}

export interface NodePosition {
  x: number;
  y: number;
}

export interface LayoutNode {
  id: string;
  position: NodePosition;
  dimensions: NodeDimensions;
  type: string;
  priority?: number; // Higher priority nodes get better positions
}

export interface LayoutConfig {
  containerWidth: number;
  containerHeight: number;
  minNodeWidth: number;
  maxNodeWidth: number;
  minNodeHeight: number;
  maxNodeHeight: number;
  horizontalGap: number;
  verticalGap: number;
  padding: number;
  maxNodesPerRow: number;
  adaptiveRowHeight: boolean;
}

export class NodeLayoutEngine {
  private config: LayoutConfig;
  private placedNodes: LayoutNode[] = [];

  constructor(config: LayoutConfig) {
    this.config = config;
  }

  /**
   * Calculate optimal dimensions for a node based on content
   */
  calculateNodeDimensions(
    content: string,
    nodeType: string,
    hasActions: boolean = false,
    hasProgress: boolean = false,
    hasFiles: boolean = false
  ): NodeDimensions {
    const baseWidth = this.config.minNodeWidth;
    const baseHeight = this.config.minNodeHeight;

    // Estimate content height based on text length and line breaks
    const lines = content.split('\n');
    const estimatedLines = Math.max(
      lines.length,
      Math.ceil(content.length / 50) // Rough estimate: 50 chars per line
    );

    let width = baseWidth;
    let height = baseHeight;

    // Adjust width based on content length
    if (content.length > 100) {
      width = Math.min(baseWidth + 80, this.config.maxNodeWidth);
    }
    if (content.length > 300) {
      width = this.config.maxNodeWidth;
    }

    // Adjust height based on content and features
    height = Math.max(
      baseHeight,
      60 + (estimatedLines * 18) // Header + content lines
    );

    // Add height for additional features
    if (hasActions) height += 50;
    if (hasProgress) height += 40;
    if (hasFiles) height += 30;

    // Node type specific adjustments
    switch (nodeType) {
      case 'analysisMessage':
      case 'analysisReview':
        height = Math.max(height, 280); // Analysis nodes need more space
        width = Math.max(width, 400);
        break;
      case 'textReview':
        height = Math.max(height, 200);
        width = Math.max(width, 350);
        break;
      case 'progressMessage':
        height = Math.max(height, 160);
        break;
    }

    return {
      width: Math.min(width, this.config.maxNodeWidth),
      height: Math.min(height, this.config.maxNodeHeight)
    };
  }

  /**
   * Check if two nodes would collide
   */
  private wouldCollide(
    pos1: NodePosition,
    dim1: NodeDimensions,
    pos2: NodePosition,
    dim2: NodeDimensions,
    gap: number = 0
  ): boolean {
    return !(
      pos1.x + dim1.width + gap <= pos2.x ||
      pos2.x + dim2.width + gap <= pos1.x ||
      pos1.y + dim1.height + gap <= pos2.y ||
      pos2.y + dim2.height + gap <= pos1.y
    );
  }

  /**
   * Find the next available position for a node
   */
  private findAvailablePosition(
    dimensions: NodeDimensions,
    preferredRow: number = 0,
    preferredCol: number = 0
  ): NodePosition {
    const { horizontalGap, verticalGap, padding } = this.config;
    
    // Start with preferred position
    let row = preferredRow;
    let col = preferredCol;
    let attempts = 0;
    const maxAttempts = 100;

    while (attempts < maxAttempts) {
      const x = padding + col * (this.config.minNodeWidth + horizontalGap);
      const y = padding + row * (this.config.minNodeHeight + verticalGap);
      
      const position = { x, y };
      
      // Check if this position would cause collisions
      let hasCollision = false;
      for (const placedNode of this.placedNodes) {
        if (this.wouldCollide(
          position,
          dimensions,
          placedNode.position,
          placedNode.dimensions,
          Math.min(horizontalGap, verticalGap)
        )) {
          hasCollision = true;
          break;
        }
      }

      if (!hasCollision) {
        // Check if position is within container bounds
        if (x + dimensions.width <= this.config.containerWidth - padding &&
            y + dimensions.height <= this.config.containerHeight - padding) {
          return position;
        }
      }

      // Move to next position
      col++;
      if (col >= this.config.maxNodesPerRow) {
        col = 0;
        row++;
      }
      
      attempts++;
    }

    // Fallback: place at end with potential overflow
    const fallbackRow = Math.floor(this.placedNodes.length / this.config.maxNodesPerRow);
    const fallbackCol = this.placedNodes.length % this.config.maxNodesPerRow;
    
    return {
      x: padding + fallbackCol * (this.config.minNodeWidth + horizontalGap),
      y: padding + fallbackRow * (this.config.minNodeHeight + verticalGap)
    };
  }

  /**
   * Calculate adaptive row heights based on tallest node in each row
   */
  private calculateAdaptiveLayout(nodes: Omit<LayoutNode, 'position'>[]): LayoutNode[] {
    const { padding, horizontalGap, verticalGap, maxNodesPerRow } = this.config;
    const layoutNodes: LayoutNode[] = [];
    
    // Group nodes by rows
    const rows: Array<Array<Omit<LayoutNode, 'position'>>> = [];
    for (let i = 0; i < nodes.length; i += maxNodesPerRow) {
      rows.push(nodes.slice(i, i + maxNodesPerRow));
    }

    let currentY = padding;

    for (let rowIndex = 0; rowIndex < rows.length; rowIndex++) {
      const rowNodes = rows[rowIndex];
      const maxHeightInRow = Math.max(...rowNodes.map(node => node.dimensions.height));
      
      // Position nodes in this row
      for (let colIndex = 0; colIndex < rowNodes.length; colIndex++) {
        const node = rowNodes[colIndex];
        const x = padding + colIndex * (this.config.minNodeWidth + horizontalGap);
        
        // Center smaller nodes vertically within the row
        const verticalOffset = (maxHeightInRow - node.dimensions.height) / 2;
        const y = currentY + verticalOffset;

        layoutNodes.push({
          ...node,
          position: { x, y }
        });
      }

      currentY += maxHeightInRow + verticalGap;
    }

    return layoutNodes;
  }

  /**
   * Layout all nodes with professional grid-based positioning
   */
  layoutNodes(
    nodeData: Array<{
      id: string;
      type: string;
      content: string;
      hasActions?: boolean;
      hasProgress?: boolean;
      hasFiles?: boolean;
      priority?: number;
    }>
  ): LayoutNode[] {
    this.placedNodes = [];
    
    // Calculate dimensions for all nodes
    const nodesWithDimensions = nodeData.map((node, index) => ({
      id: node.id,
      type: node.type,
      priority: node.priority || 0,
      originalIndex: index, // Preserve message order
      dimensions: this.calculateNodeDimensions(
        node.content,
        node.type,
        node.hasActions,
        node.hasProgress,
        node.hasFiles
      )
    }));

    // Use professional grid layout (preserve message order)
    const layoutNodes: LayoutNode[] = [];
    const { padding, horizontalGap, verticalGap, maxNodesPerRow } = this.config;

    for (let i = 0; i < nodesWithDimensions.length; i++) {
      const node = nodesWithDimensions[i];
      const row = Math.floor(i / maxNodesPerRow);
      const col = i % maxNodesPerRow;
      
      // Professional grid positioning with consistent spacing
      const x = padding + col * (this.config.minNodeWidth + horizontalGap);
      const y = padding + row * (this.config.minNodeHeight + verticalGap);

      const layoutNode: LayoutNode = {
        ...node,
        position: { x, y }
      };

      layoutNodes.push(layoutNode);
      this.placedNodes.push(layoutNode);
    }

    return layoutNodes;
  }

  /**
   * Calculate total layout bounds
   */
  calculateLayoutBounds(nodes: LayoutNode[]): {
    width: number;
    height: number;
    minX: number;
    minY: number;
    maxX: number;
    maxY: number;
  } {
    if (nodes.length === 0) {
      return { width: 0, height: 0, minX: 0, minY: 0, maxX: 0, maxY: 0 };
    }

    const minX = Math.min(...nodes.map(n => n.position.x));
    const minY = Math.min(...nodes.map(n => n.position.y));
    const maxX = Math.max(...nodes.map(n => n.position.x + n.dimensions.width));
    const maxY = Math.max(...nodes.map(n => n.position.y + n.dimensions.height));

    return {
      width: maxX - minX,
      height: maxY - minY,
      minX,
      minY,
      maxX,
      maxY
    };
  }

  /**
   * Optimize layout by reducing gaps and improving flow
   */
  optimizeLayout(nodes: LayoutNode[]): LayoutNode[] {
    // Simple optimization: pack nodes more tightly
    const optimized = [...nodes];
    const { horizontalGap, verticalGap } = this.config;

    for (let i = 1; i < optimized.length; i++) {
      const currentNode = optimized[i];
      let bestPosition = currentNode.position;
      let minDistance = Infinity;

      // Try to move closer to previous nodes
      for (let j = 0; j < i; j++) {
        const targetNode = optimized[j];
        
        // Try positioning to the right of target
        const rightPos = {
          x: targetNode.position.x + targetNode.dimensions.width + horizontalGap,
          y: targetNode.position.y
        };

        // Try positioning below target
        const belowPos = {
          x: targetNode.position.x,
          y: targetNode.position.y + targetNode.dimensions.height + verticalGap
        };

        for (const testPos of [rightPos, belowPos]) {
          // Check if this position would cause collisions
          let hasCollision = false;
          for (let k = 0; k < i; k++) {
            if (k === j) continue;
            const otherNode = optimized[k];
            if (this.wouldCollide(
              testPos,
              currentNode.dimensions,
              otherNode.position,
              otherNode.dimensions,
              Math.min(horizontalGap, verticalGap) / 2
            )) {
              hasCollision = true;
              break;
            }
          }

          if (!hasCollision) {
            const distance = Math.sqrt(
              Math.pow(testPos.x - targetNode.position.x, 2) +
              Math.pow(testPos.y - targetNode.position.y, 2)
            );
            if (distance < minDistance) {
              minDistance = distance;
              bestPosition = testPos;
            }
          }
        }
      }

      optimized[i] = { ...currentNode, position: bestPosition };
    }

    return optimized;
  }
}

/**
 * Default layout configuration - restored professional layout
 */
export const DEFAULT_LAYOUT_CONFIG: LayoutConfig = {
  containerWidth: 1400,
  containerHeight: 900,
  minNodeWidth: 320,
  maxNodeWidth: 520,
  minNodeHeight: 160,
  maxNodeHeight: 450,
  horizontalGap: 100,
  verticalGap: 80,
  padding: 60,
  maxNodesPerRow: 3,
  adaptiveRowHeight: false // Disable for consistent professional layout
};