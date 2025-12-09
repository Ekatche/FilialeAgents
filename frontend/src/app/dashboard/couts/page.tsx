'use client';

import { useState, useMemo } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import {
  DollarSign,
  TrendingUp,
  TrendingDown,
  Activity,
  Zap,
  BarChart3,
  Loader2
} from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, LineChart, Line, Legend } from 'recharts';
import { YearSelector } from '@/components/dashboard/YearSelector';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import {
  useCurrentMonthCosts,
  useYearlyCosts,
  useTopExpensiveSearches
} from '@/hooks/use-portal-costs';

export default function CoutsPage() {
  const currentYear = new Date().getFullYear();

  // Available years (from 2023 to current year)
  const availableYears = Array.from(
    { length: currentYear - 2022 },
    (_, i) => currentYear - i
  );

  const [selectedYears, setSelectedYears] = useState<number[]>([currentYear]);
  const [activeTab, setActiveTab] = useState<'timeline' | 'stacked'>('timeline');

  // Fetch data from API
  const { stats: currentMonthStats, loading: currentMonthLoading } = useCurrentMonthCosts();
  const { monthlyData, loading: yearlyLoading } = useYearlyCosts(selectedYears);
  const { searches: topExpensive, loading: topExpensiveLoading } = useTopExpensiveSearches(5);

  // Transform monthly data for charts
  const chartData = useMemo(() => {
    return selectedYears.flatMap((year) => {
      const yearData = monthlyData[year] || [];
      return yearData.map((item) => ({
        month: `${item.month_name} ${year}`,
        cost: item.total_cost_eur,
        searches: item.completed_searches,
        year,
      }));
    });
  }, [selectedYears, monthlyData]);

  // Line chart data (for comparing multiple years)
  const monthNames = [
    'Jan', 'Fév', 'Mar', 'Avr', 'Mai', 'Juin',
    'Juil', 'Août', 'Sep', 'Oct', 'Nov', 'Déc'
  ];

  const lineChartData = useMemo(() => {
    return monthNames.map((monthShort, index) => {
      const dataPoint: Record<string, string | number> = { month: monthShort };

      selectedYears.forEach((year) => {
        const yearData = monthlyData[year] || [];
        const monthItem = yearData.find((item) => item.month === index + 1);
        dataPoint[`cost_${year}`] = monthItem?.total_cost_eur || 0;
      });

      return dataPoint;
    });
  }, [selectedYears, monthlyData, monthNames]);

  // Stacked chart data
  const monthNamesFull = [
    'Janvier', 'Février', 'Mars', 'Avril', 'Mai', 'Juin',
    'Juillet', 'Août', 'Septembre', 'Octobre', 'Novembre', 'Décembre'
  ];

  const stackedChartData = useMemo(() => {
    return monthNamesFull.map((monthName, index) => {
      const monthData = selectedYears.map((year) => {
        const yearData = monthlyData[year] || [];
        const monthItem = yearData.find((item) => item.month === index + 1);
        return {
          year,
          cost: monthItem?.total_cost_eur || 0,
          searches: monthItem?.completed_searches || 0,
        };
      });

      const totalCost = monthData.reduce((sum, item) => sum + item.cost, 0);
      const totalSearches = monthData.reduce((sum, item) => sum + item.searches, 0);

      return {
        month: monthName,
        totalCost,
        totalSearches,
        ...monthData.reduce((acc, item) => {
          acc[`cost_${item.year}`] = item.cost;
          acc[`searches_${item.year}`] = item.searches;
          return acc;
        }, {} as Record<string, number>),
      };
    });
  }, [selectedYears, monthlyData, monthNamesFull]);

  // Colors for each year
  const yearColors = [
    '#FE4D01', // Orange principal
    '#3B82F6', // Bleu
    '#10B981', // Vert
    '#8B5CF6', // Violet
    '#F59E0B', // Jaune/Orange
    '#EF4444', // Rouge
  ];

  // Loading state
  if (currentMonthLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Loader2 className="w-8 h-8 animate-spin text-[#FE4D01]" />
      </div>
    );
  }

  // Calculate monthly trend (comparing to previous month)
  const monthlyTrend = 0; // TODO: Calculate from previous month data

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-zinc-900">Coûts & Requêtes API</h1>
        <p className="text-zinc-600 mt-2">
          Analyse détaillée de vos coûts et utilisation de l'API
        </p>
      </div>

      {/* Overall Stats (Current Month) */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Coût total (mois actuel)</CardTitle>
            <DollarSign className="w-4 h-4 text-zinc-400" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {currentMonthStats?.total_cost_eur.toFixed(2) || '0.00'}€
            </div>
            <p className="text-xs text-zinc-500 mt-1">
              ${currentMonthStats?.total_cost_usd.toFixed(2) || '0.00'} USD
            </p>
            {monthlyTrend !== 0 && (
              <div className="flex items-center gap-1 mt-2">
                {monthlyTrend > 0 ? (
                  <TrendingUp className="w-3 h-3 text-green-600" />
                ) : (
                  <TrendingDown className="w-3 h-3 text-red-600" />
                )}
                <span className={`text-xs ${monthlyTrend > 0 ? 'text-[#FE4D01]' : 'text-red-600'}`}>
                  {Math.abs(monthlyTrend)}% vs mois dernier
                </span>
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Recherches</CardTitle>
            <Activity className="w-4 h-4 text-zinc-400" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {currentMonthStats?.completed_searches || 0}
            </div>
            <p className="text-xs text-zinc-500 mt-1">
              sur {currentMonthStats?.total_searches || 0} lancées
            </p>
            {currentMonthStats && currentMonthStats.total_searches > 0 && (
              <div className="text-xs text-[#FE4D01] mt-2">
                {((currentMonthStats.completed_searches / currentMonthStats.total_searches) * 100).toFixed(0)}% de réussite
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Coût moyen</CardTitle>
            <BarChart3 className="w-4 h-4 text-zinc-400" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {currentMonthStats?.average_cost_per_search_eur.toFixed(2) || '0.00'}€
            </div>
            <p className="text-xs text-zinc-500 mt-1">
              par recherche
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Tokens</CardTitle>
            <Zap className="w-4 h-4 text-zinc-400" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {currentMonthStats
                ? (currentMonthStats.total_tokens / 1000000).toFixed(2)
                : '0.00'}M
            </div>
            <p className="text-xs text-zinc-500 mt-1">
              {currentMonthStats?.total_tokens.toLocaleString('fr-FR') || '0'} tokens
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Monthly Costs Charts with Tabs */}
      <Card className="border-zinc-200">
        <CardHeader>
          <div className="flex items-center justify-between flex-wrap gap-4">
            <div>
              <CardTitle className="flex items-center gap-2">
                <BarChart3 className="w-5 h-5 text-[#FE4D01]" />
                Coûts mensuels
              </CardTitle>
              <CardDescription>
                Visualisez vos coûts par mois selon différentes vues
              </CardDescription>
            </div>
            {/* Year Filter */}
            <div className="flex items-center gap-3">
              <label className="text-sm font-medium text-zinc-600">Année(s):</label>
              <YearSelector
                availableYears={availableYears}
                selectedYears={selectedYears}
                onYearsChange={setSelectedYears}
              />
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {yearlyLoading ? (
            <div className="flex items-center justify-center h-[400px]">
              <Loader2 className="w-8 h-8 animate-spin text-[#FE4D01]" />
            </div>
          ) : (
            <Tabs value={activeTab} onValueChange={(value) => setActiveTab(value as 'timeline' | 'stacked')}>
              <TabsList>
                <TabsTrigger value="timeline">Évolution temporelle</TabsTrigger>
                <TabsTrigger value="stacked">Agrégation mensuelle</TabsTrigger>
              </TabsList>

              {/* Timeline Chart */}
              <TabsContent value="timeline">
                <ResponsiveContainer width="100%" height={selectedYears.length > 1 ? 400 : 350}>
                  {selectedYears.length > 1 ? (
                    // Line chart for comparing multiple years
                    <LineChart data={lineChartData} margin={{ top: 20, right: 30, left: 20, bottom: 60 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                      <XAxis
                        dataKey="month"
                        stroke="#6b7280"
                        fontSize={12}
                        tickLine={false}
                        axisLine={false}
                      />
                      <YAxis
                        stroke="#6b7280"
                        fontSize={12}
                        tickLine={false}
                        axisLine={false}
                        tickFormatter={(value) => `${value}€`}
                      />
                      <Tooltip
                        contentStyle={{
                          backgroundColor: 'white',
                          border: '1px solid #e5e7eb',
                          borderRadius: '8px',
                          boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)',
                        }}
                        formatter={(value: number, name: string) => {
                          const year = name.replace('cost_', '');
                          return [`${value.toFixed(2)}€`, `Année ${year}`];
                        }}
                        labelStyle={{ color: '#374151', fontWeight: 600 }}
                      />
                      <Legend
                        wrapperStyle={{ paddingTop: '20px' }}
                        iconType="line"
                        formatter={(value: string) => value.replace('cost_', '')}
                      />
                      {selectedYears.map((year, index) => (
                        <Line
                          key={year}
                          type="monotone"
                          dataKey={`cost_${year}`}
                          stroke={yearColors[index % yearColors.length]}
                          strokeWidth={3}
                          dot={{ r: 4, fill: yearColors[index % yearColors.length] }}
                          activeDot={{ r: 6 }}
                          name={`${year}`}
                        />
                      ))}
                    </LineChart>
                  ) : (
                    // Bar chart for single year
                    <BarChart data={chartData} margin={{ top: 20, right: 30, left: 20, bottom: 60 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                      <XAxis
                        dataKey="month"
                        stroke="#6b7280"
                        fontSize={12}
                        tickLine={false}
                        axisLine={false}
                        angle={-45}
                        textAnchor="end"
                        height={80}
                      />
                      <YAxis
                        stroke="#6b7280"
                        fontSize={12}
                        tickLine={false}
                        axisLine={false}
                        tickFormatter={(value) => `${value}€`}
                      />
                      <Tooltip
                        contentStyle={{
                          backgroundColor: 'white',
                          border: '1px solid #e5e7eb',
                          borderRadius: '8px',
                          boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)',
                        }}
                        formatter={(value: number) => [`${value.toFixed(2)}€`, 'Coût total']}
                        labelStyle={{ color: '#374151', fontWeight: 600 }}
                      />
                      <Bar
                        dataKey="cost"
                        fill="#FE4D01"
                        radius={[8, 8, 0, 0]}
                        name="Coût total"
                      />
                    </BarChart>
                  )}
                </ResponsiveContainer>
                <div className="mt-4 pt-4 border-t border-zinc-200">
                  <div className="grid grid-cols-3 gap-4 text-center">
                    <div>
                      <div className="text-sm text-zinc-600">
                        Total {selectedYears.length === 1 ? selectedYears[0] : `${selectedYears.length} années`}
                      </div>
                      <div className="text-lg font-bold text-zinc-900">
                        {chartData.reduce((sum, item) => sum + item.cost, 0).toFixed(2)}€
                      </div>
                    </div>
                    <div>
                      <div className="text-sm text-zinc-600">Moyenne mensuelle</div>
                      <div className="text-lg font-bold text-zinc-900">
                        {chartData.length > 0
                          ? (chartData.reduce((sum, item) => sum + item.cost, 0) / chartData.length).toFixed(2)
                          : '0.00'}€
                      </div>
                    </div>
                    <div>
                      <div className="text-sm text-zinc-600">Total recherches</div>
                      <div className="text-lg font-bold text-zinc-900">
                        {chartData.reduce((sum, item) => sum + item.searches, 0)}
                      </div>
                    </div>
                  </div>
                </div>
              </TabsContent>

              {/* Stacked Chart */}
              <TabsContent value="stacked">
                <ResponsiveContainer width="100%" height={350}>
                  <BarChart data={stackedChartData} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                    <XAxis
                      dataKey="month"
                      stroke="#6b7280"
                      fontSize={12}
                      tickLine={false}
                      axisLine={false}
                      angle={-45}
                      textAnchor="end"
                      height={80}
                    />
                    <YAxis
                      stroke="#6b7280"
                      fontSize={12}
                      tickLine={false}
                      axisLine={false}
                      tickFormatter={(value) => `${value}€`}
                    />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: 'white',
                        border: '1px solid #e5e7eb',
                        borderRadius: '8px',
                        boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)',
                      }}
                      formatter={(value: number, name: string) => {
                        if (name.startsWith('cost_')) {
                          return [`${value.toFixed(2)}€`, `Coût ${name.replace('cost_', '')}`];
                        }
                        return [value, name];
                      }}
                      labelStyle={{ color: '#374151', fontWeight: 600 }}
                    />
                    {selectedYears.map((year, index) => (
                      <Bar
                        key={year}
                        dataKey={`cost_${year}`}
                        stackId="cost"
                        fill={yearColors[index % yearColors.length]}
                        name={`${year}`}
                        radius={index === selectedYears.length - 1 ? [8, 8, 0, 0] : [0, 0, 0, 0]}
                      />
                    ))}
                  </BarChart>
                </ResponsiveContainer>
                <div className="mt-4 pt-4 border-t border-zinc-200">
                  <div className="grid grid-cols-3 gap-4 text-center">
                    <div>
                      <div className="text-sm text-zinc-600">
                        Total agrégé
                      </div>
                      <div className="text-lg font-bold text-zinc-900">
                        {stackedChartData.reduce((sum, item) => sum + item.totalCost, 0).toFixed(2)}€
                      </div>
                    </div>
                    <div>
                      <div className="text-sm text-zinc-600">Moyenne mensuelle</div>
                      <div className="text-lg font-bold text-zinc-900">
                        {stackedChartData.length > 0
                          ? (stackedChartData.reduce((sum, item) => sum + item.totalCost, 0) / stackedChartData.length).toFixed(2)
                          : '0.00'}€
                      </div>
                    </div>
                    <div>
                      <div className="text-sm text-zinc-600">Total recherches</div>
                      <div className="text-lg font-bold text-zinc-900">
                        {stackedChartData.reduce((sum, item) => sum + item.totalSearches, 0)}
                      </div>
                    </div>
                  </div>
                </div>
              </TabsContent>
            </Tabs>
          )}
        </CardContent>
      </Card>

      {/* Top Expensive Searches */}
      <Card>
        <CardHeader>
          <CardTitle>Top 5 Recherches Coûteuses</CardTitle>
          <CardDescription>
            Les recherches qui ont consommé le plus de tokens
          </CardDescription>
        </CardHeader>
        <CardContent>
          {topExpensiveLoading ? (
            <div className="flex items-center justify-center h-[200px]">
              <Loader2 className="w-6 h-6 animate-spin text-[#FE4D01]" />
            </div>
          ) : topExpensive.length === 0 ? (
            <div className="text-center py-8 text-zinc-500">
              Aucune recherche effectuée pour le moment
            </div>
          ) : (
            <div className="space-y-3">
              {topExpensive.map((search, index) => (
                <div
                  key={search.id}
                  className="flex items-center justify-between p-3 rounded-lg border border-zinc-200 hover:bg-zinc-50 transition-colors"
                >
                  <div className="flex items-center gap-3">
                    <div className={`w-8 h-8 rounded-full flex items-center justify-center font-bold text-sm ${
                      index === 0 ? 'bg-[#FE4D01] text-white' :
                      index === 1 ? 'bg-zinc-300 text-zinc-700' :
                      index === 2 ? 'bg-orange-200 text-[#FE4D01]' :
                      'bg-zinc-100 text-zinc-600'
                    }`}>
                      {index + 1}
                    </div>
                    <div>
                      <div className="font-medium">{search.company_name}</div>
                      <div className="text-xs text-zinc-500">
                        {(search.total_tokens / 1000).toFixed(0)}K tokens
                        {search.subsidiaries_count > 0 && ` • ${search.subsidiaries_count} filiales`}
                      </div>
                    </div>
                  </div>
                  <div className="text-lg font-bold text-[#FE4D01]">
                    {search.cost_eur.toFixed(2)}€
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
