"use client";

import { useCompanyData } from "@/hooks/use-company-data";
import { Activity, AlertCircle, CheckCircle, XCircle } from "lucide-react";

export function ApiStatus() {
  const { isApiHealthy, apiError } = useCompanyData();

  if (apiError) {
    return (
      <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-red-500/10 border border-red-500/20 backdrop-blur-sm">
        <XCircle className="w-4 h-4 text-red-500" />
        <span className="text-sm font-medium text-red-500">API Indisponible</span>
      </div>
    );
  }

  if (isApiHealthy) {
    return (
      <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-green-500/10 border border-green-500/20 backdrop-blur-sm">
        <CheckCircle className="w-4 h-4 text-green-500" />
        <span className="text-sm font-medium text-green-500">Système Opérationnel</span>
      </div>
    );
  }

  return (
    <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-yellow-500/10 border border-yellow-500/20 backdrop-blur-sm">
      <Activity className="w-4 h-4 text-yellow-500 animate-pulse" />
      <span className="text-sm font-medium text-yellow-500">Connexion...</span>
    </div>
  );
}
