"""
Playwright Agent - Dynamic JavaScript Content Fetcher

Specialized agent that only uses fetch_playwright_content tool for dynamic content scraping.
"""

from agent_framework.azure import AzureOpenAIResponsesClient
from azure.identity import AzureCliCredential
from typing import Annotated
from bs4 import BeautifulSoup

from markdownify import markdownify as md


async def fetch_playwright_content(
    url: Annotated[
        str, "The URL of the website to fetch dynamic JavaScript-rendered content from"
    ],
) -> str:
    """Fetch dynamic JavaScript-rendered content from a website using Playwright. Use this when the website requires JavaScript execution or has dynamic/lazy-loaded content."""
    try:
        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto(url, wait_until="networkidle")

            # Scroll down to trigger lazy-loaded content
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight / 2)")
            await page.wait_for_timeout(1000)

            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await page.wait_for_timeout(1000)

            # Get HTML content
            html_content = await page.evaluate(
                """() => {
                    const body = document.body.cloneNode(true);
                    body.querySelectorAll('script, style, nav, header, footer').forEach(el => el.remove());
                    return body.innerHTML;
                }"""
            )

            await browser.close()

            # Convert to markdown
            soup = BeautifulSoup(html_content, "html.parser")
            markdown = md(str(soup), heading_style="atx", bullets="-")

            lines = [line for line in markdown.split("\n") if line.strip()]
            content = "\n".join(lines)

            if len(content) > 5000:
                content = content[:5000] + "...\n[Truncated]"

            return f"Playwright Dynamic Content:\n{content}"

    except ImportError:
        return "Playwright not installed: pip install playwright && playwright install chromium"
    except Exception as e:
        return f"Playwright error: {str(e)}"


def create_agent():
    """Create a Playwright agent that fetches dynamic JavaScript-rendered content."""
    client = AzureOpenAIResponsesClient(
        credential=AzureCliCredential(),
    )

    return client.create_agent(
        instructions="""You are a Playwright assistant specialized in dynamic JavaScript-rendered content.

Your task:
1. Use fetch_playwright_content to retrieve fully-rendered content including dynamic elements
2. Analyze JavaScript-loaded content, lazy-loaded images, and interactive elements
3. Provide a comprehensive analysis of the complete page
4. Highlight any dynamic content that wasn't visible in static HTML

Response format:
- Provide detailed analysis since this is the final scraping attempt
- Use **bold** for key findings and dynamic content
- End with: [CONFIDENCE: XX] where XX is 0-100

Confidence guidelines:
- 61-75: Good content captured, some elements may be missing
- 76-85: Comprehensive content with most dynamic elements
- 86-95: Excellent coverage of all visible content
- 96-100: Complete page analysis including all lazy-loaded content""",
        name="PlaywrightAgent",
        tools=[fetch_playwright_content],  # Only dynamic content scraping
    )


# Create default agent for DevUI auto-discovery
agent = create_agent()
