"use client";

import { useState, useCallback } from "react";
import { motion } from "framer-motion";
import { toast } from "react-hot-toast";
import {
  AlertCircle,
  Download,
  Share2,
  RefreshCw,
  BarChart3,
} from "lucide-react";
import { CompanySearch } from "@/components/company/company-search";
import { CompanyOverview } from "@/components/company/company-overview";
import { SubsidiariesList } from "@/components/company/subsidiaries-list";
import { CompanyAnalytics } from "@/components/analytics/company-analytics";
import { LoadingState } from "@/components/ui/loading-spinner";
import { ErrorBoundary } from "@/components/ui/error-boundary";
import { ApiStatus } from "@/components/features/api-status";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { api, CompanyData } from "@/lib/api";

interface CompanyDashboardProps {
  initialData?: CompanyData;
}

export function CompanyDashboard({ initialData }: CompanyDashboardProps) {
  const [companyData, setCompanyData] = useState<CompanyData | null>(
    initialData || null
  );
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searchHistory, setSearchHistory] = useState<string[]>([]);

  const handleSearch = useCallback(async (query: string) => {
    setIsLoading(true);
    setError(null);

    try {
      // Déterminer si c'est une URL ou un nom d'entreprise
      const isUrl =
        query.startsWith("http://") ||
        query.startsWith("https://") ||
        query.includes("www.");

      let data: CompanyData;
      if (isUrl) {
        // Utiliser l'endpoint URL
        data = await api.extractFromURL({
          url: query,
          include_subsidiaries: true,
          max_subsidiaries: 50,
        });
      } else {
        // Utiliser l'endpoint nom d'entreprise
        data = await api.extractCompany({
          company_name: query,
          include_subsidiaries: true,
          max_subsidiaries: 50,
        });
      }
      setCompanyData(data);
      setSearchHistory((prev) => [query, ...prev.slice(0, 4)]);

      toast.success(`Analyse terminée pour ${data.company_name}`);
    } catch (err: unknown) {
      const errorMessage =
        err instanceof Error ? err.message : "Une erreur est survenue";
      setError(errorMessage);
      toast.error(`Erreur: ${errorMessage}`);
      console.error("Search error:", err);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const handleExportData = useCallback(() => {
    if (!companyData) return;

    const dataToExport = {
      ...companyData,
      exported_at: new Date().toISOString(),
      exported_by: "Company Analyzer Dashboard",
    };

    const blob = new Blob([JSON.stringify(dataToExport, null, 2)], {
      type: "application/json",
    });

    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${companyData.company_name.replace(
      /[^a-zA-Z0-9]/g,
      "_"
    )}_analysis.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);

    toast.success("Données exportées avec succès");
  }, [companyData]);

  const handleShare = useCallback(async () => {
    if (!companyData) return;

    const shareData = {
      title: `Analyse de ${companyData.company_name}`,
      text: `Découvrez l'analyse complète de ${companyData.company_name} - ${
        companyData.activities?.join(", ") || "N/A"
      }`,
      url: window.location.href,
    };

    try {
      if (navigator.share) {
        await navigator.share(shareData);
        toast.success("Partagé avec succès");
      } else {
        await navigator.clipboard.writeText(window.location.href);
        toast.success("Lien copié dans le presse-papiers");
      }
    } catch (err) {
      console.error("Share error:", err);
      toast.error("Erreur lors du partage");
    }
  }, [companyData]);

  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        staggerChildren: 0.2,
      },
    },
  };

  const itemVariants = {
    hidden: { opacity: 0, y: 20 },
    visible: { opacity: 1, y: 0 },
  };

  return (
    <ErrorBoundary>
      <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-purple-50">
        <ApiStatus />
        <div className="container mx-auto px-4 py-8">
          <motion.div
            variants={containerVariants}
            initial="hidden"
            animate="visible"
            className="space-y-8"
          >
            {/* Header */}
            <motion.div
              variants={itemVariants}
              className="text-center space-y-4"
            >
              <h1 className="text-4xl md:text-6xl font-bold gradient-text">
                Company Analyzer
              </h1>
              <p className="text-xl text-muted-foreground max-w-2xl mx-auto">
                Plateforme d&apos;analyse intelligente d&apos;entreprises
                utilisant l&apos;IA pour extraire des informations détaillées
                sur les sociétés et leurs filiales.
              </p>
            </motion.div>

            {/* Search */}
            <motion.div variants={itemVariants}>
              <CompanySearch onSearch={handleSearch} isLoading={isLoading} />
            </motion.div>

            {/* Search History */}
            {searchHistory.length > 0 && (
              <motion.div variants={itemVariants}>
                <Card>
                  <CardHeader>
                    <CardTitle className="text-lg">
                      Recherches récentes
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="flex flex-wrap gap-2">
                      {searchHistory.map((query, index) => (
                        <Badge
                          key={index}
                          variant="secondary"
                          className="cursor-pointer hover:bg-secondary/80"
                          onClick={() => handleSearch(query)}
                        >
                          {query}
                        </Badge>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              </motion.div>
            )}

            {/* Loading State */}
            {isLoading && (
              <motion.div variants={itemVariants}>
                <LoadingState message="Analyse en cours... Cela peut prendre quelques secondes." />
              </motion.div>
            )}

            {/* Error State */}
            {error && (
              <motion.div variants={itemVariants}>
                <Card className="border-red-200 bg-red-50">
                  <CardContent className="p-6">
                    <div className="flex items-center gap-3 text-red-800">
                      <AlertCircle className="w-6 h-6" />
                      <div>
                        <h3 className="font-semibold">Erreur d&apos;analyse</h3>
                        <p className="text-sm">{error}</p>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </motion.div>
            )}

            {/* Company Data */}
            {companyData && !isLoading && (
              <motion.div variants={itemVariants} className="space-y-8">
                {/* Action Bar */}
                <Card>
                  <CardContent className="p-4">
                    <div className="flex flex-wrap items-center justify-between gap-4">
                      <div className="flex items-center gap-2">
                        <BarChart3 className="w-5 h-5 text-blue-600" />
                        <span className="font-semibold">
                          Actions sur les données
                        </span>
                      </div>
                      <div className="flex flex-wrap gap-2">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleSearch(companyData.company_name)}
                          className="flex items-center gap-2"
                        >
                          <RefreshCw className="w-4 h-4" />
                          Actualiser
                        </Button>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={handleExportData}
                          className="flex items-center gap-2"
                        >
                          <Download className="w-4 h-4" />
                          Exporter
                        </Button>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={handleShare}
                          className="flex items-center gap-2"
                        >
                          <Share2 className="w-4 h-4" />
                          Partager
                        </Button>
                      </div>
                    </div>
                  </CardContent>
                </Card>

                {/* Company Overview */}
                <CompanyOverview company={companyData} />

                {/* Analytics */}
                <CompanyAnalytics company={companyData} />

                {/* Subsidiaries */}
                <SubsidiariesList
                  subsidiaries={companyData.subsidiaries_details}
                  totalCount={companyData.subsidiaries_details?.length || 0}
                />
              </motion.div>
            )}

            {/* Welcome State */}
            {!companyData && !isLoading && !error && (
              <motion.div variants={itemVariants}>
                <Card className="text-center py-16">
                  <CardContent>
                    <div className="space-y-6">
                      <div className="w-24 h-24 mx-auto bg-gradient-to-r from-blue-500 to-purple-500 rounded-full flex items-center justify-center">
                        <BarChart3 className="w-12 h-12 text-white" />
                      </div>
                      <div>
                        <CardTitle className="text-2xl mb-2">
                          Bienvenue dans Company Analyzer
                        </CardTitle>
                        <CardDescription className="text-lg max-w-md mx-auto">
                          Commencez votre analyse en recherchant une entreprise
                          par son nom ou en saisissant l&apos;URL de son site
                          web.
                        </CardDescription>
                      </div>
                      <div className="flex flex-wrap justify-center gap-4 text-sm text-muted-foreground">
                        <div className="flex items-center gap-2">
                          <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                          Analyse IA avancée
                        </div>
                        <div className="flex items-center gap-2">
                          <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
                          Données sur les filiales
                        </div>
                        <div className="flex items-center gap-2">
                          <div className="w-2 h-2 bg-purple-500 rounded-full"></div>
                          Export de données
                        </div>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </motion.div>
            )}
          </motion.div>
        </div>
      </div>
    </ErrorBoundary>
  );
}
