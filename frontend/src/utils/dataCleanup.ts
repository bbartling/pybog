/**
 * Data cleanup utilities for PyBOG
 * Removes problematic old data and fixes storage issues
 */

import sessionPersistence from '../services/sessionPersistence';

export interface CleanupResult {
  removedKeys: string[];
  fixedSessions: string[];
  errors: string[];
}

/**
 * Comprehensive data cleanup
 */
export async function performDataCleanup(): Promise<CleanupResult> {
  const result: CleanupResult = {
    removedKeys: [],
    fixedSessions: [],
    errors: []
  };

  console.log('[DataCleanup] Starting comprehensive cleanup...');

  try {
    // 1. Clean invalid localStorage keys
    const removedKeys = sessionPersistence.cleanupInvalidLocalKeys();
    result.removedKeys.push(...removedKeys);

    // 2. Remove problematic workflow states
    const workflowKeys: string[] = [];
    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i);
      if (key && (
        key.includes('workflow_state') ||
        key.includes('resume_url') ||
        key.includes('analysis_pending')
      )) {
        workflowKeys.push(key);
      }
    }

    workflowKeys.forEach(key => {
      try {
        localStorage.removeItem(key);
        result.removedKeys.push(key);
      } catch (e) {
        result.errors.push(`Failed to remove ${key}: ${e}`);
      }
    });

    // 3. Fix corrupted session data
    const sessionIds = sessionPersistence.getLocalSessionIds();
    for (const sessionId of sessionIds) {
      try {
        const sessionKey = `pybog_session_${sessionId}`;
        const sessionData = localStorage.getItem(sessionKey);
        
        if (sessionData) {
          const parsed = JSON.parse(sessionData);
          
          // Fix common data corruption issues
          let needsUpdate = false;
          
          // Ensure createdAt is valid
          if (!parsed.createdAt || isNaN(new Date(parsed.createdAt).getTime())) {
            parsed.createdAt = new Date().toISOString();
            needsUpdate = true;
          }
          
          // Ensure messages array exists
          if (!Array.isArray(parsed.messages)) {
            parsed.messages = [];
            needsUpdate = true;
          }
          
          // Remove invalid messages
          const validMessages = parsed.messages.filter((msg: any) => 
            msg && typeof msg === 'object' && msg.id && msg.type
          );
          
          if (validMessages.length !== parsed.messages.length) {
            parsed.messages = validMessages;
            needsUpdate = true;
          }
          
          // Fix message timestamps
          parsed.messages.forEach((msg: any) => {
            if (!msg.timestamp || isNaN(new Date(msg.timestamp).getTime())) {
              msg.timestamp = new Date().toISOString();
              needsUpdate = true;
            }
          });
          
          if (needsUpdate) {
            localStorage.setItem(sessionKey, JSON.stringify(parsed));
            result.fixedSessions.push(sessionId);
          }
        }
      } catch (e) {
        result.errors.push(`Failed to fix session ${sessionId}: ${e}`);
        // Remove corrupted session
        try {
          sessionPersistence.clearLocalSession(sessionId);
          result.removedKeys.push(`pybog_session_${sessionId}`);
        } catch {}
      }
    }

    // 4. Clear problematic cache entries
    const cacheKeys = [
      'pybog_layout_cache',
      'pybog_node_positions',
      'pybog_edge_cache',
      'pybog_viewport_cache'
    ];

    cacheKeys.forEach(key => {
      try {
        if (localStorage.getItem(key)) {
          localStorage.removeItem(key);
          result.removedKeys.push(key);
        }
      } catch (e) {
        result.errors.push(`Failed to remove cache ${key}: ${e}`);
      }
    });

    console.log('[DataCleanup] Cleanup complete:', result);
    return result;

  } catch (error) {
    result.errors.push(`Cleanup failed: ${error}`);
    console.error('[DataCleanup] Cleanup failed:', error);
    return result;
  }
}

/**
 * Quick fix for immediate issues
 */
export function quickFix(): void {
  console.log('[DataCleanup] Applying quick fixes...');
  
  // Fix ResizeObserver issues
  const originalError = console.error;
  console.error = (...args) => {
    if (args[0]?.toString().includes('ResizeObserver loop completed')) {
      return; // Suppress this specific error
    }
    originalError.apply(console, args);
  };
  
  // Clear problematic active session if invalid
  try {
    const activeSession = localStorage.getItem('pybog_active_session');
    if (activeSession && (activeSession === 'undefined' || activeSession === 'null' || activeSession.trim() === '')) {
      localStorage.removeItem('pybog_active_session');
      console.log('[DataCleanup] Removed invalid active session');
    }
  } catch (e) {
    console.warn('[DataCleanup] Failed to fix active session:', e);
  }
  
  console.log('[DataCleanup] Quick fixes applied');
}

// Apply quick fixes immediately
quickFix();