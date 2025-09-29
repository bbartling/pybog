/**
 * Storage cleanup utilities for PyBOG
 * Provides functions to clear old data and fix storage issues
 */

// Make clearPyBOGData available globally for debugging
declare global {
  interface Window {
    clearPyBOGData: () => void;
    clearPyBOGCache: () => void;
    fixResizeObserver: () => void;
  }
}

/**
 * Clear all PyBOG data from localStorage and sessionStorage
 */
function clearPyBOGData(): void {
  console.log('[Storage] Clearing all PyBOG data...');
  
  const keysToRemove: string[] = [];
  
  // Collect all PyBOG-related keys
  for (let i = 0; i < localStorage.length; i++) {
    const key = localStorage.key(i);
    if (key && (
      key.startsWith('pybog_') ||
      key.startsWith('session_') ||
      key.includes('workflow') ||
      key.includes('analysis') ||
      key.includes('chat')
    )) {
      keysToRemove.push(key);
    }
  }
  
  // Remove all collected keys
  keysToRemove.forEach(key => {
    try {
      localStorage.removeItem(key);
      console.log('[Storage] Removed:', key);
    } catch (e) {
      console.warn('[Storage] Failed to remove:', key, e);
    }
  });
  
  // Clear sessionStorage as well
  try {
    sessionStorage.clear();
    console.log('[Storage] Cleared sessionStorage');
  } catch (e) {
    console.warn('[Storage] Failed to clear sessionStorage:', e);
  }
  
  console.log('[Storage] Cleanup complete. Refresh the page to start fresh.');
}

/**
 * Clear only cache-related data, keep sessions
 */
function clearPyBOGCache(): void {
  console.log('[Storage] Clearing PyBOG cache...');
  
  const cacheKeys = [
    'pybog_console_open',
    'pybog_layout_config',
    'pybog_viewport_state',
    'pybog_ui_preferences'
  ];
  
  cacheKeys.forEach(key => {
    try {
      localStorage.removeItem(key);
      console.log('[Storage] Removed cache:', key);
    } catch (e) {
      console.warn('[Storage] Failed to remove cache:', key, e);
    }
  });
  
  console.log('[Storage] Cache cleanup complete.');
}

/**
 * Fix ResizeObserver issues by debouncing and error handling
 */
function fixResizeObserver(): void {
  console.log('[ResizeObserver] Applying fixes...');
  
  // Override ResizeObserver to handle errors gracefully
  const OriginalResizeObserver = window.ResizeObserver;
  
  window.ResizeObserver = class extends OriginalResizeObserver {
    constructor(callback: ResizeObserverCallback) {
      const wrappedCallback: ResizeObserverCallback = (entries, observer) => {
        try {
          // Debounce rapid resize events
          requestAnimationFrame(() => {
            try {
              callback(entries, observer);
            } catch (error) {
              console.warn('[ResizeObserver] Callback error handled:', error);
            }
          });
        } catch (error) {
          console.warn('[ResizeObserver] Error handled:', error);
        }
      };
      
      super(wrappedCallback);
    }
  };
  
  // Handle undelivered notifications error
  window.addEventListener('error', (event) => {
    if (event.message?.includes('ResizeObserver loop completed with undelivered notifications')) {
      event.preventDefault();
      console.warn('[ResizeObserver] Loop error suppressed');
    }
  });
  
  console.log('[ResizeObserver] Fixes applied');
}

// Apply fixes immediately
fixResizeObserver();

// Make functions available globally
window.clearPyBOGData = clearPyBOGData;
window.clearPyBOGCache = clearPyBOGCache;
window.fixResizeObserver = fixResizeObserver;

export { clearPyBOGData, clearPyBOGCache, fixResizeObserver };