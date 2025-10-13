"use client";

import React, { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  CheckCircle2,
  Loader2,
  Search,
  Database,
  Shield,
  AlertCircle,
  Clock,
  Link,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";

interface AgentState {
  name: string;
  status: string;
  progress: number;
  message: string;
  started_at: string | null;
  updated_at: string | null;
  error_message: string | null;
  // Nouveaux champs pour la progression détaillée
  current_step?: number;
  total_steps?: number;
  step_name?: string;
  performance_metrics?: {
    elapsed_time?: number;
    steps_completed?: number;
    steps_remaining?: number;
    current_step_duration?: number;
    estimated_total_time?: number;
  };
}

interface AgentProgressProps {
  sessionId: string;
  onComplete?: () => void;
  onError?: (error: string) => void;
}

// Traduction des statuts
const translateStatus = (status: string) => {
  switch (status) {
    case "idle":
      return "En attente";
    case "initializing":
      return "Initialisation";
    case "searching":
      return "Recherche";
    case "extracting":
      return "Extraction";
    case "analyzing":
      return "Analyse";
    case "validating":
      return "Validation";
    case "completed":
      return "Terminé";
    case "error":
      return "Erreur";
    default:
      return status;
  }
};

// Icônes pour chaque agent
const getAgentIcon = (
  agentName: string,
  isActive: boolean,
  isCompleted: boolean,
  hasError: boolean
) => {
  const IconComponent = agentName.includes("Éclaireur")
    ? Search
    : agentName.includes("Mineur")
    ? Database
    : agentName.includes("Vérificateur")
    ? Link
    : agentName.includes("Cartographe")
    ? Shield
    : agentName.includes("Superviseur")
    ? Shield
    : Search;

  if (hasError) return <AlertCircle className="w-4 h-4 text-red-600" />;
  if (isCompleted) return <CheckCircle2 className="w-4 h-4 text-green-600" />;
  if (isActive)
    return <Loader2 className="w-4 h-4 text-blue-600 animate-spin" />;
  return <IconComponent className="w-4 h-4 text-gray-400" />;
};

// Couleurs pour les badges de statut
const getStatusColor = (status: string) => {
  switch (status) {
    case "waiting":
      return "bg-gray-100 text-gray-700";
    case "initializing":
      return "bg-blue-100 text-blue-700";
    case "running":
      return "bg-yellow-100 text-yellow-700";
    case "finalizing":
      return "bg-orange-100 text-orange-700";
    case "completed":
      return "bg-green-100 text-green-700";
    case "error":
      return "bg-red-100 text-red-700";
    // États dépréciés (pour compatibilité)
    case "idle":
      return "bg-gray-100 text-gray-700";
    case "searching":
    case "extracting":
    case "analyzing":
      return "bg-yellow-100 text-yellow-700";
    case "validating":
      return "bg-purple-100 text-purple-700";
    default:
      return "bg-gray-100 text-gray-700";
  }
};

// Composant mémorisé pour un agent individuel pour éviter les re-renders
const AgentCard = React.memo(
  ({ agent, index }: { agent: AgentState; index: number }) => {
    const isActive = [
      "running",
      "finalizing",
      // États dépréciés (pour compatibilité)
      "searching",
      "extracting",
      "analyzing",
      "validating",
    ].includes(agent.status);
    const isCompleted = agent.status === "completed";
    const hasError = agent.status === "error";

    return (
      <motion.div
        key={agent.name || index}
        initial={{ opacity: 0, y: 20, scale: 0.95 }}
        animate={{
          opacity: 1,
          y: 0,
          scale: 1,
          transition: {
            duration: 0.4,
            ease: "easeOut",
            delay: index * 0.1,
          },
        }}
        exit={{
          opacity: 0,
          y: -20,
          scale: 0.95,
          transition: { duration: 0.2 },
        }}
        layout
        className={`p-3 rounded-lg border transition-all duration-300 ${
          isActive
            ? "border-blue-300 bg-blue-50 shadow-md"
            : isCompleted
            ? "border-green-300 bg-green-50"
            : hasError
            ? "border-red-300 bg-red-50"
            : "border-gray-200 bg-gray-50"
        }`}
      >
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-3">
            {getAgentIcon(agent.name || "", isActive, isCompleted, hasError)}
            <div>
              <h4 className="font-medium text-gray-900">
                {agent.name || `Agent ${index + 1}`}
              </h4>
              <div className="flex items-center gap-2 mt-1">
                <Badge className={`text-xs ${getStatusColor(agent.status)}`}>
                  {translateStatus(agent.status)}
                </Badge>
              </div>
            </div>
          </div>
          <div className="text-right">
            <div className="text-lg font-semibold text-gray-900">
              {Math.round((agent.progress || 0) * 100)}%
            </div>
            {/* Métriques de performance optimisées */}
            {agent.performance_metrics && (
              <div className="text-xs text-gray-500">
                {agent.performance_metrics.elapsed_time && (
                  <div className="inline-block mr-3">
                    ⏱️ {Math.round(agent.performance_metrics.elapsed_time / 1000)}s
                  </div>
                )}
                {agent.performance_metrics.steps_remaining !== undefined && (
                  <div className="inline-block">
                    📋 {agent.performance_metrics.steps_remaining} restantes
                  </div>
                )}
              </div>
            )}
          </div>
        </div>

        {/* Message de l'agent optimisé */}
        <p className="text-sm text-gray-600 mb-2">{agent.message}</p>

        {/* Barre de progression individuelle avec animation granulaire */}
        <div className="space-y-1">
          <div className="relative">
            <Progress
              value={(agent.progress || 0) * 100}
              className={`h-2 transition-all duration-300 ease-out ${
                isActive
                  ? "bg-blue-100"
                  : isCompleted
                  ? "bg-green-100"
                  : hasError
                  ? "bg-red-100"
                  : "bg-gray-100"
              }`}
            />
            {/* Indicateur de progression granulaire */}
            {agent.current_step && agent.total_steps && (
              <div className="absolute top-0 right-0 text-xs text-gray-500 bg-white px-1 rounded">
                {agent.current_step}/{agent.total_steps}
              </div>
            )}
          </div>
          <div className="flex justify-between items-center text-xs text-gray-500">
            <motion.span
              key={agent.message} // Force re-render sur changement de message
              initial={{ opacity: 0, y: 5 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3 }}
            >
              {agent.step_name || agent.message || 
                (agent.progress === 0
                  ? "En attente"
                  : agent.progress === 1
                  ? "Terminé"
                  : "En cours")}
            </motion.span>
            {agent.error_message && (
              <motion.span
                initial={{ opacity: 0, x: 10 }}
                animate={{ opacity: 1, x: 0 }}
                className="text-red-600 font-medium"
              >
                {agent.error_message}
              </motion.span>
            )}
          </div>
      {/* Affichage des métriques de performance détaillées */}
      {agent.performance_metrics && (
        <div className="text-xs text-gray-400 mt-1 space-y-1">
          {/* Temps d'exécution */}
          {agent.performance_metrics.elapsed_time && (
            <div className="flex items-center gap-2">
              <span>⏱️ {Math.round(agent.performance_metrics.elapsed_time / 1000)}s</span>
              {(agent.performance_metrics as any).quality_score && (
                <span className="text-green-600">📊 {Math.round((agent.performance_metrics as any).quality_score * 100)}%</span>
              )}
            </div>
          )}
          
          {/* Progression des étapes */}
          {agent.performance_metrics.steps_completed && (agent.performance_metrics as any).total_steps && (
            <div className="flex items-center gap-2">
              <span>✅ {agent.performance_metrics.steps_completed}/{(agent.performance_metrics as any).total_steps} étapes</span>
              {(agent.performance_metrics as any).items_processed && (
                <span className="text-blue-600">🏢 {(agent.performance_metrics as any).items_processed} éléments</span>
              )}
            </div>
          )}
          
          {/* Métriques de qualité spécifiques */}
          {(agent.performance_metrics as any).subsidiaries_found && (
            <div className="text-blue-600">
              🗺️ {(agent.performance_metrics as any).subsidiaries_found} filiales trouvées
            </div>
          )}
          
          {(agent.performance_metrics as any).citations_count && (
            <div className="text-purple-600">
              📚 {(agent.performance_metrics as any).citations_count} sources
            </div>
          )}
          
          {/* Indicateur d'erreur */}
          {(agent.performance_metrics as any).error_rate > 0 && (
            <div className="text-red-600">
              ⚠️ Taux d'erreur: {Math.round((agent.performance_metrics as any).error_rate * 100)}%
            </div>
          )}
        </div>
      )}
        </div>
      </motion.div>
    );
  }
);
AgentCard.displayName = "AgentCard";

export function AgentProgress({
  sessionId,
  onComplete,
  onError,
}: AgentProgressProps) {
  const [agents, setAgents] = useState<AgentState[]>([]);
  const [overallProgress, setOverallProgress] = useState(0);
  const [overallStatus, setOverallStatus] = useState("initializing");
  const [companyName, setCompanyName] = useState("");
  const [isConnected, setIsConnected] = useState(false);
  const overallStatusRef = React.useRef(overallStatus);

  React.useEffect(() => {
    overallStatusRef.current = overallStatus;
  }, [overallStatus]);

  // Mémoriser les callbacks pour éviter les re-renders
  const stableOnComplete = React.useCallback(() => {
    if (typeof onCompleteRef.current === "function") {
      onCompleteRef.current();
    }
  }, []);

  // Référence pour éviter dépendance directe
  const onCompleteRef = React.useRef(onComplete);
  React.useEffect(() => {
    onCompleteRef.current = onComplete;
  }, [onComplete]);

  const stableOnError = React.useCallback(
    (error: string) => {
      if (typeof onError === "function") {
        onError(error);
      }
    },
    [onError]
  );

  useEffect(() => {
    if (!sessionId) {
      return;
    }

    // Ne pas se connecter aux sessions temporaires
    if (sessionId.startsWith("temp-")) {
      return;
    }

    console.log(
      "🔌 [DEBUG] Connexion WebSocket à la session réelle:",
      sessionId
    );

    // D'abord, essayer de récupérer l'état actuel de la session
    const fetchSessionStatus = async () => {
      try {
        console.log(
          "📊 [DEBUG] Récupération de l'état de la session:",
          sessionId
        );
        const response = await fetch(
          `${
            process.env.NEXT_PUBLIC_API_URL || "http://localhost:8012"
          }/status/${sessionId}`
        );
        if (response.ok) {
          const sessionData = await response.json();
          console.log("📋 [DEBUG] État de session récupéré:", sessionData);

          setAgents(sessionData?.agents || []);
          setOverallProgress(sessionData?.overall_progress || 0);
          setOverallStatus(sessionData?.overall_status || "initializing");
          setCompanyName(sessionData?.company_name || "");

          // Si la session est déjà terminée, pas besoin de WebSocket
          if (
            sessionData?.overall_status === "completed" ||
            sessionData?.overall_status === "error"
          ) {
            console.log(
              "✅ [DEBUG] Session déjà terminée, pas de WebSocket nécessaire"
            );
            if (sessionData?.overall_status === "completed") {
              stableOnComplete();
            }
            return false; // Pas besoin de WebSocket
          }
        }
      } catch (err) {
        console.log(
          "⚠️ [DEBUG] Impossible de récupérer l'état de session:",
          err
        );
      }
      return true; // WebSocket nécessaire
    };

    const wsUrl = `${
      process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8012"
    }/ws/status/${sessionId}`;
    console.log("🌐 [DEBUG] URL WebSocket:", wsUrl);

    let ws: WebSocket;
    let reconnectTimer: NodeJS.Timeout;

    const connect = async () => {
      // Vérifier d'abord l'état de la session
      const needsWebSocket = await fetchSessionStatus();
      if (!needsWebSocket) {
        return;
      }
      try {
        console.log("🔌 [DEBUG] Tentative de connexion WebSocket...");
        ws = new WebSocket(wsUrl);

        ws.onopen = () => {
          console.log(
            `🔌 [DEBUG] WebSocket connecté pour la session: ${sessionId}`
          );
          setIsConnected(true);
        };

        ws.onmessage = (event) => {
          try {
            console.log("📡 [DEBUG] Message WebSocket reçu:", event.data);

            if (!event.data) {
              console.log("❌ [DEBUG] Message vide reçu");
              return;
            }

            const data = JSON.parse(event.data);
            console.log("📋 [DEBUG] Données parsées:", data);

            // Répondre aux messages de ping avec pong
            if (data && data.type === "ping") {
              console.log("🏓 [DEBUG] Ping reçu, envoi pong...");
              if (ws && ws.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify({ type: "pong", timestamp: new Date().toISOString() }));
              }
              return;
            }

            console.log("📡 [DEBUG] Mise à jour des agents reçue:", data);

            // Gérer les deux formats de messages WebSocket
            let progressData;
            if (data?.type === "progress_update" && data?.data) {
              // Format: {type: "progress_update", data: {...}}
              progressData = data.data;
              console.log(
                "📋 [DEBUG] Format progress_update détecté, données:",
                progressData
              );
            } else {
              // Format: {session_id: "...", agents: [...], ...}
              progressData = data;
              console.log(
                "📋 [DEBUG] Format direct détecté, données:",
                progressData
              );
            }

            const agents = progressData?.agents || [];
            const overallProgress = progressData?.overall_progress || 0;
            const overallStatus =
              progressData?.overall_status || "initializing";
            const companyName = progressData?.company_name || "";

            console.log(
              "🔧 [DEBUG] Données extraites - agents:",
              agents.length,
              "progress:",
              overallProgress,
              "status:",
              overallStatus
            );

            setAgents(agents);
            setOverallProgress(overallProgress);
            setOverallStatus(overallStatus);
            setCompanyName(companyName);

            console.log(
              "🔄 [DEBUG] États mis à jour - agents:",
              agents.length,
              "progress:",
              overallProgress,
              "status:",
              overallStatus
            );

            // Vérifier si l'extraction est terminée
            if (overallStatus === "completed") {
              console.log("✅ [DEBUG] Extraction terminée");
              // Fermer le WebSocket car l'extraction est terminée
              if (ws) {
                ws.close(1000, "Extraction terminée");
              }
              // Attendre un délai pour que les résultats soient stockés côté backend
              setTimeout(() => {
                stableOnComplete();
              }, 2000); // 2 secondes de délai
            } else if (overallStatus === "error") {
              console.log("❌ [DEBUG] Erreur détectée");
              // Fermer le WebSocket car il y a une erreur
              if (ws) {
                ws.close(1000, "Erreur détectée");
              }
              const errorMsg =
                agents.find((a: AgentState) => a?.error_message)
                  ?.error_message || "Erreur inconnue";
              stableOnError(errorMsg);
            }
          } catch (err) {
            console.error("❌ [DEBUG] Erreur parsing WebSocket:", err);
          }
        };

        ws.onclose = (event) => {
          console.log("🔌 [DEBUG] WebSocket fermé:", event.code, event.reason);
          setIsConnected(false);

          // Reconnexion automatique après 3 secondes si pas terminé et pas fermé normalement
          if (
            event.code !== 1000 &&
            overallStatusRef.current !== "completed" &&
            overallStatusRef.current !== "error"
          ) {
            // 1000 = normal closure
            reconnectTimer = setTimeout(() => {
              console.log("🔄 Tentative de reconnexion...");
              connect();
            }, 3000);
          }
        };

        ws.onerror = (err) => {
          console.error("❌ [DEBUG] Erreur WebSocket:", err);
          console.error("❌ [DEBUG] Détails de l'erreur:", err);
          setIsConnected(false);
        };
      } catch (err) {
        console.error("❌ Erreur création WebSocket:", err);
        setIsConnected(false);
      }
    };

    connect();

    return () => {
      if (reconnectTimer) {
        clearTimeout(reconnectTimer);
      }
      if (ws) {
        ws.close();
      }
    };
  }, [sessionId, stableOnComplete, stableOnError]);

  if (agents.length === 0) {
    return (
      <Card className="w-full max-w-3xl mx-auto">
        <CardContent className="p-6">
          <div className="flex items-center gap-3 text-gray-600">
            <Loader2 className="w-5 h-5 animate-spin" />
            <div>
              <h3 className="font-semibold">Initialisation des agents...</h3>
              <p className="text-sm">Connexion au serveur en cours...</p>
            </div>
          </div>
        </CardContent>
      </Card>
    );
  }

  // Trouver l'agent actuellement actif
  const activeAgent = agents.find((agent) =>
    ["searching", "extracting", "analyzing", "validating"].includes(
      agent.status
    )
  );

  return (
    <div className="w-full max-w-4xl mx-auto space-y-6">
      {/* Barre de progression globale prominente */}
      <Card className="border-blue-200 bg-gradient-to-r from-blue-50 via-indigo-50 to-purple-50">
        <CardContent className="p-6">
          <div className="space-y-4">
            {/* En-tête avec statut */}
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-xl font-bold text-gray-900">
                  {companyName
                    ? `Analyse de ${companyName}`
                    : "Analyse en cours"}
                </h2>
                <div className="flex items-center gap-3 mt-2">
                  <Badge
                    className={`${getStatusColor(overallStatus)} px-3 py-1`}
                  >
                    {translateStatus(overallStatus)}
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
              <div className="flex justify-between text-xs text-gray-600">
                <motion.span
                  initial={{ opacity: 0, y: 5 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.2 }}
                >
                  Début
                </motion.span>
                <motion.span
                  initial={{ opacity: 0, y: 5 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.3 }}
                >
                  En cours...
                </motion.span>
                <motion.span
                  initial={{ opacity: 0, y: 5 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.4 }}
                >
                  Terminé
                </motion.span>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Agent actuellement actif - mise en évidence avec progression */}
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
                  <p className="text-amber-800">{activeAgent.message}</p>
                </div>
                <div className="text-right">
                  <div className="text-2xl font-bold text-amber-700">
                    {Math.round((activeAgent.progress || 0) * 100)}%
                  </div>
                  <div className="text-xs text-amber-600">Progression</div>
                </div>
              </div>
              {/* Barre de progression de l'agent actif animée */}
              <div className="space-y-2">
                <motion.div
                  initial={{ scaleX: 0 }}
                  animate={{ scaleX: 1 }}
                  transition={{ duration: 0.6, ease: "easeOut" }}
                  style={{ transformOrigin: "left" }}
                >
                  <Progress
                    value={(activeAgent.progress || 0) * 100}
                    className="h-3 bg-amber-100"
                  />
                </motion.div>
                <div className="flex justify-between text-xs text-amber-700">
                  <motion.span
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: 0.1 }}
                  >
                    Début
                  </motion.span>
                  <motion.span
                    initial={{ opacity: 0, y: -5 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.2 }}
                  >
                    En cours...
                  </motion.span>
                  <motion.span
                    initial={{ opacity: 0, x: 10 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: 0.3 }}
                  >
                    Terminé
                  </motion.span>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Liste de tous les agents avec leurs progressions individuelles */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Database className="w-5 h-5 text-blue-600" />
            État détaillé des agents
          </CardTitle>
        </CardHeader>
        <CardContent className="p-6">
          <div className="space-y-4">
            <AnimatePresence>
              {agents.map((agent, index) => (
                <AgentCard
                  key={agent.name || index}
                  agent={agent}
                  index={index}
                />
              ))}
            </AnimatePresence>
          </div>
        </CardContent>
      </Card>

      {/* Footer avec timing */}
      <div className="text-center text-xs text-gray-500">
        <Clock className="w-3 h-3 inline mr-1" />
        Session: {sessionId.slice(0, 8)}...
      </div>
    </div>
  );
}
