"""
Configuration module for company agents extraction.

This module contains all configuration constants, settings, and metadata
for the extraction pipeline.
"""

from .extraction_config import (
    URL_TIMEOUT_S,
    URL_ALLOWED_STATUSES,
    URL_REQUEST_HEADERS,
    MAX_TURNS,
    ENABLE_URL_FILTERING,
    ENABLE_FRESHNESS_FILTERING,
)

from .agent_config import (
    DEFAULT_TOOL_NAMES,
    DEFAULT_EXTRACTION_STEPS,
    DEFAULT_SUB_AGENTS,
    get_all_tools_names,
    get_agent_info,
    get_extraction_steps,
    get_sub_agents_info,
)

__all__ = [
    # Extraction config
    "URL_TIMEOUT_S",
    "URL_ALLOWED_STATUSES", 
    "URL_REQUEST_HEADERS",
    "MAX_TURNS",
    "ENABLE_URL_FILTERING",
    "ENABLE_FRESHNESS_FILTERING",
    # Agent config
    "DEFAULT_TOOL_NAMES",
    "DEFAULT_EXTRACTION_STEPS",
    "DEFAULT_SUB_AGENTS",
    "get_all_tools_names",
    "get_agent_info",
    "get_extraction_steps",
    "get_sub_agents_info",
]
