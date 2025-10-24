"""
NL2SQL Data Models.
Core models for workflow execution and routing.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


# ===== Workflow Input/Output Models =====


@dataclass
class NL2SQLInput:
    """Input for the NL2SQL workflow."""

    question: str
    selected_database: Optional[str] = None
    selected_tables: Optional[list[str]] = None
    return_natural_language: bool = False


class NL2SQLOutput(BaseModel):
    """Final output from the NL2SQL workflow."""

    sql: str = Field(..., description="Generated SQL query")
    database: str = Field(..., description="Database name")
    execution_result: Optional[dict] = Field(
        None, description="Query execution results"
    )
    natural_language_response: Optional[str] = Field(
        None, description="Human-readable response"
    )
    reasoning_evaluation: Optional[dict] = Field(
        None, description="Evaluation of the SQL generation reasoning"
    )


class StepMetadata(BaseModel):
    """
    Metadata for each workflow step.
    Sent to frontend for progress display.
    """

    executor_id: str = Field(..., description="Executor identifier")
    summary: Optional[str] = Field(
        default=None, description="Brief summary for frontend display"
    )
    database: Optional[str] = Field(default=None, description="Current database")
    tables: Optional[list[str]] = Field(default=None, description="Selected tables")
    sql: Optional[str] = Field(default=None, description="Generated or current SQL")
    confidence: Optional[float] = Field(
        default=None, description="Confidence score if applicable"
    )
    error: Optional[str] = Field(default=None, description="Error message if failed")
    retry_count: Optional[int] = Field(default=None, description="Retry attempt number")


# ===== Unified Workflow Message =====


class WorkflowMessage(BaseModel):
    """
    Unified message type for all executor communications.

    This replaces the mixed usage of ChatMessage lists and ExecutionResult dicts,
    providing a consistent interface across the entire workflow.

    Status lifecycle:
    1. Init -> initialize_context starts workflow
    2. SchemaSelected -> schema_understanding selected database/tables
    3. SQLGenerated -> sql_generation created SQL
    4. Success/SyntaxError/SemanticError/EmptyResult/Timeout -> execution results

    Design principles:
    - Small, frequently-used data in message (question, sql, status)
    - Large payloads in shared state (detailed_schema, m_schema) referenced by ID
    - Retry context included for visibility without shared state lookup
    """

    # === Core workflow state ===
    question: str = Field(..., description="User's natural language question")
    database: str = Field(default="", description="Selected database name")
    sql: Optional[str] = Field(
        default=None, description="Generated or current SQL query"
    )

    # === Execution status ===
    status: Literal[
        "Init",  # Workflow initialization
        "SchemaSelected",  # Schema understanding complete
        "SQLGenerated",  # SQL generation complete (not yet executed)
        "Success",  # Query executed successfully
        "SyntaxError",  # SQL syntax error (fixable without schema change)
        "SemanticError",  # Wrong table/column (requires schema re-analysis)
        "EmptyResult",  # Query succeeded but returned no rows
        "Timeout",  # Query execution timeout
    ] = Field(..., description="Current workflow state")

    # === Execution results ===
    result_rows: Optional[List[Dict[str, Any]]] = Field(
        default=None, description="Query execution results"
    )
    error_message: Optional[str] = Field(
        default=None, description="Error message if status indicates failure"
    )

    # === Metadata ===
    retry_context: "RetryContext" = Field(
        default_factory=lambda: RetryContext(),
        description="Retry counters (included for visibility)",
    )
    confidence: Optional[float] = Field(
        default=None, description="Confidence score (0-100) from LLM"
    )
    reasoning: Optional[str] = Field(
        default=None, description="LLM reasoning for schema/SQL selection"
    )

    # === Schema info (small - just references) ===
    selected_tables: Optional[List[str]] = Field(
        default=None, description="List of selected table names"
    )
    schema_id: Optional[str] = Field(
        default=None,
        description="Reference ID for detailed schema in shared state",
    )

    # === Execution metrics ===
    execution_time_ms: float = Field(default=0.0, description="Query execution time")
    row_count: int = Field(default=0, description="Number of rows returned")

    # === Helper methods ===
    def is_success(self) -> bool:
        """Check if execution was successful."""
        return self.status == "Success"

    def needs_schema_refinement(self) -> bool:
        """Check if error requires schema re-analysis."""
        return self.status == "SemanticError"

    def needs_sql_refinement(self) -> bool:
        """Check if error can be fixed by SQL correction only."""
        return self.status == "SyntaxError"

    def can_retry_syntax(self) -> bool:
        """Check if we can retry SQL syntax correction."""
        return self.retry_context.can_retry_syntax()

    def can_retry_semantic(self) -> bool:
        """Check if we can retry schema re-analysis."""
        return self.retry_context.can_retry_semantic()


# ===== Legacy model (deprecated - use WorkflowMessage) =====


class ExecutionResult(BaseModel):
    """
    DEPRECATED: Use WorkflowMessage instead.

    SQL execution result for switch-case routing.
    Kept for backward compatibility during migration.
    """

    status: Literal["Success", "SyntaxError", "SemanticError", "EmptyResult", "Timeout"]
    sql: str
    database: str
    error_message: Optional[str] = None
    result_rows: Optional[List[Dict[str, Any]]] = None
    execution_time_ms: float = 0.0
    row_count: int = 0

    def is_success(self) -> bool:
        """Check if execution was successful."""
        return self.status == "Success"

    def needs_schema_refinement(self) -> bool:
        """Check if error requires schema re-analysis."""
        return self.status == "SemanticError"

    def needs_sql_refinement(self) -> bool:
        """Check if error can be fixed by SQL correction only."""
        return self.status == "SyntaxError"


class RetryContext(BaseModel):
    """
    Tracks refinement attempts across workflow execution.
    Used in shared state to prevent infinite loops.
    """

    syntax_retry_count: int = 0
    semantic_retry_count: int = 0
    max_syntax_retries: int = 2
    max_semantic_retries: int = 2

    def can_retry_syntax(self) -> bool:
        """Check if we can retry SQL syntax correction."""
        return self.syntax_retry_count < self.max_syntax_retries

    def can_retry_semantic(self) -> bool:
        """Check if we can retry schema re-analysis."""
        return self.semantic_retry_count < self.max_semantic_retries

    def increment_syntax(self) -> None:
        """Increment syntax retry counter."""
        self.syntax_retry_count += 1

    def increment_semantic(self) -> None:
        """Increment semantic retry counter."""
        self.semantic_retry_count += 1


# ===== Agent Response Models =====


class SchemaMappingResponse(BaseModel):
    """Schema understanding agent response."""

    database: str = Field(..., description="Selected database name from M-Schema")
    tables: List[str] = Field(..., description="List of relevant table names")
    reasoning: str = Field(..., description="Why these tables were selected")


class SQLGenerationResponse(BaseModel):
    """SQL generation agent response."""

    sql: str = Field(..., description="Generated SQL query")
    reasoning: str = Field(..., description="Step-by-step reasoning")
    confidence: float = Field(..., ge=0, le=100, description="Confidence score (0-100)")


class ReasoningEvaluation(BaseModel):
    """
    Evaluation of the reasoning provided by the SQL generation agent.
    Used to verify if the reasoning matches the actual query results and identify system improvements.
    """

    is_correct: bool = Field(
        ..., description="Whether the reasoning correctly explains the query approach"
    )
    confidence: float = Field(
        ..., ge=0, le=100, description="Confidence in the evaluation (0-100)"
    )
    explanation: str = Field(..., description="Detailed analysis of reasoning quality")
    suggestions: str = Field(
        ...,
        description="Specific, actionable improvements for the system (prompts, schema, examples, patterns)",
    )


# ===== Workflow State Models =====


class SchemaContext(BaseModel):
    """
    Shared state for schema information.
    Stored once and referenced by ID to avoid passing large payloads.
    """

    context_id: str
    database: str
    detailed_schema: str  # Full schema with CREATE TABLE statements
    selected_tables: Optional[List[str]] = None
    schema_mapping: Optional[SchemaMappingResponse] = None
