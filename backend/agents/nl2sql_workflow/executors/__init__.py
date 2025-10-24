"""
NL2SQL Workflow Executors.

All executors follow the simple @executor function pattern for consistency.
No classes needed - executors don't maintain state across invocations.

Organized by workflow stage:
- initialization: Workflow setup and context initialization
- schema_selection: Schema understanding (LLM + processing)
- sql_generation: SQL generation (LLM + processing + execution)
- success: Success handling with fan-out/fan-in pattern
- errors: Error handling with retry logic
"""

from .errors import (
    handle_execution_issue,
    handle_semantic_error,
    handle_syntax_error,
)
from .initialization import initialize_context
from .schema_selection import schema_understanding
from .sql_generation import sql_generation
from .success import (
    aggregate_success_results,
    evaluate_sql_reasoning,
    generate_natural_language_response,
    handle_success,
)

__all__ = [
    # Initialization
    "initialize_context",
    # Schema Understanding (unified executor)
    "schema_understanding",
    # SQL Generation (unified executor)
    "sql_generation",
    # Success Handlers (with fan-out/fan-in)
    "handle_success",
    "evaluate_sql_reasoning",
    "generate_natural_language_response",
    "aggregate_success_results",
    # Error Handlers
    "handle_syntax_error",
    "handle_semantic_error",
    "handle_execution_issue",
]
