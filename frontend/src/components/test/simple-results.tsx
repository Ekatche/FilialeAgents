"use client";

import { useState, useEffect } from "react";
import { useSafeSearchParams } from "@/hooks/use-safe-search-params";

export function SimpleResults() {
  const [data, setData] = useState<string | null>(null);
  const { isReady, get } = useSafeSearchParams();

  useEffect(() => {
    console.log("SimpleResults: useEffect running, isReady =", isReady);
    if (isReady) {
      const query = get("query");
      console.log("SimpleResults: query =", query);
      setData(query || "No query");
    }
  }, [isReady, get]);

  if (!isReady) {
    return <div>Loading search params...</div>;
  }

  return (
    <div className="p-4">
      <h1>Simple Results Test</h1>
      <p>Query: {data}</p>
      <p>SearchParams ready: {isReady ? "Yes" : "No"}</p>
    </div>
  );
}
