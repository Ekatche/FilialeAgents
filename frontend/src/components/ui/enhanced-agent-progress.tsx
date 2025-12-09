"use client";

import React from "react";
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

// Interface alignée avec le backend (ExtractionProgress)
interface DetailedAgentState {
  name: string;
  status: string;
  progress: number;
  message: string;
  current_step?: number;
  total_steps?: number;
  step_name?: string;
  started_at?: string;
  updated_at?: string;
  error_message?: string | null;
  performance_metrics?: {
    elapsed_time: number;
    steps_completed: number;
    steps_remaining: number;
    current_step_duration: number;
    average_step_time?: number;
    estimated_total_time?: number;
  };
}

interface ExtractionProgress {
  session_id: string;
  company_name: string;
  overall_status: string;
  overall_progress: number;
  agents: DetailedAgentState[];
  started_at?: string;
  updated_at?: string;
  global_message?: string;
}

interface EnhancedAgentProgressProps {
  progress: ExtractionProgress;
  isConnected: boolean;
}

const translateDetailedStatus = (status: string) => {
  const translations: { [key: string]: string } = {
    initializing: "Initialisation",
    waiting: "En attente",
    running: "En cours",
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
    completed: "Terminé",
    error: "Erreur",
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
  if (status.includes("waiting")) return "bg-gray-100 text-gray-500";
  return "bg-gray-100 text-gray-800";
};

const getStatusIcon = (status: string, isActive: boolean) => {
  if (status.includes("error"))
    return <AlertCircle className="w-4 h-4 text-red-500" />;
  if (status.includes("completed"))
    return <CheckCircle2 className="w-4 h-4 text-green-500" />;
  if (isActive || status.includes("running"))
    return <Loader2 className="w-4 h-4 text-blue-500 animate-spin" />;
  if (status.includes("waiting"))
    return <Clock className="w-4 h-4 text-gray-400" />;
  return <Activity className="w-4 h-4 text-gray-500" />;
};

export function EnhancedAgentProgress({
  progress,
  isConnected,
}: EnhancedAgentProgressProps) {
  const { agents, overall_progress, overall_status, company_name, session_id } =
    progress;

  // État local pour l'interpolation fluide de la progression
  const [displayProgress, setDisplayProgress] = React.useState(0);

  // Effet pour lisser la progression
  React.useEffect(() => {
    const targetProgress = overall_progress * 100;
    
    // Si l'écart est grand (ex: début), on saute direct ou on accélère
    // Sinon on lisse
    let animationFrame: number;
    
    const updateProgress = () => {
      setDisplayProgress(prev => {
        const diff = targetProgress - prev;
        
        // Si on est très proche ou si on a dépassé (retour en arrière rare mais possible)
        if (Math.abs(diff) < 0.5) return targetProgress;
        
        // Vitesse d'approche (plus on est loin, plus on va vite)
        const step = Math.max(0.2, diff * 0.1); 
        return Math.min(targetProgress, prev + step);
      });
      
      if (Math.abs(targetProgress - displayProgress) > 0.5) {
        animationFrame = requestAnimationFrame(updateProgress);
      }
    };
    
    animationFrame = requestAnimationFrame(updateProgress);
    
    return () => cancelAnimationFrame(animationFrame);
  }, [overall_progress, displayProgress]);

  // Effet de "fake progress" pour montrer que ça travaille quand même
  // Si le statut est "running" ou "analyzing" et qu'on stagne
  React.useEffect(() => {
    const isActive = overall_status !== "completed" && overall_status !== "error" && overall_status !== "waiting";
    if (!isActive) return;

    const interval = setInterval(() => {
      setDisplayProgress(prev => {
        // Ne jamais dépasser la target réelle de trop (max +15% pour faire genre)
        // Sauf si on est proche de 100%
        const realTarget = overall_progress * 100;
        const limit = Math.min(98, realTarget + 15); 
        
        if (prev >= limit) return prev;
        
        // Avance très doucement
        return prev + 0.05; 
      });
    }, 100);

    return () => clearInterval(interval);
  }, [overall_status, overall_progress]);

  // Trouver l'agent actuellement actif (le premier qui n'est ni waiting ni completed/error)
  // Ou celui explicitement marqué comme running/analyzing/etc.
  const activeAgent = agents.find(
    (agent) =>
      agent.status !== "waiting" &&
      agent.status !== "completed" &&
      agent.status !== "error"
  );

  return (
    <div className="w-full space-y-6">
      {/* Barre de progression globale prominente */}
      <Card className="border-blue-200 bg-gradient-to-r from-blue-50 via-indigo-50 to-purple-50">
        <CardContent className="p-6">
          <div className="space-y-4">
            {/* En-tête avec statut */}
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-xl font-bold text-gray-900">
                  {company_name
                    ? `Analyse de ${company_name}`
                    : "Analyse en cours"}
                </h2>
                <div className="flex items-center gap-3 mt-2">
                  <Badge
                    className={`${getStatusColor(overall_status)} px-3 py-1`}
                  >
                    {translateDetailedStatus(overall_status)}
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
                  {Math.round(displayProgress)}%
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
                  value={displayProgress}
                  className="h-4 bg-white/50"
                />
              </motion.div>
              <p className="text-xs text-center text-gray-500 font-mono mt-2">
                Session ID: {session_id}
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Agent actuellement actif avec détails granulaires */}
      {activeAgent && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          key={activeAgent.name}
        >
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
                      <Badge variant="outline" className="border-amber-200 bg-amber-100/50">
                        {translateDetailedStatus(activeAgent.status)}
                      </Badge>
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
                  <div className="relative pt-1">
                    <Progress
                      value={activeAgent.progress * 100}
                      className="h-3 bg-amber-100"
                    />
                  </div>

                  {/* Métriques de performance (si disponibles) */}
                  {activeAgent.performance_metrics && (
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-xs text-amber-700 mt-3 bg-white/30 p-3 rounded-lg">
                      <div>
                        <span className="font-medium">Temps écoulé:</span>
                        <div className="text-lg">
                          {Math.round(activeAgent.performance_metrics.elapsed_time)}s
                        </div>
                      </div>
                      {activeAgent.performance_metrics.steps_remaining !== undefined && (
                        <div>
                          <span className="font-medium">Étapes restantes:</span>
                          <div className="text-lg">
                            {activeAgent.performance_metrics.steps_remaining}
                          </div>
                        </div>
                      )}
                      {activeAgent.step_name && (
                        <div className="col-span-2">
                          <span className="font-medium">Étape actuelle:</span>
                          <div className="text-sm truncate font-medium">
                            {activeAgent.step_name}
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>
            </CardContent>
          </Card>
        </motion.div>
      )}

      {/* Liste de tous les agents avec leurs progressions granulaires */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <BarChart3 className="w-5 h-5 text-blue-600" />
            Détail des agents
          </CardTitle>
        </CardHeader>
        <CardContent className="p-6">
          <div className="space-y-4">
            <AnimatePresence mode="popLayout">
              {agents.map((agent, index) => {
                const isActive =
                  agent.status !== "waiting" &&
                  agent.status !== "completed" &&
                  agent.status !== "error";
                const isCompleted = agent.status === "completed";
                const hasError = agent.status === "error";
                const isWaiting = agent.status === "waiting";

                return (
                  <motion.div
                    key={agent.name}
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: index * 0.1 }}
                    className={`p-4 rounded-lg border transition-all duration-300 ${
                      isActive
                        ? "border-blue-200 bg-blue-50 shadow-md scale-[1.02]"
                        : isCompleted
                        ? "border-green-200 bg-green-50/50"
                        : hasError
                        ? "border-red-200 bg-red-50"
                        : "border-gray-200 bg-gray-50/30"
                    }`}
                  >
                    <div className="flex items-center justify-between mb-3">
                      <div className="flex items-center gap-3">
                        {getStatusIcon(agent.status, isActive)}
                        <div>
                          <h4 className={`font-medium ${isWaiting ? 'text-gray-500' : 'text-gray-900'}`}>
                            {agent.name}
                          </h4>
                        </div>
                      </div>
                      <div className="text-right">
                         <Badge
                            className={`text-xs ${getStatusColor(
                              agent.status
                            )}`}
                          >
                            {translateDetailedStatus(agent.status)}
                          </Badge>
                      </div>
                    </div>

                    {/* Message de l'agent */}
                    {!isWaiting && (
                      <p className="text-sm text-gray-600 mb-3 ml-7">
                        {agent.message}
                      </p>
                    )}

                    {/* Barre de progression individuelle avec animation */}
                    {!isWaiting && (
                      <div className="space-y-2 ml-7">
                        <Progress
                          value={agent.progress * 100}
                          className={`h-1.5 ${
                            isActive
                              ? "bg-blue-100"
                              : isCompleted
                              ? "bg-green-100"
                              : "bg-gray-100"
                          }`}
                        />
                      </div>
                    )}
                  </motion.div>
                );
              })}
            </AnimatePresence>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

export default EnhancedAgentProgress;
