'use client';

import Link from 'next/link';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import {
  Search,
  Calendar,
  DollarSign,
  Building2,
  ExternalLink,
  Filter,
  Download,
  Loader2
} from 'lucide-react';
import { formatDate } from '@/lib/utils';
import { useState, useMemo } from 'react';
import { usePublicRecentExtractions } from '@/hooks/use-public-extractions';

type SearchStatus = 'all' | 'completed' | 'pending' | 'running' | 'error';

export default function HistoriquePage() {
  const [statusFilter, setStatusFilter] = useState<SearchStatus>('all');
  const [searchQuery, setSearchQuery] = useState('');

  // Charger les extractions depuis l'API
  const { extractions, loading, error } = usePublicRecentExtractions(50);

  // Filtrer les résultats
  const filteredSearches = useMemo(() => {
    return extractions.filter((search) => {
      const matchesStatus = statusFilter === 'all' || search.status === statusFilter;
      const matchesQuery = search.company_name.toLowerCase().includes(searchQuery.toLowerCase());
      return matchesStatus && matchesQuery;
    });
  }, [extractions, statusFilter, searchQuery]);

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'completed':
        return <Badge className="bg-orange-50 text-[#FE4D01] border-orange-200">Terminé</Badge>;
      case 'running':
      case 'pending':
        return <Badge className="bg-blue-50 text-blue-700 border-blue-200">En cours</Badge>;
      case 'error':
        return <Badge className="bg-red-50 text-red-700 border-red-200">Échoué</Badge>;
      default:
        return <Badge>{status}</Badge>;
    }
  };

  const getExtractionTypeLabel = (type: string) => {
    return type === 'hierarchical' ? 'Hiérarchique' : type.charAt(0).toUpperCase() + type.slice(1);
  };

  // Affichage pendant le chargement
  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <Loader2 className="w-8 h-8 animate-spin text-[#FE4D01] mx-auto mb-4" />
          <p className="text-zinc-600">Chargement de l'historique...</p>
        </div>
      </div>
    );
  }

  // Affichage en cas d'erreur
  if (error) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold text-zinc-900">Historique des recherches</h1>
          <p className="text-zinc-600 mt-2">
            Consultez toutes vos analyses d'entreprises
          </p>
        </div>
        <Card className="border-red-200 bg-red-50">
          <CardContent className="pt-6">
            <p className="text-red-600">Erreur de chargement: {error}</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-zinc-900">Historique des recherches</h1>
          <p className="text-zinc-600 mt-2">
            Consultez toutes vos analyses d'entreprises ({extractions.length} au total)
          </p>
        </div>
        <Button variant="outline">
          <Download className="w-4 h-4 mr-2" />
          Exporter
        </Button>
      </div>

      {/* Filters */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex flex-col md:flex-row gap-4">
            {/* Search */}
            <div className="flex-1">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-zinc-400" />
                <Input
                  type="text"
                  placeholder="Rechercher une entreprise..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-10"
                />
              </div>
            </div>

            {/* Status Filter */}
            <div className="flex gap-2">
              <Button
                variant={statusFilter === 'all' ? 'default' : 'outline'}
                onClick={() => setStatusFilter('all')}
                size="sm"
                className={statusFilter === 'all' ? 'bg-[#FE4D01] hover:bg-[#FE4D01]/90' : ''}
              >
                Tous
              </Button>
              <Button
                variant={statusFilter === 'completed' ? 'default' : 'outline'}
                onClick={() => setStatusFilter('completed')}
                size="sm"
                className={statusFilter === 'completed' ? 'bg-[#FE4D01] hover:bg-[#FE4D01]/90' : ''}
              >
                Terminés
              </Button>
              <Button
                variant={statusFilter === 'running' ? 'default' : 'outline'}
                onClick={() => setStatusFilter('running')}
                size="sm"
                className={statusFilter === 'running' ? 'bg-[#FE4D01] hover:bg-[#FE4D01]/90' : ''}
              >
                En cours
              </Button>
              <Button
                variant={statusFilter === 'error' ? 'default' : 'outline'}
                onClick={() => setStatusFilter('error')}
                size="sm"
                className={statusFilter === 'error' ? 'bg-[#FE4D01] hover:bg-[#FE4D01]/90' : ''}
              >
                Échoués
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Results */}
      <div className="space-y-4">
        {filteredSearches.length === 0 ? (
          <Card>
            <CardContent className="py-12 text-center">
              <Search className="w-12 h-12 text-zinc-400 mx-auto mb-4" />
              <p className="text-zinc-600">
                Aucune recherche trouvée avec ces critères
              </p>
            </CardContent>
          </Card>
        ) : (
          filteredSearches.map((search) => (
            <Card key={search.id} className="hover:shadow-md transition-shadow border-zinc-200">
              <CardContent className="pt-6">
                <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
                  {/* Left: Company Info */}
                  <div className="flex-1 space-y-2">
                    <div className="flex items-start gap-3">
                      <div className="p-2 bg-orange-50 rounded-lg">
                        <Building2 className="w-5 h-5 text-[#FE4D01]" />
                      </div>
                      <div className="flex-1">
                        <div className="flex items-center gap-2">
                          <h3 className="text-lg font-semibold">{search.company_name}</h3>
                          {getStatusBadge(search.status)}
                        </div>
                        {search.company_url && (
                          <a
                            href={search.company_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-sm text-zinc-600 hover:text-[#FE4D01] flex items-center gap-1 mt-1"
                          >
                            {search.company_url}
                            <ExternalLink className="w-3 h-3" />
                          </a>
                        )}
                        <div className="flex flex-wrap items-center gap-4 mt-2 text-sm text-zinc-600">
                          <div className="flex items-center gap-1 text-zinc-600">
                            <Calendar className="w-4 h-4" />
                            {formatDate(new Date(search.created_at))}
                          </div>
                          <Badge variant="outline">
                            {getExtractionTypeLabel(search.extraction_type)}
                          </Badge>
                          {search.subsidiaries_count !== null && (
                            <span>
                              {search.subsidiaries_count} filiale{search.subsidiaries_count > 1 ? 's' : ''}
                            </span>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Right: Stats & Actions */}
                  <div className="flex flex-col lg:items-end gap-3">
                    {search.status === 'completed' && search.cost_eur !== null && (
                      <div className="text-right">
                        <div className="text-lg font-semibold text-zinc-900">
                          {search.cost_eur.toFixed(2)}€
                        </div>
                        <div className="text-xs text-zinc-500">
                          {search.total_tokens?.toLocaleString('fr-FR')} tokens
                        </div>
                        {search.processing_time && (
                          <div className="text-xs text-zinc-500">
                            {Math.floor(search.processing_time / 60)}min {search.processing_time % 60}s
                          </div>
                        )}
                      </div>
                    )}
                    {(search.status === 'running' || search.status === 'pending') && (
                      <div className="text-sm text-zinc-600">
                        Analyse en cours...
                      </div>
                    )}
                    {search.status === 'error' && (
                      <div className="text-sm text-red-600">
                        Échec de l'analyse
                        {search.error_message && (
                          <div className="text-xs mt-1">{search.error_message}</div>
                        )}
                      </div>
                    )}
                    <Link href={`/dashboard/resultats/${search.id}`}>
                      <Button
                        variant="outline"
                        size="sm"
                      >
                        Voir détails
                        <ExternalLink className="w-4 h-4 ml-2" />
                      </Button>
                    </Link>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))
        )}
      </div>

      {/* Stats Summary */}
      <Card>
        <CardHeader>
          <CardTitle>Résumé</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div>
              <div className="text-2xl font-bold text-zinc-900">{extractions.length}</div>
              <div className="text-sm text-zinc-600">Total recherches</div>
            </div>
            <div>
              <div className="text-2xl font-bold text-[#FE4D01]">
                {extractions.filter(s => s.status === 'completed').length}
              </div>
              <div className="text-sm text-zinc-600">Terminées</div>
            </div>
            <div>
              <div className="text-2xl font-bold text-zinc-900">
                {extractions
                  .filter(s => s.cost_eur !== null)
                  .reduce((sum, s) => sum + (s.cost_eur || 0), 0)
                  .toFixed(2)}€
              </div>
              <div className="text-sm text-zinc-600">Coût total</div>
            </div>
            <div>
              <div className="text-2xl font-bold text-zinc-900">
                {extractions
                  .filter(s => s.total_tokens !== null)
                  .reduce((sum, s) => sum + (s.total_tokens || 0), 0)
                  .toLocaleString('fr-FR')}
              </div>
              <div className="text-sm text-zinc-600">Tokens utilisés</div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

