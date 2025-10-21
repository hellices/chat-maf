"""
NL2SQL Agent Response Models.
Unified data models for all workflow steps.
"""

from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class AgentResponse(BaseModel):
    """Base response model for all agents."""

    step: int = Field(..., description="Workflow step number")
    agent_name: str = Field(..., description="Name of the agent")
    model_used: str = Field(..., description="Azure OpenAI model used")
    confidence: float = Field(..., ge=0, le=100, description="Confidence score (0-100)")
    raw_response: str = Field(..., description="Raw agent response")
    success: bool = Field(default=True, description="Whether parsing was successful")
    error_message: Optional[str] = Field(
        default=None, description="Error message if parsing failed"
    )


class EntityExtractionResponse(AgentResponse):
    """Step 1: Entity Extraction response."""

    step: int = Field(default=1)
    agent_name: str = Field(default="EntityExtractor")

    tables: List[str] = Field(
        default_factory=list, description="Identified table names"
    )
    columns: List[str] = Field(
        default_factory=list, description="Identified column names"
    )
    concepts: List[str] = Field(
        default_factory=list, description="Query concepts (JOIN, COUNT, etc.)"
    )

    def to_dict(self) -> Dict:
        """Convert to dictionary for backward compatibility."""
        return {
            "tables": self.tables,
            "columns": self.columns,
            "concepts": self.concepts,
            "confidence": self.confidence,
        }


class SchemaMappingResponse(AgentResponse):
    """Step 2: Schema Mapping response."""

    step: int = Field(default=2)
    agent_name: str = Field(default="SchemaMapper")

    database: Optional[str] = Field(
        default=None, description="Selected database name from M-Schema"
    )
    table_mapping: Dict[str, str] = Field(
        default_factory=dict, description="Natural name -> actual table"
    )
    column_mapping: Dict[str, str] = Field(
        default_factory=dict, description="Natural name -> actual column"
    )
    join_paths: List[Dict[str, str]] = Field(
        default_factory=list, description="Join information"
    )
    filters: List[str] = Field(default_factory=list, description="Filter columns")

    def to_dict(self) -> Dict:
        """Convert to dictionary for backward compatibility."""
        return {
            "database": self.database,
            "table_mapping": self.table_mapping,
            "column_mapping": self.column_mapping,
            "join_paths": self.join_paths,
            "filters": self.filters,
        }


class SQLGenerationResponse(AgentResponse):
    """Step 3: SQL Generation response."""

    step: int = Field(default=3)
    agent_name: str = Field(default="SQLGenerator")

    sql: str = Field(..., description="Generated SQL query")
    reasoning: str = Field(default="", description="Step-by-step reasoning")

    def to_dict(self) -> Dict:
        """Convert to dictionary for backward compatibility."""
        return {
            "sql": self.sql,
            "reasoning": self.reasoning,
            "confidence": self.confidence,
        }


class ErrorCorrectionResponse(AgentResponse):
    """Step 5: Error Correction response."""

    step: int = Field(default=5)
    agent_name: str = Field(default="SQLErrorCorrector")

    corrected_sql: str = Field(..., description="Corrected SQL query")
    original_error: str = Field(..., description="Original error message")
    correction_applied: str = Field(default="", description="What was corrected")

    def to_dict(self) -> Dict:
        """Convert to dictionary for backward compatibility."""
        return {
            "corrected_sql": self.corrected_sql,
            "original_error": self.original_error,
        }


class NaturalLanguageResponse(AgentResponse):
    """Step 6: Natural Language Response generation."""

    step: int = Field(default=6)
    agent_name: str = Field(default="NaturalLanguageGenerator")

    response: str = Field(..., description="Natural language answer")
    summary: str = Field(default="", description="Brief summary of results")

    def to_dict(self) -> Dict:
        """Convert to dictionary for backward compatibility."""
        return {
            "response": self.response,
            "summary": self.summary,
            "confidence": self.confidence,
        }


class DebugInfo(BaseModel):
    """Debug information for workflow step."""

    step: int
    agent_name: str
    model_used: str
    confidence: float
    raw_response: str
    parsed_successfully: bool
    error_message: Optional[str] = None
    timestamp: Optional[str] = None

    def log_summary(self) -> str:
        """Generate log summary."""
        status = "✓" if self.parsed_successfully else "✗"
        return (
            f"[Step {self.step}] {self.agent_name} ({self.model_used})\n"
            f"  Status: {status} | Confidence: {self.confidence:.1f}%\n"
            f"  Response length: {len(self.raw_response)} chars"
        )
