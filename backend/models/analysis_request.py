"""
Analysis Request Models for Website Analysis
"""

from typing import Optional, Dict, Any, List
from pydantic import BaseModel


class AnalysisRequest(BaseModel):
    """Structured request for website analysis"""

    message: str
    url: str
    seo_context: Optional[Dict[str, Any]] = None
    website_content: Optional[str] = None
    playwright_content: Optional[str] = None
    history: Optional[List[str]] = None  # Previous responses to avoid duplication
