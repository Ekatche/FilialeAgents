'use client';

import { use, useState, useEffect } from 'react';
import Link from 'next/link';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  Building2,
  MapPin,
  Phone,
  Mail,
  Globe,
  Calendar,
  DollarSign,
  Users,
  ArrowLeft,
  ExternalLink,
  CheckCircle2,
  AlertCircle,
  FileText,
  Loader2
} from 'lucide-react';
import { formatDate } from '@/lib/utils';
import { useExtractionWebSocket } from '@/hooks/use-extraction-websocket';
import { EnhancedAgentProgress } from '@/components/ui/enhanced-agent-progress';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8012';

// Types d'après l'API
interface ExtractionData {
  id: string;
  session_id: string;
  company_name: string;
  company_url: string | null;
  extraction_type: string;
  status: string;
  created_at: string;
  completed_at: string | null;
  cost_eur: number | null;
  cost_usd: number | null;
  total_tokens: number | null;
  subsidiaries_count: number;
  processing_time: number | null;
  error_message: string | null;
  result_data: any; // Structure hiérarchique des résultats
}

// Mock data basé sur la structure CompanyData de l'API (fallback)
const mockCompanyData = {
  company_name: 'TechCorp Inc.',
  headquarters_address: '123 Innovation Drive',
  headquarters_city: 'San Francisco',
  headquarters_country: 'United States',
  parent_company: null,
  sector: 'Technology',
  activities: [
    'Développement de logiciels',
    'Services cloud',
    'Intelligence artificielle',
    'Consulting technologique'
  ],
  revenue_recent: 'Plus de 500 millions d\'euros',
  employees: '2,500',
  founded_year: 2010,
  phone: '+1 (555) 123-4567',
  email: 'contact@techcorp.com',
  subsidiaries_details: [
    {
      legal_name: 'TechCorp Europe SAS',
      headquarters: {
        label: 'Paris, France',
        city: 'Paris',
        country: 'France',
        postal_code: '75001',
        line1: '45 Avenue des Champs-Élysées'
      },
      activity: 'Développement et support technique',
      confidence: 0.92,
      sources: [
        {
          title: 'Registre du commerce',
          url: 'https://example.com/source1',
          tier: 'official'
        }
      ]
    },
    {
      legal_name: 'TechCorp Asia Pte Ltd',
      headquarters: {
        label: 'Singapore',
        city: 'Singapore',
        country: 'Singapore',
        postal_code: '018956',
        line1: '10 Marina Boulevard'
      },
      activity: 'Recherche et développement',
      confidence: 0.88,
      sources: [
        {
          title: 'Singapore Business Registry',
          url: 'https://example.com/source2',
          tier: 'official'
        }
      ]
    },
    {
      legal_name: 'TechCorp UK Limited',
      headquarters: {
        label: 'London, United Kingdom',
        city: 'London',
        country: 'United Kingdom',
        postal_code: 'EC2A 4DP',
        line1: '25 Old Broad Street'
      },
      activity: 'Services clients et support',
      confidence: 0.85,
      sources: [
        {
          title: 'Companies House',
          url: 'https://example.com/source3',
          tier: 'official'
        }
      ]
    }
  ],
  commercial_presence_details: [
    {
      name: 'TechCorp Canada',
      type: 'office',
      relationship: 'owned',
      activity: 'Bureau de représentation',
      location: {
        city: 'Toronto',
        country: 'Canada',
        line1: '100 King Street West'
      },
      phone: '+1 (416) 555-0123',
      status: 'active',
      confidence: 0.78
    }
  ],
  extraction_costs: {
    cost_usd: 8.42,
    cost_eur: 7.75,
    total_tokens: 125000,
    input_tokens: 85000,
    output_tokens: 40000,
    models_breakdown: [
      {
        model: 'gpt-4o',
        input_tokens: 60000,
        output_tokens: 30000,
        cost_usd: 6.30,
        cost_eur: 5.80
      },
      {
        model: 'gpt-4o-mini',
        input_tokens: 25000,
        output_tokens: 10000,
        cost_usd: 2.12,
        cost_eur: 1.95
      }
    ],
    search_type: 'advanced',
    exchange_rate: 0.92
  },
  sources: [
    {
      title: 'Site web officiel TechCorp',
      url: 'https://www.techcorp.com',
      publisher: 'TechCorp Inc.',
      tier: 'official',
      accessibility: 'ok'
    },
    {
      title: 'Rapport annuel 2023',
      url: 'https://www.techcorp.com/annual-report-2023',
      publisher: 'TechCorp Inc.',
      published_date: '2024-01-15',
      tier: 'official',
      accessibility: 'ok'
    },
    {
      title: 'Article Forbes - TechCorp Expansion',
      url: 'https://www.forbes.com/techcorp-expansion',
      publisher: 'Forbes',
      published_date: '2024-02-10',
      tier: 'financial_media',
      accessibility: 'ok'
    }
  ],
  methodology_notes: [
    'Extraction effectuée via recherche hiérarchique',
    'Données vérifiées auprès de registres officiels',
    'Confiance élevée pour les filiales européennes'
  ],
  extraction_metadata: {
    input_type: 'company_name',
    session_id: 'session_123456',
    processing_time: 285.5
  },
  extraction_date: '2024-01-15T10:35:00Z'
};

export default function ResultatsPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);

  // État pour les données d'extraction
  const [extraction, setExtraction] = useState<ExtractionData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Charger les données d'extraction depuis l'API
  useEffect(() => {
    const fetchExtraction = async () => {
      try {
        setLoading(true);
        setError(null);

        // Récupérer l'extraction depuis l'API publique
        const response = await fetch(`${API_URL}/public/extractions/${id}`);

        if (!response.ok) {
          throw new Error(`Erreur ${response.status}: ${response.statusText}`);
        }

        const data = await response.json();
        setExtraction(data);
      } catch (err) {
        console.error('Erreur chargement extraction:', err);
        setError(err instanceof Error ? err.message : 'Erreur de chargement');
      } finally {
        setLoading(false);
      }
    };

    if (id) {
      fetchExtraction();
    }
  }, [id]);

  // WebSocket pour tracking temps réel (on utilise le session_id comme ID)
  const { progress, isConnected } = useExtractionWebSocket(extraction?.session_id || null);

  // Polling automatique pour rafraîchir les données si extraction en cours
  useEffect(() => {
    if (!extraction || (extraction.status !== 'running' && extraction.status !== 'pending')) {
      return;
    }

    const interval = setInterval(async () => {
      try {
        const response = await fetch(`${API_URL}/public/extractions/${id}`);
        if (response.ok) {
          const data = await response.json();
          setExtraction(data);
          
          // Si l'extraction est terminée, arrêter le polling
          if (data.status === 'completed' || data.status === 'error') {
            clearInterval(interval);
          }
        }
      } catch (err) {
        console.error('Erreur polling extraction:', err);
      }
    }, 3000); // Poll toutes les 3 secondes

    return () => clearInterval(interval);
  }, [id, extraction?.status]);

  // Affichage pendant le chargement
  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <Loader2 className="w-8 h-8 animate-spin text-[#FE4D01] mx-auto mb-4" />
          <p className="text-zinc-600">Chargement des résultats...</p>
        </div>
      </div>
    );
  }

  // Affichage en cas d'erreur
  if (error || !extraction) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Card className="border-red-200 bg-red-50">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-red-700">
              <AlertCircle className="w-5 h-5" />
              Erreur de chargement
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-red-600">{error || 'Extraction introuvable'}</p>
            <Link href="/dashboard/historique" className="mt-4 inline-block">
              <Button variant="outline">
                <ArrowLeft className="w-4 h-4 mr-2" />
                Retour à l'historique
              </Button>
            </Link>
          </CardContent>
        </Card>
      </div>
    );
  }

  // Affichage du progrès si extraction en cours
  if (extraction.status === 'running' || extraction.status === 'pending') {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-zinc-900">Extraction en cours</h1>
            <p className="text-zinc-600 mt-1">{extraction.company_name}</p>
          </div>
          <Badge className="bg-blue-50 text-blue-700 border-blue-200 animate-pulse">
            <Loader2 className="w-3 h-3 mr-1 animate-spin" />
            En cours
          </Badge>
        </div>

        {/* Progrès WebSocket avec le nouveau composant animé */}
        {progress ? (
          <EnhancedAgentProgress 
            progress={progress as any} 
            isConnected={isConnected} 
          />
        ) : (
          <Card className="border-zinc-200">
             <CardContent className="pt-6 text-center">
               <Loader2 className="w-8 h-8 animate-spin text-zinc-400 mx-auto mb-2" />
               <p className="text-zinc-500">Connexion au flux de suivi...</p>
             </CardContent>
          </Card>
        )}

        <Card className="border-zinc-200">
          <CardContent className="pt-6 text-center text-zinc-600">
            <p>L'extraction est en cours. Cette page se mettra à jour automatiquement.</p>
            <p className="text-sm mt-2">Session ID: <code className="text-xs bg-zinc-100 px-2 py-1 rounded">{extraction.session_id}</code></p>
          </CardContent>
        </Card>
      </div>
    );
  }

  // Extraire les données du résultat
  let resultData = extraction.result_data;
  if (typeof resultData === 'string') {
    try {
      resultData = JSON.parse(resultData);
    } catch (e) {
      console.error("Error parsing result_data", e);
    }
  }
  const data = resultData || mockCompanyData;
  let parentInfo = data.parent_company_info || null;
  const minimalMapping = data.minimal_mapping || null;
  const detailedEntities = data.detailed_entities || [];

  // Transformer les données d'adresse si elles existent mais ne sont pas dans le format attendu
  if (parentInfo && !parentInfo.headquarters) {
    // Si on a headquarters_address, headquarters_city, headquarters_country mais pas headquarters
    if (parentInfo.headquarters_address || parentInfo.headquarters_city || parentInfo.headquarters_country) {
      parentInfo = {
        ...parentInfo,
        headquarters: {
          line1: parentInfo.headquarters_address || null,
          city: parentInfo.headquarters_city || null,
          country: parentInfo.headquarters_country || null,
        }
      };
    }
  }

  // Déterminer le nom à afficher (nom légal ou nom de l'extraction)
  const displayName = parentInfo?.company_name || extraction.company_name;

  // Récupérer les sources (du parent ou globales)
  const sources = parentInfo?.sources || data.sources || [];

  const getTierColor = (tier: string) => {
    switch (tier) {
      case 'official':
        return 'bg-orange-50 text-[#FE4D01] border-orange-200';
      case 'financial_media':
        return 'bg-blue-50 text-blue-700 border-blue-200';
      case 'pro_db':
        return 'bg-purple-50 text-purple-700 border-purple-200';
      default:
        return 'bg-zinc-50 text-zinc-700 border-zinc-200';
    }
  };

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.9) return 'text-[#FE4D01]';
    if (confidence >= 0.7) return 'text-orange-600';
    return 'text-yellow-600';
  };

  console.log('DEBUG RESULTATS:', {
    extractionName: extraction.company_name,
    parentInfo,
    displayName,
    sourcesCount: sources?.length,
    sources
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Link href="/dashboard/historique">
            <Button variant="outline" size="sm">
              <ArrowLeft className="w-4 h-4 mr-2" />
              Retour
            </Button>
          </Link>
          <div>
            <h1 className="text-3xl font-bold text-zinc-900">{displayName}</h1>
            <p className="text-zinc-600 mt-1">
              Résultats de l'analyse • {formatDate(extraction.created_at)}
            </p>
          </div>
        </div>
        <Badge className="bg-orange-50 text-[#FE4D01] border-orange-200">
          <CheckCircle2 className="w-3 h-3 mr-1" />
          {extraction.status === 'completed' ? 'Analyse terminée' : extraction.status}
        </Badge>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card className="border-zinc-200">
          <CardContent className="pt-6">
            <div className="text-sm text-zinc-600">Entités trouvées</div>
            <div className="text-2xl font-bold text-zinc-900 mt-1">
              {extraction.subsidiaries_count || 0}
            </div>
          </CardContent>
        </Card>
        <Card className="border-zinc-200">
          <CardContent className="pt-6">
            <div className="text-sm text-zinc-600">Coût total</div>
            <div className="text-2xl font-bold text-zinc-900 mt-1">
              {extraction.cost_eur?.toFixed(2) || '0.00'}€
            </div>
          </CardContent>
        </Card>
        <Card className="border-zinc-200">
          <CardContent className="pt-6">
            <div className="text-sm text-zinc-600">Tokens utilisés</div>
            <div className="text-2xl font-bold text-zinc-900 mt-1">
              {extraction.total_tokens ? `${(extraction.total_tokens / 1000).toFixed(0)}K` : '0K'}
            </div>
          </CardContent>
        </Card>
        <Card className="border-zinc-200">
          <CardContent className="pt-6">
            <div className="text-sm text-zinc-600">Durée</div>
            <div className="text-2xl font-bold text-zinc-900 mt-1">
              {extraction.processing_time ? `${Math.floor(extraction.processing_time / 60)}min ${Math.round(extraction.processing_time % 60)}s` : 'N/A'}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Parent Company Info */}
      {parentInfo && (
        <Card className="border-zinc-200">
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-lg">
              <Building2 className="w-5 h-5 text-[#FE4D01]" />
              Société mère - {displayName}
            </CardTitle>
          </CardHeader>
          <CardContent className="pt-0">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              <div className="space-y-3">
                {parentInfo.headquarters && (
                  <div>
                    <label className="text-xs font-medium text-zinc-500 mb-1 block">Siège social</label>
                    <div className="flex items-start gap-2">
                      <MapPin className="w-3.5 h-3.5 text-zinc-400 mt-0.5 flex-shrink-0" />
                      <div className="min-w-0">
                        {parentInfo.headquarters.line1 && (
                          <p className="text-sm text-zinc-900 leading-tight">{parentInfo.headquarters.line1}</p>
                        )}
                        <p className="text-xs text-zinc-600 mt-0.5">
                          {parentInfo.headquarters.city && `${parentInfo.headquarters.city}, `}
                          {parentInfo.headquarters.country}
                        </p>
                      </div>
                    </div>
                  </div>
                )}

                {parentInfo.phone && (
                  <div>
                    <label className="text-xs font-medium text-zinc-500 mb-1 block">Téléphone</label>
                    <div className="flex items-center gap-2">
                      <Phone className="w-3.5 h-3.5 text-zinc-400 flex-shrink-0" />
                      <span className="text-sm text-zinc-900">{parentInfo.phone}</span>
                    </div>
                  </div>
                )}

                {parentInfo.email && (
                  <div>
                    <label className="text-xs font-medium text-zinc-500 mb-1 block">Email</label>
                    <div className="flex items-center gap-2">
                      <Mail className="w-3.5 h-3.5 text-zinc-400 flex-shrink-0" />
                      <a href={`mailto:${parentInfo.email}`} className="text-sm text-[#FE4D01] hover:underline truncate">
                        {parentInfo.email}
                      </a>
                    </div>
                  </div>
                )}

                {parentInfo.website && (
                  <div>
                    <label className="text-xs font-medium text-zinc-500 mb-1 block">Site web</label>
                    <a href={parentInfo.website} target="_blank" rel="noopener noreferrer">
                      <Button variant="outline" size="sm" className="text-xs text-[#FE4D01] border-[#FE4D01]/50 hover:bg-[#FE4D01]/10 h-8">
                        <Globe className="w-3.5 h-3.5 mr-1.5" />
                        Visiter
                      </Button>
                    </a>
                  </div>
                )}
              </div>

              <div className="space-y-3">
                {parentInfo.revenue && (
                  <div>
                    <label className="text-xs font-medium text-zinc-500 mb-1 block">Chiffre d'affaires</label>
                    <div className="flex items-center gap-2">
                      <DollarSign className="w-3.5 h-3.5 text-zinc-400 flex-shrink-0" />
                      <span className="text-sm text-zinc-900">{parentInfo.revenue}</span>
                    </div>
                  </div>
                )}

                {parentInfo.employees && (
                  <div>
                    <label className="text-xs font-medium text-zinc-500 mb-1 block">Effectifs</label>
                    <div className="flex items-center gap-2">
                      <Users className="w-3.5 h-3.5 text-zinc-400 flex-shrink-0" />
                      <span className="text-sm text-zinc-900">{parentInfo.employees}</span>
                    </div>
                  </div>
                )}

                {parentInfo.founded_year && (
                  <div>
                    <label className="text-xs font-medium text-zinc-500 mb-1 block">Année de création</label>
                    <div className="flex items-center gap-2">
                      <Calendar className="w-3.5 h-3.5 text-zinc-400 flex-shrink-0" />
                      <span className="text-sm text-zinc-900">{parentInfo.founded_year}</span>
                    </div>
                  </div>
                )}

                {parentInfo.sector && (
                  <div>
                    <label className="text-xs font-medium text-zinc-500 mb-1 block">Secteur</label>
                    <p className="text-sm text-zinc-900">{parentInfo.sector}</p>
                  </div>
                )}
              </div>
              <div className="space-y-3">
                {parentInfo.activities && parentInfo.activities.length > 0 && (
                  <div>
                    <label className="text-xs font-medium text-zinc-500 mb-1.5 block">Activités</label>
                    <div className="flex flex-wrap gap-1.5">
                      {parentInfo.activities.slice(0, 4).map((activity: string, index: number) => (
                        <Badge key={index} variant="outline" className="text-xs border-zinc-200 py-0.5 px-2">
                          {activity}
                        </Badge>
                      ))}
                      {parentInfo.activities.length > 4 && (
                        <Badge variant="outline" className="text-xs border-zinc-200 py-0.5 px-2">
                          +{parentInfo.activities.length - 4}
                        </Badge>
                      )}
                    </div>
                  </div>
                )}

                {parentInfo.sources && parentInfo.sources.length > 0 && (
                  <div>
                    <label className="text-xs font-medium text-zinc-500 mb-1.5 block">Sources vérifiées</label>
                    <div className="flex flex-wrap gap-1.5">
                      {parentInfo.sources.slice(0, 3).map((source: any, idx: number) => (
                        <a 
                          key={idx} 
                          href={source.url} 
                          target="_blank" 
                          rel="noopener noreferrer"
                          className="no-underline"
                        >
                          <Badge className={`text-xs py-0.5 px-2 ${getTierColor(source.tier || 'other')}`}>
                            {source.title || 'Source Enrichisseur'}
                          </Badge>
                        </a>
                      ))}
                      {parentInfo.sources.length > 3 && (
                        <Badge variant="outline" className="text-xs border-zinc-200 py-0.5 px-2">
                          +{parentInfo.sources.length - 3}
                        </Badge>
                      )}
                    </div>
                  </div>
                )}
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Detailed Entities (Filiales) */}
      {detailedEntities && detailedEntities.length > 0 && (
        <Card className="border-zinc-200">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Building2 className="w-5 h-5 text-[#FE4D01]" />
              Entités identifiées ({detailedEntities.length})
            </CardTitle>
            <CardDescription>
              Filiales et entités du groupe
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {detailedEntities.map((entity: any, index: number) => (
                <div
                  key={index}
                  className="p-4 rounded-lg border border-zinc-200 hover:border-[#FE4D01] transition-colors"
                >
                  <div className="flex flex-col">
                    {/* Header: Nom + Confiance */}
                    <div className="flex items-center gap-2 mb-3">
                      <h3 className="font-semibold text-zinc-900">{entity.legal_name}</h3>
                      {entity.confidence && (
                        <Badge
                          variant="outline"
                          className={`${getConfidenceColor(entity.confidence)} border-current`}
                        >
                          {Math.round(entity.confidence * 100)}% confiance
                        </Badge>
                      )}
                    </div>

                    {/* Informations alignées horizontalement */}
                    <div className="flex flex-wrap items-center gap-x-4 gap-y-2 mb-3">
                      {entity.country && (
                        <div className="flex items-center gap-1.5 text-sm text-zinc-600">
                          <MapPin className="w-4 h-4" />
                          <span>{entity.country}</span>
                        </div>
                      )}

                      {entity.website && (
                        <div className="flex items-center gap-1.5 text-sm text-zinc-600">
                          <Globe className="w-4 h-4" />
                          <a href={entity.website} target="_blank" rel="noopener noreferrer" className="text-[#FE4D01] hover:underline">
                            {entity.website}
                          </a>
                        </div>
                      )}

                      {entity.phone && (
                        <div className="flex items-center gap-1.5 text-sm text-zinc-600">
                          <Phone className="w-4 h-4" />
                          <span>{entity.phone}</span>
                        </div>
                      )}

                      {entity.email && (
                        <div className="flex items-center gap-1.5 text-sm text-zinc-600">
                          <Mail className="w-4 h-4" />
                          <a href={`mailto:${entity.email}`} className="text-[#FE4D01] hover:underline">
                            {entity.email}
                          </a>
                        </div>
                      )}

                      {entity.website && (
                        <a href={entity.website} target="_blank" rel="noopener noreferrer">
                          <Button variant="outline" size="sm" className="text-[#FE4D01] border-[#FE4D01]/50 hover:bg-[#FE4D01]/10 h-8">
                            <Globe className="w-3 h-3 mr-2" />
                            Site web
                          </Button>
                        </a>
                      )}
                    </div>

                    {/* Headquarters si disponible */}
                    {entity.headquarters && (
                      <div className="flex items-start gap-2 text-sm text-zinc-600 mb-3">
                        <MapPin className="w-4 h-4 mt-0.5" />
                        <div>
                          {entity.headquarters.line1 && <div>{entity.headquarters.line1}</div>}
                          <div>
                            {entity.headquarters.city && `${entity.headquarters.city}, `}
                            {entity.headquarters.country}
                          </div>
                        </div>
                      </div>
                    )}

                    {/* Activities si disponibles */}
                    {entity.activities && entity.activities.length > 0 && (
                      <div className="mb-3 flex flex-wrap gap-1">
                        {entity.activities.map((activity: string, actIndex: number) => (
                          <Badge key={actIndex} variant="outline" className="text-xs border-zinc-200">
                            {activity}
                          </Badge>
                        ))}
                      </div>
                    )}

                    {/* Entity Sources - Gardées en bas */}
                    {entity.sources && entity.sources.length > 0 && (
                      <div className="mt-3 pt-2 border-t border-zinc-100">
                        <div className="text-xs text-zinc-500 mb-1.5">Sources :</div>
                        <div className="flex flex-wrap gap-2">
                          {entity.sources.map((source: any, srcIndex: number) => (
                            <a 
                              key={srcIndex} 
                              href={source.url} 
                              target="_blank" 
                              rel="noopener noreferrer"
                              className="no-underline"
                            >
                              <Badge variant="secondary" className="hover:bg-zinc-200 cursor-pointer transition-colors flex items-center gap-1 py-0.5 px-1.5 text-xs font-normal text-zinc-600 bg-zinc-50 border-zinc-200">
                                <Globe className="w-2.5 h-2.5 text-zinc-400" />
                                <span className="truncate max-w-[150px]">{source.title || new URL(source.url).hostname}</span>
                              </Badge>
                            </a>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Metadata */}
      <Card className="border-zinc-200">
        <CardHeader>
          <CardTitle>Informations sur l'extraction</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
            <div>
              <span className="text-zinc-600">Session ID</span>
              <p className="font-mono text-zinc-900 mt-1 text-xs">{extraction.session_id}</p>
            </div>
            <div>
              <span className="text-zinc-600">Type d'extraction</span>
              <p className="text-zinc-900 mt-1 capitalize">{extraction.extraction_type}</p>
            </div>
            <div>
              <span className="text-zinc-600">Date de création</span>
              <p className="text-zinc-900 mt-1">{formatDate(extraction.created_at)}</p>
            </div>
            {extraction.completed_at && (
              <div>
                <span className="text-zinc-600">Date de complétion</span>
                <p className="text-zinc-900 mt-1">{formatDate(extraction.completed_at)}</p>
              </div>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

