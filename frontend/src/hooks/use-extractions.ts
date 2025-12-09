'use client';

import { useState, useEffect } from 'react';
import { useAuth } from '@/contexts/AuthContext';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8012';

interface ExtractionListItem {
  id: string;
  session_id: string;
  company_name: string;
  company_url: string | null;
  extraction_type: string;
  status: string;
  created_at: string;
  completed_at: string | null;
  cost_eur: number | null;
  cost_usd: number | null;
  total_tokens: number | null;
  subsidiaries_count: number;
  processing_time: number | null;
  error_message: string | null;
}

interface ExtractionListResponse {
  items: ExtractionListItem[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

interface DashboardStats {
  current_month: {
    organization_id: string;
    total_searches: number;
    completed_searches: number;
    total_cost_eur: number;
    total_cost_usd: number;
    total_tokens: number;
    average_cost_per_search_eur: number;
    year: number;
    month: number;
    month_name: string;
  };
  recent_searches: ExtractionListItem[];
  total_searches_all_time: number;
  success_rate: number;
}

export function useExtractions() {
  const { tokens } = useAuth();

  const fetchWithAuth = async (endpoint: string, options: RequestInit = {}) => {
    if (!tokens?.access_token) {
      throw new Error('Not authenticated');
    }

    const response = await fetch(`${API_URL}${endpoint}`, {
      ...options,
      headers: {
        'Authorization': `Bearer ${tokens.access_token}`,
        'Content-Type': 'application/json',
        ...options.headers,
      },
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Request failed' }));
      throw new Error(error.detail || `HTTP ${response.status}`);
    }

    return response.json();
  };

  return {
    async listExtractions(params: {
      page?: number;
      page_size?: number;
      status?: string;
      search?: string;
      start_date?: string;
      end_date?: string;
      sort_by?: string;
      sort_order?: string;
    }): Promise<ExtractionListResponse> {
      const queryParams = new URLSearchParams();
      if (params.page) queryParams.append('page', params.page.toString());
      if (params.page_size) queryParams.append('page_size', params.page_size.toString());
      if (params.status) queryParams.append('status', params.status);
      if (params.search) queryParams.append('search', params.search);
      if (params.start_date) queryParams.append('start_date', params.start_date);
      if (params.end_date) queryParams.append('end_date', params.end_date);
      if (params.sort_by) queryParams.append('sort_by', params.sort_by);
      if (params.sort_order) queryParams.append('sort_order', params.sort_order);
      
      return fetchWithAuth(`/extractions?${queryParams.toString()}`);
    },

    async getRecentExtractions(limit: number = 5): Promise<ExtractionListItem[]> {
      return fetchWithAuth(`/extractions/recent?limit=${limit}`);
    },

    async getDashboardStats(): Promise<DashboardStats> {
      return fetchWithAuth('/extractions/dashboard/stats');
    },
  };
}

// Hook pour charger automatiquement les stats du dashboard
export function useDashboardStats() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const extractions = useExtractions();

  const loadStats = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await extractions.getDashboardStats();
      setStats(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load stats');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadStats();
  }, []);

  return { stats, loading, error, refresh: loadStats };
}

