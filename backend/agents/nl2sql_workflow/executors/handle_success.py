"""
Success handler for NL2SQL workflow.

Dispatches successful SQL execution to parallel executors (fan-out pattern).
"""

import logging

from agent_framework import WorkflowContext, executor

from ..models import NL2SQLOutput, WorkflowMessage

logger = logging.getLogger(__name__)


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
