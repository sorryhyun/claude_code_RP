// Get clean API URL without credentials
function getApiUrl(): string {
  // If VITE_API_BASE_URL is explicitly set, use it
  if (import.meta.env.VITE_API_BASE_URL) {
    const urlString = import.meta.env.VITE_API_BASE_URL;
    try {
      const parsed = new URL(urlString);
      // Remove credentials if present (they're handled by API key now)
      parsed.username = '';
      parsed.password = '';
      // Remove trailing slash to avoid double slashes in API calls
      return parsed.toString().replace(/\/$/, '');
    } catch {
      return urlString;
    }
  }

  // Auto-detect based on current window location
  // If accessing via network IP, use network IP for backend too
  const currentHost = window.location.hostname;
  if (currentHost !== 'localhost' && currentHost !== '127.0.0.1') {
    return `http://${currentHost}:8001`;
  }

  // Default to localhost
  return 'http://localhost:8001';
}

export const API_BASE_URL = getApiUrl();

// Global API key storage
let globalApiKey: string | null = null;

/**
 * Set the API key to be used for all API requests.
 * This should be called by the AuthContext when the user logs in.
 */
export function setApiKey(key: string | null) {
  globalApiKey = key;
}

/**
 * Get the current API key.
 */
export function getApiKey(): string | null {
  return globalApiKey;
}

/**
 * Helper to create fetch options with API key and common headers.
 */
export function getFetchOptions(options: RequestInit = {}): RequestInit {
  const headers: Record<string, string> = {
    ...options.headers as Record<string, string>,
  };

  // Add API key header if available
  if (globalApiKey) {
    headers['X-API-Key'] = globalApiKey;
  }

  // Add ngrok header to skip browser warning page
  headers['ngrok-skip-browser-warning'] = 'true';

  return {
    ...options,
    headers,
  };
}
