'use client';

import { useState, useEffect, useCallback, useRef } from 'react';

const WS_URL = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8012';

interface AgentState {
  name: string;
  status: string;
  progress: number;
  message: string;
  started_at?: string;
  updated_at?: string;
}

interface ExtractionProgress {
  session_id: string;
  company_name: string;
  overall_status: string;
  overall_progress: number;
  agents: AgentState[];
  started_at?: string;
  updated_at?: string;
}

export function useExtractionWebSocket(sessionId: string | null) {
  const [progress, setProgress] = useState<ExtractionProgress | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  const connect = useCallback(() => {
    if (!sessionId) {
      console.log('❌ Pas de session_id, connexion annulée');
      return;
    }

    // Nettoyer l'ancienne connexion si elle existe
    if (wsRef.current) {
      wsRef.current.close();
    }

    try {
      console.log(`🔌 Connexion WebSocket: ${WS_URL}/ws/status/${sessionId}`);
      const ws = new WebSocket(`${WS_URL}/ws/status/${sessionId}`);
      wsRef.current = ws;

      ws.onopen = () => {
        console.log(`✅ WebSocket connecté: ${sessionId}`);
        setIsConnected(true);
        setError(null);
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);

          if (data.type === 'ping') {
            // Répondre au ping pour maintenir la connexion
            if (ws.readyState === WebSocket.OPEN) {
              ws.send(JSON.stringify({
                type: 'pong',
                timestamp: new Date().toISOString()
              }));
            }
          } else {
            // Mise à jour du progrès
            console.log('📊 Mise à jour progrès:', data.overall_status, `${Math.round(data.overall_progress * 100)}%`);
            setProgress(data);
          }
        } catch (err) {
          console.error('❌ Erreur parsing WebSocket:', err);
        }
      };

      ws.onerror = (err) => {
        console.error('❌ Erreur WebSocket:', err);
        setError('Erreur de connexion WebSocket');
        setIsConnected(false);
      };

      ws.onclose = (event) => {
        console.log(`🔌 WebSocket fermé (code: ${event.code}, reason: ${event.reason})`);
        setIsConnected(false);

        // Auto-reconnexion après 3s si la session est toujours active
        // Ne pas reconnecter si status = completed ou error
        if (progress?.overall_status !== 'completed' && progress?.overall_status !== 'error') {
          reconnectTimeoutRef.current = setTimeout(() => {
            if (sessionId) {
              console.log('🔄 Tentative de reconnexion...');
              connect();
            }
          }, 3000);
        }
      };
    } catch (err) {
      console.error('❌ Erreur création WebSocket:', err);
      setError(err instanceof Error ? err.message : 'Erreur inconnue');
    }
  }, [sessionId, progress?.overall_status]);

  useEffect(() => {
    if (sessionId) {
      connect();
    }

    return () => {
      // Nettoyage à la déconnexion
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [sessionId, connect]);

  return { progress, isConnected, error };
}
