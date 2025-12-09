'use client';

import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '@/contexts/AuthContext';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8012';

// Types matching API models
export interface User {
  user_id: string;
  email: string;
  first_name: string | null;
  last_name: string | null;
  role: 'admin' | 'member';
  portal_id: string;
  portal_name: string;
  is_active: boolean;
  created_at: string;
  last_login: string | null;
}

export interface Portal {
  id: string;
  hubspot_portal_id: number;
  name: string;
  domain: string | null;
  timezone: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  settings: Record<string, any> | null;
}

export interface UserPreferences {
  email_notifications: boolean;
  push_notifications: boolean;
  weekly_report: boolean;
  dark_mode: boolean;
  auto_save: boolean;
}

/**
 * Hook to manage user profile data
 */
export function useUserProfile() {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadUser = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      // Essayer d'abord de récupérer depuis AuthContext
      const authTokens = localStorage.getItem('auth_tokens');
      const authUser = localStorage.getItem('auth_user');
      
      let token: string | null = null;
      
      if (authTokens) {
        try {
          const tokens = JSON.parse(authTokens);
          token = tokens.access_token;
        } catch (e) {
          console.warn('Error parsing auth_tokens:', e);
        }
      }
      
      // Fallback sur l'ancien format
      if (!token) {
        token = localStorage.getItem('access_token');
      }

      // Si pas de token, essayer d'utiliser les données utilisateur stockées
      if (!token && authUser) {
        try {
          const userData = JSON.parse(authUser);
          // Formater les données pour correspondre à l'interface User
          // AuthContext stocke user_id, mais peut aussi avoir id
          const userId = userData.user_id || userData.id || '';
          const role = userData.role?.toLowerCase() === 'admin' || userData.role === 'ADMIN' ? 'admin' : 'member';
          // AuthContext utilise organization_id/organization_name, mais l'API retourne portal_id/portal_name
          const portalId = userData.portal_id || userData.organization_id || '';
          const portalName = userData.portal_name || userData.organization_name || 'Local Mode';
          
          setUser({
            user_id: userId,
            email: userData.email || '',
            first_name: userData.first_name || null,
            last_name: userData.last_name || null,
            role: role,
            portal_id: portalId,
            portal_name: portalName,
            is_active: userData.is_active !== false,
            created_at: userData.created_at || new Date().toISOString(),
            last_login: userData.last_login || null,
          });
          setLoading(false);
          return;
        } catch (e) {
          console.warn('Error parsing auth_user:', e);
        }
      }

      // En mode local (pas de token), utiliser l'endpoint local
      if (!token) {
        const response = await fetch(`${API_URL}/auth/local/me`);

        if (!response.ok) {
          throw new Error('Failed to load local user profile');
        }

        const data = await response.json();
        setUser(data);
        setLoading(false);
        return;
      }

      const response = await fetch(`${API_URL}/auth/me`, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        if (response.status === 401) {
          // Token expired, clear auth
          localStorage.removeItem('auth_tokens');
          localStorage.removeItem('auth_user');
          localStorage.removeItem('access_token');
          localStorage.removeItem('refresh_token');
          localStorage.removeItem('user');
          throw new Error('Session expired. Please login again.');
        }
        throw new Error('Failed to load user profile');
      }

      const data = await response.json();
      setUser(data);
    } catch (err) {
      console.error('Error loading user:', err);
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadUser();
  }, [loadUser]);

  const updateProfile = async (updates: { first_name?: string; last_name?: string }) => {
    try {
      const token = localStorage.getItem('access_token');
      if (!token) {
        throw new Error('Not authenticated');
      }

      const response = await fetch(`${API_URL}/auth/profile`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify(updates),
      });

      if (!response.ok) {
        throw new Error('Failed to update profile');
      }

      const data = await response.json();
      setUser(data);
      return data;
    } catch (err) {
      console.error('Error updating profile:', err);
      throw err;
    }
  };

  return { user, loading, error, refresh: loadUser, updateProfile };
}

/**
 * Hook to manage portal data
 */
export function usePortalInfo() {
  const [portal, setPortal] = useState<Portal | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadPortal = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      // Essayer d'abord de récupérer depuis AuthContext
      const authTokens = localStorage.getItem('auth_tokens');
      const authUser = localStorage.getItem('auth_user');
      
      let token: string | null = null;
      
      if (authTokens) {
        try {
          const tokens = JSON.parse(authTokens);
          token = tokens.access_token;
        } catch (e) {
          console.warn('Error parsing auth_tokens:', e);
        }
      }
      
      // Fallback sur l'ancien format
      if (!token) {
        token = localStorage.getItem('access_token');
      }

      // Si pas de token, essayer d'utiliser les données utilisateur stockées
      if (!token && authUser) {
        try {
          const userData = JSON.parse(authUser);
          // Créer un portail mocké depuis les données utilisateur
          const portalId = userData.portal_id || userData.organization_id || '';
          const portalName = userData.portal_name || userData.organization_name || 'Local Mode';
          
          setPortal({
            id: portalId,
            hubspot_portal_id: userData.hubspot_portal_id || 0,
            name: portalName,
            domain: null,
            timezone: null,
            is_active: true,
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
            settings: null,
          });
          setLoading(false);
          return;
        } catch (e) {
          console.warn('Error parsing auth_user:', e);
        }
      }

      // En mode local (pas de token), utiliser l'endpoint local
      if (!token) {
        const response = await fetch(`${API_URL}/auth/local/me`);

        if (!response.ok) {
          throw new Error('Failed to load local portal info');
        }

        const data = await response.json();
        // Créer un objet Portal depuis les données utilisateur
        setPortal({
          id: data.portal_id,
          hubspot_portal_id: 0,
          name: data.portal_name,
          domain: null,
          timezone: null,
          is_active: true,
          created_at: data.created_at,
          updated_at: data.created_at,
          settings: null,
        });
        setLoading(false);
        return;
      }

      const response = await fetch(`${API_URL}/auth/portal`, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        throw new Error('Failed to load portal info');
      }

      const data = await response.json();
      setPortal(data);
    } catch (err) {
      console.error('Error loading portal:', err);
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadPortal();
  }, [loadPortal]);

  return { portal, loading, error, refresh: loadPortal };
}

/**
 * Hook to manage user preferences
 */
export function useUserPreferences() {
  const [preferences, setPreferences] = useState<UserPreferences>({
    email_notifications: true,
    push_notifications: false,
    weekly_report: true,
    dark_mode: false,
    auto_save: true,
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Load preferences from localStorage on mount
  useEffect(() => {
    const stored = localStorage.getItem('user_preferences');
    if (stored) {
      try {
        setPreferences(JSON.parse(stored));
      } catch (err) {
        console.error('Error parsing stored preferences:', err);
      }
    }
    setLoading(false);
  }, []);

  const updatePreferences = async (updates: Partial<UserPreferences>) => {
    try {
      const newPreferences = { ...preferences, ...updates };

      // Save to localStorage
      localStorage.setItem('user_preferences', JSON.stringify(newPreferences));
      setPreferences(newPreferences);

      // Also sync with backend (for future notification system)
      const token = localStorage.getItem('access_token');
      if (token) {
        await fetch(`${API_URL}/auth/preferences`, {
          method: 'PUT',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`,
          },
          body: JSON.stringify(updates),
        });
      }

      return newPreferences;
    } catch (err) {
      console.error('Error updating preferences:', err);
      throw err;
    }
  };

  return { preferences, loading, error, updatePreferences };
}
