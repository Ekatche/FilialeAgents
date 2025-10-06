from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, Any, Optional
import uuid
import logging

from status import status_manager
from services.agent_tracking_service import agent_tracking_service

from .extraction_manager import orchestrate_extraction

logger = logging.getLogger(__name__)


async def extract_company_data(
    input_query: str,
    *,
    session_id: Optional[str] = None,
    include_subsidiaries: bool = True,
    force_company_profile: Optional[str] = None,
    max_turns: int = 4,
) -> Dict[str, Any]:
    sid = session_id or str(uuid.uuid4())

    await agent_tracking_service.start_extraction_tracking(sid, input_query)

    try:
        result = await orchestrate_extraction(
            input_query,
            session_id=sid,
            include_subsidiaries=include_subsidiaries,
        )

        result.setdefault(
            "extraction_metadata",
            {"input_type": "url" if input_query.startswith("http") else "name"},
        )
        result.setdefault("extraction_date", datetime.now(timezone.utc).isoformat())

        await status_manager.store_extraction_results(sid, result)
        await agent_tracking_service.complete_extraction_tracking(sid, result)
        return result
    except Exception as exc:
        logger.exception("❌ Échec extraction [Session: %s]", sid)
        await agent_tracking_service.error_extraction_tracking(sid, str(exc))
        raise
