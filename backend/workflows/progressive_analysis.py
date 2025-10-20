import os
import re
from typing import AsyncGenerator

from agent_framework import (
    ChatMessage,
    Executor,
    Role,
    SequentialBuilder,
    WorkflowContext,
    WorkflowOutputEvent,
    handler,
)

from agents.webscraper_agent.agent import create_agent as create_web_scraper_agent
from agents.playwright_agent.agent import create_agent as create_playwright_agent


class WebScraperAnalyzer(Executor):
    """Custom executor for static HTML scraping analysis."""

    def __init__(self, url: str, seo_context: dict | None = None):
        super().__init__(id="web-scraper-analyzer")
        self.url = url
        self.seo_context = seo_context
        self.agent = create_web_scraper_agent()
        # Shared state for passing data between executors
        self.confidence = 0

    @handler
    async def analyze(
        self,
        conversation: list[ChatMessage],
        ctx: WorkflowContext[list[ChatMessage], str],
    ) -> None:
        """Analyze website using static HTML scraping."""
        message = conversation[-1].text if conversation else ""

        # Yield progress message
        await ctx.yield_output("**[Step 1/2] Fetching static HTML...**\n\n")

        # Build prompt with SEO context if available
        prompt = f"Analyze this website: {self.url}\n\n"
        if self.seo_context:
            prompt += f"SEO Context: {self.seo_context}\n\n"
        prompt += (
            f"User question: {message}\n\nUse fetch_web_content to analyze the page."
        )

        # Stream response from web scraper agent
        response = ""
        async for chunk in self.agent.run_stream(prompt):
            if chunk.text:
                response += chunk.text
                await ctx.yield_output(chunk.text)

        # Extract confidence for next executor
        self.confidence = _extract_confidence(response)

        # Add assistant response to conversation
        updated_conversation = list(conversation)
        assistant_msg = ChatMessage(
            role=Role.ASSISTANT, text=response, author_name="web-scraper-analyzer"
        )
        updated_conversation.append(assistant_msg)

        # Send updated conversation to next executor
        await ctx.send_message(updated_conversation)


class PlaywrightAnalyzer(Executor):
    """Custom executor for Playwright-based dynamic content analysis."""

    def __init__(
        self, scraper_analyzer: WebScraperAnalyzer, quality_threshold: int = 60
    ):
        super().__init__(id="playwright-analyzer")
        self.scraper_analyzer = scraper_analyzer
        self.quality_threshold = quality_threshold
        self.agent = create_playwright_agent()

    @handler
    async def analyze(
        self,
        conversation: list[ChatMessage],
        ctx: WorkflowContext[list[ChatMessage], str],
    ) -> None:
        """Conditionally analyze with Playwright if confidence is low."""
        confidence = self.scraper_analyzer.confidence

        # Check if we need Playwright
        # Check if we need Playwright
        if confidence >= self.quality_threshold:
            await ctx.yield_output(
                f"\n\n*Analysis complete with {confidence}% confidence. Skipping Playwright.*\n"
            )
            return

        # Need more data - use Playwright
        await ctx.yield_output(
            f"\n\n*Confidence {confidence}% is below threshold. Fetching dynamic content...*\n\n"
        )
        await ctx.yield_output(
            "**[Step 2/2] Fetching dynamic content with Playwright...**\n\n"
        )

        # Extract original user message
        user_message = conversation[0].text if conversation else ""

        # Build prompt for Playwright agent
        prompt = f"Analyze this website: {self.scraper_analyzer.url}\n\n"
        if self.scraper_analyzer.seo_context:
            prompt += f"SEO Context: {self.scraper_analyzer.seo_context}\n\n"
        prompt += f"User question: {user_message}\n\nUse fetch_playwright_content to get fully-rendered content."

        # Stream response from Playwright agent
        response = ""
        async for chunk in self.agent.run_stream(prompt):
            if chunk.text:
                response += chunk.text
                await ctx.yield_output(chunk.text)

        await ctx.yield_output("\n\n*Complete analysis finished.*\n")


async def call_website_assistant(
    message: str, url: str, seo_context: dict | None = None
) -> AsyncGenerator[str, None]:
    """Progressive website analysis with web scraper and Playwright using Sequential workflow."""
    quality_threshold = int(os.getenv("QUALITY_THRESHOLD", "60"))

    # Build sequential workflow with specialized agent executors
    scraper_analyzer = WebScraperAnalyzer(url=url, seo_context=seo_context)
    playwright_analyzer = PlaywrightAnalyzer(
        scraper_analyzer=scraper_analyzer, quality_threshold=quality_threshold
    )

    workflow = (
        SequentialBuilder()
        .participants([scraper_analyzer, playwright_analyzer])
        .build()
    )

    # Run workflow and stream outputs
    async for event in workflow.run_stream(message):
        if isinstance(event, WorkflowOutputEvent):
            output = event.data
            if isinstance(output, str):
                yield output


def _extract_confidence(text: str) -> int:
    """Extract confidence score from response."""
    match = re.search(r"\[CONFIDENCE:\s*(\d+)\]", text, re.IGNORECASE)
    return int(match.group(1)) if match else 0
