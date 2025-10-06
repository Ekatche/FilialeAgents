"use client";

import { useSearchParams } from "next/navigation";
import { useState, useEffect } from "react";

export function useSafeSearchParams() {
  const [isReady, setIsReady] = useState(false);
  const [params, setParams] = useState<URLSearchParams | null>(null);
  const searchParams = useSearchParams();

  useEffect(() => {
    if (searchParams) {
      setParams(searchParams);
      setIsReady(true);
    }
  }, [searchParams]);

  return {
    isReady,
    searchParams: params,
    get: (key: string) => params?.get(key) || null,
    has: (key: string) => params?.has(key) || false,
  };
}
