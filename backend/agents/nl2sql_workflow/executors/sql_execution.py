"""SQL execution related executors."""

import logging
import time
import sqlite3

from agent_framework import AgentExecutorResponse, WorkflowContext, executor

from database.spider_utils import SpiderDatabase

from ..config import (
    CURRENT_SCHEMA_ID_KEY,
    CURRENT_SQL_RESPONSE_KEY,
    SCHEMA_STATE_PREFIX,
)
from ..models import ExecutionResult, SchemaContext, SQLGenerationResponse, StepMetadata

logger = logging.getLogger(__name__)


@executor(id="parse_sql_generation")
async def parse_sql_generation(
    response: AgentExecutorResponse, ctx: WorkflowContext[ExecutionResult]
) -> StepMetadata:
    """
    Parse SQL generation agent's response and execute the query.

    Responsibilities:
    - Validate agent's JSON response
    - Extract SQL query
    - Execute SQL against the database
    - Create ExecutionResult for switch-case routing
    - Return metadata for frontend display
    """
    logger.info("--- Parsing SQL Generation ---")

    # Parse agent response
    parsed = SQLGenerationResponse.model_validate_json(response.agent_run_response.text)

    sql = parsed.sql
    logger.info(f"Generated SQL: {sql}")
    logger.info(f"Reasoning: {parsed.reasoning}")
    logger.info(f"Confidence: {parsed.confidence}%")

    # Check confidence threshold - if too low, treat as semantic error for re-analysis
    CONFIDENCE_THRESHOLD = 50  # Require at least 50% confidence
    if parsed.confidence < CONFIDENCE_THRESHOLD:
        logger.warning(
            f"⚠️ Confidence ({parsed.confidence}%) below threshold ({CONFIDENCE_THRESHOLD}%)"
        )
        logger.warning("→ Triggering schema re-analysis due to low confidence")

        # Store SQLGenerationResponse for error handler
        await ctx.set_shared_state(CURRENT_SQL_RESPONSE_KEY, parsed.model_dump())

        # Create semantic error result for re-analysis
        execution_result = ExecutionResult(
            status="SemanticError",
            sql=sql,
            database="",  # Will be filled by error handler
            error_message=f"Low confidence ({parsed.confidence}%). Agent suggests schema re-analysis.",
            execution_time_ms=0.0,
            row_count=0,
        )

        metadata = StepMetadata(
            executor_id="parse_sql_generation",
            summary=f"⚠️ Low confidence ({parsed.confidence}%) - Re-analyzing schema",
            sql=sql,
            confidence=parsed.confidence,
            error=f"Confidence below {CONFIDENCE_THRESHOLD}%",
        )

        await ctx.send_message(execution_result)
        return metadata

    # Store SQLGenerationResponse for later evaluation
    await ctx.set_shared_state(CURRENT_SQL_RESPONSE_KEY, parsed.model_dump())

    # Get schema context
    schema_id: str = await ctx.get_shared_state(CURRENT_SCHEMA_ID_KEY)
    schema_ctx_dict: dict = await ctx.get_shared_state(
        f"{SCHEMA_STATE_PREFIX}{schema_id}"
    )
    schema_ctx = SchemaContext(**schema_ctx_dict)

    # Execute SQL
    spider_db = SpiderDatabase()

    start_time = time.time()
    metadata = StepMetadata(
        executor_id="parse_sql_generation",
        database=schema_ctx.database,
        sql=sql,
        confidence=parsed.confidence,
    )

    try:
        columns, rows = spider_db.execute_query(schema_ctx.database, sql, timeout=30.0)
        execution_time = (time.time() - start_time) * 1000

        # Convert to list of dicts
        result_rows = [dict(zip(columns, row)) for row in rows]

        if not result_rows or len(result_rows) == 0:
            # Empty result
            execution_result = ExecutionResult(
                status="EmptyResult",
                sql=sql,
                database=schema_ctx.database,
                result_rows=[],
                execution_time_ms=execution_time,
                row_count=0,
            )
            metadata.summary = f"⚠️ Query returned 0 rows ({execution_time:.0f}ms)"
        else:
            # Success
            execution_result = ExecutionResult(
                status="Success",
                sql=sql,
                database=schema_ctx.database,
                result_rows=result_rows,
                execution_time_ms=execution_time,
                row_count=len(result_rows),
            )
            metadata.summary = f"✅ {len(result_rows)} rows ({execution_time:.0f}ms)"

        logger.info(
            f"✓ Execution successful: {len(result_rows)} rows in {execution_time:.2f}ms"
        )

    except sqlite3.OperationalError as e:
        # Semantic errors: wrong table/column names
        execution_time = (time.time() - start_time) * 1000
        error_msg = str(e).lower()

        if any(
            keyword in error_msg
            for keyword in ["no such table", "no such column", "ambiguous"]
        ):
            status = "SemanticError"
        else:
            status = "SyntaxError"

        execution_result = ExecutionResult(
            status=status,
            sql=sql,
            database=schema_ctx.database,
            error_message=str(e),
            execution_time_ms=execution_time,
        )
        metadata.summary = f"❌ {status}: {str(e)[:50]}"
        metadata.error = str(e)
        logger.warning(f"✗ Execution failed ({status}): {e}")

    except sqlite3.Error as e:
        # Syntax errors
        execution_time = (time.time() - start_time) * 1000
        execution_result = ExecutionResult(
            status="SyntaxError",
            sql=sql,
            database=schema_ctx.database,
            error_message=str(e),
            execution_time_ms=execution_time,
        )
        metadata.summary = f"❌ SyntaxError: {str(e)[:50]}"
        metadata.error = str(e)
        logger.warning(f"✗ SQL syntax error: {e}")

    except TimeoutError as e:
        # Query timeout
        execution_time = (time.time() - start_time) * 1000
        execution_result = ExecutionResult(
            status="Timeout",
            sql=sql,
            database=schema_ctx.database,
            error_message=str(e),
            execution_time_ms=execution_time,
        )
        metadata.summary = f"⏱️ Timeout after {execution_time:.0f}ms"
        metadata.error = str(e)
        logger.warning(f"✗ Query timeout: {e}")

    except Exception as e:
        # Unknown errors - default to SyntaxError for retry
        execution_time = (time.time() - start_time) * 1000
        execution_result = ExecutionResult(
            status="SyntaxError",
            sql=sql,
            database=schema_ctx.database,
            error_message=str(e),
            execution_time_ms=execution_time,
        )
        metadata.summary = f"❌ Error: {str(e)[:50]}"
        metadata.error = str(e)
        logger.error(f"✗ Unexpected error: {e}", exc_info=True)

    # Send ExecutionResult for switch-case routing
    await ctx.send_message(execution_result)

    return metadata
