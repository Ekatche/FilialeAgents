'use client';

import { useState, useEffect } from 'react';
import { useAuth } from '@/contexts/AuthContext';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8012';

interface MonthlyCostStats {
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

interface TopExpensiveSearch {
  id: string;
  company_name: string;
  created_at: string;
  cost_eur: number;
  cost_usd: number;
  total_tokens: number;
  subsidiaries_count: number;
  processing_time: number | null;
}

interface CostEstimate {
  total_input_tokens: number;
  total_output_tokens: number;
  total_tokens: number;
  total_cost_usd: number;
  total_cost_eur: number;
  models_breakdown: Array<{
    model: string;
    input_tokens: number;
    output_tokens: number;
    cost_usd: number;
    cost_eur: number;
  }>;
  exchange_rate: number;
  estimate_type: string;
  extraction_type: string;
  estimated_subsidiaries: number;
}

export function useCosts() {
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
    async getCurrentMonthStats(): Promise<MonthlyCostStats> {
      return fetchWithAuth('/costs/organization/current-month');
    },

    async getMonthlyStats(year: number, month: number): Promise<MonthlyCostStats> {
      return fetchWithAuth(`/costs/organization/monthly/${year}/${month}`);
    },

    async getTopExpensive(limit: number = 10): Promise<TopExpensiveSearch[]> {
      return fetchWithAuth(`/costs/organization/top-expensive?limit=${limit}`);
    },

    async estimateCost(
      extractionType: 'simple' | 'advanced',
      hasSubsidiaries: boolean,
      subsidiariesCount: number
    ): Promise<CostEstimate> {
      return fetchWithAuth('/costs/estimate', {
        method: 'POST',
        body: JSON.stringify({
          extraction_type: extractionType,
          has_subsidiaries: hasSubsidiaries,
          subsidiaries_count: subsidiariesCount
        })
      });
    },

    async getExtractionDetail(extractionId: string) {
      return fetchWithAuth(`/costs/extraction/session/${extractionId}`);
    },

    async getBudgetStatus() {
      return fetchWithAuth('/costs/organization/budget-status');
    }
  };
}

// Hook pour charger automatiquement les stats du mois courant
export function useCurrentMonthStats() {
  const [stats, setStats] = useState<MonthlyCostStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const costs = useCosts();

  const loadStats = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await costs.getCurrentMonthStats();
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

// Hook pour charger les recherches les plus coûteuses
export function useTopExpensiveSearches(limit: number = 10) {
  const [searches, setSearches] = useState<TopExpensiveSearch[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const costs = useCosts();

  useEffect(() => {
    const loadSearches = async () => {
      try {
        setLoading(true);
        setError(null);
        const data = await costs.getTopExpensive(limit);
        setSearches(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load searches');
      } finally {
        setLoading(false);
      }
    };

    loadSearches();
  }, [limit]);

  return { searches, loading, error };
}
