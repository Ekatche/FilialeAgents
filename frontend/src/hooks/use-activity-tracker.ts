'use client';

import { useEffect, useRef, useCallback } from 'react';

interface UseActivityTrackerOptions {
  /**
   * Temps d'inactivité en millisecondes avant de considérer l'utilisateur comme inactif
   * Par défaut: 5 minutes (300000 ms)
   */
  inactivityThreshold?: number;
  
  /**
   * Callback appelé lorsque l'utilisateur devient inactif
   */
  onInactive?: () => void;
  
  /**
   * Callback appelé lorsque l'utilisateur redevient actif après une période d'inactivité
   */
  onActive?: () => void;
  
  /**
   * Événements à écouter pour détecter l'activité
   * Par défaut: tous les événements de base
   */
  events?: string[];
}

/**
 * Hook pour détecter l'activité utilisateur sur la page
 * 
 * @example
 * ```tsx
 * const { isActive, lastActivityTime } = useActivityTracker({
 *   inactivityThreshold: 300000, // 5 minutes
 *   onInactive: () => console.log('User inactive'),
 *   onActive: () => console.log('User active'),
 * });
 * ```
 */
export function useActivityTracker(options: UseActivityTrackerOptions = {}) {
  const {
    inactivityThreshold = 300000, // 5 minutes par défaut
    onInactive,
    onActive,
    events = [
      'mousedown',
      'mousemove',
      'keypress',
      'scroll',
      'touchstart',
      'click',
      'focus',
    ],
  } = options;

  const lastActivityTime = useRef<number>(Date.now());
  const isActiveRef = useRef<boolean>(true);
  const inactivityTimerRef = useRef<NodeJS.Timeout | null>(null);
  const wasInactiveRef = useRef<boolean>(false);

  const onActiveRef = useRef(onActive);
  const onInactiveRef = useRef(onInactive);

  // Mettre à jour les refs quand les callbacks changent
  useEffect(() => {
    onActiveRef.current = onActive;
    onInactiveRef.current = onInactive;
  }, [onActive, onInactive]);

  const handleActivity = useCallback(() => {
    const now = Date.now();
    const wasInactive = !isActiveRef.current;
    
    lastActivityTime.current = now;
    
    // Si l'utilisateur était inactif et redevient actif
    if (wasInactive) {
      isActiveRef.current = true;
      wasInactiveRef.current = false;
      onActiveRef.current?.();
    }
    
    // Réinitialiser le timer d'inactivité
    if (inactivityTimerRef.current) {
      clearTimeout(inactivityTimerRef.current);
    }
    
    inactivityTimerRef.current = setTimeout(() => {
      if (!wasInactiveRef.current) {
        isActiveRef.current = false;
        wasInactiveRef.current = true;
        onInactiveRef.current?.();
      }
    }, inactivityThreshold);
  }, [inactivityThreshold]);

  useEffect(() => {
    // Ajouter les listeners d'événements
    events.forEach((event) => {
      window.addEventListener(event, handleActivity, { passive: true });
    });

    // Initialiser le timer d'inactivité
    inactivityTimerRef.current = setTimeout(() => {
      isActiveRef.current = false;
      wasInactiveRef.current = true;
      onInactive?.();
    }, inactivityThreshold);

    // Nettoyer les listeners et le timer
    return () => {
      events.forEach((event) => {
        window.removeEventListener(event, handleActivity);
      });
      
      if (inactivityTimerRef.current) {
        clearTimeout(inactivityTimerRef.current);
      }
    };
  }, [events, handleActivity, inactivityThreshold, onInactive]);

  return {
    /**
     * Indique si l'utilisateur est actuellement actif
     */
    isActive: isActiveRef.current,
    
    /**
     * Timestamp de la dernière activité détectée
     */
    lastActivityTime: lastActivityTime.current,
  };
}

