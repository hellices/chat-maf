import os
import re
from typing import AsyncGenerator

from agent.website_assistant_agent import WebsiteAssistantAgent
from models.analysis_request import AnalysisRequest
from tools.progressive_data_sources import fetch_web_content, fetch_playwright_content


async def call_website_assistant(
    message: str, url: str, seo_context: dict | None = None
) -> AsyncGenerator[str, None]:
    """Progressive website analysis with web scraper and Playwright."""
    assistant = WebsiteAssistantAgent()
    quality_threshold = int(os.getenv("QUALITY_THRESHOLD", "80"))
    response_history = []

    scraper_data = await fetch_web_content(url)
    yield "**Step 1: Analyzing with web scraper...**\n\n"

    request = AnalysisRequest(
        message=message,
        url=url,
        seo_context=seo_context,
        website_content=scraper_data,
        history=None,
    )

    response = ""
    async for chunk in assistant.analyze_website(request):
        response += chunk
        yield chunk

    response_history.append(response)
    confidence = _extract_confidence(response)

    if confidence >= quality_threshold:
        yield "\n\n---\n\n*[Analysis Complete]*\n"
        return

    yield "\n\n---\n\n*[Fetching dynamic content with Playwright...]*\n\n"
    playwright_data = await fetch_playwright_content(url)
    yield "**Step 2: Analyzing with Playwright dynamic content...**\n\n"

    request = AnalysisRequest(
        message=message,
        url=url,
        seo_context=seo_context,
        website_content=scraper_data,
        playwright_content=playwright_data,
        history=response_history,
    )

    async for chunk in assistant.analyze_website(request):
        yield chunk

    yield "\n\n---\n\n*[Complete Analysis Finished]*\n"


def _extract_confidence(text: str) -> int:
    """Extract confidence score from response."""
    match = re.search(r"\[CONFIDENCE:\s*(\d+)\]", text, re.IGNORECASE)
    return int(match.group(1)) if match else 0
