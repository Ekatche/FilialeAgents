"use client";

import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  CheckCircle,
  XCircle,
  AlertCircle,
  Activity,
  Clock,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { useCompanyData } from "@/hooks/use-company-data";

export function ApiStatus() {
  const { isApiHealthy, apiError, healthData } = useCompanyData();
  const [isVisible, setIsVisible] = useState(true);

  useEffect(() => {
    const timer = setTimeout(() => {
      if (isApiHealthy) {
        setIsVisible(false);
      }
    }, 5000); // Hide after 5 seconds if API is healthy

    return () => clearTimeout(timer);
  }, [isApiHealthy]);

  const getStatusConfig = () => {
    if (apiError) {
      return {
        icon: XCircle,
        color: "text-red-600",
        bgColor: "bg-red-50 border-red-200",
        label: "API Indisponible",
        variant: "destructive" as const,
      };
    }

    if (isApiHealthy) {
      return {
        icon: CheckCircle,
        color: "text-green-600",
        bgColor: "bg-green-50 border-green-200",
        label: "API Opérationnelle",
        variant: "success" as const,
      };
    }

    return {
      icon: AlertCircle,
      color: "text-yellow-600",
      bgColor: "bg-yellow-50 border-yellow-200",
      label: "Vérification...",
      variant: "warning" as const,
    };
  };

  const config = getStatusConfig();
  const Icon = config.icon;

  if (!isVisible && isApiHealthy) {
    return (
      <motion.div
        className="fixed top-4 right-4 z-50"
        initial={{ opacity: 0, scale: 0.8 }}
        animate={{ opacity: 1, scale: 1 }}
        whileHover={{ scale: 1.05 }}
      >
        <Badge
          variant="success"
          className="cursor-pointer"
          onClick={() => setIsVisible(true)}
        >
          <Activity className="w-3 h-3 mr-1" />
          API OK
        </Badge>
      </motion.div>
    );
  }

  return (
    <AnimatePresence>
      {isVisible && (
        <motion.div
          className="fixed top-4 right-4 z-50 max-w-sm"
          initial={{ opacity: 0, y: -50 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -50 }}
          transition={{ duration: 0.3 }}
        >
          <Card className={`${config.bgColor} shadow-lg`}>
            <CardContent className="p-4">
              <div className="flex items-center gap-3">
                <Icon className={`w-5 h-5 ${config.color}`} />
                <div className="flex-1">
                  <div className="flex items-center justify-between">
                    <span className="font-medium text-sm">{config.label}</span>
                    <button
                      onClick={() => setIsVisible(false)}
                      className="text-gray-400 hover:text-gray-600 text-sm"
                    >
                      ×
                    </button>
                  </div>
                  {healthData && (
                    <div className="text-xs text-muted-foreground mt-1">
                      <div className="flex items-center gap-1">
                        <Clock className="w-3 h-3" />
                        Version {healthData.version}
                      </div>
                      {healthData.openai_agents_available && (
                        <div className="text-xs text-green-600 mt-1">
                          OpenAI Agents disponibles
                        </div>
                      )}
                      {!healthData.openai_agents_available && (
                        <div className="text-xs text-orange-600 mt-1">
                          OpenAI Agents indisponibles
                        </div>
                      )}
                    </div>
                  )}
                  {apiError && (
                    <p className="text-xs text-red-600 mt-1">
                      Impossible de se connecter à l&apos;API
                    </p>
                  )}
                </div>
              </div>
            </CardContent>
          </Card>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
