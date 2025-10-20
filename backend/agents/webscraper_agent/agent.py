"""
Web Scraper Agent - Static HTML Content Fetcher

Specialized agent that only uses fetch_web_content tool for static HTML scraping.
"""

from agent_framework.azure import AzureOpenAIResponsesClient
from azure.identity import AzureCliCredential
import asyncio
import requests
from typing import Annotated
from bs4 import BeautifulSoup

from markdownify import markdownify as md


async def fetch_web_content(
    url: Annotated[str, "The URL of the website to fetch static HTML content from"],
) -> Annotated[str, "Static HTML content in markdown format"]:
    """Fetch static HTML content from a website and convert to markdown. Use this for standard websites."""
    try:
        loop = asyncio.get_event_loop()

        def scrape():
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            }
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, "html.parser")
            for element in soup(["script", "style", "nav", "header", "footer"]):
                element.decompose()

            body = soup.find("body") or soup
            markdown = md(str(body), heading_style="atx", bullets="-")

            lines = [line for line in markdown.split("\n") if line.strip()]
            content = "\n".join(lines)

            if len(content) > 5000:
                content = content[:5000] + "...\n[Truncated]"

            return content

        content = await loop.run_in_executor(None, scrape)
        return f"Web Scraper Data:\n{content}"

    except Exception as e:
        return f"Web scraper error: {str(e)}"


def create_agent():
    client = AzureOpenAIResponsesClient(
        credential=AzureCliCredential(),
    )

    return client.create_agent(
        instructions="""You are a web scraper assistant specialized in static HTML content.

Your task:
1. Use fetch_web_content to retrieve static HTML from the given URL
2. Analyze the content and provide a concise summary
3. Focus on main content, headings, and key information
4. Evaluate if the content is sufficient or if dynamic scraping might be needed

Response format:
- Keep answers brief and focused (2-3 sentences for summary)
- Use **bold** for key findings
- End with: [CONFIDENCE: XX] where XX is 0-100

Confidence guidelines:
- 0-30: Very limited content, likely needs JavaScript rendering
- 31-60: Some content visible, but may be incomplete
- 61-85: Good content, appears mostly complete
- 86-100: Comprehensive content, no dynamic loading detected""",
        name="WebscraperAgent",
        tools=[fetch_web_content],  # Only static HTML scraping
    )


# Create default agent for DevUI auto-discovery
agent = create_agent()
