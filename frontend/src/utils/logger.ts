/**
 * Environment-aware logging utility
 * Reduces console spam in production
 */

const isDevelopment = process.env.NODE_ENV === 'development' || process.env.REACT_APP_DEBUG === 'true';

export const logger = {
  debug: (...args: any[]) => {
    if (isDevelopment) {
      console.log(...args);
    }
  },
  
  info: (...args: any[]) => {
    console.info(...args);
  },
  
  warn: (...args: any[]) => {
    console.warn(...args);
  },
  
  error: (...args: any[]) => {
    console.error(...args);
  },
  
  // For WebSocket and service debugging - only show in dev
  service: (...args: any[]) => {
    if (isDevelopment) {
      console.log(...args);
    }
  }
};

export default logger;