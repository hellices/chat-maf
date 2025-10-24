"""Reasoning evaluation executor for SQL generation.

Part of the NL2SQL workflow's fan-out/fan-in pattern.
Runs in parallel with natural language response generation after successful SQL execution.
"""

import logging
from typing import Any

from agent_framework import ChatMessage, Role, WorkflowContext, executor

from middleware import exception_handling_middleware, logging_middleware

from ..config import CURRENT_QUESTION_KEY, CURRENT_SQL_RESPONSE_KEY
from ..models import ExecutionResult, ReasoningEvaluation, SQLGenerationResponse
from ..prompt_manager import prompt_manager

logger = logging.getLogger(__name__)


@executor(id="evaluate_sql_reasoning")
async def evaluate_sql_reasoning(
    result: ExecutionResult,
    ctx: WorkflowContext[Any, dict],
) -> dict:
    """
    Evaluate the reasoning provided by SQL generation agent using LLM.

    Args:
        result: Execution result with query results
        ctx: Workflow context for retrieving question and schema info

    Returns:
        Dictionary with evaluation results
    """
    try:
        question: str = await ctx.get_shared_state(CURRENT_QUESTION_KEY)

        # Get stored SQL generation response
        sql_response_dict: dict = await ctx.get_shared_state(CURRENT_SQL_RESPONSE_KEY)
        sql_response = SQLGenerationResponse(**sql_response_dict)

        # Format results for evaluation
        from utils import (
            format_results_as_markdown_table,
            format_single_value,
            should_use_table_format,
        )

        if result.result_rows and should_use_table_format(result.result_rows):
            formatted_results = format_results_as_markdown_table(
                result.result_rows, max_rows=10
            )
        elif result.result_rows:
            formatted_results = format_single_value(result.result_rows)
        else:
            formatted_results = "No results"

        # Get m_schema for the selected database
        from ..config import M_SCHEMA_CACHE_KEY

        m_schema_subset = ""
        try:
            # Get m_schema from cache
            m_schema_cache: dict = await ctx.get_shared_state(M_SCHEMA_CACHE_KEY)
            if result.database and result.database in m_schema_cache:
                import json

                db_schema = m_schema_cache[result.database]
                # Format as readable JSON (limited size)
                m_schema_subset = (
                    json.dumps(db_schema, indent=2)[:2000] + "\n... (truncated)"
                )
        except Exception as e:
            logger.warning(f"Could not retrieve m_schema: {e}")
            m_schema_subset = "(Schema not available)"

        # Get system prompts
        schema_system_prompt = prompt_manager.get_system_prompt("schema_understanding")
        sql_generation_system_prompt = prompt_manager.get_system_prompt(
            "sql_generation"
        )

        # Generate evaluation prompt with full context
        eval_prompt = prompt_manager.get_reasoning_evaluation_prompt(
            question=question,
            sql=sql_response.sql,
            reasoning=sql_response.reasoning,
            confidence=sql_response.confidence,
            formatted_results=formatted_results,
            row_count=result.row_count,
            execution_time_ms=result.execution_time_ms,
            m_schema_subset=m_schema_subset,
            schema_system_prompt=(
                schema_system_prompt[:500] + "..."
                if len(schema_system_prompt) > 500
                else schema_system_prompt
            ),
            sql_generation_system_prompt=(
                sql_generation_system_prompt[:500] + "..."
                if len(sql_generation_system_prompt) > 500
                else sql_generation_system_prompt
            ),
        )

        # Call LLM for evaluation
        from agent_framework.azure import AzureOpenAIChatClient
        from azure.identity import AzureCliCredential

        chat_client = AzureOpenAIChatClient(credential=AzureCliCredential())

        system_prompt = prompt_manager.get_system_prompt("reasoning_evaluation")

        # Create agent with middleware
        agent = chat_client.create_agent(
            instructions=system_prompt,
            response_format=ReasoningEvaluation,
            model_kwargs={"temperature": 0.3},  # Lower temperature for evaluation
            middleware=[logging_middleware, exception_handling_middleware],
        )

        eval_response = await agent.run([ChatMessage(Role.USER, text=eval_prompt)])
        evaluation = ReasoningEvaluation.model_validate_json(eval_response.text)

        logger.info(f"Reasoning Evaluation: is_correct={evaluation.is_correct}")
        logger.info(f"Evaluation Confidence: {evaluation.confidence}%")
        logger.info(f"Evaluation Explanation: {evaluation.explanation}")
        if evaluation.suggestions:
            logger.info(f"Suggestions: {evaluation.suggestions[:200]}...")

        return evaluation.model_dump()

    except Exception as e:
        logger.warning(f"Failed to evaluate reasoning: {e}")
        # Return a default evaluation
        return {
            "is_correct": None,
            "confidence": 0,
            "explanation": f"Evaluation failed: {str(e)}",
            "suggestions": "• System: Enable detailed error logging to diagnose evaluation failures\n• Monitoring: Track evaluation success rate and failure patterns",
        }
