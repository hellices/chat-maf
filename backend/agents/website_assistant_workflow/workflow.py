from typing import AsyncGenerator
import re
import os
from dotenv import load_dotenv

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

# Load environment variables from .env file
load_dotenv()


class WebScraperExecutor(Executor):
    """Executor that uses static HTML scraping (fetch_web_content only)."""

    def __init__(self, url: str):
        super().__init__(id="web-scraper")
        self.url = url
        self.agent = create_web_scraper_agent()

    @handler
    async def analyze(
        self,
        conversation: list[ChatMessage],
        ctx: WorkflowContext[list[ChatMessage], str],
    ) -> None:
        """Analyze website using static HTML scraping."""
        message = conversation[-1].text if conversation else ""

        await ctx.yield_output(f"**[1/2] Fetching static HTML from: {self.url}**\n\n")

        prompt = f"Analyze this website: {self.url}\n\nUser question: {message}\n\nUse fetch_web_content to get static HTML and analyze it."

        response = ""
        async for chunk in self.agent.run_stream(prompt):
            if chunk.text:
                response += chunk.text
                await ctx.yield_output(chunk.text)

        # Extract confidence score
        confidence_match = re.search(r"\[CONFIDENCE:\s*(\d+)\]", response)
        confidence = int(confidence_match.group(1)) if confidence_match else 50

        # Add to conversation
        updated_conversation = list(conversation)
        assistant_msg = ChatMessage(
            role=Role.ASSISTANT, text=response, author_name="web-scraper"
        )
        updated_conversation.append(assistant_msg)

        # Get quality threshold from environment variable
        quality_threshold = int(os.getenv("QUALITY_THRESHOLD", "60"))

        # Only proceed to Playwright if confidence is below or equal to threshold
        if confidence <= quality_threshold:
            await ctx.yield_output(
                f"\n\n*Confidence {confidence}% is at or below threshold ({quality_threshold}%). Fetching dynamic content...*\n\n"
            )
            await ctx.send_message(updated_conversation)
        else:
            await ctx.yield_output(
                f"\n\n*Analysis complete with {confidence}% confidence (above threshold: {quality_threshold}%).*"
            )


class PlaywrightExecutor(Executor):
    """Executor that uses dynamic JavaScript rendering (fetch_playwright_content only)."""

    def __init__(self, url: str):
        super().__init__(id="playwright-scraper")
        self.url = url
        self.agent = create_playwright_agent()

    @handler
    async def analyze(
        self,
        conversation: list[ChatMessage],
        ctx: WorkflowContext[list[ChatMessage], str],
    ) -> None:
        """Analyze website using Playwright for dynamic content."""
        message = conversation[0].text if conversation else ""

        await ctx.yield_output(
            f"**[2/2] Fetching dynamic content with Playwright: {self.url}**\n\n"
        )

        prompt = f"Analyze this website: {self.url}\n\nUser question: {message}\n\nUse fetch_playwright_content to get fully-rendered content including JavaScript-loaded elements."

        response = ""
        async for chunk in self.agent.run_stream(prompt):
            if chunk.text:
                response += chunk.text
                await ctx.yield_output(chunk.text)

        await ctx.yield_output("\n\n*Complete analysis finished.*")


async def call_website_assistant(
    message: str, url: str, seo_context: dict | None = None
) -> AsyncGenerator[str, None]:
    """Website analysis using separate scraper agents with conditional Playwright execution."""

    # Build workflow with two specialized executors
    web_scraper = WebScraperExecutor(url=url)
    playwright_scraper = PlaywrightExecutor(url=url)

    workflow = (
        SequentialBuilder().participants([web_scraper, playwright_scraper]).build()
    )

    # Run workflow and stream outputs
    async for event in workflow.run_stream(message):
        if isinstance(event, WorkflowOutputEvent):
            output = event.data
            if isinstance(output, str):
                yield output
