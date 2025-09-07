/**
 * Session Naming Utilities
 * Generates meaningful session names based on conversation content
 */

export function generateSessionId(): string {
  // Prefer built-in crypto UUID when available
  try {
    const anyCrypto: any = (globalThis as any).crypto;
    if (anyCrypto && typeof anyCrypto.randomUUID === 'function') {
      return anyCrypto.randomUUID();
    }
  } catch {}
  // Fallback: RFC4122 v4 implementation
  const bytes = new Uint8Array(16);
  if (typeof (globalThis as any).crypto?.getRandomValues === 'function') {
    (globalThis as any).crypto.getRandomValues(bytes);
  } else {
    for (let i = 0; i < 16; i++) bytes[i] = Math.floor(Math.random() * 256);
  }
  bytes[6] = (bytes[6] & 0x0f) | 0x40; // version 4
  bytes[8] = (bytes[8] & 0x3f) | 0x80; // variant
  const hex = Array.from(bytes, (b) => b.toString(16).padStart(2, '0'));
  return `${hex.slice(0, 4).join('')}-${hex.slice(4, 6).join('')}-${hex.slice(6, 8).join('')}-${hex.slice(8, 10).join('')}-${hex.slice(10, 16).join('')}`;
}

export function generateDefaultSessionName(index: number): string {
  return `Session ${index}`;
}

/**
 * Generate a display name based on conversation content
 * @param messages - Array of messages in the session
 * @returns A meaningful display name for the session
 */
export function generateSessionDisplayName(messages: any[]): string {
  if (!messages || messages.length === 0) {
    return 'New Session';
  }

  // Find first user message with meaningful content
  const userMessage = messages.find(m => 
    m.type === 'user' && 
    m.content && 
    m.content.length > 10
  );

  if (userMessage) {
    // Extract key phrases from user message
    const content = userMessage.content;
    
    // Check for specific HVAC terms
    if (content.toLowerCase().includes('chiller')) {
      return 'Chiller Control';
    }
    if (content.toLowerCase().includes('ahu') || content.toLowerCase().includes('air handling')) {
      return 'AHU Control';
    }
    if (content.toLowerCase().includes('vav')) {
      return 'VAV Control';
    }
    if (content.toLowerCase().includes('boiler')) {
      return 'Boiler Control';
    }
    if (content.toLowerCase().includes('pump')) {
      return 'Pump Control';
    }
    if (content.toLowerCase().includes('fan')) {
      return 'Fan Control';
    }
    if (content.toLowerCase().includes('temperature')) {
      return 'Temperature Control';
    }
    if (content.toLowerCase().includes('pressure')) {
      return 'Pressure Control';
    }
    
    // Check for file uploads
    const hasFiles = messages.some(m => m.files && m.files.length > 0);
    if (hasFiles) {
      const fileMessage = messages.find(m => m.files && m.files.length > 0);
      if (fileMessage && fileMessage.files[0]) {
        const fileName = fileMessage.files[0].name;
        // Remove extension and clean up
        return fileName.replace(/\.[^/.]+$/, '').replace(/[_-]/g, ' ').substring(0, 30);
      }
    }
    
    // Use first 30 chars of user message as fallback
    const truncated = content.substring(0, 30);
    const lastSpace = truncated.lastIndexOf(' ');
    return lastSpace > 0 ? truncated.substring(0, lastSpace) + '...' : truncated + '...';
  }

  // Check if there's an analysis
  const analysisMessage = messages.find(m => 
    m.metadata?.analysisData || 
    m.type === 'assistant' && m.content?.includes('analysis')
  );
  
  if (analysisMessage) {
    return 'HVAC Analysis';
  }

  // Default based on timestamp
  const date = new Date();
  const timeStr = date.toLocaleTimeString('en-US', { 
    hour: '2-digit', 
    minute: '2-digit',
    hour12: true 
  });
  return `Session at ${timeStr}`;
}

/**
 * Update session display name based on new messages
 * @param currentName - Current session name
 * @param messages - Updated messages array
 * @returns Whether the name should be updated
 */
export function shouldUpdateSessionName(currentName: string, messages: any[]): boolean {
  // Don't update if user has manually renamed
  if (!currentName.startsWith('Session ') && 
      !currentName.startsWith('New Session') &&
      !currentName.includes(' at ')) {
    return false;
  }
  
  // Update if we have meaningful user content
  const hasUserContent = messages.some(m => 
    m.type === 'user' && 
    m.content && 
    m.content.length > 10
  );
  
  return hasUserContent;
}

/**
 * Ensure a session display name is unique within a set of names.
 */
export function ensureUniqueSessionName(desired: string, existingNames: string[]): string {
  const existing = new Set((existingNames || []).map(n => (n || '').trim().toLowerCase()));
  const base = (desired || 'Session').trim();
  let candidate = base;
  let i = 2;
  while (existing.has(candidate.trim().toLowerCase())) {
    candidate = `${base} (${i})`;
    i += 1;
  }
  return candidate;
}
