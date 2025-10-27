'use client';

import { useState } from 'react';
import { useCosts } from '@/hooks/use-costs';

export function CostEstimator() {
  const costs = useCosts();
  const [extractionType, setExtractionType] = useState<'simple' | 'advanced'>('simple');
  const [hasSubsidiaries, setHasSubsidiaries] = useState(true);
  const [subsidiariesCount, setSubsidiariesCount] = useState(5);
  const [estimate, setEstimate] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleEstimate = async () => {
    try {
      setLoading(true);
      setError(null);
      const result = await costs.estimateCost(
        extractionType,
        hasSubsidiaries,
        subsidiariesCount
      );
      setEstimate(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Estimation failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-white rounded-xl shadow-md p-6 border border-gray-200">
      <div className="flex items-center gap-3 mb-6">
        <div className="bg-purple-100 p-2 rounded-lg">
          <svg
            className="w-6 h-6 text-purple-600"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M9 7h6m0 10v-3m-3 3h.01M9 17h.01M9 14h.01M12 14h.01M15 11h.01M12 11h.01M9 11h.01M7 21h10a2 2 0 002-2V5a2 2 0 00-2-2H7a2 2 0 00-2 2v14a2 2 0 002 2z"
            />
          </svg>
        </div>
        <div>
          <h3 className="text-lg font-semibold text-gray-900">
            Estimateur de Coûts
          </h3>
          <p className="text-sm text-gray-600">
            Estimez le coût avant de lancer une recherche
          </p>
        </div>
      </div>

      {/* Formulaire */}
      <div className="space-y-4 mb-6">
        {/* Type d'extraction */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Type de recherche
          </label>
          <div className="flex gap-3">
            <button
              onClick={() => setExtractionType('simple')}
              className={`
                flex-1 px-4 py-3 rounded-lg border-2 transition-all
                ${extractionType === 'simple'
                  ? 'border-blue-500 bg-blue-50 text-blue-700'
                  : 'border-gray-200 hover:border-gray-300'
                }
              `}
            >
              <div className="font-medium">Simple</div>
              <div className="text-xs text-gray-600">Recherche standard</div>
            </button>
            <button
              onClick={() => setExtractionType('advanced')}
              className={`
                flex-1 px-4 py-3 rounded-lg border-2 transition-all
                ${extractionType === 'advanced'
                  ? 'border-blue-500 bg-blue-50 text-blue-700'
                  : 'border-gray-200 hover:border-gray-300'
                }
              `}
            >
              <div className="font-medium">Avancée</div>
              <div className="text-xs text-gray-600">Recherche approfondie</div>
            </button>
          </div>
        </div>

        {/* Avec filiales */}
        <div className="flex items-center justify-between">
          <label htmlFor="has-subsidiaries" className="text-sm font-medium text-gray-700">
            L&apos;entreprise a des filiales
          </label>
          <button
            id="has-subsidiaries"
            onClick={() => setHasSubsidiaries(!hasSubsidiaries)}
            className={`
              relative inline-flex h-6 w-11 items-center rounded-full transition-colors
              ${hasSubsidiaries ? 'bg-blue-600' : 'bg-gray-200'}
            `}
          >
            <span
              className={`
                inline-block h-4 w-4 transform rounded-full bg-white transition-transform
                ${hasSubsidiaries ? 'translate-x-6' : 'translate-x-1'}
              `}
            />
          </button>
        </div>

        {/* Nombre de filiales */}
        {hasSubsidiaries && (
          <div>
            <label htmlFor="subsidiaries-count" className="block text-sm font-medium text-gray-700 mb-2">
              Nombre estimé de filiales: {subsidiariesCount}
            </label>
            <input
              id="subsidiaries-count"
              type="range"
              min="1"
              max="50"
              value={subsidiariesCount}
              onChange={(e) => setSubsidiariesCount(parseInt(e.target.value))}
              className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-blue-600"
            />
            <div className="flex justify-between text-xs text-gray-500 mt-1">
              <span>1</span>
              <span>25</span>
              <span>50</span>
            </div>
          </div>
        )}

        {/* Bouton d'estimation */}
        <button
          onClick={handleEstimate}
          disabled={loading}
          className="w-full px-6 py-3 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white font-medium rounded-lg transition-colors duration-200"
        >
          {loading ? (
            <span className="flex items-center justify-center gap-2">
              <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
              </svg>
              Estimation en cours...
            </span>
          ) : (
            'Estimer le coût'
          )}
        </button>
      </div>

      {/* Erreur */}
      {error && (
        <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
          {error}
        </div>
      )}

      {/* Résultat */}
      {estimate && (
        <div className="bg-gradient-to-br from-blue-50 to-indigo-50 rounded-lg p-6 border border-blue-200">
          <h4 className="font-semibold text-gray-900 mb-4">Estimation</h4>

          {/* Coût principal */}
          <div className="bg-white rounded-lg p-4 mb-4 shadow-sm">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-sm text-gray-600 mb-1">Coût estimé</div>
                <div className="text-3xl font-bold text-blue-600">
                  {estimate.total_cost_eur.toFixed(4)}€
                </div>
                <div className="text-sm text-gray-500">
                  ${estimate.total_cost_usd.toFixed(4)}
                </div>
              </div>
              <div className="text-right">
                <div className="text-sm text-gray-600 mb-1">Tokens</div>
                <div className="text-2xl font-bold text-gray-900">
                  {(estimate.total_tokens / 1000).toFixed(1)}K
                </div>
                <div className="text-xs text-gray-500">
                  {estimate.total_tokens.toLocaleString('fr-FR')}
                </div>
              </div>
            </div>
          </div>

          {/* Breakdown */}
          <div className="space-y-2">
            <div className="text-xs font-semibold text-gray-700 uppercase tracking-wide">
              Détail par modèle
            </div>
            {estimate.models_breakdown.map((model: any, index: number) => (
              <div
                key={index}
                className="bg-white rounded p-3 text-sm flex items-center justify-between"
              >
                <div className="flex items-center gap-2">
                  <div className="w-2 h-2 rounded-full bg-blue-500"></div>
                  <span className="font-mono text-xs text-gray-700">{model.model}</span>
                </div>
                <div className="text-right">
                  <div className="font-semibold text-gray-900">
                    {model.cost_eur.toFixed(4)}€
                  </div>
                  <div className="text-[10px] text-gray-500">
                    {model.input_tokens.toLocaleString('fr-FR')} in / {model.output_tokens.toLocaleString('fr-FR')} out
                  </div>
                </div>
              </div>
            ))}
          </div>

          {/* Note */}
          <div className="mt-4 p-3 bg-yellow-50 border border-yellow-200 rounded-lg text-xs text-yellow-800">
            <div className="flex items-start gap-2">
              <svg className="w-4 h-4 flex-shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
              </svg>
              <div>
                <strong>Note:</strong> Il s&apos;agit d&apos;une estimation approximative.
                Le coût réel peut varier en fonction de la complexité des données et du nombre réel de filiales trouvées.
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
