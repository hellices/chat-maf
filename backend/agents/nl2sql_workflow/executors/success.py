"""
Success handlers for NL2SQL workflow.

Handles successful SQL execution with fan-out/fan-in pattern:
- handle_success: Dispatches to parallel executors
- evaluate_sql_reasoning: Evaluates SQL generation reasoning (parallel)
- generate_natural_language_response: Generates NL response (parallel)
- aggregate_success_results: Aggregates parallel execution results
"""

import json
import logging
from typing import Any

from agent_framework import ChatMessage, Role, WorkflowContext, executor

from middleware import exception_handling_middleware, logging_middleware

from ..config import (
    CURRENT_SQL_RESPONSE_KEY,
    M_SCHEMA_CACHE_KEY,
    RETURN_NL_KEY,
)
from ..models import (
    NL2SQLOutput,
    ReasoningEvaluation,
    SQLGenerationResponse,
    WorkflowMessage,
)
from ..prompt_manager import prompt_manager

logger = logging.getLogger(__name__)


# ============================================================================
# Success Dispatcher
# ============================================================================


@executor(id="handle_success")
async def handle_success(
    message: WorkflowMessage, ctx: WorkflowContext[WorkflowMessage, NL2SQLOutput]
) -> None:
    """
    Handle successful SQL execution.

    Receives WorkflowMessage with status="Success".
    Stores data in shared state and triggers fan-out to parallel executors.

    Args:
        message: Workflow message with successful SQL execution results
        ctx: Workflow context
    """
    if not message.is_success():
        raise RuntimeError("This executor should only handle successful results")

    logger.info("=== ✅ SQL Execution Successful ===")
    logger.info(
        f"📊 Results: {message.row_count} rows in {message.execution_time_ms:.0f}ms"
    )
    logger.info("🚀 Starting Parallel Analysis (Reasoning + NL Response)")

    # Pre-format results once (optimization: avoid duplicate work in parallel executors)
    from utils import (
        format_results_as_markdown_table,
        format_single_value,
        should_use_table_format,
    )

    if message.result_rows and should_use_table_format(message.result_rows):
        formatted_results = format_results_as_markdown_table(
            message.result_rows, max_rows=10
        )
        format_type = "table"
    elif message.result_rows:
        formatted_results = format_single_value(message.result_rows)
        format_type = "single"
    else:
        formatted_results = "No results"
        format_type = "empty"

    # Store formatted results and WorkflowMessage in shared state for parallel executors and aggregator
    await ctx.set_shared_state("FORMATTED_RESULTS", formatted_results)
    await ctx.set_shared_state("FORMAT_TYPE", format_type)
    await ctx.set_shared_state("SUCCESS_MESSAGE", message.model_dump())

    # Send message to trigger fan-out to parallel executors
    await ctx.send_message(message)


# ============================================================================
# Parallel Executors (Fan-Out)
# ============================================================================


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
        logger.info(f"🔄 Sending evaluation result to fan-in aggregator")

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
        logger.info(f"🔄 Sending NL response to fan-in aggregator")

        # Fan-out executors must use send_message (framework collects for fan-in)
        await ctx.send_message(natural_language_response)

    except Exception as e:
        logger.warning(f"⚠️  Failed to generate natural language response: {e}")
        result_count = len(message.result_rows) if message.result_rows else 0
        fallback = f"Found {result_count} result(s)."

        # Send fallback to fan-in aggregator
        await ctx.send_message(fallback)


# ============================================================================
# Result Aggregator (Fan-In)
# ============================================================================


@executor(id="aggregate_success_results")
async def aggregate_success_results(
    results: list[dict | str | None], ctx: WorkflowContext[Any, Any]
) -> None:
    """
    Aggregate results from parallel executors (fan-in).

    Receives list of outputs from parallel executors:
    - evaluate_sql_reasoning returns dict
    - generate_natural_language_response returns str | None

    Framework automatically collects these into a list for this executor.

    Args:
        results: List of outputs from parallel executors [dict, str|None]
        ctx: Workflow context for yielding final output
    """
    logger.info("=== 🎯 Aggregating Success Results ===")
    logger.info(f"📥 Received {len(results)} results from parallel executors")

    # Get WorkflowMessage from shared state (stored by handle_success)
    message_dict: dict = await ctx.get_shared_state("SUCCESS_MESSAGE")
    message = WorkflowMessage(**message_dict)

    # Extract results from parallel executors
    reasoning_evaluation = None
    natural_language_response = None

    for msg in results:
        if isinstance(msg, dict):
            reasoning_evaluation = msg
        elif isinstance(msg, str):
            natural_language_response = msg
        elif msg is None:
            pass  # NL response not requested

    # Handle missing results (defensive)
    if reasoning_evaluation is None:
        logger.warning("⚠️  Reasoning evaluation not found, using default")
        reasoning_evaluation = {
            "is_correct": None,
            "confidence": 0,
            "explanation": "Evaluation not performed",
            "suggestions": "• System: Check reasoning evaluation executor",
        }

    # Log success and quality
    eval_confidence = reasoning_evaluation.get("confidence", 0)
    quality_status = ""
    if not reasoning_evaluation.get("is_correct") and eval_confidence < 50:
        quality_status = " ⚠️ Low reasoning quality"

    logger.info(
        f"✅ Success: {message.row_count} rows ({message.execution_time_ms:.0f}ms){quality_status} - Evaluation: {eval_confidence}%"
    )

    # Create final output
    output = NL2SQLOutput(
        sql=message.sql or "",
        database=message.database,
        execution_result={
            "rows": message.result_rows,
            "row_count": message.row_count,
            "execution_time_ms": message.execution_time_ms,
        },
        natural_language_response=natural_language_response,
        reasoning_evaluation=reasoning_evaluation,
    )

    await ctx.yield_output(output)
