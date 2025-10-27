"""
Cost tracking service for AI model usage.
Tracks token usage and calculates costs for each extraction.
"""

from datetime import datetime
from typing import Dict, Any, Optional, List
from decimal import Decimal
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from models.db_models import CompanyExtraction

logger = logging.getLogger(__name__)


class ModelPricing:
    """
    Pricing information for AI models (in USD per 1M tokens).
    Updated as of January 2025.
    """

    # OpenAI GPT-4o Pricing (standard)
    GPT_4O = {
        "name": "gpt-4o",
        "input_price_per_1m": 2.50,  # $2.50 per 1M input tokens
        "output_price_per_1m": 10.00,  # $10.00 per 1M output tokens
    }

    # OpenAI GPT-4o-mini Pricing (optimized)
    GPT_4O_MINI = {
        "name": "gpt-4o-mini",
        "input_price_per_1m": 0.15,  # $0.15 per 1M input tokens
        "output_price_per_1m": 0.60,  # $0.60 per 1M output tokens
    }

    # OpenAI GPT-4o Search Preview (web search capability)
    GPT_4O_SEARCH = {
        "name": "gpt-4o-search-preview",
        "input_price_per_1m": 2.50,  # Same as GPT-4o
        "output_price_per_1m": 10.00,
    }

    # Perplexity Sonar Pro (deep research)
    SONAR_PRO = {
        "name": "sonar-pro",
        "input_price_per_1m": 3.00,  # $3.00 per 1M input tokens (Perplexity pricing)
        "output_price_per_1m": 15.00,  # $15.00 per 1M output tokens
    }

    # Exchange rate USD to EUR
    # In production, fetch this from a live API like ECB or exchangerate-api.com
    USD_TO_EUR_RATE = Decimal("0.92")  # Approximate rate, update regularly

    @classmethod
    def get_pricing(cls, model_name: str) -> Optional[Dict[str, Any]]:
        """
        Get pricing for a specific model.

        Args:
            model_name: Name of the AI model

        Returns:
            Dictionary with pricing information or None if model not found
        """
        # Normalize model name
        model_lower = model_name.lower().strip()

        # Map model names to pricing
        if "gpt-4o-search" in model_lower:
            return cls.GPT_4O_SEARCH
        elif "gpt-4o-mini" in model_lower or "gpt-4.1-mini" in model_lower:
            # Note: gpt-4.1-mini in code likely means gpt-4o-mini
            return cls.GPT_4O_MINI
        elif "gpt-4o" in model_lower:
            return cls.GPT_4O
        elif "sonar-pro" in model_lower or "sonar" in model_lower:
            return cls.SONAR_PRO
        else:
            # Default to GPT-4o-mini if unknown (most commonly used)
            return cls.GPT_4O_MINI

    @classmethod
    def calculate_cost_usd(
        cls,
        model_name: str,
        input_tokens: int,
        output_tokens: int
    ) -> Decimal:
        """
        Calculate cost in USD for token usage.

        Args:
            model_name: Name of the AI model
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens

        Returns:
            Cost in USD as Decimal
        """
        pricing = cls.get_pricing(model_name)
        if not pricing:
            return Decimal("0")

        # Calculate costs (price is per 1M tokens)
        input_cost = (
            Decimal(str(input_tokens))
            * Decimal(str(pricing["input_price_per_1m"]))
            / Decimal("1000000")
        )
        output_cost = (
            Decimal(str(output_tokens))
            * Decimal(str(pricing["output_price_per_1m"]))
            / Decimal("1000000")
        )

        total_cost = input_cost + output_cost
        return total_cost.quantize(Decimal("0.000001"))  # 6 decimal places

    @classmethod
    def calculate_cost_eur(
        cls,
        model_name: str,
        input_tokens: int,
        output_tokens: int
    ) -> Decimal:
        """
        Calculate cost in EUR for token usage.

        Args:
            model_name: Name of the AI model
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens

        Returns:
            Cost in EUR as Decimal
        """
        cost_usd = cls.calculate_cost_usd(model_name, input_tokens, output_tokens)
        cost_eur = cost_usd * cls.USD_TO_EUR_RATE
        return cost_eur.quantize(Decimal("0.000001"))  # 6 decimal places


class CostTrackingService:
    """Service for tracking and analyzing extraction costs."""

    @staticmethod
    def calculate_extraction_cost(
        models_usage: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Calculate total cost for an extraction based on model usage.

        Args:
            models_usage: List of dictionaries with model usage info
                [
                    {
                        "model": "gpt-4o",
                        "input_tokens": 1000,
                        "output_tokens": 500
                    },
                    {
                        "model": "sonar-pro",
                        "input_tokens": 2000,
                        "output_tokens": 1000
                    }
                ]

        Returns:
            Dictionary with cost breakdown:
            {
                "total_input_tokens": 3000,
                "total_output_tokens": 1500,
                "total_tokens": 4500,
                "total_cost_usd": 0.0625,
                "total_cost_eur": 0.0575,
                "models_breakdown": [...],
                "exchange_rate": 0.92
            }
        """
        total_input_tokens = 0
        total_output_tokens = 0
        total_cost_usd = Decimal("0")
        total_cost_eur = Decimal("0")
        model_breakdown = []

        for usage in models_usage:
            model_name = usage.get("model", "gpt-4o-mini")
            input_tokens = usage.get("input_tokens", 0)
            output_tokens = usage.get("output_tokens", 0)

            cost_usd = ModelPricing.calculate_cost_usd(
                model_name, input_tokens, output_tokens
            )
            cost_eur = ModelPricing.calculate_cost_eur(
                model_name, input_tokens, output_tokens
            )

            total_input_tokens += input_tokens
            total_output_tokens += output_tokens
            total_cost_usd += cost_usd
            total_cost_eur += cost_eur

            model_breakdown.append({
                "model": model_name,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "cost_usd": float(cost_usd),
                "cost_eur": float(cost_eur)
            })

        return {
            "total_input_tokens": total_input_tokens,
            "total_output_tokens": total_output_tokens,
            "total_tokens": total_input_tokens + total_output_tokens,
            "total_cost_usd": float(total_cost_usd),
            "total_cost_eur": float(total_cost_eur),
            "models_breakdown": model_breakdown,
            "exchange_rate": float(ModelPricing.USD_TO_EUR_RATE)
        }

    @staticmethod
    def calculate_tools_cost(
        models_usage: List[Dict[str, Any]],
        search_type: str,
        real_time_data: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Calculer les coûts des tools avec données en temps réel si disponibles.
        
        Args:
            models_usage: Liste des modèles utilisés par les agents principaux
            search_type: "simple" ou "advanced"
            real_time_data: Données de tracking en temps réel (optionnel)
            
        Returns:
            Dictionnaire avec les coûts des tools
        """
        # Si on a des données en temps réel, les utiliser
        if real_time_data:
            logger.info("💰 Utilisation des données de coûts en temps réel")
            return {
                "total_input_tokens": real_time_data.get("input_tokens", 0),
                "total_output_tokens": real_time_data.get("output_tokens", 0),
                "total_tokens": real_time_data.get("input_tokens", 0) + real_time_data.get("output_tokens", 0),
                "total_cost_usd": float(real_time_data.get("cost_usd", 0)),
                "total_cost_eur": float(real_time_data.get("cost_eur", 0)),
                "tools_breakdown": real_time_data.get("tools_breakdown", []),
                "real_time_tracking": True
            }
        
        # Essayer d'utiliser les tokens réels du ToolTokensTracker
        real_tool_data = None
        if session_id:
            try:
                from company_agents.metrics.tool_tokens_tracker import ToolTokensTracker
                
                # Récupérer les données de tracking réelles
                real_tool_data = ToolTokensTracker.get_session_tools(session_id)
                logger.info(f"🔧 Données réelles récupérées pour session {session_id}: {len(real_tool_data)} tools")
                
                # Si on a des données réelles, les utiliser
                if real_tool_data:
                    logger.info("💰 Utilisation des tokens réels au lieu des estimations")
                    return CostTrackingService._calculate_real_tools_cost(real_tool_data, search_type)
                else:
                    logger.info("⚠️ Aucune donnée réelle trouvée, utilisation des estimations")
                    
            except ImportError:
                logger.warning("⚠️ ToolTokensTracker non disponible, utilisation des estimations")
            except Exception as e:
                logger.warning(f"⚠️ Erreur lors de la récupération des données réelles: {e}")
        
        # Fallback vers les estimations si pas de données réelles
        logger.info("⚠️ Utilisation de l'estimation des coûts (pas de données temps réel)")
        
        tools_breakdown = []
        total_input_tokens = 0
        total_output_tokens = 0
        total_cost_usd = Decimal("0")
        total_cost_eur = Decimal("0")
        
        # Estimation basée sur les agents principaux (fallback)
        num_agents = len(models_usage)
        
        # Coûts des tools web_search et filiales_search
        # Estimation basée sur l'utilisation réelle observée (plus conservatrice)
        # Basé sur les données réelles : ~1 appel par agent avec tokens moyens
        # CORRECTION : Estimations réduites car les estimations précédentes étaient 3.7x trop élevées
        web_search_calls = max(1, num_agents)  # 1 appel par agent (au lieu de 1.5)
        filiales_search_calls = max(1, num_agents)  # 1 appel par agent (au lieu de 1.2)
        
        # Tool web_search (gpt-4o-search-preview)
        # Estimation basée sur l'usage réel observé : ~15k input / 7.5k output
        web_search_input_tokens = 15000  # Basé sur l'usage réel
        web_search_output_tokens = 7500   # Basé sur l'usage réel (50% input)
        web_search_cost_usd = ModelPricing.calculate_cost_usd(
            "gpt-4o-search-preview", web_search_input_tokens, web_search_output_tokens
        )
        web_search_cost_eur = web_search_cost_usd * ModelPricing.USD_TO_EUR_RATE
        # Coût des appels de recherche web : $10.00 pour 1000 appels
        web_search_calls_cost = Decimal(str((web_search_calls / 1000) * 10.00))
        web_search_cost_usd += web_search_calls_cost
        web_search_cost_eur += web_search_calls_cost * ModelPricing.USD_TO_EUR_RATE
        
        tools_breakdown.append({
            "model": "gpt-4o-search-preview (web_search)",
            "input_tokens": web_search_input_tokens,
            "output_tokens": web_search_output_tokens,
            "cost_usd": float(web_search_cost_usd),
            "cost_eur": float(web_search_cost_eur),
            "calls": web_search_calls
        })
        
        total_input_tokens += web_search_input_tokens
        total_output_tokens += web_search_output_tokens
        total_cost_usd += web_search_cost_usd
        total_cost_eur += web_search_cost_eur
        
        # Tool filiales_search (gpt-4o-search-preview)
        # Estimation basée sur l'usage réel observé : ~20k input / 10k output
        filiales_search_input_tokens = 20000  # Basé sur l'usage réel
        filiales_search_output_tokens = 10000  # Basé sur l'usage réel (50% input)
        filiales_search_cost_usd = ModelPricing.calculate_cost_usd(
            "gpt-4o-search-preview", filiales_search_input_tokens, filiales_search_output_tokens
        )
        filiales_search_cost_eur = filiales_search_cost_usd * ModelPricing.USD_TO_EUR_RATE
        # Coût des appels de recherche web : $10.00 pour 1000 appels
        filiales_search_calls_cost = Decimal(str((filiales_search_calls / 1000) * 10.00))
        filiales_search_cost_usd += filiales_search_calls_cost
        filiales_search_cost_eur += filiales_search_calls_cost * ModelPricing.USD_TO_EUR_RATE
        
        tools_breakdown.append({
            "model": "gpt-4o-search-preview (filiales_search)",
            "input_tokens": filiales_search_input_tokens,
            "output_tokens": filiales_search_output_tokens,
            "cost_usd": float(filiales_search_cost_usd),
            "cost_eur": float(filiales_search_cost_eur),
            "calls": filiales_search_calls
        })
        
        total_input_tokens += filiales_search_input_tokens
        total_output_tokens += filiales_search_output_tokens
        total_cost_usd += filiales_search_cost_usd
        total_cost_eur += filiales_search_cost_eur
        
        # Perplexity Sonar Pro pour les recherches avancées
        if search_type == "advanced":
            perplexity_tokens = 30000  # Estimation pour recherche approfondie
            perplexity_cost_usd = ModelPricing.calculate_cost_usd(
                "sonar-pro", perplexity_tokens, perplexity_tokens // 2
            )
            perplexity_cost_eur = perplexity_cost_usd * ModelPricing.USD_TO_EUR_RATE
            
            tools_breakdown.append({
                "model": "sonar-pro (perplexity)",
                "input_tokens": perplexity_tokens,
                "output_tokens": perplexity_tokens // 2,
                "cost_usd": float(perplexity_cost_usd),
                "cost_eur": float(perplexity_cost_eur),
                "calls": 1
            })
            
            total_input_tokens += perplexity_tokens
            total_output_tokens += perplexity_tokens // 2
            total_cost_usd += perplexity_cost_usd
            total_cost_eur += perplexity_cost_eur
        
        # Autres tools OpenAI selon la documentation officielle
        # Interpréteur de code : $0.03 par session (si utilisé)
        code_interpreter_sessions = 0  # Pas utilisé dans notre workflow actuel
        if code_interpreter_sessions > 0:
            code_interpreter_cost = Decimal(str(code_interpreter_sessions * 0.03))  # $0.03 par session
            tools_breakdown.append({
                "model": "code_interpreter",
                "input_tokens": 0,
                "output_tokens": 0,
                "cost_usd": code_interpreter_cost,
                "cost_eur": code_interpreter_cost * ModelPricing.USD_TO_EUR_RATE,
                "sessions": code_interpreter_sessions
            })
            total_cost_usd += code_interpreter_cost
            total_cost_eur += code_interpreter_cost * ModelPricing.USD_TO_EUR_RATE
        
        # File Search : $0.10 par Go de stockage par jour (premier Go gratuit)
        # Pas utilisé dans notre workflow actuel
        file_search_storage_gb = 0  # Pas utilisé dans notre workflow actuel
        if file_search_storage_gb > 0:
            file_search_cost = Decimal(str(max(0, file_search_storage_gb - 1) * 0.10))  # Premier Go gratuit
            tools_breakdown.append({
                "model": "file_search",
                "input_tokens": 0,
                "output_tokens": 0,
                "cost_usd": file_search_cost,
                "cost_eur": file_search_cost * ModelPricing.USD_TO_EUR_RATE,
                "storage_gb": file_search_storage_gb
            })
            total_cost_usd += file_search_cost
            total_cost_eur += file_search_cost * ModelPricing.USD_TO_EUR_RATE
        
        return {
            "total_input_tokens": total_input_tokens,
            "total_output_tokens": total_output_tokens,
            "total_tokens": total_input_tokens + total_output_tokens,
            "total_cost_usd": float(total_cost_usd),
            "total_cost_eur": float(total_cost_eur),
            "tools_breakdown": tools_breakdown,
            "web_search_calls": web_search_calls,
            "filiales_search_calls": filiales_search_calls,
            "perplexity_used": search_type == "advanced",
            "openai_tools_used": {
                "web_search": {
                    "calls": web_search_calls,
                    "cost_per_1000_calls": 10.00,  # Selon doc OpenAI
                    "tokens_cost": float(web_search_cost_usd - web_search_calls_cost)
                },
                "filiales_search": {
                    "calls": filiales_search_calls,
                    "cost_per_1000_calls": 10.00,  # Selon doc OpenAI
                    "tokens_cost": float(filiales_search_cost_usd - filiales_search_calls_cost)
                },
                "code_interpreter": {
                    "sessions": code_interpreter_sessions,
                    "cost_per_session": 0.03  # Selon doc OpenAI
                },
                "file_search": {
                    "storage_gb": file_search_storage_gb,
                    "cost_per_gb_per_day": 0.10,  # Selon doc OpenAI
                    "first_gb_free": True
                }
            }
        }

    @staticmethod
    def _calculate_real_tools_cost(
        real_tool_data: List[Dict[str, Any]],
        search_type: str
    ) -> Dict[str, Any]:
        """
        Calculer les coûts des tools basés sur les données réelles du ToolTokensTracker.
        
        Args:
            real_tool_data: Données réelles des tools trackés
            search_type: Type de recherche (simple/advanced)
            
        Returns:
            Dictionnaire avec les coûts réels des tools
        """
        logger.info("💰 Calcul des coûts basé sur les données réelles")
        
        total_input_tokens = 0
        total_output_tokens = 0
        total_cost_usd = Decimal("0")
        total_cost_eur = Decimal("0")
        tools_breakdown = []
        
        # Grouper les tools par type
        web_search_tools = [t for t in real_tool_data if "web_search" in t.get("tool", "")]
        filiales_search_tools = [t for t in real_tool_data if "subsidiary" in t.get("tool", "") or "filiales" in t.get("tool", "")]
        other_tools = [t for t in real_tool_data if "web_search" not in t.get("tool", "") and "subsidiary" not in t.get("tool", "") and "filiales" not in t.get("tool", "")]
        
        # Calculer les coûts pour chaque type de tool
        for tool_group, tool_name in [
            (web_search_tools, "web_search"),
            (filiales_search_tools, "subsidiary_search"),
            (other_tools, "other_tools")
        ]:
            if not tool_group:
                continue
                
            group_input_tokens = sum(t.get("input_tokens", 0) for t in tool_group)
            group_output_tokens = sum(t.get("output_tokens", 0) for t in tool_group)
            group_total_tokens = sum(t.get("total_tokens", 0) for t in tool_group)
            
            # Calculer le coût basé sur le modèle utilisé
            model_name = tool_group[0].get("model", "gpt-4o-search-preview")
            group_cost_usd = ModelPricing.calculate_cost_usd(
                model_name, group_input_tokens, group_output_tokens
            )
            group_cost_eur = group_cost_usd * ModelPricing.USD_TO_EUR_RATE
            
            # Ajouter les coûts des appels de recherche web ($10.00 pour 1000 appels)
            if tool_name == "web_search":
                web_search_calls = len(tool_group)
                calls_cost_usd = Decimal(str((web_search_calls / 1000) * 10.00))
                group_cost_usd += calls_cost_usd
                group_cost_eur += calls_cost_usd * ModelPricing.USD_TO_EUR_RATE
            
            total_input_tokens += group_input_tokens
            total_output_tokens += group_output_tokens
            total_cost_usd += group_cost_usd
            total_cost_eur += group_cost_eur
            
            tools_breakdown.append({
                "model": f"{model_name} ({tool_name})",
                "input_tokens": group_input_tokens,
                "output_tokens": group_output_tokens,
                "cost_usd": float(group_cost_usd),
                "cost_eur": float(group_cost_eur),
                "calls": len(tool_group),
                "real_data": True
            })
            
            logger.info(
                f"💰 {tool_name}: {group_input_tokens} in + {group_output_tokens} out = "
                f"{group_cost_eur:.4f}€ ({len(tool_group)} appels)"
            )
        
        return {
            "total_input_tokens": total_input_tokens,
            "total_output_tokens": total_output_tokens,
            "total_tokens": total_input_tokens + total_output_tokens,
            "total_cost_usd": float(total_cost_usd),
            "total_cost_eur": float(total_cost_eur),
            "tools_breakdown": tools_breakdown,
            "real_time_tracking": True
        }

    @staticmethod
    async def get_organization_costs(
        organization_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        db: AsyncSession = None
    ) -> Dict[str, Any]:
        """
        Get cost statistics for an organization.

        Args:
            organization_id: Organization UUID
            start_date: Optional start date filter
            end_date: Optional end date filter
            db: Database session

        Returns:
            Dictionary with cost statistics
        """
        query = select(CompanyExtraction).where(
            CompanyExtraction.organization_id == organization_id
        )

        if start_date:
            query = query.where(CompanyExtraction.created_at >= start_date)
        if end_date:
            query = query.where(CompanyExtraction.created_at <= end_date)

        result = await db.execute(query)
        extractions = result.scalars().all()

        total_cost_eur = Decimal("0")
        total_cost_usd = Decimal("0")
        total_tokens = 0
        total_searches = len(extractions)
        completed_searches = 0

        for extraction in extractions:
            if extraction.cost_eur:
                total_cost_eur += Decimal(str(extraction.cost_eur))
            if extraction.cost_usd:
                total_cost_usd += Decimal(str(extraction.cost_usd))
            if extraction.total_tokens:
                total_tokens += extraction.total_tokens
            if extraction.status.value == "completed":
                completed_searches += 1

        avg_cost_per_search_eur = (
            total_cost_eur / Decimal(str(completed_searches))
            if completed_searches > 0
            else Decimal("0")
        )

        return {
            "organization_id": organization_id,
            "total_searches": total_searches,
            "completed_searches": completed_searches,
            "total_cost_eur": float(total_cost_eur),
            "total_cost_usd": float(total_cost_usd),
            "total_tokens": total_tokens,
            "average_cost_per_search_eur": float(avg_cost_per_search_eur),
            "start_date": start_date.isoformat() if start_date else None,
            "end_date": end_date.isoformat() if end_date else None
        }

    @staticmethod
    async def get_monthly_costs(
        organization_id: str,
        year: int,
        month: int,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """
        Get cost statistics for a specific month.

        Args:
            organization_id: Organization UUID
            year: Year (e.g., 2025)
            month: Month (1-12)
            db: Database session

        Returns:
            Dictionary with monthly cost statistics
        """
        from datetime import date
        from calendar import monthrange

        # Get first and last day of month
        first_day = date(year, month, 1)
        last_day = date(year, month, monthrange(year, month)[1])

        start_datetime = datetime.combine(first_day, datetime.min.time())
        end_datetime = datetime.combine(last_day, datetime.max.time())

        return await CostTrackingService.get_organization_costs(
            organization_id,
            start_datetime,
            end_datetime,
            db
        )

    @staticmethod
    async def get_top_expensive_searches(
        organization_id: str,
        limit: int = 10,
        db: AsyncSession = None
    ) -> List[Dict[str, Any]]:
        """
        Get the most expensive searches for an organization.

        Args:
            organization_id: Organization UUID
            limit: Number of results to return
            db: Database session

        Returns:
            List of expensive searches
        """
        query = (
            select(CompanyExtraction)
            .where(CompanyExtraction.organization_id == organization_id)
            .where(CompanyExtraction.cost_eur.isnot(None))
            .order_by(CompanyExtraction.cost_eur.desc())
            .limit(limit)
        )

        result = await db.execute(query)
        extractions = result.scalars().all()

        return [
            {
                "id": str(extraction.id),
                "company_name": extraction.company_name,
                "created_at": extraction.created_at.isoformat(),
                "cost_eur": extraction.cost_eur,
                "cost_usd": extraction.cost_usd,
                "total_tokens": extraction.total_tokens,
                "input_tokens": extraction.input_tokens,
                "output_tokens": extraction.output_tokens,
                "models_usage": extraction.models_usage,
                "subsidiaries_count": extraction.subsidiaries_count,
                "processing_time": extraction.processing_time
            }
            for extraction in extractions
        ]

    @staticmethod
    def estimate_search_cost(
        extraction_type: str = "simple",
        has_subsidiaries: bool = True,
        subsidiaries_count: int = 5
    ) -> Dict[str, Any]:
        """
        Estimate the cost of a search before execution.

        Args:
            extraction_type: "simple" or "advanced"
            has_subsidiaries: Whether the company has subsidiaries
            subsidiaries_count: Estimated number of subsidiaries

        Returns:
            Dictionary with cost estimate
        """
        # Base extraction (Company Analyzer + Information Extractor)
        # Estimate: ~5K input + ~2K output tokens with gpt-4o-mini
        base_usage = [
            {"model": "gpt-4o-mini", "input_tokens": 5000, "output_tokens": 2000}
        ]

        # If has subsidiaries
        if has_subsidiaries:
            # Subsidiary extraction: ~10K input + ~5K output per subsidiary with gpt-4o
            # Meta Validator: ~8K input + ~3K output with gpt-4o
            # Data Restructurer: ~6K input + ~2K output with gpt-4o

            subsidiary_tokens = subsidiaries_count * 15000  # ~15K total per subsidiary

            base_usage.extend([
                {"model": "gpt-4o", "input_tokens": subsidiary_tokens // 2, "output_tokens": subsidiary_tokens // 3},
                {"model": "gpt-4o", "input_tokens": 8000, "output_tokens": 3000},
                {"model": "gpt-4o", "input_tokens": 6000, "output_tokens": 2000}
            ])

            # If advanced search, add Perplexity usage
            if extraction_type == "advanced":
                # Estimate ~20K input + ~10K output with sonar-pro
                base_usage.append(
                    {"model": "sonar-pro", "input_tokens": 20000, "output_tokens": 10000}
                )
            else:
                # Simple search uses gpt-4o-search-preview
                base_usage.append(
                    {"model": "gpt-4o-search-preview", "input_tokens": 15000, "output_tokens": 8000}
                )

        cost_breakdown = CostTrackingService.calculate_extraction_cost(base_usage)

        return {
            **cost_breakdown,
            "estimate_type": "approximate",
            "extraction_type": extraction_type,
            "estimated_subsidiaries": subsidiaries_count if has_subsidiaries else 0
        }

    async def get_extraction_cost(self, session_id: str, db: AsyncSession) -> Optional[Dict[str, Any]]:
        """
        Get cost information for a specific extraction by session_id.
        
        Args:
            session_id: The session ID of the extraction
            db: Database session
            
        Returns:
            Dictionary with cost information or None if not found
        """
        result = await db.execute(
            select(CompanyExtraction).where(CompanyExtraction.session_id == session_id)
        )
        extraction = result.scalar_one_or_none()
        
        if not extraction:
            return None
            
        return {
            "total_cost_usd": extraction.cost_usd,
            "total_cost_eur": extraction.cost_eur,
            "total_tokens": extraction.total_tokens,
            "models_used": extraction.models_usage.get("models_breakdown", []) if extraction.models_usage else []
        }


# Global instance
cost_tracking_service = CostTrackingService()
