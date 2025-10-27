'use client';

import { useTopExpensiveSearches } from '@/hooks/use-costs';
import Link from 'next/link';

interface TopExpensiveSearchesProps {
  limit?: number;
}

export function TopExpensiveSearches({ limit = 10 }: TopExpensiveSearchesProps) {
  const { searches, loading, error } = useTopExpensiveSearches(limit);

  if (loading) {
    return (
      <div className="bg-white rounded-xl shadow-md p-6">
        <div className="h-6 bg-gray-200 rounded w-1/3 mb-4 animate-pulse"></div>
        <div className="space-y-3">
          {[...Array(5)].map((_, i) => (
            <div key={i} className="h-16 bg-gray-100 rounded animate-pulse"></div>
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-white rounded-xl shadow-md p-6">
        <div className="flex items-center gap-3 text-red-600">
          <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <span className="text-sm">{error}</span>
        </div>
      </div>
    );
  }

  if (!searches || searches.length === 0) {
    return (
      <div className="bg-white rounded-xl shadow-md p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">
          Recherches les Plus Coûteuses
        </h3>
        <div className="text-center py-8 text-gray-500">
          <svg className="w-16 h-16 mx-auto mb-4 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
          </svg>
          <p>Aucune recherche pour le moment</p>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-xl shadow-md p-6">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <div className="bg-orange-100 p-2 rounded-lg">
            <svg className="w-6 h-6 text-orange-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
            </svg>
          </div>
          <div>
            <h3 className="text-lg font-semibold text-gray-900">
              Top {limit} Recherches Coûteuses
            </h3>
            <p className="text-sm text-gray-600">
              Les recherches qui ont consommé le plus de tokens
            </p>
          </div>
        </div>
      </div>

      <div className="space-y-3">
        {searches.map((search, index) => {
          const date = new Date(search.created_at);
          const dateStr = date.toLocaleDateString('fr-FR', {
            day: '2-digit',
            month: 'short',
            year: 'numeric'
          });

          return (
            <div
              key={search.id}
              className="group relative bg-gradient-to-r from-gray-50 to-white hover:from-orange-50 hover:to-orange-50 rounded-lg p-4 border border-gray-200 hover:border-orange-300 transition-all cursor-pointer"
            >
              <Link href={`/results/${search.id}`} className="block">
                <div className="flex items-start justify-between gap-4">
                  {/* Rang */}
                  <div className="flex-shrink-0">
                    <div className={`
                      w-8 h-8 rounded-full flex items-center justify-center font-bold text-sm
                      ${index === 0 ? 'bg-yellow-400 text-yellow-900' : ''}
                      ${index === 1 ? 'bg-gray-300 text-gray-700' : ''}
                      ${index === 2 ? 'bg-orange-300 text-orange-900' : ''}
                      ${index > 2 ? 'bg-gray-100 text-gray-600' : ''}
                    `}>
                      {index + 1}
                    </div>
                  </div>

                  {/* Infos */}
                  <div className="flex-1 min-w-0">
                    <h4 className="font-semibold text-gray-900 truncate group-hover:text-orange-700 transition-colors">
                      {search.company_name}
                    </h4>
                    <div className="flex items-center gap-4 mt-1 text-xs text-gray-500">
                      <span className="flex items-center gap-1">
                        <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                        </svg>
                        {dateStr}
                      </span>
                      {search.subsidiaries_count > 0 && (
                        <span className="flex items-center gap-1">
                          <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
                          </svg>
                          {search.subsidiaries_count} filiales
                        </span>
                      )}
                      {search.processing_time && (
                        <span className="flex items-center gap-1">
                          <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                          </svg>
                          {search.processing_time.toFixed(1)}s
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Coûts */}
                  <div className="flex-shrink-0 text-right">
                    <div className="text-lg font-bold text-orange-600">
                      {search.cost_eur.toFixed(4)}€
                    </div>
                    <div className="text-xs text-gray-500">
                      {(search.total_tokens / 1000).toFixed(1)}K tokens
                    </div>
                  </div>
                </div>
              </Link>
            </div>
          );
        })}
      </div>

      {/* Total */}
      <div className="mt-4 pt-4 border-t border-gray-200">
        <div className="flex justify-between items-center text-sm">
          <span className="font-medium text-gray-700">
            Coût total des {searches.length} recherches
          </span>
          <span className="text-lg font-bold text-gray-900">
            {searches.reduce((sum, s) => sum + s.cost_eur, 0).toFixed(2)}€
          </span>
        </div>
      </div>
    </div>
  );
}
