"""
Service de cache in-memory pour les entités identifiées (Phase 1, Step 1.2)

Permet de cacher les entités déjà identifiées pour éviter des recherches redondantes
et réduire les coûts d'API.
Utilise un cache in-memory avec TTL (remplace Redis).
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

# TTL par défaut : 2 heures
DEFAULT_TTL_SECONDS = 7200


class EntityCacheService:
    """Service de cache in-memory pour les entités extraites"""

    def __init__(self, ttl_seconds: Optional[int] = None):
        """
        Initialise le service de cache

        Args:
            ttl_seconds: Durée de vie du cache en secondes (défaut: 7200 = 2h)
        """
        self.ttl_seconds = ttl_seconds or DEFAULT_TTL_SECONDS
        # Cache in-memory : {entity_name: (data, expires_at)}
        self._cache: Dict[str, tuple[Dict[str, Any], datetime]] = {}

        # Statistiques en mémoire
        self._stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "invalidations": 0,
        }

    def _normalize_key(self, entity_name: str) -> str:
        """
        Normalise le nom d'entité pour la clé de cache

        Args:
            entity_name: Nom légal de l'entité

        Returns:
            Clé normalisée (lowercase + trim)
        """
        return entity_name.lower().strip()

    async def get(self, entity_name: str) -> Optional[Dict[str, Any]]:
        """
        Récupère les données d'une entité depuis le cache

        Args:
            entity_name: Nom légal de l'entité

        Returns:
            Dict avec les données de l'entité si trouvée, None sinon
        """
        try:
            key = self._normalize_key(entity_name)
            now = datetime.now()

            # Vérifier si la clé existe et n'est pas expirée
            if key in self._cache:
                data, expires_at = self._cache[key]
                
                if expires_at > now:
                    self._stats["hits"] += 1
                    logger.debug(f"✅ Cache HIT pour entité: {entity_name}")
                    return data
                else:
                    # Expiré, supprimer
                    del self._cache[key]
                    logger.debug(f"⏰ Cache expiré pour entité: {entity_name}")

            self._stats["misses"] += 1
            logger.debug(f"❌ Cache MISS pour entité: {entity_name}")
            return None

        except Exception as e:
            logger.error(f"❌ Erreur lors de la lecture du cache pour {entity_name}: {e}")
            self._stats["misses"] += 1
            return None

    async def set(
        self,
        entity_name: str,
        entity_data: Dict[str, Any],
        ttl_override: Optional[int] = None
    ) -> bool:
        """
        Stocke les données d'une entité dans le cache

        Args:
            entity_name: Nom légal de l'entité
            entity_data: Données de l'entité à cacher (format dict)
            ttl_override: TTL personnalisé en secondes (optionnel)

        Returns:
            True si succès, False sinon
        """
        try:
            key = self._normalize_key(entity_name)
            ttl = ttl_override or self.ttl_seconds
            now = datetime.now()
            expires_at = now + timedelta(seconds=ttl)

            # Ajout de métadonnées
            cached_data = {
                **entity_data,
                "_cached_at": now.isoformat(),
                "_ttl": ttl,
            }

            # Stocker dans le cache in-memory
            self._cache[key] = (cached_data, expires_at)

            self._stats["sets"] += 1
            logger.debug(f"✅ Entité cachée: {entity_name} (TTL: {ttl}s)")
            return True

        except Exception as e:
            logger.error(f"❌ Erreur lors de l'écriture du cache pour {entity_name}: {e}")
            return False

    async def invalidate(self, entity_name: str) -> bool:
        """
        Invalide (supprime) une entité du cache

        Args:
            entity_name: Nom légal de l'entité

        Returns:
            True si l'entité a été supprimée, False sinon
        """
        try:
            key = self._normalize_key(entity_name)

            if key in self._cache:
                del self._cache[key]
                self._stats["invalidations"] += 1
                logger.debug(f"✅ Cache invalidé pour: {entity_name}")
                return True
            else:
                logger.debug(f"ℹ️ Aucun cache à invalider pour: {entity_name}")
                return False

        except Exception as e:
            logger.error(f"❌ Erreur lors de l'invalidation du cache pour {entity_name}: {e}")
            return False

    async def invalidate_pattern(self, pattern: str = "*") -> int:
        """
        Invalide toutes les entités correspondant à un pattern

        Args:
            pattern: Pattern de recherche (ex: "acme*" pour toutes les entités commençant par "acme")

        Returns:
            Nombre d'entités invalidées
        """
        try:
            import fnmatch
            
            pattern_lower = pattern.lower()
            keys_to_delete = []
            
            # Trouver les clés correspondantes
            for key in list(self._cache.keys()):
                if fnmatch.fnmatch(key, pattern_lower):
                    keys_to_delete.append(key)
            
            # Supprimer les clés trouvées
            deleted_count = 0
            for key in keys_to_delete:
                del self._cache[key]
                deleted_count += 1
            
            if deleted_count > 0:
                self._stats["invalidations"] += deleted_count
                logger.info(f"✅ {deleted_count} entrées de cache invalidées (pattern: {pattern})")
                return deleted_count
            else:
                logger.debug(f"ℹ️ Aucune entrée trouvée pour le pattern: {pattern}")
                return 0

        except Exception as e:
            logger.error(f"❌ Erreur lors de l'invalidation par pattern '{pattern}': {e}")
            return 0

    def get_stats(self) -> Dict[str, Any]:
        """
        Récupère les statistiques du cache

        Returns:
            Dict avec hits, misses, sets, invalidations, hit_rate
        """
        total_requests = self._stats["hits"] + self._stats["misses"]
        hit_rate = (
            self._stats["hits"] / total_requests * 100
            if total_requests > 0
            else 0.0
        )

        return {
            **self._stats,
            "total_requests": total_requests,
            "hit_rate_percent": round(hit_rate, 2),
        }

    async def cleanup_expired(self):
        """Nettoie les entrées expirées du cache"""
        now = datetime.now()
        expired_keys = [
            key for key, (_, expires_at) in self._cache.items()
            if expires_at <= now
        ]
        
        for key in expired_keys:
            del self._cache[key]
        
        if expired_keys:
            logger.debug(f"🧹 {len(expired_keys)} entrées expirées nettoyées du cache")

    async def close(self):
        """Ferme le service de cache (vide le cache)"""
        self._cache.clear()
        logger.info("✅ Cache EntityCacheService vidé")


# Instance globale du service
entity_cache = EntityCacheService()
