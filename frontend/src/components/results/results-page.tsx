"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { motion } from "framer-motion";
import { toast } from "react-hot-toast";
import {
  ArrowLeft,
  Download,
  Share2,
  RefreshCw,
  Search,
  AlertCircle,
} from "lucide-react";
import { LoadingState } from "@/components/ui/loading-spinner";
import { ErrorBoundary } from "@/components/ui/error-boundary";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { api, CompanyData, SubsidiaryDetail } from "@/lib/api";
import { DebugWrapper } from "@/components/debug/debug-wrapper";
import { CompanyOverview } from "@/components/company/company-overview";
import dynamic from "next/dynamic";

const SubsidiariesVisualization = dynamic(
  () =>
    import("@/components/company/subsidiaries-visualization").then(
      (mod) => mod.SubsidiariesVisualization
    ),
  {
    ssr: false,
    loading: () => (
      <LoadingState message="Chargement de la visualisation des filiales" />
    ),
  }
);

const SubsidiariesList = dynamic(
  () =>
    import("@/components/company/subsidiaries-list").then(
      (mod) => mod.SubsidiariesList
    ),
  {
    ssr: false,
    loading: () => <LoadingState message="Chargement des filiales" />,
  }
);

const SubsidiariesNavbar = dynamic(
  () =>
    import("@/components/navigation/subsidiaries-navbar").then(
      (mod) => mod.SubsidiariesNavbar
    ),
  {
    ssr: false,
    loading: () => null,
  }
);

const SubsidiaryDetailPanel = dynamic(
  () =>
    import("@/components/company/subsidiary-detail-panel").then(
      (mod) => mod.SubsidiaryDetailPanel
    ),
  {
    ssr: false,
    loading: () => <LoadingState message="Chargement des détails..." />,
  }
);

// Fonction utilitaire pour vérifier si companyData a des filiales
const hasSubsidiaries = (data: CompanyData | null): boolean => {
  if (!data) {
    return false;
  }
  const result =
    Array.isArray(data.subsidiaries_details) &&
    data.subsidiaries_details.length > 0;
  return result;
};

interface ResultsPageProps {
  initialData?: CompanyData;
}

const AgentProgressWrapper = dynamic(
  () =>
    import("@/components/ui/agent-progress").then((mod) => mod.AgentProgress),
  {
    ssr: false,
    loading: () => (
      <div className="space-y-6">
        <LoadingState message="Connexion au suivi temps réel" />
      </div>
    ),
  }
);

export function ResultsPage({ initialData }: ResultsPageProps) {
  const [companyData, setCompanyData] = useState<CompanyData | null>(
    initialData || null
  );
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [showAgentStatus, setShowAgentStatus] = useState(false);
  const [notificationShown, setNotificationShown] = useState(false);
  const [selectedSubsidiary, setSelectedSubsidiary] =
    useState<SubsidiaryDetail | null>(null);

  const router = useRouter();
  const searchParams = useSearchParams();

  // Gérer le cas où searchParams pourrait être null
  const query = searchParams?.get("query") || null;

  // Debug logs simplifiés (déplacé hors du render pour éviter les re-renders)
  useEffect(() => {
    console.log(
      "🎨 [DEBUG] Rendu - sessionId:",
      sessionId,
      "showAgentStatus:",
      showAgentStatus
    );
  }, [sessionId, showAgentStatus]);

  // TOUS LES HOOKS DOIVENT ÊTRE APPELÉS AVANT TOUT RETURN CONDITIONNEL
  const handleSearch = useCallback(async () => {
    if (!query) {
      setError("Aucune requête de recherche fournie");
      return Promise.resolve();
    }

    setIsLoading(true);
    setError(null);
    setNotificationShown(false);

    try {
      // Déterminer si c'est une URL ou un nom d'entreprise
      const isUrl =
        query.startsWith("http://") ||
        query.startsWith("https://") ||
        query.includes("www.");

      // 1. Démarrer l'extraction asynchrone
      let response;
      if (isUrl) {
        response = await api.startExtractionFromURLAsync({
          url: query,
          include_subsidiaries: true,
          max_subsidiaries: 50,
        });
      } else {
        response = await api.startExtractionAsync({
          company_name: query,
          include_subsidiaries: true,
          max_subsidiaries: 50,
        });
      }

      // 2. Activer l'affichage du tracking avec le vrai session_id
      setSessionId(response.session_id);
      setShowAgentStatus(true);
      setIsLoading(false);

      // 3. Le reste se passe via les callbacks de AgentProgress
      // - handleExtractionComplete() sera appelé quand c'est terminé
      // - handleExtractionError() sera appelé en cas d'erreur
    } catch (err) {
      let userFriendlyMessage =
        "Une erreur est survenue lors du démarrage de l'extraction";

      if (err instanceof Error) {
        if (
          err.message.includes("ERR_NETWORK_IO_SUSPENDED") ||
          err.message.includes("Network Error")
        ) {
          userFriendlyMessage =
            "Erreur réseau. Veuillez vérifier votre connexion.";
        } else if (err.message.includes("timeout")) {
          userFriendlyMessage = "Timeout. Le serveur ne répond pas.";
        }
      }

      setError(userFriendlyMessage);
      toast.error(`Erreur: ${userFriendlyMessage}`);
      setIsLoading(false);
      setShowAgentStatus(false);
    }
  }, [query]);

  // Callback appelé quand l'extraction est terminée
  const handleExtractionComplete = useCallback(async () => {
    if (!sessionId) {
      return;
    }

    try {
      // Récupérer les données finales d'extraction
      const extractionData = await api.getExtractionResults(sessionId);

      // Définir les données d'entreprise
      if (extractionData) {
        setCompanyData(extractionData);

        // Notification unique de fin
        if (!notificationShown) {
          toast.success(`Analyse terminée pour ${extractionData.company_name}`);
          setNotificationShown(true);
        }

        setIsLoading(false);

        // Masquer les agents après quelques secondes pour montrer les résultats
        setTimeout(() => {
          setShowAgentStatus(false);
        }, 3000);
      }
    } catch (err) {
      console.error(
        "❌ [DEBUG] Erreur lors de la récupération des données finales:",
        err
      );
      setIsLoading(false);
    }
  }, [sessionId, notificationShown]);

  // Callback appelé en cas d'erreur
  const handleExtractionError = useCallback((error: string) => {
    setError(error);
    setIsLoading(false);
    toast.error(`Erreur: ${error}`);
  }, []);

  // --- Polling fallback (si WS indisponible/retardé) ---
  const [isPolling, setIsPolling] = useState(false);
  const pollTimeoutRef = useRef<number | null>(null);
  const pollBackoffRef = useRef<number>(2000); // 2s -> 4s -> 8s ... cap à ~30s

  const clearTimeoutCompat = useCallback((id: number | null) => {
    if (typeof globalThis !== "undefined" && id !== null) {
      clearTimeout(id);
    }
  }, []);

  const setTimeoutCompat = useCallback(
    (callback: () => void, delay: number): number | null =>
      typeof globalThis !== "undefined"
        ? Number(setTimeout(callback, delay))
        : null,
    []
  );

  const stopPolling = useCallback(() => {
    if (pollTimeoutRef.current !== null) {
      clearTimeoutCompat(pollTimeoutRef.current);
      pollTimeoutRef.current = null;
    }
    setIsPolling(false);
    pollBackoffRef.current = 2000;
  }, [clearTimeoutCompat]);

  const pollOnce = useCallback(async () => {
    if (!sessionId) return;
    try {
      const status = await api.getSessionStatus(sessionId);
      // overall_status: initializing | running | completed | error
      if (status?.overall_status === "completed") {
        stopPolling();
        await handleExtractionComplete();
        return;
      }
      if (status?.overall_status === "error") {
        stopPolling();
        handleExtractionError(
          status?.agents?.find?.((a) => a.status === "error")?.error_message ||
            "Erreur d'extraction"
        );
        return;
      }
    } catch (e) {
      console.warn("🔎 [POLL] échec status:", e);
      // on continue avec backoff
    }
    // replanifier avec backoff exponentiel (cap 30s)
    const nextDelay = Math.min(pollBackoffRef.current * 2, 30000);
    pollBackoffRef.current = nextDelay;
    pollTimeoutRef.current = setTimeoutCompat(pollOnce, nextDelay);
  }, [
    sessionId,
    handleExtractionComplete,
    handleExtractionError,
    stopPolling,
    setTimeoutCompat,
  ]);

  const startPolling = useCallback(() => {
    if (isPolling || !sessionId) return;
    setIsPolling(true);
    pollBackoffRef.current = 2000;
    // premier tick rapide
    pollTimeoutRef.current = setTimeoutCompat(pollOnce, 1000);
  }, [isPolling, sessionId, pollOnce, setTimeoutCompat]);

  useEffect(() => {
    // Quand on démarre une session, armer un fallback si WS ne donne pas de nouvelles sous 12s
    if (sessionId && showAgentStatus) {
      if (pollTimeoutRef.current !== null) {
        clearTimeoutCompat(pollTimeoutRef.current);
        pollTimeoutRef.current = null;
      }
      pollTimeoutRef.current = setTimeoutCompat(() => {
        if (!isPolling) {
          console.log("📡 [POLL] Démarrage du polling fallback");
          startPolling();
        }
      }, 12000);
    }
    return () => {
      if (pollTimeoutRef.current !== null) {
        clearTimeoutCompat(pollTimeoutRef.current);
        pollTimeoutRef.current = null;
      }
    };
  }, [
    sessionId,
    showAgentStatus,
    isPolling,
    startPolling,
    setTimeoutCompat,
    clearTimeoutCompat,
  ]);

  useEffect(() => {
    // Vérifier que les paramètres sont prêts avant de faire la recherche
    if (query && !initialData && !companyData) {
      handleSearch().catch((error) => {
        console.error("Erreur lors de la recherche automatique:", error);
      });
    }
  }, [query, initialData, companyData, handleSearch]);

  const handleExportData = async () => {
    if (!companyData?.company_name) return;

    if (typeof window === "undefined") {
      console.warn("Export ignoré côté serveur");
      return;
    }

    try {
      const dataStr = JSON.stringify(companyData, null, 2);
      const dataUri =
        "data:application/json;charset=utf-8," + encodeURIComponent(dataStr);

      const exportFileDefaultName = `${(companyData?.company_name || "company")
        .replace(/[^a-z0-9]/gi, "_")
        .toLowerCase()}_analysis.json`;

      const linkElement = document.createElement("a");
      linkElement.setAttribute("href", dataUri);
      linkElement.setAttribute("download", exportFileDefaultName);
      linkElement.click();

      toast.success("Données exportées avec succès");
    } catch {
      toast.error("Erreur lors de l&apos;export");
    }
  };

  const getCurrentUrl = () => {
    if (typeof window === "undefined") {
      return "";
    }
    return window.location.href ?? "";
  };

  const canShare = () =>
    typeof navigator !== "undefined" && typeof navigator.share === "function";

  const handleShare = async () => {
    try {
      const currentUrl = getCurrentUrl();

      if (!currentUrl) {
        toast.error("URL indisponible");
        return;
      }

      if (canShare() && companyData?.company_name) {
        await navigator.share({
          title: `Analyse de ${companyData?.company_name || "l'entreprise"}`,
          text: `Découvrez l'analyse complète de ${
            companyData?.company_name || "cette entreprise"
          } et ses ${companyData?.subsidiaries_details?.length || 0} filiales.`,
          url: currentUrl,
        });
        return;
      }

      if (
        typeof navigator !== "undefined" &&
        navigator.clipboard &&
        typeof navigator.clipboard.writeText === "function"
      ) {
        await navigator.clipboard.writeText(currentUrl);
        toast.success("Lien copié dans le presse-papiers");
        return;
      }

      toast.error("Partage non supporté sur cet appareil");
    } catch {
      toast.error("Erreur lors du partage");
    }
  };

  const handleSubsidiarySelect = useCallback((subsidiary: SubsidiaryDetail) => {
    setSelectedSubsidiary(subsidiary);
  }, []);

  const handleNewSearch = () => {
    router.push("/");
  };

  const fadeInUp = {
    hidden: { opacity: 0, y: 20 },
    visible: {
      opacity: 1,
      y: 0,
      transition: { duration: 0.5, ease: [0.25, 0.25, 0, 1] },
    },
  };

  if (isLoading || showAgentStatus) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-purple-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="space-y-8"
          >
            <div className="text-center">
              <Button
                variant="ghost"
                onClick={handleNewSearch}
                className="mb-8"
              >
                <ArrowLeft className="w-4 h-4 mr-2" />
                Nouvelle recherche
              </Button>

              <div className="max-w-2xl mx-auto text-center space-y-4 mb-8">
                <h2 className="text-2xl font-semibold text-gray-900">
                  Recherche : {query}
                </h2>
                <p className="text-gray-600">
                  Nos agents IA travaillent pour analyser l&apos;entreprise et
                  ses filiales...
                </p>
              </div>
            </div>

            {/* Affichage du tracking en temps réel avec AgentProgress */}
            {sessionId && showAgentStatus ? (
              <div className="space-y-6">
                <AgentProgressWrapper
                  sessionId={sessionId}
                  onComplete={handleExtractionComplete}
                  onError={handleExtractionError}
                />
              </div>
            ) : (
              <div className="space-y-6">
                <LoadingState message={`Initialisation de l'analyse...`} />
              </div>
            )}
          </motion.div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-purple-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="text-center space-y-6"
          >
            <Button variant="ghost" onClick={handleNewSearch} className="mb-8">
              <ArrowLeft className="w-4 h-4 mr-2" />
              Nouvelle recherche
            </Button>

            <Card className="max-w-2xl mx-auto border-red-200 bg-red-50">
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-red-700">
                  <AlertCircle className="w-5 h-5" />
                  Erreur lors de l&apos;analyse
                </CardTitle>
              </CardHeader>
              <CardContent className="text-center space-y-4">
                <p className="text-red-600">{error}</p>
                <div className="flex gap-4 justify-center">
                  <Button onClick={handleSearch} variant="outline">
                    <RefreshCw className="w-4 h-4 mr-2" />
                    Réessayer
                  </Button>
                  <Button onClick={handleNewSearch}>
                    <Search className="w-4 h-4 mr-2" />
                    Nouvelle recherche
                  </Button>
                </div>
              </CardContent>
            </Card>
          </motion.div>
        </div>
      </div>
    );
  }

  if (!companyData) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-purple-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="text-center"
          >
            <Button variant="ghost" onClick={handleNewSearch} className="mb-8">
              <ArrowLeft className="w-4 h-4 mr-2" />
              Nouvelle recherche
            </Button>
            <p className="text-gray-600">Aucune donnée à afficher</p>
          </motion.div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-purple-50">
      {/* Navigation des filiales */}
      {hasSubsidiaries(companyData) && companyData?.company_name && (
        <div className="sticky top-0 z-50 bg-white/95 backdrop-blur-sm border-b border-gray-200 shadow-sm">
          <SubsidiariesNavbar
            subsidiaries={companyData?.subsidiaries_details || []}
            companyName={companyData?.company_name}
            onSubsidiarySelect={handleSubsidiarySelect}
          />
        </div>
      )}

      <div
        className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8"
        style={{ paddingTop: hasSubsidiaries(companyData) ? "140px" : "32px" }}
      >
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="space-y-8"
        >
          {/* Header avec actions */}
          <motion.div
            variants={fadeInUp}
            initial="hidden"
            animate="visible"
            className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-6 border-b border-white/20"
          >
            <div className="flex items-center gap-4">
              <Button
                variant="ghost"
                onClick={handleNewSearch}
                className="flex-shrink-0"
              >
                <ArrowLeft className="w-4 h-4 mr-2" />
                Nouvelle recherche
              </Button>

              <div className="flex items-center gap-2 flex-wrap">
                <Badge variant="default" className="text-xs">
                  Haute confiance
                </Badge>

                {companyData?.extraction_metadata?.processing_time && (
                  <Badge variant="outline" className="text-xs">
                    {(
                      companyData.extraction_metadata.processing_time / 1000
                    ).toFixed(1)}
                    s
                  </Badge>
                )}
              </div>
            </div>

            <div className="flex items-center gap-2">
              <Button onClick={handleShare} variant="outline" size="sm">
                <Share2 className="w-4 h-4 mr-2" />
                Partager
              </Button>

              <Button onClick={handleExportData} variant="outline" size="sm">
                <Download className="w-4 h-4 mr-2" />
                Exporter
              </Button>

              <Button onClick={handleSearch} variant="outline" size="sm">
                <RefreshCw className="w-4 h-4 mr-2" />
                Actualiser
              </Button>
            </div>
          </motion.div>

          {/* Contenu des résultats */}
          <ErrorBoundary>
            <div className="space-y-8">
              {/* Informations générales de l'entreprise */}
              <motion.div
                variants={fadeInUp}
                initial="hidden"
                animate="visible"
                transition={{ delay: 0.08 }}
              >
                <DebugWrapper name="CompanyOverview">
                  <CompanyOverview company={companyData} />
                </DebugWrapper>
              </motion.div>

              {/* Cartographie dynamique avec panneau de détails */}
              {hasSubsidiaries(companyData) && (
                <motion.div
                  variants={fadeInUp}
                  initial="hidden"
                  animate="visible"
                  transition={{ delay: 0.12 }}
                  className="grid grid-cols-1 lg:grid-cols-4 gap-6"
                >
                  {/* Panneau de détails de la filiale sélectionnée - Colonne gauche */}
                  <div className="lg:col-span-1">
                    <DebugWrapper name="SubsidiaryDetailPanel">
                      <SubsidiaryDetailPanel
                        subsidiary={selectedSubsidiary}
                        onClose={() => setSelectedSubsidiary(null)}
                      />
                    </DebugWrapper>
                  </div>

                  {/* Cartographie dynamique - Colonne droite */}
                  <div className="lg:col-span-3">
                    <DebugWrapper name="SubsidiariesVisualization">
                      <SubsidiariesVisualization
                        subsidiaries={companyData?.subsidiaries_details ?? []}
                        highlightedSubsidiary={selectedSubsidiary}
                        onSubsidiarySelect={setSelectedSubsidiary}
                      />
                    </DebugWrapper>
                  </div>
                </motion.div>
              )}

              {/* Liste détaillée des filiales - En dessous */}
              {hasSubsidiaries(companyData) && (
                <motion.div
                  variants={fadeInUp}
                  initial="hidden"
                  animate="visible"
                  transition={{ delay: 0.4 }}
                >
                  <DebugWrapper name="SubsidiariesList">
                    <SubsidiariesList
                      subsidiaries={companyData?.subsidiaries_details || []}
                      totalCount={
                        companyData?.subsidiaries_details?.length || 0
                      }
                    />
                  </DebugWrapper>
                </motion.div>
              )}
            </div>
          </ErrorBoundary>
        </motion.div>
      </div>
    </div>
  );
}
