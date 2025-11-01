"""
Result aggregator for NL2SQL workflow.

Aggregates results from parallel executors (fan-in pattern).
"""

import logging
from typing import Any

from agent_framework import WorkflowContext, executor

from ..models import NL2SQLOutput, WorkflowMessage

logger = logging.getLogger(__name__)


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
