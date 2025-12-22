import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { setApiKey as setGlobalApiKey } from '../services';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8001';
const API_KEY_STORAGE_KEY = 'chitchats_api_key';

interface AuthContextType {
  isAuthenticated: boolean;
  isLoading: boolean;
  apiKey: string | null;
  role: 'admin' | 'guest' | null;
  userId: string | null;
  isGuest: boolean;
  isAdmin: boolean;
  login: (password: string) => Promise<void>;
  logout: () => void;
  error: string | null;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
};

interface AuthProviderProps {
  children: ReactNode;
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [apiKey, setApiKey] = useState<string | null>(null);
  const [role, setRole] = useState<'admin' | 'guest' | null>(null);
  const [userId, setUserId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Check for stored API key on mount and verify it
  useEffect(() => {
    const checkAuth = async () => {
      const storedKey = localStorage.getItem(API_KEY_STORAGE_KEY);

      if (storedKey) {
        // Verify the stored key is still valid
        try {
          const response = await fetch(`${API_BASE_URL}/auth/verify`, {
            headers: {
              'X-API-Key': storedKey,
            },
          });

          if (response.ok) {
            const data = await response.json();
            setApiKey(storedKey);
            setRole(data.role || 'admin'); // Default to admin for backward compatibility
            setUserId(data.user_id || null);
            setGlobalApiKey(storedKey);
          } else {
            // Invalid key, remove it
            localStorage.removeItem(API_KEY_STORAGE_KEY);
            setGlobalApiKey(null);
          }
        } catch (err) {
          console.error('Auth verification error:', err);
          // Clear the key on verification failure to prevent using invalid credentials
          localStorage.removeItem(API_KEY_STORAGE_KEY);
          setApiKey(null);
          setRole(null);
          setGlobalApiKey(null);
        }
      }

      setIsLoading(false);
    };

    checkAuth();
  }, []);

  const login = async (password: string) => {
    setError(null);
    setIsLoading(true);

    try {
      const response = await fetch(`${API_BASE_URL}/auth/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ password }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Login failed' }));
        throw new Error(errorData.detail || 'Invalid password');
      }

      const data = await response.json();
      const key = data.api_key;
      const userRole = data.role || 'admin'; // Default to admin for backward compatibility
      const userIdFromApi = data.user_id || null;

      // Store the API key
      localStorage.setItem(API_KEY_STORAGE_KEY, key);
      setApiKey(key);
      setRole(userRole);
      setUserId(userIdFromApi);
      setGlobalApiKey(key);
      setError(null);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Login failed';
      setError(message);
      throw err;
    } finally {
      setIsLoading(false);
    }
  };

  const logout = () => {
    localStorage.removeItem(API_KEY_STORAGE_KEY);
    setApiKey(null);
    setRole(null);
    setUserId(null);
    setGlobalApiKey(null);
    setError(null);
  };

  const value: AuthContextType = {
    isAuthenticated: !!apiKey,
    isLoading,
    apiKey,
    role,
    userId,
    isGuest: role === 'guest',
    isAdmin: role === 'admin',
    login,
    logout,
    error,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};
