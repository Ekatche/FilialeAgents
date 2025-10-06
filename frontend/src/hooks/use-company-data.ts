"use client";

import { useState, useCallback, useMemo } from "react";
import useSWR from "swr";
import {
  api,
  CompanyData,
  CompanyExtractionRequest,
  URLExtractionRequest,
} from "@/lib/api";

interface UseCompanyDataOptions {
  onSuccess?: (data: CompanyData) => void;
  onError?: (error: Error) => void;
}

export function useCompanyData(options: UseCompanyDataOptions = {}) {
  const [searchHistory, setSearchHistory] = useState<string[]>([]);

  // Stabilise les callbacks onSuccess/onError sans re-créer l'objet options
  const memoizedOptions = useMemo(() => options, [options]);

  // Health check with SWR
  const { data: healthData, error: healthError } = useSWR(
    "health",
    () => api.healthCheck(),
    {
      refreshInterval: 30000, // Check every 30 seconds
      revalidateOnFocus: false,
    }
  );

  const extractCompany = useCallback(
    async (request: CompanyExtractionRequest) => {
      try {
        const data = await api.extractCompany(request);
        setSearchHistory((prev) => [request.company_name, ...prev.slice(0, 4)]);
        memoizedOptions.onSuccess?.(data);
        return data;
      } catch (error) {
        const err = error as Error;
        memoizedOptions.onError?.(err);
        throw err;
      }
    },
    [memoizedOptions]
  );

  const extractFromURL = useCallback(
    async (request: URLExtractionRequest) => {
      try {
        const data = await api.extractFromURL(request);
        setSearchHistory((prev) => [request.url, ...prev.slice(0, 4)]);
        memoizedOptions.onSuccess?.(data);
        return data;
      } catch (error) {
        const err = error as Error;
        memoizedOptions.onError?.(err);
        throw err;
      }
    },
    [memoizedOptions]
  );

  const extractByName = useCallback(
    async (companyName: string) => {
      try {
        const data = await api.extractCompany({ company_name: companyName });
        setSearchHistory((prev) => [companyName, ...prev.slice(0, 4)]);
        memoizedOptions.onSuccess?.(data);
        return data;
      } catch (error) {
        const err = error as Error;
        memoizedOptions.onError?.(err);
        throw err;
      }
    },
    [memoizedOptions]
  );

  return {
    // API functions
    extractCompany,
    extractFromURL,
    extractByName,

    // Health status
    isApiHealthy: !!healthData && healthData.status === "healthy",
    apiError: healthError,
    healthData,

    // Search history
    searchHistory,
    clearSearchHistory: () => setSearchHistory([]),
  };
}

// Hook for caching company data
export function useCachedCompanyData(companyName?: string) {
  return useSWR(
    companyName ? ["company", companyName] : null,
    ([, name]) => api.extractCompany({ company_name: name }),
    {
      revalidateOnFocus: false,
      revalidateOnReconnect: false,
      dedupingInterval: 5 * 60 * 1000, // 5 minutes
    }
  );
}
