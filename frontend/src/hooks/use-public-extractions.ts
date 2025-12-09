'use client';

import { useState, useEffect } from 'react';

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

/**
 * Hook pour récupérer les stats du dashboard (mode local, sans auth)
 */
export function usePublicDashboardStats() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadStats = async () => {
    try {
      setLoading(true);
      setError(null);

      const response = await fetch(`${API_URL}/public/extractions/stats`);

      if (!response.ok) {
        throw new Error(`Erreur ${response.status}: ${response.statusText}`);
      }

      const data = await response.json();
      setStats(data);
    } catch (err) {
      console.error('Erreur chargement stats:', err);
      setError(err instanceof Error ? err.message : 'Erreur de chargement');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadStats();
  }, []);

  return { stats, loading, error, refresh: loadStats };
}

/**
 * Hook pour récupérer les extractions récentes (mode local, sans auth)
 */
export function usePublicRecentExtractions(limit: number = 10) {
  const [extractions, setExtractions] = useState<ExtractionListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadExtractions = async () => {
    try {
      setLoading(true);
      setError(null);

      const response = await fetch(`${API_URL}/public/extractions/recent?limit=${limit}`);

      if (!response.ok) {
        throw new Error(`Erreur ${response.status}: ${response.statusText}`);
      }

      const data = await response.json();
      setExtractions(data);
    } catch (err) {
      console.error('Erreur chargement extractions:', err);
      setError(err instanceof Error ? err.message : 'Erreur de chargement');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadExtractions();
  }, [limit]);

  return { extractions, loading, error, refresh: loadExtractions };
}
