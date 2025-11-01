"""
Natural language response generator for NL2SQL workflow.

Generates human-readable responses from query results (parallel execution).
"""

import logging
from typing import Any

from agent_framework import ChatMessage, Role, WorkflowContext, executor

from middleware import exception_handling_middleware, logging_middleware

from ..config import RETURN_NL_KEY
from ..models import WorkflowMessage
from ..prompt_manager import prompt_manager

logger = logging.getLogger(__name__)


@executor(id="generate_natural_language_response")
async def generate_natural_language_response(
    message: WorkflowMessage,
    ctx: WorkflowContext[Any, Any],
) -> None:
    """
    Generate natural language response for query results using LLM.

    Part of fan-out/fan-in pattern - runs in parallel with reasoning evaluation.
    Receives WorkflowMessage with status="Success" from handle_success.

    Sends str|None via send_message - framework collects for fan-in.

    Args:
        message: Workflow message with question, SQL, and results
        ctx: Workflow context
    """
    try:
        logger.info("💬 Generating Natural Language Response")

        # Check if natural language response is requested
        return_nl: bool = await ctx.get_shared_state(RETURN_NL_KEY)
        if not return_nl or not message.result_rows:
            logger.info("ℹ️  Natural language response not requested or no results")
            await ctx.send_message(None)
            return

        # Get pre-formatted results from handle_success (optimization)
        formatted_results: str = await ctx.get_shared_state("FORMATTED_RESULTS")
        format_type: str = await ctx.get_shared_state("FORMAT_TYPE")

        nl_prompt = prompt_manager.get_natural_language_response_prompt(
            question=message.question,
            sql=message.sql or "",
            formatted_results=formatted_results,
            format_instruction_type=format_type,
        )

        # Call LLM for natural language response
        from agent_framework.azure import AzureOpenAIChatClient
        from azure.identity import AzureCliCredential

        chat_client = AzureOpenAIChatClient(credential=AzureCliCredential())
        system_prompt = prompt_manager.get_system_prompt("natural_language_response")

        agent = chat_client.create_agent(
            instructions=system_prompt,
            model_kwargs={"temperature": 0.7},
            middleware=[logging_middleware, exception_handling_middleware],
        )

        nl_response = await agent.run([ChatMessage(Role.USER, text=nl_prompt)])
        natural_language_response = str(nl_response)

        logger.info(f"✅ Generated NL response: {natural_language_response[:100]}...")
        logger.info("🔄 Sending NL response to fan-in aggregator")

        # Fan-out executors must use send_message (framework collects for fan-in)
        await ctx.send_message(natural_language_response)

    except Exception as e:
        logger.warning(f"⚠️  Failed to generate natural language response: {e}")
        result_count = len(message.result_rows) if message.result_rows else 0
        fallback = f"Found {result_count} result(s)."

        # Send fallback to fan-in aggregator
        await ctx.send_message(fallback)
