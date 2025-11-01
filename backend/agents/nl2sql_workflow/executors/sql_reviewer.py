"""
SQL Reviewer executor for reflection pattern.

Evaluates SQL generation quality and provides feedback for iterative improvement.
Based on workflow_as_agent_reflection_pattern.py from Microsoft Agent Framework.
"""

import logging
from typing import Any

from agent_framework import WorkflowContext, executor

from ..models import NL2SQLOutput, WorkflowMessage

logger = logging.getLogger(__name__)

# Maximum retry limits
MAX_SYNTAX_RETRIES = 2
MAX_SEMANTIC_RETRIES = 2


@executor(id="sql_reviewer")
async def sql_reviewer(
    message: WorkflowMessage, ctx: WorkflowContext[WorkflowMessage, NL2SQLOutput]
) -> None:
    """
    Review SQL generation quality and provide feedback.

    Reflection pattern - acts as Reviewer in Worker ↔ Reviewer cycle.

    Evaluation criteria:
    - Success: SQL executed successfully → approve (send to handle_success)
    - SyntaxError: SQL syntax issues → provide feedback and retry (if under limit)
    - SemanticError: Schema misunderstanding → provide feedback and retry (if under limit)
    - Other errors: Non-recoverable → terminate with error output

    Args:
        message: WorkflowMessage from sql_generation (Worker)
        ctx: Workflow context
    """
    logger.info("=== 🔍 SQL Reviewer - Evaluating SQL Quality ===")
    logger.info(f"📊 Status: {message.status}")
    logger.info(
        f"🔄 Retries: Syntax={message.retry_context.syntax_retry_count}, "
        f"Semantic={message.retry_context.semantic_retry_count}"
    )

    # Case 1: Success - Approve and send to success handler
    if message.status == "Success":
        logger.info("✅ APPROVED: SQL executed successfully")
        logger.info(f"📤 Sending to handle_success: {message.row_count} rows")
        await ctx.send_message(message, target_id="handle_success")
        return

    # Case 2: Syntax Error - Provide feedback and retry (if under limit)
    if message.status == "SyntaxError":
        retry_count = message.retry_context.syntax_retry_count

        if retry_count >= MAX_SYNTAX_RETRIES:
            logger.error(
                f"❌ REJECTED: Max syntax retries ({MAX_SYNTAX_RETRIES}) reached"
            )
            await _terminate_with_error(message, "SyntaxError", ctx)
            return

        logger.warning(f"⚠️  FEEDBACK: Syntax error (attempt {retry_count + 1})")
        logger.info(f"💬 Error: {message.error_message}")
        logger.info("🔄 Sending feedback to sql_generation for retry")

        # Increment retry count and send back to worker
        message.retry_context.syntax_retry_count += 1
        await ctx.send_message(message, target_id="sql_generation")
        return

    # Case 3: Semantic Error - Provide feedback and retry (if under limit)
    if message.status == "SemanticError":
        retry_count = message.retry_context.semantic_retry_count

        if retry_count >= MAX_SEMANTIC_RETRIES:
            logger.error(
                f"❌ REJECTED: Max semantic retries ({MAX_SEMANTIC_RETRIES}) reached"
            )
            await _terminate_with_error(message, "SemanticError", ctx)
            return

        logger.warning(f"⚠️  FEEDBACK: Semantic error (attempt {retry_count + 1})")
        logger.info(f"💬 Error: {message.error_message}")
        logger.info("🔄 Sending feedback to sql_generation for retry")

        # Increment retry count and send back to worker
        message.retry_context.semantic_retry_count += 1
        await ctx.send_message(message, target_id="sql_generation")
        return

    # Case 4: Other errors (Timeout, EmptyResult, etc.) - Non-recoverable
    logger.error(f"❌ REJECTED: Non-recoverable error - {message.status}")
    await _terminate_with_error(message, message.status, ctx)


async def _terminate_with_error(
    message: WorkflowMessage, error_type: str, ctx: WorkflowContext[Any, NL2SQLOutput]
) -> None:
    """
    Terminate workflow with error output.

    Args:
        message: WorkflowMessage with error details
        error_type: Type of error
        ctx: Workflow context
    """
    logger.error(f"🛑 Terminating workflow due to {error_type}")
    logger.error(f"📝 Error message: {message.error_message}")
    logger.error(
        f"🔄 Final retries: Syntax={message.retry_context.syntax_retry_count}, "
        f"Semantic={message.retry_context.semantic_retry_count}"
    )

    error_output = NL2SQLOutput(
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

    await ctx.yield_output(error_output)
