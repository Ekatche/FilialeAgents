"use client";

import React, { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  CheckCircle2,
  Loader2,
  AlertCircle,
  Clock,
  BarChart3,
  Activity,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";

interface DetailedAgentState {
  name: string;
  status: string;
  progress: number;
  message: string;
  current_step: number;
  total_steps: number;
  step_name: string;
  started_at: string | null;
  updated_at: string | null;
  error_message: string | null;
  performance_metrics: {
    elapsed_time: number;
    steps_completed: number;
    steps_remaining: number;
    current_step_duration: number;
    average_step_time: number;
  };
}

interface EnhancedAgentProgressProps {
  sessionId: string;
  onComplete?: () => void;
  onError?: (error: string) => void;
}

const translateDetailedStatus = (status: string) => {
  const translations: { [key: string]: string } = {
    analyzing_basic_info: "Analyse des informations de base",
    validating_company_name: "Validation du nom d'entreprise",
    researching_company_history: "Recherche de l'historique",
    identifying_business_model: "Identification du modèle d'affaires",
    searching_web_sources: "Recherche de sources web",
    extracting_company_data: "Extraction des données d'entreprise",
    processing_subsidiaries: "Traitement des filiales",
    analyzing_financial_data: "Analyse des données financières",
    gathering_employee_info: "Collecte d'informations sur les employés",
    collating_sources: "Compilation des sources",
    validating_data_quality: "Validation de la qualité des données",
    cross_referencing_sources: "Vérification croisée des sources",
    checking_consistency: "Vérification de la cohérence",
    finalizing_results: "Finalisation des résultats",
  };
  return translations[status] || status;
};

const getStatusColor = (status: string) => {
  if (status.includes("error")) return "bg-red-100 text-red-800";
  if (status.includes("completed") || status.includes("finalizing"))
    return "bg-green-100 text-green-800";
  if (status.includes("analyzing") || status.includes("validating"))
    return "bg-blue-100 text-blue-800";
  if (status.includes("searching") || status.includes("extracting"))
    return "bg-amber-100 text-amber-800";
  if (status.includes("processing") || status.includes("gathering"))
    return "bg-purple-100 text-purple-800";
  return "bg-gray-100 text-gray-800";
};

const getStatusIcon = (status: string, isActive: boolean) => {
  if (status.includes("error"))
    return <AlertCircle className="w-4 h-4 text-red-500" />;
  if (status.includes("completed") || status.includes("finalizing"))
    return <CheckCircle2 className="w-4 h-4 text-green-500" />;
  if (isActive)
    return <Loader2 className="w-4 h-4 text-blue-500 animate-spin" />;
  return <Activity className="w-4 h-4 text-gray-500" />;
};

export function EnhancedAgentProgress({
  sessionId,
  onComplete,
  onError,
}: EnhancedAgentProgressProps) {
  const [agents, setAgents] = useState<DetailedAgentState[]>([]);
  const [overallProgress, setOverallProgress] = useState(0);
  const [overallStatus, setOverallStatus] = useState("initializing");
  const [companyName, setCompanyName] = useState("");
  const [isConnected, setIsConnected] = useState(false);

  useEffect(() => {
    let reconnectTimer: NodeJS.Timeout;

    const connect = () => {
      try {
        const wsUrl = `ws://localhost:8012/ws/enhanced-status/${sessionId}`;
        console.log(`🔌 [ENHANCED] Connexion WebSocket granulaire: ${wsUrl}`);

        const websocket = new WebSocket(wsUrl);
        websocket.onopen = () => {
          console.log(
            `🔌 [ENHANCED] WebSocket granulaire connecté pour la session: ${sessionId}`
          );
          setIsConnected(true);
        };

        websocket.onmessage = (event) => {
          try {
            console.log(
              "📡 [ENHANCED] Message WebSocket granulaire reçu:",
              event.data
            );

            if (!event.data) {
              console.log("❌ [ENHANCED] Message vide reçu");
              return;
            }

            const data = JSON.parse(event.data);
            console.log("📋 [ENHANCED] Données parsées:", data);

            if (data && data.type === "agent_update") {
              console.log("📡 [ENHANCED] Mise à jour d'agent reçue:", data);

              // Mettre à jour l'agent spécifique
              setAgents((prev) => {
                const updated = [...prev];
                const agentIndex = updated.findIndex(
                  (a) => a.name === data.agent_name
                );

                if (agentIndex >= 0) {
                  updated[agentIndex] = data.agent_state;
                } else {
                  updated.push(data.agent_state);
                }

                return updated;
              });

              setOverallProgress(data.overall_progress || 0);
              setOverallStatus(data.overall_status || "processing");
              setCompanyName(data.company_name || "");

              console.log(
                "🔄 [ENHANCED] États mis à jour - agents:",
                data.agent_state?.name,
                "progress:",
                data.overall_progress,
                "status:",
                data.overall_status
              );

              // Vérifier si l'extraction est terminée
              if (data.overall_status === "completed") {
                console.log("✅ [ENHANCED] Extraction terminée");
                if (onComplete) {
                  onComplete();
                }
              } else if (data.overall_status === "error") {
                console.log("❌ [ENHANCED] Erreur détectée");
                const errorMsg =
                  data.agent_state?.error_message || "Erreur inconnue";
                if (onError) {
                  onError(errorMsg);
                }
              }
            }
          } catch (err) {
            console.error("❌ [ENHANCED] Erreur parsing WebSocket:", err);
          }
        };

        websocket.onclose = (event) => {
          console.log(
            "🔌 [ENHANCED] WebSocket granulaire fermé:",
            event.code,
            event.reason
          );
          setIsConnected(false);

          // Reconnexion automatique après 3 secondes si pas terminé
          if (overallStatus !== "completed" && overallStatus !== "error") {
            reconnectTimer = setTimeout(() => {
              console.log("🔄 [ENHANCED] Tentative de reconnexion...");
              connect();
            }, 3000);
          }
        };

        websocket.onerror = (err) => {
          console.error("❌ [ENHANCED] Erreur WebSocket granulaire:", err);
          setIsConnected(false);
        };
      } catch (err) {
        console.error("❌ [ENHANCED] Erreur création WebSocket:", err);
        setIsConnected(false);
      }
    };

    connect();

    return () => {
      if (reconnectTimer) {
        clearTimeout(reconnectTimer);
      }
      // nothing to cleanup
    };
  }, [sessionId, overallStatus, onComplete, onError]);

  if (agents.length === 0) {
    return (
      <Card className="w-full max-w-4xl mx-auto">
        <CardContent className="p-6">
          <div className="flex items-center gap-3 text-gray-600">
            <Loader2 className="w-5 h-5 animate-spin" />
            <div>
              <h3 className="font-semibold">
                Initialisation des agents granulaires...
              </h3>
              <p className="text-sm">Connexion au serveur en cours...</p>
            </div>
          </div>
        </CardContent>
      </Card>
    );
  }

  // Trouver l'agent actuellement actif
  const activeAgent = agents.find(
    (agent) =>
      agent.status.includes("analyzing") ||
      agent.status.includes("searching") ||
      agent.status.includes("extracting") ||
      agent.status.includes("processing") ||
      agent.status.includes("validating")
  );

  return (
    <div className="w-full max-w-6xl mx-auto space-y-6">
      {/* Barre de progression globale prominente */}
      <Card className="border-blue-200 bg-gradient-to-r from-blue-50 via-indigo-50 to-purple-50">
        <CardContent className="p-6">
          <div className="space-y-4">
            {/* En-tête avec statut */}
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-xl font-bold text-gray-900">
                  {companyName
                    ? `Analyse granulaire de ${companyName}`
                    : "Analyse granulaire en cours"}
                </h2>
                <div className="flex items-center gap-3 mt-2">
                  <Badge
                    className={`${getStatusColor(overallStatus)} px-3 py-1`}
                  >
                    {translateDetailedStatus(overallStatus)}
                  </Badge>
                  <div className="flex items-center gap-2">
                    <div
                      className={`w-2 h-2 rounded-full ${
                        isConnected ? "bg-green-400" : "bg-red-400"
                      }`}
                    />
                    <span className="text-sm text-gray-600">
                      {isConnected ? "Connecté" : "Déconnecté"}
                    </span>
                  </div>
                </div>
              </div>
              <div className="text-right">
                <div className="text-3xl font-bold text-blue-600">
                  {Math.round(overallProgress * 100)}%
                </div>
                <div className="text-sm text-gray-500">Progression globale</div>
              </div>
            </div>

            {/* Barre de progression principale animée */}
            <div className="space-y-2">
              <motion.div
                initial={{ scaleX: 0 }}
                animate={{ scaleX: 1 }}
                transition={{ duration: 0.8, ease: "easeOut" }}
                style={{ transformOrigin: "left" }}
              >
                <Progress
                  value={overallProgress * 100}
                  className="h-4 bg-white/50"
                />
              </motion.div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Agent actuellement actif avec détails granulaires */}
      {activeAgent && (
        <Card className="border-amber-300 bg-gradient-to-r from-amber-50 to-orange-50 shadow-lg">
          <CardContent className="p-6">
            <div className="space-y-4">
              <div className="flex items-center gap-4">
                <div className="relative">
                  <Loader2 className="w-8 h-8 text-amber-600 animate-spin" />
                  <div className="absolute -top-1 -right-1 w-3 h-3 bg-amber-500 rounded-full animate-pulse"></div>
                </div>
                <div className="flex-1">
                  <h3 className="text-lg font-bold text-amber-900 mb-1">
                    🤖 {activeAgent.name} en action
                  </h3>
                  <p className="text-amber-800 mb-2">{activeAgent.message}</p>
                  <div className="flex items-center gap-4 text-sm text-amber-700">
                    <span>{translateDetailedStatus(activeAgent.status)}</span>
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-2xl font-bold text-amber-700">
                    {Math.round(activeAgent.progress * 100)}%
                  </div>
                  <div className="text-xs text-amber-600">Progression</div>
                </div>
              </div>

              {/* Barre de progression de l'agent actif avec étapes */}
              <div className="space-y-3">
                <motion.div
                  initial={{ scaleX: 0 }}
                  animate={{ scaleX: 1 }}
                  transition={{ duration: 0.6, ease: "easeOut" }}
                  style={{ transformOrigin: "left" }}
                >
                  <Progress
                    value={activeAgent.progress * 100}
                    className="h-3 bg-amber-100"
                  />
                </motion.div>

                {/* Métriques de performance */}
                {activeAgent.performance_metrics && (
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-xs text-amber-700">
                    <div>
                      <span className="font-medium">Temps écoulé:</span>
                      <br />
                      {Math.round(activeAgent.performance_metrics.elapsed_time)}
                      s
                    </div>
                    <div>
                      <span className="font-medium">Étapes restantes:</span>
                      <br />
                      {activeAgent.performance_metrics.steps_remaining}
                    </div>
                    <div>
                      <span className="font-medium">Durée étape actuelle:</span>
                      <br />
                      {Math.round(
                        activeAgent.performance_metrics.current_step_duration
                      )}
                      s
                    </div>
                    <div>
                      <span className="font-medium">Temps moyen/étape:</span>
                      <br />
                      {Math.round(
                        activeAgent.performance_metrics.average_step_time
                      )}
                      s
                    </div>
                  </div>
                )}
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Visualisation avancée de la progression - Temporairement désactivée */}
      {/* TODO: Réimplémenter AgentProgressVisualization si nécessaire */}

      {/* Liste de tous les agents avec leurs progressions granulaires */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <BarChart3 className="w-5 h-5 text-blue-600" />
            État détaillé des agents granulaires
          </CardTitle>
        </CardHeader>
        <CardContent className="p-6">
          <div className="space-y-4">
            <AnimatePresence>
              {agents.map((agent, index) => {
                const isActive =
                  agent.status.includes("analyzing") ||
                  agent.status.includes("searching") ||
                  agent.status.includes("extracting") ||
                  agent.status.includes("processing") ||
                  agent.status.includes("validating");
                const isCompleted =
                  agent.status.includes("completed") ||
                  agent.status.includes("finalizing");
                const hasError = agent.status.includes("error");

                return (
                  <motion.div
                    key={index}
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{
                      duration: 0.4,
                      ease: "easeOut",
                      delay: index * 0.1,
                    }}
                    exit={{
                      opacity: 0,
                      y: -20,
                      scale: 0.95,
                      transition: { duration: 0.2 },
                    }}
                    layout
                    className={`p-4 rounded-lg border transition-all duration-300 ${
                      isActive
                        ? "border-blue-200 bg-blue-50 shadow-md"
                        : isCompleted
                        ? "border-green-200 bg-green-50"
                        : hasError
                        ? "border-red-200 bg-red-50"
                        : "border-gray-200 bg-white"
                    }`}
                  >
                    <div className="flex items-center justify-between mb-3">
                      <div className="flex items-center gap-3">
                        {getStatusIcon(agent.status, isActive)}
                        <div>
                          <h4 className="font-medium text-gray-900">
                            {agent.name}
                          </h4>
                          <div className="flex items-center gap-2 mt-1">
                            <Badge
                              className={`text-xs ${getStatusColor(
                                agent.status
                              )}`}
                            >
                              {translateDetailedStatus(agent.status)}
                            </Badge>
                          </div>
                        </div>
                      </div>
                      <div className="text-right">
                        <div className="text-lg font-semibold text-gray-900">
                          {Math.round(agent.progress * 100)}%
                        </div>
                        <div className="text-xs text-gray-500">
                          {agent.step_name}
                        </div>
                      </div>
                    </div>

                    {/* Message de l'agent */}
                    <p className="text-sm text-gray-600 mb-3">
                      {agent.message}
                    </p>

                    {/* Barre de progression individuelle avec animation */}
                    <div className="space-y-2">
                      <motion.div
                        initial={{ width: 0 }}
                        animate={{ width: "100%" }}
                        transition={{ duration: 0.5, ease: "easeOut" }}
                      >
                        <Progress
                          value={agent.progress * 100}
                          className={`h-2 ${
                            isActive
                              ? "bg-blue-100"
                              : isCompleted
                              ? "bg-green-100"
                              : hasError
                              ? "bg-red-100"
                              : "bg-gray-100"
                          }`}
                        />
                      </motion.div>

                      {/* Métriques de performance */}
                      {agent.performance_metrics && (
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-xs text-gray-500">
                          <div>
                            Temps:{" "}
                            {Math.round(agent.performance_metrics.elapsed_time)}
                            s
                          </div>
                          <div>
                            Restant: {agent.performance_metrics.steps_remaining}
                          </div>
                          <div>
                            Actuel:{" "}
                            {Math.round(
                              agent.performance_metrics.current_step_duration
                            )}
                            s
                          </div>
                          <div>
                            Moyen:{" "}
                            {Math.round(
                              agent.performance_metrics.average_step_time
                            )}
                            s
                          </div>
                        </div>
                      )}
                    </div>
                  </motion.div>
                );
              })}
            </AnimatePresence>
          </div>
        </CardContent>
      </Card>

      {/* Footer avec timing */}
      <div className="text-center text-xs text-gray-500">
        <Clock className="w-3 h-3 inline mr-1" />
        Session granulaire: {sessionId.slice(0, 8)}...
      </div>
    </div>
  );
}

export default EnhancedAgentProgress;
