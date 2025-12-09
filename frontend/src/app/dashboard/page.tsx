'use client';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { 
  TrendingUp, 
  Search, 
  DollarSign, 
  Activity,
  ArrowRight,
  Building2
} from 'lucide-react';
import Link from 'next/link';
import { usePublicDashboardStats } from '@/hooks/use-public-extractions';
import { formatDate } from '@/lib/utils';

export default function DashboardPage() {
  const { stats, loading, error } = usePublicDashboardStats();

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="h-8 bg-zinc-200 rounded w-1/3 animate-pulse"></div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {[1, 2, 3, 4].map((i) => (
            <Card key={i} className="animate-pulse border-zinc-200">
              <CardHeader className="h-20 bg-zinc-100 rounded"></CardHeader>
              <CardContent className="h-16 bg-zinc-100 rounded mt-2"></CardContent>
            </Card>
          ))}
        </div>
      </div>
    );
  }

  if (error || !stats) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold text-zinc-900">Dashboard</h1>
          <p className="text-zinc-600 mt-2">
            Vue d'ensemble de votre activité
          </p>
        </div>
        <Card className="border-red-200 bg-red-50">
          <CardContent className="pt-6">
            <p className="text-red-600">Erreur de chargement: {error || 'Données non disponibles'}</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  const currentMonth = stats.current_month;
  const successRate = Math.round(stats.success_rate * 100);
  
  // Calculate change (mock for now, could be calculated from previous month)
  const stats_cards = [
    {
      title: 'Recherches ce mois',
      value: currentMonth.total_searches.toString(),
      change: '+12%', // TODO: Calculate from previous month
      icon: Search,
      color: 'text-[#FE4D01]',
      bgColor: 'bg-orange-50',
    },
    {
      title: 'Coût total',
      value: `${currentMonth.total_cost_eur.toFixed(2)}€`,
      change: '-8%', // TODO: Calculate from previous month
      icon: DollarSign,
      color: 'text-zinc-700',
      bgColor: 'bg-zinc-100',
    },
    {
      title: 'Entreprises analysées',
      value: currentMonth.completed_searches.toString(),
      change: `+${currentMonth.completed_searches}`,
      icon: Building2,
      color: 'text-zinc-700',
      bgColor: 'bg-zinc-100',
    },
    {
      title: 'Taux de réussite',
      value: `${successRate}%`,
      change: '+2%', // TODO: Calculate from previous month
      icon: TrendingUp,
      color: 'text-[#FE4D01]',
      bgColor: 'bg-orange-50',
    },
  ];

  const recentSearches = stats.recent_searches.map((search) => ({
    id: search.id,
    company: search.company_name,
    date: formatDate(new Date(search.created_at)),
    status: search.status === 'completed' ? 'Terminé' : 
            search.status === 'running' ? 'En cours' : 
            search.status === 'failed' ? 'Échoué' : 'En attente',
    cost: search.cost_eur ? `${search.cost_eur.toFixed(2)}€` : '-',
  }));

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-zinc-900">Dashboard</h1>
        <p className="text-zinc-600 mt-2">
          Vue d'ensemble de votre activité
        </p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {stats_cards.map((stat) => {
          const Icon = stat.icon;
          return (
            <Card key={stat.title} className="border-zinc-200">
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium text-zinc-600">
                  {stat.title}
                </CardTitle>
                <div className={`p-2 rounded-lg ${stat.bgColor}`}>
                  <Icon className={`w-4 h-4 ${stat.color}`} />
                </div>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-zinc-900">{stat.value}</div>
                <p className="text-xs text-zinc-500 mt-1">
                  <span className="text-[#FE4D01]">{stat.change}</span> vs mois dernier
                </p>
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* Quick Actions & Recent Searches */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Quick Actions */}
        <Card className="border-zinc-200">
          <CardHeader>
            <CardTitle>Actions rapides</CardTitle>
            <CardDescription>
              Démarrer une nouvelle analyse ou consulter vos données
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <Link href="/dashboard/analyses">
              <Button className="w-full justify-start my-3 bg-[#FE4D01] text-white hover:bg-[#FE4D01]/90 transition-colors shadow-md hover:shadow-lg" variant="default">
                <Search className="w-4 h-4 mr-2" />
                Nouvelle analyse
                <ArrowRight className="w-4 h-4 ml-auto" />
              </Button>
            </Link>
            <Link href="/dashboard/historique">
              <Button className="w-full justify-start my-3 hover:bg-[#FE4D01] hover:text-white hover:border-[#FE4D01] transition-colors" variant="outline">
                <Activity className="w-4 h-4 mr-2" />
                Voir l'historique
                <ArrowRight className="w-4 h-4 ml-auto" />
              </Button>
            </Link>
            <Link href="/dashboard/couts">
              <Button className="w-full justify-start my-3 hover:bg-[#FE4D01] hover:text-white hover:border-[#FE4D01] transition-colors" variant="outline">
                <DollarSign className="w-4 h-4 mr-2" />
                Analyser les coûts
                <ArrowRight className="w-4 h-4 ml-auto" />
              </Button>
            </Link>
          </CardContent>
        </Card>

        {/* Recent Searches */}
        <Card className="border-zinc-200">
          <CardHeader>
            <CardTitle>Recherches récentes</CardTitle>
            <CardDescription>
              Vos dernières analyses d'entreprises
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {recentSearches.length === 0 ? (
                <div className="text-center py-8 text-zinc-500">
                  <p>Aucune recherche récente</p>
                </div>
              ) : (
                recentSearches.map((search) => (
                  <div
                    key={search.id}
                    className="flex items-center justify-between p-3 rounded-lg border border-zinc-200 hover:bg-zinc-50 transition-colors"
                  >
                    <div className="flex-1">
                      <div className="font-medium">{search.company}</div>
                      <div className="text-sm text-zinc-600">{search.date}</div>
                    </div>
                    <div className="flex items-center gap-3">
                      <span className="text-sm font-medium">{search.cost}</span>
                      <span
                        className={`text-xs px-2 py-1 rounded-full ${
                          search.status === 'Terminé'
                            ? 'bg-orange-50 text-[#FE4D01]'
                            : search.status === 'En cours'
                            ? 'bg-blue-50 text-blue-700'
                            : search.status === 'Échoué'
                            ? 'bg-red-50 text-red-700'
                            : 'bg-zinc-100 text-zinc-700'
                        }`}
                      >
                        {search.status}
                      </span>
                    </div>
                  </div>
                ))
              )}
            </div>
            <Link href="/dashboard/historique">
              <Button variant="ghost" className="w-full mt-4">
                Voir tout l'historique
                <ArrowRight className="w-4 h-4 ml-2" />
              </Button>
            </Link>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

