'use client';

import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '@/contexts/AuthContext';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8012';

// Types matching API models
export interface MonthlyCostStats {
  organization_id: string;
  total_searches: number;
  completed_searches: number;
  total_cost_eur: number;
  total_cost_usd: number;
  total_tokens: number;
  average_cost_per_search_eur: number;
  start_date: string | null;
  end_date: string | null;
  year: number;
  month: number;
  month_name: string;
}

export interface TopExpensiveSearch {
  id: string;
  company_name: string;
  created_at: string;
  cost_eur: number;
  cost_usd: number;
  total_tokens: number;
  subsidiaries_count: number;
  processing_time: number | null;
}

export interface ModelUsageDetail {
  model: string;
  input_tokens: number;
  output_tokens: number;
  cost_usd: number;
  cost_eur: number;
}

/**
 * Hook to fetch current month cost statistics
 */
export function useCurrentMonthCosts() {
  const { tokens } = useAuth();
  const [stats, setStats] = useState<MonthlyCostStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadStats = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      if (!tokens?.access_token) {
        throw new Error('Not authenticated');
      }

      const response = await fetch(`${API_URL}/costs/portal/current-month`, {
        headers: {
          'Authorization': `Bearer ${tokens.access_token}`,
        },
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Unknown error' }));
        console.error('❌ API Error:', {
          status: response.status,
          statusText: response.statusText,
          error: errorData
        });
        throw new Error(errorData.detail || `Failed to load current month costs (${response.status})`);
      }

      const data = await response.json();
      console.log('✅ Current month costs loaded:', data);
      setStats(data);
    } catch (err) {
      console.error('❌ Error loading current month costs:', err);
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  }, [tokens]);

  useEffect(() => {
    loadStats();
  }, [loadStats]);

  return { stats, loading, error, refresh: loadStats };
}

/**
 * Hook to fetch monthly cost statistics for specific year/month
 */
export function useMonthlyCosts(year: number, month: number) {
  const { tokens } = useAuth();
  const [stats, setStats] = useState<MonthlyCostStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadStats = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      if (!tokens?.access_token) {
        throw new Error('Not authenticated');
      }

      const response = await fetch(
        `${API_URL}/costs/portal/monthly/${year}/${month}`,
        {
          headers: {
            'Authorization': `Bearer ${tokens.access_token}`,
          },
        }
      );

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Unknown error' }));
        console.error('❌ API Error:', {
          status: response.status,
          statusText: response.statusText,
          error: errorData
        });
        throw new Error(errorData.detail || `Failed to load monthly costs (${response.status})`);
      }

      const data = await response.json();
      console.log(`✅ Monthly costs loaded for ${year}/${month}:`, data);
      setStats(data);
    } catch (err) {
      console.error('❌ Error loading monthly costs:', err);
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  }, [year, month, tokens]);

  useEffect(() => {
    loadStats();
  }, [loadStats]);

  return { stats, loading, error, refresh: loadStats };
}

/**
 * Hook to fetch top expensive searches
 */
export function useTopExpensiveSearches(limit: number = 10) {
  const { tokens } = useAuth();
  const [searches, setSearches] = useState<TopExpensiveSearch[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadSearches = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      if (!tokens?.access_token) {
        throw new Error('Not authenticated');
      }

      const response = await fetch(
        `${API_URL}/costs/portal/top-expensive?limit=${limit}`,
        {
          headers: {
            'Authorization': `Bearer ${tokens.access_token}`,
          },
        }
      );

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Unknown error' }));
        console.error('❌ API Error:', {
          status: response.status,
          statusText: response.statusText,
          error: errorData
        });
        throw new Error(errorData.detail || `Failed to load expensive searches (${response.status})`);
      }

      const data = await response.json();
      console.log(`✅ Top expensive searches loaded (limit=${limit}):`, data);
      setSearches(data);
    } catch (err) {
      console.error('❌ Error loading expensive searches:', err);
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  }, [limit, tokens]);

  useEffect(() => {
    loadSearches();
  }, [loadSearches]);

  return { searches, loading, error, refresh: loadSearches };
}

/**
 * Hook to fetch all monthly costs for multiple years
 * This aggregates data from multiple months
 */
export function useYearlyCosts(years: number[]) {
  const { tokens } = useAuth();
  const [monthlyData, setMonthlyData] = useState<Record<number, MonthlyCostStats[]>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      if (!tokens?.access_token) {
        throw new Error('Not authenticated');
      }

      // Fetch data for all 12 months for each selected year
      const promises = years.flatMap((year) =>
        Array.from({ length: 12 }, (_, i) => i + 1).map(async (month) => {
          const response = await fetch(
            `${API_URL}/costs/portal/monthly/${year}/${month}`,
            {
              headers: {
                'Authorization': `Bearer ${tokens.access_token}`,
              },
            }
          );

          if (!response.ok) {
            // Return null for failed requests (month might not have data yet)
            return null;
          }

          const data = await response.json();
          return { year, month, data };
        })
      );

      const results = await Promise.all(promises);

      // Organize by year
      const organized: Record<number, MonthlyCostStats[]> = {};
      results.forEach((result) => {
        if (result && result.data) {
          if (!organized[result.year]) {
            organized[result.year] = [];
          }
          organized[result.year].push(result.data);
        }
      });

      setMonthlyData(organized);
    } catch (err) {
      console.error('Error loading yearly costs:', err);
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  }, [years, tokens]);

  useEffect(() => {
    if (years.length > 0) {
      loadData();
    }
  }, [loadData, years.length]);

  return { monthlyData, loading, error, refresh: loadData };
}
