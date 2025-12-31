/**
 * Application configuration
 */

// Determine API URL based on environment
const getApiUrl = (): string => {
  // Check if we're in development mode (Vite dev server)
  const isDev = typeof window !== 'undefined' && 
                window.location.hostname === 'localhost' && 
                window.location.port === '5173';
  
  // In development (Vite dev server), use proxy
  if (isDev) {
    return '';
  }
  
  // In production (Docker), check environment variable or use default
  // @ts-ignore - Vite env variables
  const envApiUrl = typeof import.meta !== 'undefined' ? import.meta.env?.VITE_API_URL : undefined;
  
  // Default to localhost API
  return envApiUrl || 'http://localhost:8000';
};

export const API_URL = getApiUrl();

export const config = {
  apiUrl: API_URL,
};
