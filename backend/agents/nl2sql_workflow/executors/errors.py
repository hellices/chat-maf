"""
Error handlers for NL2SQL workflow.

Handles various error scenarios with retry logic:
- handle_syntax_error: SQL syntax errors with retry
- handle_semantic_error: Schema-related errors with retry
- handle_execution_issue: Non-recoverable errors
"""

import json
import logging
from typing import Any

from agent_framework import (
    WorkflowContext,
    executor,
)

from ..config import (
    CURRENT_SCHEMA_ID_KEY,
    M_SCHEMA_CACHE_KEY,
    RETURN_NL_KEY,
    SCHEMA_STATE_PREFIX,
)
from ..models import (
    NL2SQLOutput,
    SchemaContext,
    WorkflowMessage,
)
from ..prompt_manager import prompt_manager

logger = logging.getLogger(__name__)


def _create_error_output(message: WorkflowMessage, error_type: str) -> NL2SQLOutput:
    """Create standardized error output."""
    return NL2SQLOutput(
        sql=message.sql or "-- Error: SQL not generated",
        database=message.database or "unknown",
        execution_result={
            "error": message.error_message,
            "error_type": error_type,
            "syntax_retry_count": message.retry_context.syntax_retry_count,
            "semantic_retry_count": message.retry_context.semantic_retry_count,
        },
        natural_language_response=f"❌ {error_type}: {message.error_message}",
        reasoning_evaluation=None,
    )


# ============================================================================
# Syntax Error Handler
# ============================================================================


@executor(id="handle_syntax_error")
async def handle_syntax_error(
    message: WorkflowMessage, ctx: WorkflowContext[WorkflowMessage, NL2SQLOutput]
) -> None:
    """
    Handle SQL syntax errors by requesting correction.

    Receives WorkflowMessage with status="SyntaxError".
    Returns WorkflowMessage with updated retry_context (loops to sql_generation).

    Responsibilities:
    - Check retry count (TERMINATION CONDITION)
    - Request SQL correction from agent (without changing schema)
    - Loop back to SQL generation OR terminate if max retries reached

    Termination:
    - If max_syntax_retries (2) exceeded: yield_output() and return
    - This breaks the retry loop and prevents infinite cycles
    """
    if not message.needs_sql_refinement():
        raise RuntimeError("This executor should only handle syntax errors")

    logger.info("--- 🔧 Handling Syntax Error ---")
    logger.info(f"❌ Error: {message.error_message}")
    logger.info(f"🔄 Current retry count: {message.retry_context.syntax_retry_count}")

    # Check retry count (TERMINATION CHECK)
    if not message.can_retry_syntax():
        logger.error(
            f"⛔ Max syntax retries ({message.retry_context.max_syntax_retries}) reached"
        )
        error_output = _create_error_output(message, "SQL Syntax Error")
        await ctx.yield_output(error_output)
        return  # Workflow terminates here

    # Increment retry count
    message.retry_context.increment_syntax()
    logger.info(
        f"♻️  Retry {message.retry_context.syntax_retry_count}/{message.retry_context.max_syntax_retries}"
    )

    # Create retry message with updated retry_context
    # Status remains "SyntaxError" so sql_generation knows it's a retry
    retry_message = WorkflowMessage(
        question=message.question,
        database=message.database,
        sql=message.sql,  # Failed SQL for context
        status="SyntaxError",  # sql_generation will handle retry
        error_message=message.error_message,
        retry_context=message.retry_context,  # Updated retry count
        selected_tables=message.selected_tables,
        schema_id=message.schema_id,
    )

    logger.info("📤 Sending retry request to sql_generation")
    await ctx.send_message(retry_message)


# ============================================================================
# Semantic Error Handler
# ============================================================================


@executor(id="handle_semantic_error")
async def handle_semantic_error(
    message: WorkflowMessage, ctx: WorkflowContext[WorkflowMessage, NL2SQLOutput]
) -> None:
    """
    Handle semantic errors (wrong table/column names).

    Receives WorkflowMessage with status="SemanticError".
    Returns WorkflowMessage with updated retry_context (loops to schema_understanding).

    Responsibilities:
    - Check retry count (TERMINATION CONDITION)
    - Request schema re-analysis OR terminate if max retries reached
    - Loop back to schema understanding agent

    Termination:
    - If max_semantic_retries (2) exceeded: yield_output() and return
    - This breaks the retry loop and prevents infinite cycles
    """
    if not message.needs_schema_refinement():
        raise RuntimeError("This executor should only handle semantic errors")

    # Check if this is a low confidence case (just for logging)
    is_low_confidence = "Low confidence" in (message.error_message or "")
    log_msg = (
        "⚠️ Low confidence - Re-analyzing schema"
        if is_low_confidence
        else f"Semantic error: {message.error_message}"
    )
    logger.info(f"--- 🔄 Handling Semantic Error --- {log_msg}")
    logger.info(f"🔄 Current retry count: {message.retry_context.semantic_retry_count}")

    # Check retry count (TERMINATION CHECK)
    if not message.can_retry_semantic():
        logger.error(
            f"⛔ Max semantic retries ({message.retry_context.max_semantic_retries}) reached"
        )
        error_output = _create_error_output(message, "Database Schema Error")
        await ctx.yield_output(error_output)
        return  # Workflow terminates here

    # Increment retry count
    message.retry_context.increment_semantic()
    logger.info(
        f"♻️  Retry {message.retry_context.semantic_retry_count}/{message.retry_context.max_semantic_retries}"
    )

    # Create retry message with updated retry_context
    # Status changes to "SemanticError" so schema_understanding knows it's a retry
    retry_message = WorkflowMessage(
        question=message.question,
        database=message.database,
        sql=message.sql,  # Failed SQL for context
        status="SemanticError",  # schema_understanding will handle retry
        error_message=message.error_message,
        retry_context=message.retry_context,  # Updated retry count
        selected_tables=message.selected_tables,
        schema_id=message.schema_id,
    )

    logger.info("📤 Sending retry request to schema_understanding")
    await ctx.send_message(retry_message)


# ============================================================================
# Execution Issue Handler
# ============================================================================


@executor(id="handle_execution_issue")
async def handle_execution_issue(
    message: WorkflowMessage, ctx: WorkflowContext[WorkflowMessage, NL2SQLOutput]
) -> None:
    """
    Handle non-recoverable execution issues.

    Receives WorkflowMessage with status=EmptyResult/Timeout.
    Terminal step: yields error output.
    """
    logger.warning(f"=== ⚠️  Execution Issue: {message.status} ===")
    logger.warning(f"📄 Message: {message.error_message}")

    # Check if natural language response was requested
    return_nl: bool = await ctx.get_shared_state(RETURN_NL_KEY)

    nl_response = None
    if return_nl and message.status == "EmptyResult":
        # For empty results, we can still provide a natural language explanation
        nl_response = f"The query returned no results. This might be because the data matching your question ('{message.question}') doesn't exist in the database."

    error_output = NL2SQLOutput(
        sql=message.sql or "-- Error: SQL not generated",
        database=message.database,
        execution_result={
            "error": message.error_message,
            "status": message.status,
        },
        natural_language_response=nl_response
        or f"⚠️ {message.status}: {message.error_message}",
        reasoning_evaluation=None,
    )

    await ctx.yield_output(error_output)
