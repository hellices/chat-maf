"""Schema understanding executor."""

import json
import logging
from typing import Any
from uuid import uuid4

from agent_framework import ChatMessage, Role, WorkflowContext, executor
from agent_framework.azure import AzureOpenAIChatClient
from azure.identity import AzureCliCredential

from database.schema_cache import load_m_schema
from database.spider_utils import SpiderDatabase
from middleware import exception_handling_middleware, logging_middleware

from ..config import CURRENT_SCHEMA_ID_KEY, M_SCHEMA_CACHE_KEY, SCHEMA_STATE_PREFIX
from ..models import SchemaContext, SchemaMappingResponse, WorkflowMessage
from ..prompt_manager import prompt_manager

logger = logging.getLogger(__name__)


@executor(id="schema_understanding")
async def schema_understanding(
    message: WorkflowMessage, ctx: WorkflowContext[Any, WorkflowMessage]
) -> None:
    """
    Process schema understanding request.

    Receives WorkflowMessage with status="Init" or "SemanticError" (retry).
    Returns WorkflowMessage with status="SchemaSelected".

    Responsibilities:
    - Build M-Schema prompt from message context
    - Call LLM to select database and tables
    - Load detailed schema (CREATE TABLE statements)
    - Store SchemaContext in shared state
    - Send WorkflowMessage with selected schema info
    """
    logger.info("=== 🗄️ Schema Understanding ===")
    logger.info(f"📨 Received message with status: {message.status}")
    logger.info(f"❓ Question: {message.question}")
    
    # Get M-Schema from shared state
    m_schema = await ctx.get_shared_state(M_SCHEMA_CACHE_KEY)
    
    # Prepare M-Schema for agent (simplified view)
    if message.database:
        # Case: Database pre-selected or retry with same database
        if message.database in m_schema:
            m_schema_for_agent = {
                message.database: {
                    "tables": list(
                        m_schema[message.database].get("tables", {}).keys()
                    )
                }
            }
        else:
            logger.warning(
                f"⚠️ Selected database '{message.database}' not found"
            )
            m_schema_for_agent = m_schema
    else:
        # Case: Search all databases
        m_schema_for_agent = {}
        for db_name, db_meta in m_schema.items():
            m_schema_for_agent[db_name] = {
                "tables": list(db_meta.get("tables", {}).keys())
            }

    # Create prompt
    m_schema_json = json.dumps(m_schema_for_agent, indent=2, ensure_ascii=False)
    
    prompt = prompt_manager.get_schema_understanding_prompt(
        question=message.question,
        m_schema_json=m_schema_json,
        selected_database=message.database if message.database else None,
        selected_tables=message.selected_tables,
    )

    # Get system prompt
    system_prompt = prompt_manager.get_system_prompt("schema_understanding")

    # Create chat client and agent
    chat_client = AzureOpenAIChatClient(credential=AzureCliCredential())

    agent = chat_client.create_agent(
        instructions=system_prompt,
        response_format=SchemaMappingResponse,
        middleware=[logging_middleware, exception_handling_middleware],
    )

    # Call LLM
    logger.info("📞 Calling LLM for schema selection...")
    response = await agent.run([ChatMessage(Role.USER, text=prompt)])

    # Parse agent response with error handling
    try:
        parsed = SchemaMappingResponse.model_validate_json(response.text)
    except Exception as e:
        logger.error(f"❌ Failed to parse LLM response: {e}")
        logger.error(f"📄 Response text (first 500 chars): {response.text[:500]}")
        logger.error(f"📄 Response text (last 500 chars): {response.text[-500:]}")
        
        # Try to extract database name manually as fallback
        import re
        db_match = re.search(r'"database":\s*"([^"]+)"', response.text)
        if db_match:
            database = db_match.group(1)
            logger.warning(f"⚠️  Fallback: Extracted database '{database}' from partial response")
            # Create minimal valid response
            parsed = SchemaMappingResponse(
                database=database,
                tables=[],
                reasoning="Schema selection completed with partial response (JSON parsing failed)"
            )
        else:
            # Cannot recover - re-raise
            raise ValueError(f"Failed to parse schema selection response: {e}\nResponse: {response.text[:1000]}...")

    database = parsed.database
    if not database:
        raise ValueError("Agent did not select a database")

    tables = parsed.tables

    logger.info(f"✅ Selected database: {database}")
    logger.info(f"📋 Selected tables: {tables}")
    logger.info(f"💭 Reasoning: {parsed.reasoning}")

    # Load detailed schema
    spider_db = SpiderDatabase()
    detailed_schema = spider_db.get_schema(database)

    # Create schema context
    schema_id = str(uuid4())
    schema_ctx = SchemaContext(
        context_id=schema_id,
        database=database,
        detailed_schema=detailed_schema,
        selected_tables=tables if tables else None,
        schema_mapping=parsed,
    )

    # Store in shared state
    await ctx.set_shared_state(
        f"{SCHEMA_STATE_PREFIX}{schema_id}", schema_ctx.model_dump()
    )
    await ctx.set_shared_state(CURRENT_SCHEMA_ID_KEY, schema_id)

    logger.info(f"💾 Stored schema context with ID: {schema_id}")
    logger.info(f"📏 Schema length: {len(detailed_schema)} characters")

    # Create next WorkflowMessage
    next_message = WorkflowMessage(
        question=message.question,
        database=database,
        status="SchemaSelected",
        retry_context=message.retry_context,
        selected_tables=tables,
        schema_id=schema_id,
        reasoning=parsed.reasoning,
    )

    logger.info("� Sending message to SQL generation executor")
    await ctx.send_message(next_message)
