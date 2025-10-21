"""
NL2SQL Workflow Helper Functions.
Agent execution helpers for each workflow step.
"""

import json
import logging
import re
from typing import Any

from agent_framework.azure import AzureOpenAIResponsesClient
from config.settings import settings

from .models import (
    EntityExtractionResponse,
    ErrorCorrectionResponse,
    NaturalLanguageResponse,
    SchemaMappingResponse,
    SQLGenerationResponse,
)
from .prompts import (
    ENTITY_EXTRACTION_INSTRUCTIONS,
    ERROR_CORRECTION_INSTRUCTIONS,
    NL_RESPONSE_INSTRUCTIONS,
    SCHEMA_MAPPING_INSTRUCTIONS,
    SQL_GENERATION_INSTRUCTIONS,
    entity_extraction_prompt,
    error_correction_prompt,
    nl_response_prompt,
    schema_mapping_prompt,
    sql_generation_prompt,
)

logger = logging.getLogger(__name__)


async def extract_entities(
    client: AzureOpenAIResponsesClient, question: str, schema: str
) -> EntityExtractionResponse:
    """Extract query target entities from natural language."""
    model_name = settings.nl2sql_entity_extractor_model

    agent = client.create_agent(
        model=model_name,
        instructions=ENTITY_EXTRACTION_INSTRUCTIONS,
        name="EntityExtractor",
        json_output=True,
    )

    prompt = entity_extraction_prompt(question, schema)

    logger.info(f"[Step 1] Using model: {model_name}")
    response = await agent.run(prompt)
    response_text = str(response)
    logger.info(f"[Step 1] Agent response: {response_text[:500]}...")

    try:
        parsed = json.loads(response_text)

        result = EntityExtractionResponse(
            model_used=model_name,
            confidence=parsed.get("confidence", 80),
            raw_response=response_text,
            tables=parsed.get("tables", []),
            columns=parsed.get("columns", []),
            concepts=parsed.get("concepts", []),
            success=True,
        )

        if result.confidence < settings.nl2sql_min_confidence_score:
            logger.warning(
                f"[Step 1] Low confidence: {result.confidence:.1f}% "
                f"(threshold: {settings.nl2sql_min_confidence_score}%)"
            )

        logger.info(
            f"[Step 1] ✓ Parsed successfully. Confidence: {result.confidence:.1f}%"
        )
        logger.info(f"[Step 1] Tables: {result.tables}")
        logger.info(f"[Step 1] Columns: {result.columns}")
        logger.info(f"[Step 1] Concepts: {result.concepts}")

    except Exception as e:
        logger.error(f"[Step 1] Failed to parse JSON: {e}")
        result = EntityExtractionResponse(
            model_used=model_name,
            confidence=0,
            raw_response=response_text,
            tables=[],
            columns=[],
            concepts=[],
            success=False,
            error_message=str(e),
        )

    return result


async def map_schema(
    client: AzureOpenAIResponsesClient,
    entities: EntityExtractionResponse,
    schema: str,
    db_name: str,
) -> SchemaMappingResponse:
    """Map extracted entities to precise schema elements."""
    model_name = settings.nl2sql_schema_mapper_model

    agent = client.create_agent(
        model=model_name,
        instructions=SCHEMA_MAPPING_INSTRUCTIONS,
        name="SchemaMapper",
        json_output=True,
    )

    entities_dict = {
        "tables": entities.tables,
        "columns": entities.columns,
        "concepts": entities.concepts,
    }
    prompt = schema_mapping_prompt(db_name, entities_dict, schema)

    logger.info(f"[Step 2] Using model: {model_name}")
    response = await agent.run(prompt)
    response_text = str(response)
    logger.info(f"[Step 2] Agent response: {response_text[:500]}...")
    try:
        parsed = json.loads(response_text)

        result = SchemaMappingResponse(
            model_used=model_name,
            confidence=parsed.get("confidence", 80),
            raw_response=response_text,
            database=parsed.get("_database"),  # Extract _database from JSON
            table_mapping=parsed.get("table_mapping", {}),
            column_mapping=parsed.get("column_mapping", {}),
            join_paths=parsed.get("join_paths", []),
            filters=parsed.get("filters", []),
            success=True,
        )

        if result.confidence < settings.nl2sql_min_confidence_score:
            logger.warning(
                f"[Step 2] Low confidence: {result.confidence:.1f}% "
                f"(threshold: {settings.nl2sql_min_confidence_score}%)"
            )

        logger.info(
            f"[Step 2] ✓ Parsed successfully. Confidence: {result.confidence:.1f}%"
        )
        logger.info(f"[Step 2] Selected database: {result.database}")
        logger.info(f"[Step 2] Table mapping: {result.table_mapping}")
        logger.info(f"[Step 2] Join paths: {len(result.join_paths)} joins")

    except Exception as e:
        logger.error(f"[Step 2] Failed to parse JSON: {e}")
        result = SchemaMappingResponse(
            model_used=model_name,
            confidence=0,
            raw_response=response_text,
            table_mapping={},
            column_mapping={},
            join_paths=[],
            filters=[],
            success=False,
            error_message=str(e),
        )

    return result


async def generate_sql(
    client: AzureOpenAIResponsesClient,
    question: str,
    schema: str,
    schema_mapping: SchemaMappingResponse,
    selected_tables: list[str] | None = None,
) -> SQLGenerationResponse:
    """Generate SQL query based on mapped schema."""
    model_name = settings.nl2sql_sql_generator_model

    agent = client.create_agent(
        model=model_name,
        instructions=SQL_GENERATION_INSTRUCTIONS,
        name="SQLGenerator",
        json_output=True,
    )

    schema_mapping_dict = {
        "table_mapping": schema_mapping.table_mapping,
        "column_mapping": schema_mapping.column_mapping,
        "join_paths": schema_mapping.join_paths,
    }
    prompt = sql_generation_prompt(
        question, schema, schema_mapping_dict, selected_tables
    )

    logger.info(f"[Step 3] Using model: {model_name}")
    response = await agent.run(prompt)
    response_text = str(response)
    logger.info(f"[Step 3] Agent response: {response_text[:500]}...")

    try:
        # Try to parse as JSON first
        parsed = json.loads(response_text)
        sql = parsed.get("sql", "").strip().rstrip(";")
        reasoning = parsed.get("reasoning", "")
        confidence = parsed.get("confidence", 0)

        result = SQLGenerationResponse(
            model_used=model_name,
            confidence=confidence,
            raw_response=response_text,
            sql=sql,
            reasoning=reasoning,
            success=True,
        )

    except Exception as e:
        logger.warning(f"[Step 3] Failed to parse JSON: {e}, trying regex extraction")
        # Fallback: extract SQL using regex
        sql_match = re.search(
            r"SELECT\s+.*?(?:;|$)", response_text, re.IGNORECASE | re.DOTALL
        )
        sql = (
            sql_match.group(0).strip().rstrip(";")
            if sql_match
            else response_text.strip()
        )

        result = SQLGenerationResponse(
            model_used=model_name,
            confidence=75,
            raw_response=response_text,
            sql=sql,
            reasoning="Extracted from agent response using regex",
            success=False,
            error_message=str(e),
        )

    if result.confidence < settings.nl2sql_min_confidence_score:
        logger.warning(
            f"[Step 3] Low confidence: {result.confidence:.1f}% "
            f"(threshold: {settings.nl2sql_min_confidence_score}%)"
        )

    logger.info(f"[Step 3] ✓ Generated SQL. Confidence: {result.confidence:.1f}%")
    logger.info(f"[Step 3] SQL: {result.sql}")

    return result


async def correct_sql_error(
    client: AzureOpenAIResponsesClient,
    message: str,
    schema: str,
    failed_sql: str,
    error_msg: str,
    schema_mapping: SchemaMappingResponse,
) -> ErrorCorrectionResponse:
    """Correct SQL execution errors iteratively."""
    model_name = settings.nl2sql_error_corrector_model

    agent = client.create_agent(
        model=model_name,
        instructions=ERROR_CORRECTION_INSTRUCTIONS,
        name="SQLErrorCorrector",
        json_output=True,
    )

    schema_mapping_dict = {
        "table_mapping": schema_mapping.table_mapping,
        "column_mapping": schema_mapping.column_mapping,
    }
    prompt = error_correction_prompt(
        message, schema, failed_sql, error_msg, schema_mapping_dict
    )

    logger.info(f"[Step 5] Using model: {model_name}")
    response = await agent.run(prompt)
    response_text = str(response)
    logger.info(f"[Step 5] Agent response: {response_text[:500]}...")

    # Extract corrected SQL from response
    sql_match = re.search(
        r"SELECT\s+.*?(?:;|$)", response_text, re.IGNORECASE | re.DOTALL
    )
    if sql_match:
        corrected_sql = sql_match.group(0).strip().rstrip(";")
    else:
        # If no SELECT found, try to extract any SQL-like statement
        corrected_sql = response_text.strip().rstrip(";")

    result = ErrorCorrectionResponse(
        model_used=model_name,
        confidence=80,  # Default confidence for error correction
        raw_response=response_text,
        corrected_sql=corrected_sql,
        original_error=error_msg,
        correction_applied="Extracted SQL from agent response",
        success=True,
    )

    logger.info(f"[Step 5] ✓ Corrected SQL: {result.corrected_sql}")

    return result


async def generate_natural_language_response(
    client: AzureOpenAIResponsesClient,
    message: str,
    sql: str,
    execution_result: Any,
) -> NaturalLanguageResponse:
    """Generate natural language response from SQL execution results."""
    model_name = settings.nl2sql_entity_extractor_model  # Reuse model for NL generation

    agent = client.create_agent(
        model=model_name,
        instructions=NL_RESPONSE_INSTRUCTIONS,
        name="NaturalLanguageGenerator",
        json_output=True,
    )

    # Format execution result for prompt
    result_str = str(execution_result)
    if len(result_str) > 500:
        result_str = result_str[:500] + "... (truncated)"

    prompt = nl_response_prompt(message, sql, result_str)

    logger.info(f"[Step 6] Using model: {model_name}")
    response = await agent.run(prompt)
    response_text = str(response)
    logger.info(f"[Step 6] Agent response: {response_text[:500]}...")

    try:
        parsed = json.loads(response_text)

        result = NaturalLanguageResponse(
            model_used=model_name,
            confidence=parsed.get("confidence", 85),
            raw_response=response_text,
            response=parsed.get("response", response_text),
            summary=parsed.get("summary", ""),
            success=True,
        )
    except Exception as e:
        logger.warning(f"[Step 6] Failed to parse JSON: {e}, using raw response")

        result = NaturalLanguageResponse(
            model_used=model_name,
            confidence=75,
            raw_response=response_text,
            response=response_text,
            summary="",
            success=False,
            error_message=str(e),
        )

    logger.info("[Step 6] ✓ Generated natural language response")

    return result
