"""
Result handlers for NL2SQL workflow.
Handles successful execution, syntax errors, semantic errors, and other execution issues.

Includes parallel execution handlers (fan-out/fan-in pattern):
- evaluate_sql_reasoning: Evaluates SQL generation reasoning
- generate_natural_language_response: Generates NL response for results
- aggregate_success_results: Aggregates parallel execution results
"""

import json
import logging
from typing import Any

from agent_framework import (
    AgentExecutorRequest,
    ChatMessage,
    Role,
    WorkflowContext,
    executor,
)


from ..config import (
    CURRENT_QUESTION_KEY,
    CURRENT_SCHEMA_ID_KEY,
    M_SCHEMA_CACHE_KEY,
    RETRY_CONTEXT_KEY,
    SCHEMA_STATE_PREFIX,
)
from ..models import (
    ExecutionResult,
    NL2SQLOutput,
    RetryContext,
    SchemaContext,
)
from ..prompt_manager import prompt_manager

logger = logging.getLogger(__name__)


def _create_error_output(
    result: ExecutionResult, error_type: str, retry_count: int, max_retries: int
) -> NL2SQLOutput:
    """Create standardized error output."""
    return NL2SQLOutput(
        sql=result.sql or "-- Error: SQL not generated",
        database=result.database or "unknown",
        execution_result={
            "error": result.error_message,
            "error_type": error_type,
            "retry_count": retry_count,
        },
        natural_language_response=f"❌ {error_type} after {retry_count} retries: {result.error_message}",
        reasoning_evaluation=None,
    )


# ============================================================================
# Success Handler
# ============================================================================


@executor(id="handle_success")
async def handle_success(
    result: ExecutionResult, ctx: WorkflowContext[Any, NL2SQLOutput]
) -> ExecutionResult:
    """
    Handle successful SQL execution.

    This executor passes the ExecutionResult to parallel executors
    (reasoning evaluation and NL response generation) at the workflow level.

    Returns:
        ExecutionResult to be passed to parallel executors
    """
    if not result.is_success():
        raise RuntimeError("This executor should only handle successful results")

    logger.info("=== Workflow Completed Successfully ===")
    logger.info(f"SQL: {result.sql}")
    logger.info(f"Rows: {result.row_count}")

    # Return result to be passed to parallel executors
    return result


@executor(id="aggregate_success_results")
async def aggregate_success_results(
    messages: list[dict | str | None], ctx: WorkflowContext[Any, NL2SQLOutput]
) -> None:
    """
    Aggregate results from parallel executors (reasoning evaluation and NL generation).

    This executor receives outputs from:
    - evaluate_sql_reasoning (dict)
    - generate_natural_language_response (str | None)

    Args:
        messages: List of outputs from parallel executors
        ctx: Workflow context for yielding final output
    """
    logger.info("=== Aggregating Success Results ===")

    # Extract ExecutionResult (should be first message from handle_success)
    result = None
    reasoning_evaluation = None
    natural_language_response = None

    for msg in messages:
        if isinstance(msg, ExecutionResult):
            result = msg
        elif isinstance(msg, dict):
            # Reasoning evaluation result
            reasoning_evaluation = msg
        elif isinstance(msg, str):
            # Natural language response
            natural_language_response = msg
        elif msg is None:
            # NL response not requested
            pass

    if result is None:
        logger.error("ExecutionResult not found in messages")
        raise RuntimeError("ExecutionResult not found in parallel execution results")

    # Handle missing results (should not happen, but be defensive)
    if reasoning_evaluation is None:
        logger.warning("Reasoning evaluation not found, using default")
        reasoning_evaluation = {
            "is_correct": None,
            "confidence": 0,
            "explanation": "Evaluation not performed",
            "suggestions": "• System: Check reasoning evaluation executor\n• Monitoring: Track evaluation availability",
        }

    # Log success and reasoning quality
    eval_confidence = reasoning_evaluation.get("confidence", 0)
    quality_status = ""
    if not reasoning_evaluation.get("is_correct"):
        if eval_confidence < 50:
            quality_status = " ⚠️ Low reasoning quality"

    logger.info(
        f"✅ Success: {result.row_count} rows ({result.execution_time_ms:.0f}ms){quality_status} - Evaluation confidence: {eval_confidence}%"
    )

    # Create final output
    output = NL2SQLOutput(
        sql=result.sql,
        database=result.database,
        execution_result={
            "rows": result.result_rows,
            "row_count": result.row_count,
            "execution_time_ms": result.execution_time_ms,
        },
        natural_language_response=natural_language_response,
        reasoning_evaluation=reasoning_evaluation,
    )

    await ctx.yield_output(output)


# ============================================================================
# Error Handlers
# ============================================================================


@executor(id="handle_syntax_error")
async def handle_syntax_error(
    result: ExecutionResult, ctx: WorkflowContext[Any, Any]
) -> None:
    """
    Handle SQL syntax errors by requesting correction.

    Responsibilities:
    - Check retry count (TERMINATION CONDITION)
    - Request SQL correction from agent (without changing schema)
    - Loop back to SQL generation OR terminate if max retries reached

    Termination:
    - If max_syntax_retries (2) exceeded: yield_output() and return
    - This breaks the retry loop and prevents infinite cycles
    """
    if not result.needs_sql_refinement():
        raise RuntimeError("This executor should only handle syntax errors")

    logger.info("--- Handling Syntax Error ---")
    logger.info(f"Error: {result.error_message}")

    # Check retry count (TERMINATION CHECK)
    retry_ctx_dict: dict = await ctx.get_shared_state(RETRY_CONTEXT_KEY)
    retry_ctx = RetryContext(**retry_ctx_dict)

    if not retry_ctx.can_retry_syntax():
        logger.error(f"Max syntax retries ({retry_ctx.max_syntax_retries}) reached")
        error_output = _create_error_output(
            result,
            "SQL Syntax Error",
            retry_ctx.syntax_retry_count,
            retry_ctx.max_syntax_retries,
        )
        await ctx.yield_output(error_output)
        return  # Workflow terminates here

    # Increment retry count
    retry_ctx.increment_syntax()
    await ctx.set_shared_state(RETRY_CONTEXT_KEY, retry_ctx.model_dump())

    logger.info(f"Retry {retry_ctx.syntax_retry_count}/{retry_ctx.max_syntax_retries}")

    # Get schema context
    schema_id: str = await ctx.get_shared_state(CURRENT_SCHEMA_ID_KEY)
    schema_ctx_dict: dict = await ctx.get_shared_state(
        f"{SCHEMA_STATE_PREFIX}{schema_id}"
    )
    schema_ctx = SchemaContext(**schema_ctx_dict)

    question: str = await ctx.get_shared_state(CURRENT_QUESTION_KEY)

    # Request correction
    prompt = prompt_manager.get_syntax_error_correction_prompt(
        question=question,
        detailed_schema=schema_ctx.detailed_schema,
        failed_sql=result.sql,
        error_message=result.error_message or "",
    )

    await ctx.send_message(
        AgentExecutorRequest(
            messages=[ChatMessage(Role.USER, text=prompt)], should_respond=True
        )
    )


@executor(id="handle_semantic_error")
async def handle_semantic_error(
    result: ExecutionResult, ctx: WorkflowContext[Any, Any]
) -> None:
    """
    Handle semantic errors (wrong table/column names).

    Responsibilities:
    - Check retry count (TERMINATION CONDITION)
    - Request schema re-analysis OR terminate if max retries reached
    - Loop back to schema understanding agent

    Termination:
    - If max_semantic_retries (2) exceeded: yield_output() and return
    - This breaks the retry loop and prevents infinite cycles
    """
    if not result.needs_schema_refinement():
        raise RuntimeError("This executor should only handle semantic errors")

    # Check if this is a low confidence case (just for logging)
    is_low_confidence = "Low confidence" in (result.error_message or "")
    log_msg = (
        "⚠️ Low confidence - Re-analyzing schema"
        if is_low_confidence
        else f"Semantic error: {result.error_message}"
    )
    logger.info(f"--- Handling Semantic Error --- {log_msg}")

    # Check retry count (TERMINATION CHECK)
    retry_ctx_dict: dict = await ctx.get_shared_state(RETRY_CONTEXT_KEY)
    retry_ctx = RetryContext(**retry_ctx_dict)

    if not retry_ctx.can_retry_semantic():
        logger.error(f"Max semantic retries ({retry_ctx.max_semantic_retries}) reached")
        error_output = _create_error_output(
            result,
            "Database Schema Error",
            retry_ctx.semantic_retry_count,
            retry_ctx.max_semantic_retries,
        )
        await ctx.yield_output(error_output)
        return  # Workflow terminates here

    # Increment retry count
    retry_ctx.increment_semantic()
    await ctx.set_shared_state(RETRY_CONTEXT_KEY, retry_ctx.model_dump())

    logger.info(
        f"Retry {retry_ctx.semantic_retry_count}/{retry_ctx.max_semantic_retries}"
    )

    # Get schema context
    schema_id: str = await ctx.get_shared_state(CURRENT_SCHEMA_ID_KEY)
    schema_ctx_dict: dict = await ctx.get_shared_state(
        f"{SCHEMA_STATE_PREFIX}{schema_id}"
    )
    schema_ctx = SchemaContext(**schema_ctx_dict)

    question: str = await ctx.get_shared_state(CURRENT_QUESTION_KEY)

    # Get M-Schema
    m_schema: dict = await ctx.get_shared_state(M_SCHEMA_CACHE_KEY)

    # Request schema re-analysis
    db_schema = m_schema.get(schema_ctx.database, {})
    tables_info = db_schema.get("tables", {})

    m_schema_simplified = {schema_ctx.database: {"tables": list(tables_info.keys())}}
    m_schema_json = json.dumps(m_schema_simplified, indent=2)

    prompt = prompt_manager.get_semantic_error_correction_prompt(
        question=question,
        database=schema_ctx.database,
        m_schema_json=m_schema_json,
        failed_sql=result.sql,
        error_message=result.error_message or "",
    )

    await ctx.send_message(
        AgentExecutorRequest(
            messages=[ChatMessage(Role.USER, text=prompt)], should_respond=True
        )
    )


@executor(id="handle_execution_issue")
async def handle_execution_issue(
    result: ExecutionResult, ctx: WorkflowContext[Any, NL2SQLOutput]
) -> None:
    """
    Handle non-recoverable execution issues.

    Terminal step: yields error output.
    For EmptyResult, Timeout, and other non-recoverable errors.
    """
    logger.warning(f"=== Execution Issue: {result.status} ===")
    logger.warning(f"Message: {result.error_message}")

    error_output = NL2SQLOutput(
        sql=result.sql,
        database=result.database,
        execution_result={
            "error": result.error_message,
            "status": result.status,
        },
        natural_language_response=f"⚠️ {result.status}: {result.error_message}",
        reasoning_evaluation=None,
    )

    await ctx.yield_output(error_output)
