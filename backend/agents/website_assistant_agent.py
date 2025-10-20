"""
Website Assistant Agent for Progressive Analysis

A unified agent that handles website analysis with different levels of data
(SEO context, web scraper, Playwright content).
"""

from agent_framework.azure import AzureOpenAIResponsesClient
from azure.identity import AzureCliCredential
from models.analysis_request import AnalysisRequest


class WebsiteAssistantAgent:
    """Unified agent for website assistance"""

    def __init__(self):
        # Initialize Azure OpenAI client
        self.client = AzureOpenAIResponsesClient(
            credential=AzureCliCredential(),
        )

        # Create unified website assistant agent (no middleware)
        self.agent = self.client.create_agent(
            instructions="""You are a concise website assistant. Answer user questions about websites directly and briefly.

Input: JSON with message, url, seo_context, website_content, playwright_content, history

Rules:
1. Keep answers SHORT and to the point (2-3 sentences max unless asked for details)
2. Use ONLY the provided data - never make up information
3. If history exists, don't repeat previous information
4. Use **bold** for key points sparingly
5. End with: [CONFIDENCE: XX] where XX is 0-100

Confidence scale:
- 0-30: Limited info
- 31-60: Some details
- 61-85: Good details
- 86-100: Complete info""",
        )

    async def analyze_website(self, request: AnalysisRequest):
        """
        Analyze website and respond to user question

        Args:
            request: Structured analysis request with all context

        Yields:
            Response chunks from the agent
        """
        # Stream response from unified agent with structured request
        async for chunk in self.agent.run_stream(request.model_dump_json(indent=2)):
            if chunk.text:
                yield chunk.text
