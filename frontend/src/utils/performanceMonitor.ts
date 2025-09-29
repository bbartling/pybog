/**
 * Performance monitoring utilities for React components
 */

import React from 'react';

interface RenderInfo {
  componentName: string;
  renderCount: number;
  lastRender: number;
  props?: any;
}

class PerformanceMonitor {
  private renderCounts = new Map<string, RenderInfo>();
  private isEnabled = process.env.NODE_ENV === 'development';

  /**
   * Track component renders
   */
  trackRender(componentName: string, props?: any): void {
    if (!this.isEnabled) return;

    const now = Date.now();
    const existing = this.renderCounts.get(componentName);
    
    if (existing) {
      existing.renderCount++;
      existing.lastRender = now;
      existing.props = props;
      
      // Warn about excessive renders
      if (existing.renderCount > 10 && (now - existing.lastRender) < 1000) {
        console.warn(`🔥 [Performance] ${componentName} rendered ${existing.renderCount} times rapidly`);
      }
    } else {
      this.renderCounts.set(componentName, {
        componentName,
        renderCount: 1,
        lastRender: now,
        props
      });
    }
  }

  /**
   * Get render statistics
   */
  getStats(): RenderInfo[] {
    return Array.from(this.renderCounts.values()).sort((a, b) => b.renderCount - a.renderCount);
  }

  /**
   * Reset statistics
   */
  reset(): void {
    this.renderCounts.clear();
  }

  /**
   * Log current statistics
   */
  logStats(): void {
    if (!this.isEnabled) return;
    
    const stats = this.getStats();
    if (stats.length === 0) return;
    
    console.group('📊 Render Statistics');
    stats.forEach(stat => {
      console.log(`${stat.componentName}: ${stat.renderCount} renders`);
    });
    console.groupEnd();
  }
}

export const performanceMonitor = new PerformanceMonitor();

/**
 * React hook to track component renders
 */
export function useRenderTracker(componentName: string, props?: any): void {
  React.useEffect(() => {
    performanceMonitor.trackRender(componentName, props);
  });
}

/**
 * Higher-order component to track renders
 * Note: Use the useRenderTracker hook directly instead for better TypeScript support
 */
export function withRenderTracking<P extends object>(
  Component: React.ComponentType<P>,
  componentName?: string
): React.ComponentType<P> {
  const TrackedComponent = (props: P) => {
    useRenderTracker(componentName || Component.displayName || Component.name || 'Unknown');
    return React.createElement(Component, props);
  };
  
  TrackedComponent.displayName = `withRenderTracking(${componentName || Component.displayName || Component.name})`;
  return TrackedComponent;
}

/**
 * Utility to compare props and identify what changed
 */
export function compareProps(prevProps: any, nextProps: any, componentName: string): void {
  if (process.env.NODE_ENV !== 'development') return;
  
  const prevKeys = Object.keys(prevProps || {});
  const nextKeys = Object.keys(nextProps || {});
  const allKeys = new Set([...prevKeys, ...nextKeys]);
  
  const changes: string[] = [];
  
  allKeys.forEach(key => {
    const prevValue = prevProps?.[key];
    const nextValue = nextProps?.[key];
    
    if (prevValue !== nextValue) {
      // Check if it's a function
      if (typeof prevValue === 'function' && typeof nextValue === 'function') {
        changes.push(`${key}: function changed`);
      } else if (Array.isArray(prevValue) && Array.isArray(nextValue)) {
        if (prevValue.length !== nextValue.length) {
          changes.push(`${key}: array length changed (${prevValue.length} → ${nextValue.length})`);
        } else {
          changes.push(`${key}: array contents changed`);
        }
      } else if (typeof prevValue === 'object' && typeof nextValue === 'object') {
        changes.push(`${key}: object changed`);
      } else {
        changes.push(`${key}: ${prevValue} → ${nextValue}`);
      }
    }
  });
  
  if (changes.length > 0) {
    console.log(`🔄 [${componentName}] Props changed:`, changes);
  }
}

// Make available globally for debugging
declare global {
  interface Window {
    performanceMonitor: PerformanceMonitor;
  }
}

if (typeof window !== 'undefined') {
  window.performanceMonitor = performanceMonitor;
}