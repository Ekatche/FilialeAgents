"""
Modèles de données API pour l'extraction d'informations d'entreprise
"""

from typing import List, Optional, Literal
from pydantic import BaseModel, Field


class CompanyExtractionRequest(BaseModel):
    """Requête pour l'extraction d'informations d'entreprise"""

    company_name: str = Field(description="Nom de l'entreprise à analyser")
    deep_search: Optional[bool] = Field(
        default=False,
        description="Mode de recherche approfondie (Perplexity) vs simple (GPT-4o-search)"
    )


class URLExtractionRequest(BaseModel):
    """Requête pour l'extraction d'informations d'entreprise depuis une URL"""

    url: str = Field(description="URL de l'entreprise à analyser")
    include_subsidiaries: Optional[bool] = Field(
        default=True, description="Inclure les filiales"
    )
    max_subsidiaries: Optional[int] = Field(
        default=50, description="Nombre maximum de filiales"
    )
    deep_search: Optional[bool] = Field(
        default=False,
        description="Mode de recherche approfondie (Perplexity) vs simple (GPT-4o-search)"
    )


class CompanyExtractionResponse(BaseModel):
    """Réponse de l'extraction d'informations d'entreprise"""

    company_name: str
    headquarters_address: str
    headquarters_city: str
    headquarters_country: str
    parent_company: Optional[str] = None
    subsidiaries: List[str] = []
    subsidiaries_details: List[dict] = []
    core_business: str
    industry_sector: str
    revenue: Optional[str] = None
    employee_count: Optional[str] = None
    confidence_score: float
    sources: List[str] = []
    extraction_date: str
    extraction_status: str
    total_subsidiaries: int
    detailed_subsidiaries: int
    optimization_note: str
    processing_time_seconds: float
    error_message: Optional[str] = None
    source_url: Optional[str] = None
    session_id: str


class AsyncExtractionResponse(BaseModel):
    """Réponse pour le démarrage d'une extraction asynchrone"""

    session_id: str = Field(description="ID de session pour suivre l'extraction")
    status: Literal["started", "queued"] = Field(
        description="Statut du démarrage de l'extraction"
    )
    message: str = Field(description="Message descriptif")


class HealthCheckResponse(BaseModel):
    """Réponse pour le health check"""

    status: str
    timestamp: str
    version: str
    openai_agents_available: bool
