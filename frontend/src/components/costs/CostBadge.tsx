'use client';

import { useState } from 'react';

interface CostBadgeProps {
  costEur?: number;
  costUsd?: number;
  totalTokens?: number;
  inputTokens?: number;
  outputTokens?: number;
  modelsBreakdown?: Array<{
    model: string;
    input_tokens: number;
    output_tokens: number;
    cost_usd: number;
    cost_eur: number;
  }>;
  size?: 'sm' | 'md' | 'lg';
  showDetails?: boolean;
}

export function CostBadge({
  costEur,
  costUsd,
  totalTokens,
  inputTokens,
  outputTokens,
  modelsBreakdown,
  size = 'md',
  showDetails = true
}: CostBadgeProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  if (!costEur && !costUsd) {
    return null;
  }

  const sizeClasses = {
    sm: 'text-xs px-2 py-1',
    md: 'text-sm px-3 py-1.5',
    lg: 'text-base px-4 py-2'
  };

  return (
    <div className="inline-block">
      <div
        className={`
          inline-flex items-center gap-2
          bg-blue-50 text-blue-700
          rounded-full font-medium
          ${sizeClasses[size]}
          ${showDetails ? 'cursor-pointer hover:bg-blue-100' : ''}
        `}
        onClick={() => showDetails && setIsExpanded(!isExpanded)}
      >
        <svg
          className="w-4 h-4"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
          />
        </svg>
        <span className="font-semibold">
          {costEur?.toFixed(4)}€
        </span>
        {costUsd && (
          <span className="text-xs opacity-75">
            (${costUsd.toFixed(4)})
          </span>
        )}
        {totalTokens && (
          <span className="text-xs opacity-75 ml-1">
            {totalTokens.toLocaleString('fr-FR')} tokens
          </span>
        )}
        {showDetails && (
          <svg
            className={`w-4 h-4 transition-transform ${isExpanded ? 'rotate-180' : ''}`}
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M19 9l-7 7-7-7"
            />
          </svg>
        )}
      </div>

      {/* Détails expandables */}
      {showDetails && isExpanded && (
        <div className="mt-2 p-4 bg-white border border-gray-200 rounded-lg shadow-lg">
          <h4 className="text-sm font-semibold text-gray-900 mb-3">
            Détail des coûts
          </h4>

          {/* Tokens */}
          {(inputTokens !== undefined || outputTokens !== undefined) && (
            <div className="mb-3 text-sm text-gray-600">
              <div className="flex justify-between">
                <span>Tokens d&apos;entrée:</span>
                <span className="font-medium">{inputTokens?.toLocaleString('fr-FR') || 0}</span>
              </div>
              <div className="flex justify-between">
                <span>Tokens de sortie:</span>
                <span className="font-medium">{outputTokens?.toLocaleString('fr-FR') || 0}</span>
              </div>
              <div className="flex justify-between pt-1 border-t mt-1">
                <span className="font-medium">Total:</span>
                <span className="font-semibold">{totalTokens?.toLocaleString('fr-FR') || 0}</span>
              </div>
            </div>
          )}

          {/* Breakdown par modèle */}
          {modelsBreakdown && modelsBreakdown.length > 0 && (
            <div className="space-y-2">
              <h5 className="text-xs font-semibold text-gray-700 uppercase tracking-wide">
                Par modèle AI
              </h5>
              {modelsBreakdown.map((model, index) => (
                <div
                  key={index}
                  className="text-xs bg-gray-50 p-2 rounded"
                >
                  <div className="flex justify-between items-center mb-1">
                    <span className="font-mono text-gray-900">{model.model}</span>
                    <span className="font-semibold text-blue-600">
                      {model.cost_eur.toFixed(4)}€
                    </span>
                  </div>
                  <div className="text-gray-500 text-[10px]">
                    {model.input_tokens.toLocaleString('fr-FR')} in / {model.output_tokens.toLocaleString('fr-FR')} out
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
