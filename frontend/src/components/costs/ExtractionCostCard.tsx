'use client';

import { useState, useEffect } from 'react';
import { useCosts } from '@/hooks/use-costs';

interface ExtractionCostCardProps {
  extractionId: string;
}

export function ExtractionCostCard({ extractionId }: ExtractionCostCardProps) {
  const costs = useCosts();
  const [costData, setCostData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isExpanded, setIsExpanded] = useState(false);

  useEffect(() => {
    const loadCostData = async () => {
      try {
        setLoading(true);
        setError(null);
        const data = await costs.getExtractionDetail(extractionId);
        setCostData(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load cost data');
      } finally {
        setLoading(false);
      }
    };

    loadCostData();
  }, [extractionId]);

  if (loading) {
    return (
      <div className="bg-white rounded-lg border border-gray-200 p-4 animate-pulse">
        <div className="h-5 bg-gray-200 rounded w-1/3 mb-3"></div>
        <div className="h-8 bg-gray-100 rounded"></div>
      </div>
    );
  }

  if (error || !costData) {
    return null; // Ne pas afficher si pas de données de coût
  }

  // Si pas de coût, ne rien afficher
  if (!costData.cost_eur && !costData.cost_usd) {
    return null;
  }

  return (
    <div className="bg-gradient-to-br from-blue-50 to-indigo-50 rounded-lg border border-blue-200 p-5">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className="bg-blue-600 p-2 rounded-lg">
            <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <div>
            <h3 className="font-semibold text-gray-900">Coût de cette recherche</h3>
            <p className="text-xs text-gray-600">Utilisation des modèles AI</p>
          </div>
        </div>
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="text-blue-600 hover:text-blue-700 text-sm font-medium flex items-center gap-1"
        >
          {isExpanded ? 'Masquer' : 'Détails'}
          <svg
            className={`w-4 h-4 transition-transform ${isExpanded ? 'rotate-180' : ''}`}
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </button>
      </div>

      {/* Main Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
        {/* Coût EUR */}
        <div className="bg-white rounded-lg p-3 shadow-sm">
          <div className="text-xs text-gray-600 mb-1">Coût Total</div>
          <div className="text-2xl font-bold text-blue-600">
            {costData.cost_eur?.toFixed(4)}€
          </div>
          <div className="text-[10px] text-gray-500 mt-0.5">
            ${costData.cost_usd?.toFixed(4)}
          </div>
        </div>

        {/* Tokens Total */}
        <div className="bg-white rounded-lg p-3 shadow-sm">
          <div className="text-xs text-gray-600 mb-1">Tokens Total</div>
          <div className="text-2xl font-bold text-gray-900">
            {costData.total_tokens ? (costData.total_tokens / 1000).toFixed(1) : '0'}K
          </div>
          <div className="text-[10px] text-gray-500 mt-0.5">
            {costData.total_tokens?.toLocaleString('fr-FR') || '0'}
          </div>
        </div>

        {/* Tokens Input */}
        <div className="bg-white rounded-lg p-3 shadow-sm">
          <div className="text-xs text-gray-600 mb-1">Entrée</div>
          <div className="text-xl font-semibold text-gray-700">
            {costData.input_tokens ? (costData.input_tokens / 1000).toFixed(1) : '0'}K
          </div>
          <div className="text-[10px] text-gray-500 mt-0.5">
            tokens in
          </div>
        </div>

        {/* Tokens Output */}
        <div className="bg-white rounded-lg p-3 shadow-sm">
          <div className="text-xs text-gray-600 mb-1">Sortie</div>
          <div className="text-xl font-semibold text-gray-700">
            {costData.output_tokens ? (costData.output_tokens / 1000).toFixed(1) : '0'}K
          </div>
          <div className="text-[10px] text-gray-500 mt-0.5">
            tokens out
          </div>
        </div>
      </div>

      {/* Détails expandables */}
      {isExpanded && costData.models_breakdown && costData.models_breakdown.length > 0 && (
        <div className="mt-4 pt-4 border-t border-blue-200">
          <h4 className="text-sm font-semibold text-gray-900 mb-3">
            Détail par modèle AI
          </h4>
          <div className="space-y-2">
            {costData.models_breakdown.map((model: any, index: number) => (
              <div
                key={index}
                className="bg-white rounded-lg p-3 flex items-center justify-between"
              >
                <div className="flex items-center gap-3">
                  <div className="w-2 h-2 rounded-full bg-blue-500"></div>
                  <div>
                    <div className="font-mono text-sm text-gray-900">
                      {model.model}
                    </div>
                    <div className="text-xs text-gray-500">
                      {model.input_tokens.toLocaleString('fr-FR')} in / {model.output_tokens.toLocaleString('fr-FR')} out
                    </div>
                  </div>
                </div>
                <div className="text-right">
                  <div className="font-semibold text-gray-900">
                    {model.cost_eur.toFixed(4)}€
                  </div>
                  <div className="text-xs text-gray-500">
                    ${model.cost_usd.toFixed(4)}
                  </div>
                </div>
              </div>
            ))}
          </div>

          {/* Info */}
          <div className="mt-4 p-3 bg-blue-100 rounded-lg text-xs text-blue-800">
            <div className="flex items-start gap-2">
              <svg className="w-4 h-4 flex-shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
              </svg>
              <div>
                Les coûts sont calculés en fonction des tokens utilisés par chaque modèle AI.
                Taux de change USD→EUR: 0.92
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
