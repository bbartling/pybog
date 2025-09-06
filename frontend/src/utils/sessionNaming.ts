/**
 * Session Naming Utilities
 * Generates meaningful session names based on conversation content
 */

export function generateSessionId(): string {
  return `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
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
