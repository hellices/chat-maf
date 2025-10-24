"""
Schema caching utilities for NL2SQL workflow.
Prevents redundant disk reads of m_schema.json.
"""

import json
import logging
from functools import lru_cache
from pathlib import Path
from typing import Dict, Any

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def load_m_schema() -> Dict[str, Any]:
    """
    Load and cache M-Schema in memory.

    Uses LRU cache to ensure the schema is only loaded once per process.

    Returns:
        Dictionary containing all database schemas

    Raises:
        FileNotFoundError: If m_schema.json doesn't exist
    """
    m_schema_path = Path(__file__).parent / "spider" / "m_schema.json"

    if not m_schema_path.exists():
        raise FileNotFoundError(
            f"M-Schema file not found: {m_schema_path}\n"
            "Please run: python database/generate_m_schema.py"
        )

    logger.info(f"Loading M-Schema from {m_schema_path}")

    with open(m_schema_path, "r", encoding="utf-8") as f:
        m_schema = json.load(f)

    logger.info(f"Loaded M-Schema with {len(m_schema)} databases")
    return m_schema


def invalidate_schema_cache():
    """
    Invalidate the schema cache.
    Call this after regenerating m_schema.json.
    """
    load_m_schema.cache_clear()
    logger.info("Schema cache invalidated")
