"""
Script de migration pour réassigner les extractions sans hubspot_portal_id
au portail local par défaut ou au portail de l'utilisateur.

Usage:
    python -m api.scripts.migrate_extractions_portal
"""

import asyncio
import sys
from pathlib import Path

# Ajouter le répertoire parent au path pour les imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from core.database import AsyncSessionLocal
from models.db_models import CompanyExtraction, HubSpotPortal, User
from core.config import settings
from uuid import UUID
import logging

logger = logging.getLogger(__name__)


async def migrate_extractions_portal():
    """Migre les extractions sans hubspot_portal_id vers le portail approprié."""
    async with AsyncSessionLocal() as db:
        print("=" * 80)
        print("🔄 MIGRATION DES EXTRACTIONS - ASSIGNATION AU PORTAL")
        print("=" * 80)
        
        # 1. Compter les extractions sans portal
        result = await db.execute(
            select(CompanyExtraction)
            .where(CompanyExtraction.hubspot_portal_id.is_(None))
        )
        extractions_without_portal = result.scalars().all()
        
        print(f"\n📊 Extractions sans portal_id: {len(extractions_without_portal)}")
        
        if len(extractions_without_portal) == 0:
            print("✅ Aucune extraction à migrer")
            return
        
        # 2. Déterminer le portail cible
        # Par défaut, utiliser le portail local
        portal_uuid = UUID(settings.LOCAL_DEFAULT_PORTAL_ID)
        
        # Vérifier si le portail existe
        result = await db.execute(
            select(HubSpotPortal).where(HubSpotPortal.id == portal_uuid)
        )
        portal = result.scalar_one_or_none()
        
        if not portal:
            print(f"❌ Portail local {portal_uuid} introuvable")
            print("   Création du portail local...")
            portal = HubSpotPortal(
                id=portal_uuid,
                hubspot_portal_id=0,
                name="Local Development",
                domain="localhost",
                is_active=True
            )
            db.add(portal)
            await db.flush()
            print(f"✅ Portail local créé: {portal_uuid}")
        else:
            print(f"✅ Portail local trouvé: {portal.name} ({portal_uuid})")
        
        # 3. Mettre à jour les extractions
        print(f"\n🔄 Mise à jour de {len(extractions_without_portal)} extractions...")
        
        updated = await db.execute(
            update(CompanyExtraction)
            .where(CompanyExtraction.hubspot_portal_id.is_(None))
            .values(hubspot_portal_id=portal_uuid)
        )
        
        await db.commit()
        
        print(f"✅ {updated.rowcount} extractions mises à jour avec portal_id={portal_uuid}")
        
        # 4. Vérification
        result = await db.execute(
            select(CompanyExtraction)
            .where(CompanyExtraction.hubspot_portal_id == portal_uuid)
        )
        extractions = result.scalars().all()
        
        total_cost = sum(ext.cost_eur for ext in extractions if ext.cost_eur)
        total_tokens = sum(ext.total_tokens for ext in extractions if ext.total_tokens)
        
        print(f"\n📈 Statistiques après migration:")
        print(f"   • Extractions liées au portail: {len(extractions)}")
        print(f"   • Coût total: {total_cost:.2f}€")
        print(f"   • Tokens totaux: {total_tokens:,}")
        
        print("\n" + "=" * 80)
        print("✅ Migration terminée")


if __name__ == "__main__":
    asyncio.run(migrate_extractions_portal())

