'use client';

import React, { createContext, useContext, useState, useEffect, useRef, useCallback, ReactNode } from 'react';
import { useRouter } from 'next/navigation';
import { useActivityTracker } from '@/hooks/use-activity-tracker';

// Types
export interface User {
  user_id: string;
  email: string;
  first_name?: string;
  last_name?: string;
  role: 'admin' | 'member';
  organization_id: string;
  organization_name: string;
  is_active: boolean;
  created_at: string;
  last_login?: string;
}

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  expires_at?: number; // Timestamp d'expiration (en millisecondes)
}

interface AuthContextType {
  user: User | null;
  tokens: AuthTokens | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: () => void;
  loginLocal: (email: string, password: string) => Promise<boolean>;
  logout: () => void;
  refreshToken: () => Promise<boolean>;
  setUser: (user: User | null) => void;
  setTokens: (tokens: AuthTokens | null) => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

const TOKEN_STORAGE_KEY = 'auth_tokens';
const USER_STORAGE_KEY = 'auth_user';

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [tokens, setTokens] = useState<AuthTokens | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const router = useRouter();
  const refreshTimerRef = useRef<NodeJS.Timeout | null>(null);
  const expirationCheckTimerRef = useRef<NodeJS.Timeout | null>(null);
  const isRefreshingRef = useRef<boolean>(false);
  const isActiveRef = useRef<boolean>(true);

  // Helper pour calculer expires_at à partir de expires_in
  const calculateExpiresAt = useCallback((expiresIn: number): number => {
    return Date.now() + expiresIn * 1000;
  }, []);

  // Helper pour vérifier si le token est expiré
  const isTokenExpired = useCallback((tokenData: AuthTokens): boolean => {
    if (!tokenData.expires_at) {
      // Si pas de expires_at, utiliser expires_in comme fallback
      return false; // On ne peut pas vérifier, donc on assume qu'il est valide
    }
    return Date.now() >= tokenData.expires_at;
  }, []);

  // Helper pour obtenir le temps restant avant expiration (en ms)
  const getTimeUntilExpiration = useCallback((tokenData: AuthTokens): number => {
    if (!tokenData.expires_at) {
      // Fallback: utiliser expires_in si expires_at n'est pas disponible
      return tokenData.expires_in * 1000;
    }
    return Math.max(0, tokenData.expires_at - Date.now());
  }, []);

  // Tracker d'activité utilisateur (5 minutes d'inactivité)
  const { isActive } = useActivityTracker({
    inactivityThreshold: 5 * 60 * 1000, // 5 minutes
  });

  // Mettre à jour la ref d'activité
  useEffect(() => {
    isActiveRef.current = isActive;
  }, [isActive]);

  // Load auth state from localStorage on mount
  useEffect(() => {
    const loadAuthState = () => {
      try {
        const storedTokens = localStorage.getItem(TOKEN_STORAGE_KEY);
        const storedUser = localStorage.getItem(USER_STORAGE_KEY);

        if (storedTokens && storedUser) {
          const parsedTokens: AuthTokens = JSON.parse(storedTokens);
          
          // Vérifier si le token est expiré au chargement
          if (isTokenExpired(parsedTokens)) {
            console.warn('Token expired on load, clearing auth state');
            localStorage.removeItem(TOKEN_STORAGE_KEY);
            localStorage.removeItem(USER_STORAGE_KEY);
            setIsLoading(false);
            return;
          }

          // S'assurer que expires_at est défini
          if (!parsedTokens.expires_at && parsedTokens.expires_in) {
            parsedTokens.expires_at = calculateExpiresAt(parsedTokens.expires_in);
          }

          setTokens(parsedTokens);
          setUser(JSON.parse(storedUser));
        }
      } catch (error) {
        console.error('Error loading auth state:', error);
        // Clear invalid data
        localStorage.removeItem(TOKEN_STORAGE_KEY);
        localStorage.removeItem(USER_STORAGE_KEY);
      } finally {
        setIsLoading(false);
      }
    };

    loadAuthState();
  }, []);

  // Save auth state to localStorage whenever it changes
  useEffect(() => {
    if (tokens) {
      // S'assurer que expires_at est défini avant de sauvegarder
      if (!tokens.expires_at && tokens.expires_in) {
        tokens.expires_at = calculateExpiresAt(tokens.expires_in);
      }
      localStorage.setItem(TOKEN_STORAGE_KEY, JSON.stringify(tokens));
    } else {
      localStorage.removeItem(TOKEN_STORAGE_KEY);
    }

    if (user) {
      localStorage.setItem(USER_STORAGE_KEY, JSON.stringify(user));
    } else {
      localStorage.removeItem(USER_STORAGE_KEY);
    }
  }, [tokens, user, calculateExpiresAt]);

  // Définir logout et refreshToken avant les useEffect qui les utilisent
  const logout = useCallback(async () => {
    try {
      // Call logout endpoint if tokens exist
      const currentTokens = tokens; // Capturer la valeur actuelle
      if (currentTokens) {
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8012';
        await fetch(`${apiUrl}/auth/logout`, {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${currentTokens.access_token}`,
          },
        });
      }
    } catch (error) {
      console.error('Error during logout:', error);
    } finally {
      // Clear local state
      setUser(null);
      setTokens(null);
      localStorage.removeItem(TOKEN_STORAGE_KEY);
      localStorage.removeItem(USER_STORAGE_KEY);

      // Redirect to login
      router.push('/login');
    }
  }, [tokens, router]);

  // Ref pour logout afin d'éviter les dépendances circulaires
  const logoutRef = useRef(logout);
  useEffect(() => {
    logoutRef.current = logout;
  }, [logout]);

  const refreshToken = useCallback(async (): Promise<boolean> => {
    const currentTokens = tokens; // Capturer la valeur actuelle
    if (!currentTokens?.refresh_token) {
      return false;
    }

    // Éviter les refresh multiples simultanés
    if (isRefreshingRef.current) {
      console.log('Token refresh already in progress, skipping');
      return false;
    }

    isRefreshingRef.current = true;

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8012';
      const response = await fetch(`${apiUrl}/auth/refresh`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          refresh_token: currentTokens.refresh_token,
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to refresh token');
      }

      const data = await response.json();
      const expiresIn = data.expires_in || currentTokens.expires_in || 3600 * 24;
      
      const newTokens: AuthTokens = {
        ...data,
        expires_in: expiresIn,
        expires_at: calculateExpiresAt(expiresIn),
      };
      
      setTokens(newTokens);
      console.log('Token refreshed successfully');

      return true;
    } catch (error) {
      console.error('Error refreshing token:', error);
      // Si le refresh échoue et que l'utilisateur est inactif, rediriger vers login
      // Sinon, on laisse l'utilisateur continuer (il sera redirigé à la prochaine vérification)
      if (!isActiveRef.current) {
        logoutRef.current();
      }
      return false;
    } finally {
      isRefreshingRef.current = false;
    }
  }, [tokens, calculateExpiresAt]);

  // Vérification périodique de l'expiration du token (toutes les 30 secondes)
  useEffect(() => {
    if (!tokens) {
      // Nettoyer les timers si pas de token
      if (refreshTimerRef.current) {
        clearTimeout(refreshTimerRef.current);
        refreshTimerRef.current = null;
      }
      if (expirationCheckTimerRef.current) {
        clearInterval(expirationCheckTimerRef.current);
        expirationCheckTimerRef.current = null;
      }
      return;
    }

    // Vérifier l'expiration toutes les 30 secondes
    expirationCheckTimerRef.current = setInterval(() => {
      if (!tokens) return;

      if (isTokenExpired(tokens)) {
        console.warn('Token expired detected');
        
        // Si l'utilisateur est inactif, rediriger vers login
        if (!isActiveRef.current) {
          console.log('User inactive and token expired, redirecting to login');
          logout();
          return;
        }

        // Si l'utilisateur est actif, essayer de rafraîchir
        if (!isRefreshingRef.current) {
          console.log('User active and token expired, attempting refresh');
          refreshToken();
        }
      }
    }, 30000); // Vérifier toutes les 30 secondes

    return () => {
      if (expirationCheckTimerRef.current) {
        clearInterval(expirationCheckTimerRef.current);
      }
    };
  }, [tokens, isTokenExpired, logout, refreshToken]);

  // Auto-refresh token before expiration (seulement si utilisateur actif)
  useEffect(() => {
    if (!tokens) {
      if (refreshTimerRef.current) {
        clearTimeout(refreshTimerRef.current);
        refreshTimerRef.current = null;
      }
      return;
    }

    // Nettoyer le timer précédent
    if (refreshTimerRef.current) {
      clearTimeout(refreshTimerRef.current);
    }

    const timeUntilExpiration = getTimeUntilExpiration(tokens);
    const refreshBeforeMs = 2 * 60 * 1000; // 2 minutes avant expiration

    // Si le token expire dans moins de 2 minutes et que l'utilisateur est actif, rafraîchir
    if (timeUntilExpiration <= refreshBeforeMs && isActiveRef.current) {
      if (!isRefreshingRef.current) {
        console.log('Token expiring soon and user active, refreshing token');
        refreshToken();
      }
    } else if (timeUntilExpiration > refreshBeforeMs) {
      // Programmer le refresh 2 minutes avant expiration (seulement si actif)
      const timeUntilRefresh = timeUntilExpiration - refreshBeforeMs;
      
      refreshTimerRef.current = setTimeout(() => {
        if (isActiveRef.current && !isRefreshingRef.current) {
          console.log('Scheduled token refresh (2 min before expiration)');
          refreshToken();
        }
      }, timeUntilRefresh);
    }

    return () => {
      if (refreshTimerRef.current) {
        clearTimeout(refreshTimerRef.current);
      }
    };
  }, [tokens, getTimeUntilExpiration, refreshToken]);

  const login = useCallback(() => {
    // Redirect to backend OAuth endpoint
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8012';
    window.location.href = `${apiUrl}/auth/hubspot/login`;
  }, []);

  const loginLocal = useCallback(async (email: string, password: string): Promise<boolean> => {
    try {
      setIsLoading(true);
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8012';
      
      const response = await fetch(`${apiUrl}/auth/local/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          email,
          password,
        }),
      });

      if (!response.ok) {
        throw new Error('Login failed');
      }

      const data = await response.json();
      
      // Données de l'API : { access_token, refresh_token, token_type, expires_in?, user }
      const expiresIn = data.expires_in || 3600 * 24; // Par défaut 24h
      const newTokens: AuthTokens = {
        access_token: data.access_token,
        refresh_token: data.refresh_token,
        token_type: data.token_type,
        expires_in: expiresIn,
        expires_at: calculateExpiresAt(expiresIn),
      };
      
      const newUser: User = data.user;

      setTokens(newTokens);
      setUser(newUser);
      return true;
    } catch (error) {
      console.error('Local login error:', error);
      return false;
    } finally {
      setIsLoading(false);
    }
  }, [calculateExpiresAt]);

  const value: AuthContextType = {
    user,
    tokens,
    isAuthenticated: !!user && !!tokens,
    isLoading,
    login,
    loginLocal,
    logout,
    refreshToken,
    setUser,
    setTokens,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
