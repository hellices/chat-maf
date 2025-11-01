"""Initialization executor for NL2SQL workflow."""

import logging

from agent_framework import WorkflowContext, executor

from database.schema_cache import load_m_schema

from ..config import M_SCHEMA_CACHE_KEY, RETURN_NL_KEY
from ..models import NL2SQLInput, RetryContext, WorkflowMessage

logger = logging.getLogger(__name__)


@executor(id="initialize_context")
async def initialize_context(
    input_data: NL2SQLInput, ctx: WorkflowContext[WorkflowMessage]
) -> None:
    """
    Initialize workflow by loading M-Schema and creating initial WorkflowMessage.

    Responsibilities:
    - Load M-Schema (all databases metadata) from disk
    - Initialize RetryContext for tracking refinement attempts
    - Store large payloads in shared state (M-Schema)
    - Create and send initial WorkflowMessage with status="Init"
    """
    logger.info("=== 🚀 NL2SQL Workflow Started ===")
    logger.info(f"❓ Question: {input_data.question}")
    logger.info(f"🗄️  Selected Database: {input_data.selected_database}")
    logger.info(f"📋 Selected Tables: {input_data.selected_tables}")

    # Load M-Schema (cached in memory) and store in shared state
    m_schema = load_m_schema()
    await ctx.set_shared_state(M_SCHEMA_CACHE_KEY, m_schema)

    # Store flags in shared state (not frequently needed)
    await ctx.set_shared_state(RETURN_NL_KEY, input_data.return_natural_language)

    # Create initial WorkflowMessage
    message = WorkflowMessage(
        question=input_data.question,
        database=input_data.selected_database or "",
        status="Init",
        retry_context=RetryContext(),
        selected_tables=input_data.selected_tables,
    )

    logger.info("📤 Sending initial message to schema understanding executor")
    await ctx.send_message(message)
