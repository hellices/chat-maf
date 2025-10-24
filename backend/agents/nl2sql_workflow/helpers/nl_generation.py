"""Natural language response generation helper."""

import logging
from typing import Any

from agent_framework import ChatMessage, Role, WorkflowContext, executor

from middleware import exception_handling_middleware, logging_middleware

from ..config import CURRENT_QUESTION_KEY, RETURN_NL_KEY
from ..models import ExecutionResult
from ..prompt_manager import prompt_manager

logger = logging.getLogger(__name__)


@executor(id="generate_natural_language_response")
async def generate_natural_language_response(
    result: ExecutionResult,
    ctx: WorkflowContext[Any, str | None],
) -> str | None:
    """
    Generate natural language response for query results using LLM.

    Args:
        result: Execution result with query results
        ctx: Workflow context for retrieving question

    Returns:
        Natural language response string or None if not requested
    """
    try:
        # Check if natural language response is requested
        return_nl: bool = await ctx.get_shared_state(RETURN_NL_KEY)
        if not return_nl or not result.result_rows:
            return None

        question: str = await ctx.get_shared_state(CURRENT_QUESTION_KEY)

        # Format results
        from utils import (
            format_results_as_markdown_table,
            format_single_value,
            should_use_table_format,
        )

        # Determine format type and format results
        if should_use_table_format(result.result_rows):
            formatted_results = format_results_as_markdown_table(
                result.result_rows, max_rows=10
            )
            format_type = "table"
        else:
            formatted_results = format_single_value(result.result_rows)
            format_type = "single"

        nl_prompt = prompt_manager.get_natural_language_response_prompt(
            question=question,
            sql=result.sql,
            formatted_results=formatted_results,
            format_instruction_type=format_type,
        )

        # Call LLM for natural language response
        from agent_framework.azure import AzureOpenAIChatClient
        from azure.identity import AzureCliCredential

        chat_client = AzureOpenAIChatClient(credential=AzureCliCredential())

        system_prompt = prompt_manager.get_system_prompt("natural_language_response")

        # Create agent with middleware
        agent = chat_client.create_agent(
            instructions=system_prompt,
            model_kwargs={"temperature": 0.7},
            middleware=[logging_middleware, exception_handling_middleware],
        )

        nl_response = await agent.run([ChatMessage(Role.USER, text=nl_prompt)])
        natural_language_response = str(nl_response)

        logger.info(f"Generated NL response: {natural_language_response}")
        return natural_language_response

    except Exception as e:
        logger.warning(f"Failed to generate natural language response: {e}")
        # Fallback to simple response
        result_count = len(result.result_rows) if result.result_rows else 0
        return f"Found {result_count} result(s)."
