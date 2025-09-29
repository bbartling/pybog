/**
 * Idempotency utilities for PyBOG N4 Builder
 * Generates consistent idempotency keys for API requests
 */

/**
 * Simple hash function for browser compatibility
 */
function simpleHash(str: string): string {
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    const char = str.charCodeAt(i);
    hash = ((hash << 5) - hash) + char;
    hash = hash & hash; // Convert to 32-bit integer
  }
  return Math.abs(hash).toString(16).padStart(8, '0');
}

/**
 * Generate an idempotency key for a request
 * Uses session ID and content hash to ensure consistency
 */
export function generateIdempotencyKey(sessionId: string, content: string): string {
  // Create a hash of the content for consistency
  const contentHash = simpleHash(content).substring(0, 16);
  
  // Combine session ID with content hash and timestamp (rounded to minute for retry consistency)
  const timestamp = Math.floor(Date.now() / 60000); // Round to minute
  
  return `${sessionId}-${contentHash}-${timestamp}`;
}

/**
 * Generate a retry-safe idempotency key
 * Uses the same key for retries within a time window
 */
export function generateRetryableIdempotencyKey(sessionId: string, operation: string, windowMinutes: number = 5): string {
  // Round timestamp to the specified window for retry consistency
  const timestamp = Math.floor(Date.now() / (windowMinutes * 60000));
  
  const operationHash = simpleHash(operation).substring(0, 12);
  
  return `${sessionId}-${operationHash}-${timestamp}`;
}

/**
 * Check if an idempotency key is still valid for retries
 */
export function isIdempotencyKeyValid(key: string, maxAgeMinutes: number = 60): boolean {
  try {
    const parts = key.split('-');
    if (parts.length < 3) return false;
    
    const timestamp = parseInt(parts[parts.length - 1]);
    const currentTimestamp = Math.floor(Date.now() / 60000);
    
    return (currentTimestamp - timestamp) <= maxAgeMinutes;
  } catch {
    return false;
  }
}