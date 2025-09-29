/**
 * Responsive Layout Hook for ChatCanvasGrid
 * Handles window resizing and layout updates
 */

import { useState, useEffect, useCallback, useMemo } from 'react';
import { LayoutConfig, DEFAULT_LAYOUT_CONFIG } from '../utils/nodeLayoutEngine';

export interface ResponsiveLayoutConfig extends LayoutConfig {
  breakpoints: {
    mobile: number;
    tablet: number;
    desktop: number;
    wide: number;
  };
}

const DEFAULT_RESPONSIVE_CONFIG: ResponsiveLayoutConfig = {
  ...DEFAULT_LAYOUT_CONFIG,
  breakpoints: {
    mobile: 768,
    tablet: 1024,
    desktop: 1440,
    wide: 1920,
  },
};

export function useResponsiveLayout(
  initialConfig: Partial<ResponsiveLayoutConfig> = {}
): {
  layoutConfig: LayoutConfig;
  screenSize: 'mobile' | 'tablet' | 'desktop' | 'wide';
  containerDimensions: { width: number; height: number };
  updateLayout: () => void;
} {
  const config = { ...DEFAULT_RESPONSIVE_CONFIG, ...initialConfig };
  
  const [containerDimensions, setContainerDimensions] = useState({
    width: window.innerWidth,
    height: window.innerHeight,
  });

  const [screenSize, setScreenSize] = useState<'mobile' | 'tablet' | 'desktop' | 'wide'>('desktop');

  const getScreenSize = useCallback((width: number): 'mobile' | 'tablet' | 'desktop' | 'wide' => {
    if (width < config.breakpoints.mobile) return 'mobile';
    if (width < config.breakpoints.tablet) return 'tablet';
    if (width < config.breakpoints.desktop) return 'desktop';
    return 'wide';
  }, [config.breakpoints]);

  const updateLayout = useCallback(() => {
    const width = window.innerWidth;
    const height = window.innerHeight;
    
    setContainerDimensions({ width, height });
    setScreenSize(getScreenSize(width));
  }, [getScreenSize]);

  useEffect(() => {
    let resizeTimeout: NodeJS.Timeout;
    
    const handleResize = () => {
      // Debounce resize events to prevent ResizeObserver loops
      clearTimeout(resizeTimeout);
      resizeTimeout = setTimeout(() => {
        try {
          updateLayout();
        } catch (error) {
          console.warn('[ResponsiveLayout] Resize error handled:', error);
        }
      }, 100);
    };

    window.addEventListener('resize', handleResize, { passive: true });
    return () => {
      window.removeEventListener('resize', handleResize);
      clearTimeout(resizeTimeout);
    };
  }, [updateLayout]);

  // Memoize responsive layout config to prevent unnecessary re-renders
  const layoutConfig: LayoutConfig = useMemo(() => ({
    ...config,
    containerWidth: Math.max(800, containerDimensions.width - 100),
    containerHeight: Math.max(600, containerDimensions.height - 200),
    
    // Responsive adjustments
    maxNodesPerRow: screenSize === 'mobile' ? 1 : screenSize === 'tablet' ? 2 : 3,
    minNodeWidth: screenSize === 'mobile' ? 260 : 280,
    maxNodeWidth: screenSize === 'mobile' ? 320 : screenSize === 'tablet' ? 400 : 480,
    horizontalGap: screenSize === 'mobile' ? 40 : screenSize === 'tablet' ? 60 : 80,
    verticalGap: screenSize === 'mobile' ? 40 : screenSize === 'tablet' ? 60 : 80,
    padding: screenSize === 'mobile' ? 20 : screenSize === 'tablet' ? 40 : 60,
  }), [
    config.adaptiveRowHeight,
    containerDimensions.width,
    containerDimensions.height,
    screenSize
  ]);

  return {
    layoutConfig,
    screenSize,
    containerDimensions,
    updateLayout,
  };
}

/**
 * Hook for detecting layout changes and triggering re-renders
 */
export function useLayoutChangeDetection(
  dependencies: any[],
  onLayoutChange?: () => void
): { layoutVersion: number } {
  const [layoutVersion, setLayoutVersion] = useState(0);

  useEffect(() => {
    setLayoutVersion(prev => prev + 1);
    onLayoutChange?.();
  }, dependencies);

  return { layoutVersion };
}

/**
 * Hook for optimizing node visibility based on viewport
 */
export function useNodeVisibility(
  nodes: Array<{ id: string; position: { x: number; y: number }; dimensions: { width: number; height: number } }>,
  viewport: { x: number; y: number; zoom: number },
  containerDimensions: { width: number; height: number }
): {
  visibleNodes: Set<string>;
  totalNodes: number;
  visibilityRatio: number;
} {
  const [visibleNodes, setVisibleNodes] = useState<Set<string>>(new Set());

  useEffect(() => {
    const visible = new Set<string>();
    
    // Calculate viewport bounds
    const viewportBounds = {
      left: -viewport.x / viewport.zoom,
      top: -viewport.y / viewport.zoom,
      right: (-viewport.x + containerDimensions.width) / viewport.zoom,
      bottom: (-viewport.y + containerDimensions.height) / viewport.zoom,
    };

    // Add some padding for smooth transitions
    const padding = 100;
    viewportBounds.left -= padding;
    viewportBounds.top -= padding;
    viewportBounds.right += padding;
    viewportBounds.bottom += padding;

    // Check each node for visibility
    nodes.forEach(node => {
      const nodeRight = node.position.x + node.dimensions.width;
      const nodeBottom = node.position.y + node.dimensions.height;

      const isVisible = !(
        nodeRight < viewportBounds.left ||
        node.position.x > viewportBounds.right ||
        nodeBottom < viewportBounds.top ||
        node.position.y > viewportBounds.bottom
      );

      if (isVisible) {
        visible.add(node.id);
      }
    });

    setVisibleNodes(visible);
  }, [nodes, viewport, containerDimensions]);

  return {
    visibleNodes,
    totalNodes: nodes.length,
    visibilityRatio: nodes.length > 0 ? visibleNodes.size / nodes.length : 0,
  };
}