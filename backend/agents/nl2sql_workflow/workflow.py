"""
NL2SQL Workflow - 6-step process for Natural Language to SQL translation.
Uses Microsoft Agent Framework WorkflowBuilder pattern for proper workflow orchestration.

Reference: https://github.com/microsoft/agent-framework/blob/main/python/samples/getting_started/workflows/control-flow/sequential_streaming.py
"""

# Standard library imports
import logging
from dataclasses import dataclass
from typing import Any, Optional

# Third-party imports
from agent_framework import WorkflowBuilder, WorkflowContext, executor
from agent_framework.azure import AzureOpenAIResponsesClient
from azure.identity import AzureCliCredential
from typing_extensions import Never

# Local application imports
from database.spider_utils import SpiderDatabase

from .helpers import (
    correct_sql_error,
    extract_entities,
    generate_natural_language_response,
    generate_sql,
    map_schema,
)
from .models import (
    EntityExtractionResponse,
    SchemaMappingResponse,
    SQLGenerationResponse,
)

logger = logging.getLogger(__name__)

# Static workflow configuration
DEFAULT_MAX_RETRIES = 3  # Maximum retry attempts for error correction

# M-Schema cache (loaded once and reused)
_M_SCHEMA_CACHE: Optional[dict] = None


@dataclass
class NL2SQLInput:
    """Input data for NL2SQL workflow."""

    message: str
    max_retries: int = DEFAULT_MAX_RETRIES
    return_natural_language: bool = False
    selected_database: Optional[str] = None  # Pre-selected database from UI
    selected_tables: Optional[list[str]] = None  # Pre-selected tables from UI


@dataclass
class WorkflowState:
    """Maintains state across workflow execution."""

    message: str
    max_retries: int
    return_natural_language: bool
    selected_database: Optional[str] = None  # UI pre-selected database
    selected_tables: Optional[list[str]] = None  # UI pre-selected tables
    m_schema: Optional[dict] = None  # All databases metadata
    db_name: Optional[str] = None  # Will be determined in Step 2
    schema: Optional[str] = None  # Detailed schema for selected DB
    entities: Optional[EntityExtractionResponse] = None
    schema_mapping: Optional[SchemaMappingResponse] = None
    sql_result: Optional[SQLGenerationResponse] = None
    current_sql: Optional[str] = None
    execution_result: Optional[Any] = None
    error_count: int = 0
    failed_sql: Optional[str] = None
    error_msg: Optional[str] = None


# ===== Step 0: Load M-Schema =====
@executor(id="load_m_schema")
async def load_m_schema_executor(
    input_data: NL2SQLInput, ctx: WorkflowContext[WorkflowState]
) -> None:
    """Load M-Schema metadata for all Spider databases (cached)."""
    global _M_SCHEMA_CACHE

    logger.info("=== NL2SQL Workflow Started ===")
    logger.info(f"Message: {input_data.message}")
    logger.info(f"Max Retries: {input_data.max_retries}")
    logger.info(f"Return Natural Language: {input_data.return_natural_language}")

    # Use cached M-Schema if available
    if _M_SCHEMA_CACHE is not None:
        logger.info(f"Using cached M-Schema for {len(_M_SCHEMA_CACHE)} databases")
        m_schema = _M_SCHEMA_CACHE
    else:
        # Load M-Schema (all databases metadata) for the first time
        import json
        from pathlib import Path

        m_schema_path = (
            Path(__file__).parent.parent.parent
            / "database"
            / "spider"
            / "m_schema.json"
        )

        if not m_schema_path.exists():
            raise FileNotFoundError(
                f"M-Schema file not found: {m_schema_path}\n"
                "Please run: python database/generate_m_schema.py"
            )

        with open(m_schema_path, "r", encoding="utf-8") as f:
            m_schema = json.load(f)

        # Cache for future use
        _M_SCHEMA_CACHE = m_schema
        logger.info(f"Loaded and cached M-Schema for {len(m_schema)} databases")

    state = WorkflowState(
        message=input_data.message,
        max_retries=input_data.max_retries,
        return_natural_language=input_data.return_natural_language,
        selected_database=input_data.selected_database,
        selected_tables=input_data.selected_tables,
        m_schema=m_schema,
    )

    await ctx.send_message(state)


# ===== Step 1: Query Intent Extraction =====
@executor(id="extract_entities")
async def extract_entities_executor(
    state: WorkflowState, ctx: WorkflowContext[WorkflowState]
) -> None:
    """Extract query intent from natural language WITHOUT looking at schema.

    This step analyzes the user's question to identify:
    - What entities/tables they're asking about (in natural language)
    - What columns/attributes they want
    - What operations (COUNT, LIMIT, JOIN, etc.)

    M-Schema is NOT used here - pure query intent extraction.
    """
    logger.info("\n--- Step 1: Query Intent Extraction (Schema-Agnostic) ---")

    try:
        client = AzureOpenAIResponsesClient(credential=AzureCliCredential())
        # Pass empty/minimal schema - we only want to extract intent
        entities = await extract_entities(client, state.message, schema="")
        logger.info(f"Step 1 completed - Extracted query intent: {entities}")
        logger.info(f"  Tables/Entities mentioned: {entities.tables}")
        logger.info(f"  Columns/Attributes: {entities.columns}")
        logger.info(f"  Query concepts: {entities.concepts}")

        state.entities = entities
        await ctx.send_message(state)
    except Exception as e:
        logger.error(f"Step 1 failed: {str(e)}", exc_info=True)
        raise


# ===== Step 2: Schema Mapping + Database Selection =====
@executor(id="map_schema")
async def map_schema_executor(
    state: WorkflowState, ctx: WorkflowContext[WorkflowState]
) -> None:
    """Map extracted query intent to actual database schema using M-Schema.

    This step uses an LLM agent to intelligently:
    1. Select the best matching database from M-Schema
    2. Map natural language entities to actual table names
    3. Map attributes to actual column names

    All mapping is done by the agent, not by hardcoded logic.
    """
    logger.info("\n--- Step 2: Schema Mapping + Database Selection ---")

    assert state.entities is not None, "Query intent must be extracted first"
    assert state.m_schema is not None, "M-Schema must be loaded"

    # Case 1: User pre-selected BOTH database AND tables
    if state.selected_database and state.selected_tables:
        logger.info("🎯 Case 1: Using UI pre-selected database and tables:")
        logger.info(f"  Database: {state.selected_database}")
        logger.info(f"  Tables: {state.selected_tables}")

        # Skip LLM mapping - use pre-selected values directly
        state.db_name = state.selected_database

        # Create a simple schema mapping based on selected tables
        schema_mapping = SchemaMappingResponse(
            model_used="UI_SELECTION",
            confidence=100,  # User's explicit choice
            raw_response=f"User selected database: {state.selected_database}, tables: {state.selected_tables}",
            database=state.selected_database,
            table_mapping={"_database": state.selected_database},
            column_mapping={},
            join_paths=[],
            filters=[],
            success=True,
        )

        # Load the detailed schema for the selected database
        spider_db = SpiderDatabase()
        detailed_schema = spider_db.get_schema(state.selected_database)
        state.schema = detailed_schema
        logger.info(f"Loaded detailed schema: {len(detailed_schema)} characters")

        state.schema_mapping = schema_mapping
        await ctx.send_message(state)
        return

    try:
        client = AzureOpenAIResponsesClient(credential=AzureCliCredential())
        import json

        # Case 2: User pre-selected ONLY database (no tables)
        if state.selected_database:
            logger.info(
                "🎯 Case 2: Using UI pre-selected database (LLM will select tables):"
            )
            logger.info(f"  Database: {state.selected_database}")

            # Verify database exists in M-Schema
            if state.selected_database not in state.m_schema:
                logger.warning(
                    f"Selected database '{state.selected_database}' not found in M-Schema!"
                )
                logger.warning(
                    f"Available databases: {list(state.m_schema.keys())[:10]}..."
                )
                # Fall through to Case 3 (search all databases)
            else:
                # Use ONLY the selected database's M-Schema
                m_schema_for_agent = {
                    state.selected_database: {
                        "tables": list(
                            state.m_schema[state.selected_database]
                            .get("tables", {})
                            .keys()
                        )
                    }
                }

                m_schema_json = json.dumps(
                    m_schema_for_agent, indent=2, ensure_ascii=False
                )
                logger.info(
                    f"Passing M-Schema for database '{state.selected_database}' with {len(m_schema_for_agent[state.selected_database]['tables'])} tables"
                )
                logger.info(f"Query intent to map: {state.entities}")

                # Let LLM map tables within the selected database
                schema_mapping = await map_schema(
                    client,
                    state.entities,
                    m_schema_json,
                    state.selected_database,  # Pass database name as hint
                )

                # Force the selected database (even if LLM returns something else)
                schema_mapping.database = state.selected_database
                state.db_name = state.selected_database

                # Load detailed schema
                spider_db = SpiderDatabase()
                detailed_schema = spider_db.get_schema(state.selected_database)
                state.schema = detailed_schema
                logger.info(f"✓ Using pre-selected database: {state.selected_database}")
                logger.info(
                    f"Loaded detailed schema: {len(detailed_schema)} characters"
                )

                state.schema_mapping = schema_mapping
                await ctx.send_message(state)
                return

        # Case 3: No database selected - search ALL databases
        logger.info(
            "🔍 Case 3: No database pre-selected - LLM will search all databases"
        )

        m_schema_for_agent = {}
        for db_name, db_meta in state.m_schema.items():
            tables = db_meta.get("tables", {})
            # Simplify schema: just database name and table names
            m_schema_for_agent[db_name] = {"tables": list(tables.keys())}

        m_schema_json = json.dumps(m_schema_for_agent, indent=2, ensure_ascii=False)
        logger.info(
            f"Passing M-Schema with {len(m_schema_for_agent)} databases to agent"
        )
        logger.info(f"Query intent to map: {state.entities}")

        # Let the LLM agent do the intelligent mapping
        schema_mapping = await map_schema(
            client,
            state.entities,
            m_schema_json,  # Pass full M-Schema to agent
            "",  # Database name will be determined by agent
        )

        # Extract the selected database from schema_mapping.database field
        selected_db = schema_mapping.database
        if not selected_db or selected_db not in state.m_schema:
            # Fallback if agent didn't specify or specified invalid database
            logger.warning(f"Agent didn't select valid database: {selected_db}")
            logger.warning(f"Available databases: {list(state.m_schema.keys())[:5]}...")
            selected_db = (
                "concert_singer"
                if "concert_singer" in state.m_schema
                else list(state.m_schema.keys())[0]
            )
            logger.warning(f"Using fallback database: {selected_db}")

        logger.info(f"✓ Agent selected database: {selected_db}")
        state.db_name = selected_db

        # Now load the detailed schema for the selected database
        spider_db = SpiderDatabase()
        detailed_schema = spider_db.get_schema(selected_db)
        state.schema = detailed_schema
        logger.info(f"Loaded detailed schema: {len(detailed_schema)} characters")

        logger.info(f"Step 2 completed - Schema mapping: {schema_mapping}")
        state.schema_mapping = schema_mapping
        await ctx.send_message(state)
    except Exception as e:
        logger.error(f"Step 2 failed: {str(e)}", exc_info=True)
        raise


# ===== Step 3: SQL Generation =====
@executor(id="generate_sql")
async def generate_sql_executor(
    state: WorkflowState, ctx: WorkflowContext[WorkflowState]
) -> None:
    """Generate SQL query based on mapped schema."""
    logger.info("\n--- Step 3: SQL Generation ---")

    assert state.schema_mapping is not None, "Schema mapping must be completed first"
    assert state.schema is not None, "Schema must be initialized"

    try:
        client = AzureOpenAIResponsesClient(credential=AzureCliCredential())
        sql_result = await generate_sql(
            client,
            state.message,
            state.schema,
            state.schema_mapping,
            selected_tables=state.selected_tables,  # Pass UI-selected tables
        )
        logger.info(
            f"Step 3 completed successfully. Confidence: {sql_result.confidence:.1f}%"
        )
        logger.info(f"Generated SQL: {sql_result.sql}")
        if state.selected_tables:
            logger.info(f"  (Using UI-selected tables: {state.selected_tables})")

        state.sql_result = sql_result
        state.current_sql = sql_result.sql
        await ctx.send_message(state)
    except Exception as e:
        logger.error(f"Step 3 failed: {str(e)}", exc_info=True)
        raise


# ===== Step 4: SQL Execution (with retry logic) =====
@executor(id="execute_sql")
async def execute_sql_executor(
    state: WorkflowState, ctx: WorkflowContext[WorkflowState]
) -> None:
    """Execute SQL query and handle errors with retry logic."""
    logger.info("\n--- Step 4: SQL Execution ---")

    assert state.current_sql is not None, "SQL must be generated first"
    assert state.schema is not None, "Schema must be initialized"
    assert state.schema_mapping is not None, "Schema mapping must be completed"
    assert state.db_name is not None, "Database must be selected"

    spider_db = SpiderDatabase()

    while state.error_count <= state.max_retries:
        attempt = state.error_count + 1
        logger.info(
            f"Attempting to execute SQL (attempt {attempt}/{state.max_retries + 1}): {state.current_sql}"
        )

        try:
            execution_result = spider_db.execute_query(
                state.db_name, state.current_sql, max_rows=100
            )
            logger.info(f"✓ SQL execution successful! Result: {execution_result}")

            state.execution_result = execution_result
            await ctx.send_message(state)
            return

        except Exception as e:
            error_msg = str(e)
            logger.error(f"✗ SQL execution failed: {error_msg}")

            if state.error_count >= state.max_retries:
                logger.error(f"Max retries ({state.max_retries}) exceeded. Giving up.")
                raise Exception(f"Max retries exceeded. Last error: {error_msg}")

            # Store error info for correction step
            state.failed_sql = state.current_sql
            state.error_msg = error_msg
            state.error_count += 1

            # Attempt error correction
            try:
                logger.info(f"\n--- Step 5: Error Correction (attempt {attempt}) ---")
                assert state.failed_sql is not None, "Failed SQL must be set"

                client = AzureOpenAIResponsesClient(credential=AzureCliCredential())
                corrected_response = await correct_sql_error(
                    client=client,
                    message=state.message,
                    schema=state.schema,
                    failed_sql=state.failed_sql,
                    error_msg=error_msg,
                    schema_mapping=state.schema_mapping,
                )

                state.current_sql = corrected_response.corrected_sql
                logger.info(f"Step 5 completed. Corrected SQL: {state.current_sql}")

            except Exception as correction_error:
                logger.error(f"Step 5 failed: {str(correction_error)}", exc_info=True)
                raise


# ===== Step 6: Natural Language Response (Optional) =====
@executor(id="generate_nl_response")
async def generate_nl_response_executor(
    state: WorkflowState, ctx: WorkflowContext[Never, dict]
) -> None:
    """Generate natural language response from SQL execution results."""

    # Always include SQL in the result
    base_result = {
        "sql": state.current_sql or "",
        "execution_result": state.execution_result,
        "database": state.db_name,
    }

    if not state.return_natural_language:
        logger.info("Skipping Step 6: Natural Language Response (disabled)")
        await ctx.yield_output(base_result)
        return

    logger.info("\n--- Step 6: Natural Language Response ---")

    try:
        client = AzureOpenAIResponsesClient(credential=AzureCliCredential())
        nl_response = await generate_natural_language_response(
            client=client,
            message=state.message,
            sql=state.current_sql or "",
            execution_result=state.execution_result,
        )
        logger.info("Step 6 completed successfully")
        logger.info(f"Natural Language Response: {nl_response.response}")

        result = {
            **base_result,
            "natural_language_response": nl_response.response,
        }
        await ctx.yield_output(result)
    except Exception as e:
        logger.error(f"Step 6 failed: {str(e)}", exc_info=True)
        # Fallback to SQL if NL generation fails
        result = {
            **base_result,
            "error": str(e),
        }
        await ctx.yield_output(result)


# ===== Build Workflow =====


def build_nl2sql_workflow():
    """
    Build the NL2SQL workflow using WorkflowBuilder pattern.

    Returns:
        Configured Workflow instance ready for execution
    """
    workflow = (
        WorkflowBuilder()
        .add_edge(load_m_schema_executor, extract_entities_executor)
        .add_edge(extract_entities_executor, map_schema_executor)
        .add_edge(map_schema_executor, generate_sql_executor)
        .add_edge(generate_sql_executor, execute_sql_executor)
        .add_edge(execute_sql_executor, generate_nl_response_executor)
        .set_start_executor(load_m_schema_executor)
        .build()  # This returns a Workflow instance
    )

    return workflow


# ===== Backward Compatibility Wrapper =====


async def nl2sql_workflow(
    message: str,
    max_retries: int = DEFAULT_MAX_RETRIES,
    return_natural_language: bool = False,
    selected_database: Optional[str] = None,
    selected_tables: Optional[list[str]] = None,
):
    """
    Backward compatible wrapper for streaming workflow execution.

    This maintains the old API while using the new WorkflowBuilder pattern internally.
    """
    workflow_instance = build_nl2sql_workflow()

    input_data = NL2SQLInput(
        message=message,
        max_retries=max_retries,
        return_natural_language=return_natural_language,
        selected_database=selected_database,
        selected_tables=selected_tables,
    )

    async for event in workflow_instance.run_stream(input_data):
        # Convert workflow events to old WorkflowStep format for compatibility
        logger.info(f"Workflow Event: {event}")
        yield event


# ===== DevUI Entry Point =====


async def run_workflow(message: str):
    """Entry point for DevUI workflow execution."""
    workflow_instance = build_nl2sql_workflow()

    input_data = NL2SQLInput(
        message=message,
        return_natural_language=False,
    )

    results = []
    async for event in workflow_instance.run_stream(input_data):
        results.append(event)
        logger.info(f"Event: {event}")

    return results


# ===== Main Entry Point for DevUI Serve =====


def main():
    """Launch the NL2SQL workflow in DevUI."""
    from agent_framework.devui import serve

    logger.info("=" * 80)
    logger.info("NL2SQL Workflow - Natural Language to SQL Translation")
    logger.info("=" * 80)
    logger.info("Available at: http://localhost:8080")
    logger.info("")
    logger.info("This workflow demonstrates:")
    logger.info("  • 6-step NL2SQL process using WorkflowBuilder pattern")
    logger.info("  • Entity Extraction → Schema Mapping → SQL Generation")
    logger.info("  • SQL Execution with automatic error correction (retry logic)")
    logger.info("  • Optional Natural Language response generation")
    logger.info("")
    logger.info("Try asking:")
    logger.info("  - 'How many singers do we have?'")
    logger.info("  - 'List all stadium names and their capacity'")
    logger.info("  - 'What is the average age of students?'")
    logger.info("=" * 80)

    # Build and serve the workflow
    workflow = build_nl2sql_workflow()
    serve(entities=[workflow], port=8080, auto_open=True)


if __name__ == "__main__":
    main()
