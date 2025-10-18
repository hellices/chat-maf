import asyncio
import requests
from bs4 import BeautifulSoup
from markdownify import markdownify as md


async def fetch_web_content(url: str) -> str:
    """Fetch static HTML and convert to markdown."""
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


async def fetch_playwright_content(url: str) -> str:
    """Fetch dynamic content using Playwright and convert to markdown."""
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
