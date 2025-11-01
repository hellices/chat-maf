"""
NL2SQL Workflow Executors.

All executors follow the simple @executor function pattern for consistency.
No classes needed - executors don't maintain state across invocations.

Organized by workflow stage:
- initialization: Workflow setup and context initialization
- schema_selection: Schema understanding (LLM + processing)
- sql_generation: SQL generation (LLM + processing + execution)
- sql_reviewer: SQL quality review with reflection pattern
- handle_success: Success handler (fan-out dispatcher)
- evaluate_reasoning: Reasoning evaluation (parallel)
- generate_nl_response: NL response generation (parallel)
- aggregate_results: Result aggregation (fan-in)
"""

from .aggregate_results import aggregate_success_results
from .evaluate_reasoning import evaluate_sql_reasoning
from .generate_nl_response import generate_natural_language_response
from .handle_success import handle_success
from .initialization import initialize_context
from .schema_selection import schema_understanding
from .sql_generation import sql_generation
from .sql_reviewer import sql_reviewer

__all__ = [
    # Initialization
    "initialize_context",
    # Schema Understanding
    "schema_understanding",
    # SQL Generation (Worker in reflection pattern)
    "sql_generation",
    # SQL Reviewer (Reviewer in reflection pattern)
    "sql_reviewer",
    # Success Handlers (fan-out/fan-in pattern)
    "handle_success",
    "evaluate_sql_reasoning",
    "generate_natural_language_response",
    "aggregate_success_results",
]
