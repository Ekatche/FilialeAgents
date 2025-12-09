'use client';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Search, Link as LinkIcon, Zap, Layers, Rocket, Loader2 } from 'lucide-react';
import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useExtractionWebSocket } from '@/hooks/use-extraction-websocket';

export default function AnalysesPage() {
  const router = useRouter();
  // State simplifié : on ne gère plus le type de recherche, uniquement l'URL
  const [searchValue, setSearchValue] = useState('');
  const [sector, setSector] = useState('');
  const [useCache, setUseCache] = useState(false);
  const [maxParallel, setMaxParallel] = useState(5);
  const [isLoading, setIsLoading] = useState(false);
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);
  const [currentExtractionId, setCurrentExtractionId] = useState<string | null>(null);

  // WebSocket pour suivi temps réel (juste pour l'initialisation, le vrai suivi se fait sur la page résultats)
  const { progress, isConnected } = useExtractionWebSocket(currentSessionId);

  const handleAnalyze = async () => {
    if (!searchValue.trim()) return;

    setIsLoading(true);
    try {
      // Construction du payload forcé en mode URL
      const requestBody: {
        url: string;
        sector?: string;
        use_cache: boolean;
        max_parallel: number;
      } = {
        url: searchValue.trim(),
        use_cache: useCache,
        max_parallel: maxParallel,
      };

      if (sector.trim()) {
        requestBody.sector = sector.trim();
      }

      const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8012';
      
      // Appel à l'endpoint hiérarchique
      const response = await fetch(`${API_BASE_URL}/hierarchical/extract`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestBody),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Erreur lors de l\'analyse');
      }

      const data = await response.json();

      // Stocker les IDs pour le suivi immédiat
      setCurrentSessionId(data.session_id);
      setCurrentExtractionId(data.extraction_id);

      // Rediriger vers la page de résultats après un court délai
      // Cela permet à l'utilisateur de voir que la requête a été prise en compte
      setTimeout(() => {
        router.push(`/dashboard/resultats/${data.extraction_id}`);
      }, 500);

    } catch (error) {
      console.error('Erreur lors de l\'analyse:', error);
      alert(error instanceof Error ? error.message : 'Une erreur est survenue');
      setIsLoading(false);
      setCurrentSessionId(null);
      setCurrentExtractionId(null);
    }
  };

  // Sécurité : Redirection automatique si le WebSocket signale que c'est terminé
  // (Au cas où le timeout ci-dessus n'aurait pas suffi ou si l'utilisateur est resté sur la page)
  useEffect(() => {
    if (progress && (progress.overall_status === 'completed' || progress.overall_status === 'error') && currentExtractionId) {
      router.push(`/dashboard/resultats/${currentExtractionId}`);
    }
  }, [progress, currentExtractionId, router]);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-zinc-900">Nouvelle analyse</h1>
        <p className="text-zinc-600 mt-2">
          Analyse hiérarchique d'entreprise à partir d'un site web
        </p>
      </div>

      {/* Feedback visuel immédiat si l'extraction démarre */}
      {isLoading && (
        <Card className="border-blue-200 bg-blue-50">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-blue-900">
              <Loader2 className="w-5 h-5 animate-spin" />
              Démarrage de l'analyse...
              {isConnected && (
                <Badge variant="outline" className="border-green-500 text-green-700 ml-auto">
                  🟢 Connecté
                </Badge>
              )}
            </CardTitle>
            <CardDescription>
              Initialisation des agents pour {searchValue}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="w-full bg-blue-200 rounded-full h-2 overflow-hidden">
              <div className="bg-blue-600 h-2 rounded-full w-full animate-pulse" />
            </div>
            <p className="text-xs text-blue-700 mt-2 text-center">
              Vous allez être redirigé vers le tableau de bord des résultats...
            </p>
          </CardContent>
        </Card>
      )}

      {/* Formulaire d'analyse */}
      <Card className="border-zinc-200">
        <CardHeader>
          <CardTitle className="text-zinc-900 flex items-center gap-2">
            <LinkIcon className="w-5 h-5 text-[#FE4D01]" />
            Cible de l'analyse
          </CardTitle>
          <CardDescription>
            Entrez l'URL du site web de l'entreprise à analyser
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          
          {/* Input URL Principal */}
          <div className="space-y-2">
            <label className="text-sm font-medium text-zinc-900">
              URL du site web
            </label>
            <div className="flex gap-2">
              <Input
                type="url"
                placeholder="Ex: https://www.techcorp.com"
                value={searchValue}
                onChange={(e) => setSearchValue(e.target.value)}
                className="flex-1 border-zinc-200 focus:border-[#FE4D01] focus:ring-[#FE4D01]"
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && searchValue.trim() && !isLoading) {
                    handleAnalyze();
                  }
                }}
              />
              <Button
                onClick={handleAnalyze}
                disabled={!searchValue.trim() || isLoading}
                className="bg-[#FE4D01] text-white hover:bg-[#FE4D01]/90 min-w-[120px]"
              >
                {isLoading ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <>
                    <Search className="w-4 h-4 mr-2" />
                    Analyser
                  </>
                )}
              </Button>
            </div>
            <p className="text-xs text-zinc-500">
              L'IA naviguera sur le site pour identifier la structure, les filiales et les informations clés.
            </p>
          </div>

          {/* Options avancées (Collapsible ou juste en dessous) */}
          <div className="pt-4 border-t border-zinc-200 space-y-4">
            <div className="text-sm font-medium text-zinc-900">Informations complémentaires (Optionnel)</div>
            
            {/* Secteur */}
            <div className="space-y-2">
              <label htmlFor="sector" className="text-sm text-zinc-600">
                Secteur d'activité connu
              </label>
              <Input
                id="sector"
                type="text"
                placeholder="Ex: Technologie, Finance, Commerce..."
                value={sector}
                onChange={(e) => setSector(e.target.value)}
                className="border-zinc-200 focus:border-[#FE4D01] focus:ring-[#FE4D01] max-w-md"
              />
              <p className="text-xs text-zinc-500">
                Aider l'IA à se focaliser sur le bon contexte sectoriel.
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Info Cards - Architecture hiérarchique */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card className="border-zinc-200 bg-white/50">
          <CardHeader>
            <div className="flex items-center gap-2">
              <div className="p-2 rounded-lg bg-orange-50">
                <Zap className="w-5 h-5 text-[#FE4D01]" />
              </div>
              <CardTitle className="text-lg text-zinc-900">Phase 0 : Éclaireur</CardTitle>
            </div>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-zinc-600">
              Identification rapide de la société mère et du secteur d'activité pour une analyse rapide et économique.
            </p>
          </CardContent>
        </Card>

        <Card className="border-zinc-200 bg-white/50">
          <CardHeader>
            <div className="flex items-center gap-2">
              <div className="p-2 rounded-lg bg-orange-50">
                <Layers className="w-5 h-5 text-[#FE4D01]" />
              </div>
              <CardTitle className="text-lg text-zinc-900">Phase 1 : Cartographe</CardTitle>
            </div>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-zinc-600">
              Identification jusqu'à 15 entités (filiales, succursales) pour une cartographie précise de l'organisation.
            </p>
          </CardContent>
        </Card>

        <Card className="border-zinc-200 bg-white/50">
          <CardHeader>
            <div className="flex items-center gap-2">
              <div className="p-2 rounded-lg bg-orange-50">
                <Rocket className="w-5 h-5 text-[#FE4D01]" />
              </div>
              <CardTitle className="text-lg text-zinc-900">Phase 2 : Extraction</CardTitle>
            </div>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-zinc-600">
              Extraction parallèle des informations détaillées pour une analyse 5x plus rapide.
            </p>
          </CardContent>
        </Card>
      </div>

    </div>
  );
}

