"""
Reasoning evaluation executor for NL2SQL workflow.

Evaluates SQL generation reasoning quality using LLM (parallel execution).
"""

import json
import logging
from typing import Any

from agent_framework import ChatMessage, Role, WorkflowContext, executor

from middleware import exception_handling_middleware, logging_middleware

from ..config import CURRENT_SQL_RESPONSE_KEY, M_SCHEMA_CACHE_KEY
from ..models import ReasoningEvaluation, SQLGenerationResponse, WorkflowMessage
from ..prompt_manager import prompt_manager

logger = logging.getLogger(__name__)


@executor(id="evaluate_sql_reasoning")
async def evaluate_sql_reasoning(
    message: WorkflowMessage,
    ctx: WorkflowContext[Any, Any],
) -> None:
    """
    Evaluate SQL reasoning quality using LLM.

    Part of fan-out/fan-in pattern - runs in parallel with NL response generation.
    Receives WorkflowMessage with status="Success" from handle_success.

    Sends dict via send_message - framework collects for fan-in.

    Args:
        message: Workflow message with SQL, results, and reasoning
        ctx: Workflow context
    """
    try:
        logger.info("🔍 Evaluating SQL Reasoning Quality")

        # Get stored SQL generation response
        sql_response_dict: dict = await ctx.get_shared_state(CURRENT_SQL_RESPONSE_KEY)
        sql_response = SQLGenerationResponse(**sql_response_dict)

        # Get pre-formatted results from handle_success (optimization)
        formatted_results: str = await ctx.get_shared_state("FORMATTED_RESULTS")

        # Get m_schema for the selected database
        m_schema_subset = ""
        try:
            m_schema_cache: dict = await ctx.get_shared_state(M_SCHEMA_CACHE_KEY)
            if message.database and message.database in m_schema_cache:
                db_schema = m_schema_cache[message.database]
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

        # Generate evaluation prompt
        eval_prompt = prompt_manager.get_reasoning_evaluation_prompt(
            question=message.question,
            sql=sql_response.sql,
            reasoning=sql_response.reasoning,
            confidence=sql_response.confidence,
            formatted_results=formatted_results,
            row_count=message.row_count,
            execution_time_ms=message.execution_time_ms,
            m_schema_subset=m_schema_subset,
            schema_system_prompt=schema_system_prompt,
            sql_generation_system_prompt=sql_generation_system_prompt,
        )

        # Call LLM for evaluation
        from agent_framework.azure import AzureOpenAIChatClient
        from azure.identity import AzureCliCredential

        chat_client = AzureOpenAIChatClient(credential=AzureCliCredential())
        system_prompt = prompt_manager.get_system_prompt("reasoning_evaluation")

        agent = chat_client.create_agent(
            instructions=system_prompt,
            response_format=ReasoningEvaluation,
            model_kwargs={"temperature": 0.3},
            middleware=[logging_middleware, exception_handling_middleware],
        )

        eval_response = await agent.run([ChatMessage(Role.USER, text=eval_prompt)])
        evaluation = ReasoningEvaluation.model_validate_json(eval_response.text)

        logger.info(f"✅ Reasoning Evaluation: is_correct={evaluation.is_correct}")
        logger.info(f"🎯 Evaluation Confidence: {evaluation.confidence}%")

        result_dict = evaluation.model_dump()
        logger.info("🔄 Sending evaluation result to fan-in aggregator")

        # Fan-out executors must use send_message (framework collects for fan-in)
        await ctx.send_message(result_dict)

    except Exception as e:
        logger.warning(f"⚠️  Failed to evaluate reasoning: {e}")
        error_result = {
            "is_correct": None,
            "confidence": 0,
            "explanation": f"Evaluation failed: {str(e)}",
            "suggestions": "• System: Enable detailed error logging\n• Monitoring: Track evaluation success rate",
        }
        # Send error result to fan-in aggregator
        await ctx.send_message(error_result)
