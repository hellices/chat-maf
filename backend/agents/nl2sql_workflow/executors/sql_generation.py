"""SQL generation executor."""

import logging
import sqlite3
import time
from typing import Any

from agent_framework import ChatMessage, Role, WorkflowContext, executor
from agent_framework.azure import AzureOpenAIChatClient
from azure.identity import AzureCliCredential

from database.spider_utils import SpiderDatabase
from middleware import exception_handling_middleware, logging_middleware

from ..config import (
    CURRENT_SCHEMA_ID_KEY,
    CURRENT_SQL_RESPONSE_KEY,
    SCHEMA_STATE_PREFIX,
)
from ..models import (
    SchemaContext,
    SQLGenerationResponse,
    WorkflowMessage,
)
from ..prompt_manager import prompt_manager

logger = logging.getLogger(__name__)


@executor(id="sql_generation")
async def sql_generation(
    message: WorkflowMessage, ctx: WorkflowContext[Any, WorkflowMessage]
) -> None:
    """
    Process SQL generation request and execute query.

    Receives WorkflowMessage with status="SchemaSelected" or "SyntaxError" (retry).
    Returns WorkflowMessage with status=Success/SyntaxError/SemanticError/EmptyResult/Timeout.

    Responsibilities:
    - Build SQL generation prompt from message context
    - Call LLM to generate SQL
    - Execute SQL against database
    - Create WorkflowMessage with execution results
    - Handle errors (syntax, semantic, execution)
    """
    logger.info("=== 🔧 SQL Generation ===")
    logger.info(f"📨 Received message with status: {message.status}")
    logger.info(f"🗄️  Database: {message.database}")

    # Check if this is a retry with feedback
    is_retry = message.status in ("SyntaxError", "SemanticError")
    if is_retry:
        logger.info("🔄 Retry attempt detected")
        logger.info(f"💬 Previous error: {message.error_message}")
        logger.info(f"📝 Previous SQL: {message.sql}")

    # Get schema context from shared state
    schema_id: str = await ctx.get_shared_state(CURRENT_SCHEMA_ID_KEY)
    schema_ctx_dict: dict = await ctx.get_shared_state(
        f"{SCHEMA_STATE_PREFIX}{schema_id}"
    )
    schema_ctx = SchemaContext(**schema_ctx_dict)

    # Build SQL generation prompt with feedback if this is a retry
    if is_retry and message.sql and message.error_message:
        # Retry: Include previous attempt and error for LLM to learn from
        if message.status == "SyntaxError":
            # Syntax error: Use syntax correction prompt
            sql_prompt = prompt_manager.get_syntax_error_correction_prompt(
                question=message.question,
                detailed_schema=schema_ctx.detailed_schema,
                failed_sql=message.sql,
                error_message=message.error_message,
            )
            logger.info("📋 Using SYNTAX correction prompt with feedback")
        else:  # SemanticError
            # Semantic error: This shouldn't happen in reflection pattern
            # (semantic errors should go back to schema_understanding)
            # But handle it as fallback
            logger.warning("⚠️  Semantic error in sql_generation - using fallback")
            sql_prompt = prompt_manager.get_sql_generation_prompt(
                question=message.question,
                detailed_schema=schema_ctx.detailed_schema,
                selected_tables=schema_ctx.selected_tables,
            )
    else:
        # Initial generation
        sql_prompt = prompt_manager.get_sql_generation_prompt(
            question=message.question,
            detailed_schema=schema_ctx.detailed_schema,
            selected_tables=schema_ctx.selected_tables,
        )
        logger.info("📋 Using initial SQL generation prompt")

    # Get system prompt
    system_prompt = prompt_manager.get_system_prompt("sql_generation")

    # Create chat client and agent
    chat_client = AzureOpenAIChatClient(credential=AzureCliCredential())

    agent = chat_client.create_agent(
        instructions=system_prompt,
        response_format=SQLGenerationResponse,
        model_kwargs={"temperature": 0.3},  # Lower temperature for SQL
        middleware=[logging_middleware, exception_handling_middleware],
    )

    # Call LLM
    logger.info("📞 Calling LLM for SQL generation...")
    response = await agent.run([ChatMessage(Role.USER, text=sql_prompt)])

    # Parse agent response with error handling
    try:
        parsed = SQLGenerationResponse.model_validate_json(response.text)
    except Exception as e:
        logger.error(f"❌ Failed to parse LLM response: {e}")
        logger.error(f"📄 Response text (first 500 chars): {response.text[:500]}")
        logger.error(f"📄 Response text (last 500 chars): {response.text[-500:]}")

        # Try to extract SQL manually as fallback
        import re

        sql_match = re.search(r'"sql":\s*"([^"]+)"', response.text)
        if sql_match:
            sql = sql_match.group(1)
            logger.warning("⚠️  Fallback: Extracted SQL from partial response")
            # Create minimal valid response
            parsed = SQLGenerationResponse(
                sql=sql,
                reasoning="SQL generation completed with partial response (JSON parsing failed)",
                confidence=50.0,  # Low confidence for fallback
            )
        else:
            # Cannot recover - create semantic error
            error_message = WorkflowMessage(
                question=message.question,
                database=message.database,
                sql="",
                status="SemanticError",
                error_message=f"Failed to parse SQL generation response: {e}",
                retry_context=message.retry_context,
                selected_tables=message.selected_tables,
                schema_id=message.schema_id,
            )
            await ctx.send_message(error_message)
            return

    sql = parsed.sql
    logger.info(f"✅ Generated SQL: {sql}")
    logger.info(f"💭 Reasoning: {parsed.reasoning}")
    logger.info(f"🎯 Confidence: {parsed.confidence}%")

    # Check confidence threshold - if too low, treat as semantic error
    CONFIDENCE_THRESHOLD = 50
    if parsed.confidence < CONFIDENCE_THRESHOLD:
        logger.warning(
            f"⚠️ Confidence ({parsed.confidence}%) below threshold ({CONFIDENCE_THRESHOLD}%)"
        )
        logger.warning("→ Triggering schema re-analysis due to low confidence")

        # Store SQLGenerationResponse for error handler
        await ctx.set_shared_state(CURRENT_SQL_RESPONSE_KEY, parsed.model_dump())

        # Create semantic error message for re-analysis
        error_message = WorkflowMessage(
            question=message.question,
            database=message.database,
            sql=sql,
            status="SemanticError",
            error_message=f"Low confidence ({parsed.confidence}%). Agent suggests schema re-analysis.",
            retry_context=message.retry_context,
            selected_tables=message.selected_tables,
            schema_id=message.schema_id,
            confidence=parsed.confidence,
            reasoning=parsed.reasoning,
        )

        # Send to sql_reviewer (reflection pattern)
        await ctx.send_message(error_message)
        return

    # Store SQLGenerationResponse for later evaluation
    await ctx.set_shared_state(CURRENT_SQL_RESPONSE_KEY, parsed.model_dump())

    # Execute SQL
    logger.info(f"🚀 Executing SQL on database: {schema_ctx.database}")
    spider_db = SpiderDatabase()

    start_time = time.time()

    try:
        columns, rows = spider_db.execute_query(schema_ctx.database, sql, timeout=30.0)
        execution_time = (time.time() - start_time) * 1000

        # Format results
        result_rows = [dict(zip(columns, row)) for row in rows]
        row_count = len(result_rows)

        logger.info(
            f"✅ Execution successful: {row_count} rows in {execution_time:.0f}ms"
        )

        # Create success message
        success_message = WorkflowMessage(
            question=message.question,
            database=schema_ctx.database,
            sql=sql,
            status="Success",
            result_rows=result_rows,
            retry_context=message.retry_context,
            selected_tables=message.selected_tables,
            schema_id=message.schema_id,
            confidence=parsed.confidence,
            reasoning=parsed.reasoning,
            execution_time_ms=execution_time,
            row_count=row_count,
        )

        # Send to sql_reviewer (reflection pattern)
        await ctx.send_message(success_message)

    except sqlite3.OperationalError as e:
        execution_time = (time.time() - start_time) * 1000
        error_msg = str(e)

        logger.error(f"❌ SQL syntax error: {error_msg}")

        # Determine error type
        syntax_keywords = [
            "syntax error",
            "near",
            "unrecognized token",
            "incomplete input",
        ]
        is_syntax_error = any(kw in error_msg.lower() for kw in syntax_keywords)

        if is_syntax_error:
            # Syntax error - can be fixed by SQL agent alone
            error_message = WorkflowMessage(
                question=message.question,
                database=schema_ctx.database,
                sql=sql,
                status="SyntaxError",
                error_message=error_msg,
                retry_context=message.retry_context,
                selected_tables=message.selected_tables,
                schema_id=message.schema_id,
                confidence=parsed.confidence,
                reasoning=parsed.reasoning,
                execution_time_ms=execution_time,
            )
        else:
            # Semantic error - requires schema re-analysis
            error_message = WorkflowMessage(
                question=message.question,
                database=schema_ctx.database,
                sql=sql,
                status="SemanticError",
                error_message=error_msg,
                retry_context=message.retry_context,
                selected_tables=message.selected_tables,
                schema_id=message.schema_id,
                confidence=parsed.confidence,
                reasoning=parsed.reasoning,
                execution_time_ms=execution_time,
            )

        # Send to sql_reviewer (reflection pattern)
        await ctx.send_message(error_message)

    except TimeoutError:
        execution_time = (time.time() - start_time) * 1000
        logger.error(f"⏱️ Query timeout after {execution_time:.0f}ms")

        timeout_message = WorkflowMessage(
            question=message.question,
            database=schema_ctx.database,
            sql=sql,
            status="Timeout",
            error_message="Query execution timed out",
            retry_context=message.retry_context,
            selected_tables=message.selected_tables,
            schema_id=message.schema_id,
            confidence=parsed.confidence,
            reasoning=parsed.reasoning,
            execution_time_ms=execution_time,
        )

        # Send to sql_reviewer (reflection pattern)
        await ctx.send_message(timeout_message)

    except Exception as e:
        execution_time = (time.time() - start_time) * 1000
        error_msg = str(e)

        logger.error(f"💥 Unexpected execution error: {error_msg}")

        # Treat unexpected errors as semantic errors for re-analysis
        error_message = WorkflowMessage(
            question=message.question,
            database=schema_ctx.database,
            sql=sql,
            status="SemanticError",
            error_message=f"Unexpected error: {error_msg}",
            retry_context=message.retry_context,
            selected_tables=message.selected_tables,
            schema_id=message.schema_id,
            confidence=parsed.confidence,
            reasoning=parsed.reasoning,
            execution_time_ms=execution_time,
        )

        # Send to sql_reviewer (reflection pattern)
        await ctx.send_message(error_message)
