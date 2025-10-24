"""
NL2SQL Workflow - Agent-centric architecture with switch-case routing.

Based on Microsoft Agent Framework patterns:
- shared_states_with_agents.py: Shared state management
- switch_case_edge_group.py: Conditional routing with multiple branches
- Simple @executor functions (no classes) for stateless executors

Key improvements:
- Executors handle both LLM calls and processing (no separate parse steps)
- Consistent @executor function pattern (no unnecessary classes)
- Clear separation of concerns (schema understanding vs SQL generation)
- Retry logic handled via switch-case routing
- Shared state for large payloads (schema, candidates)
"""

from typing import Any, Optional

from agent_framework import Case, Default, WorkflowBuilder

from .executors import (
    aggregate_success_results,
    evaluate_sql_reasoning,
    generate_natural_language_response,
    handle_execution_issue,
    handle_semantic_error,
    handle_success,
    handle_syntax_error,
    initialize_context,
    schema_understanding,
    sql_generation,
)
from .models import (
    NL2SQLInput,
    WorkflowMessage,
)


def get_execution_status_condition(expected_status: str):
    """
    Create a condition predicate for WorkflowMessage.status.
    Used in switch-case routing to filter execution results by status.
    """

    def condition(message: Any) -> bool:
        if not isinstance(message, WorkflowMessage):
            return True
        return message.status == expected_status

    return condition


def build_nl2sql_workflow():
    """
    Build the NL2SQL workflow with switch-case routing and fan-out/fan-in parallelism.

    Workflow structure:
    1. initialize_context (function executor)
    2. schema_understanding (function executor: LLM call + processing)
    3. sql_generation (function executor: LLM call + processing + execution)
    4. SWITCH (WorkflowMessage.status):
        - Success -> handle_success -> FAN-OUT:
            ├─ evaluate_sql_reasoning ────┐
            └─ generate_natural_language_response ─┴─> FAN-IN: aggregate_success_results (terminal)
        - SyntaxError -> handle_syntax_error -> loop to sql_generation
        - SemanticError -> handle_semantic_error -> loop to schema_understanding
        - Default (EmptyResult, Timeout) -> handle_execution_issue (terminal)

    Fan-out/Fan-in pattern:
    - Fan-out: Dispatches WorkflowMessage to multiple executors in parallel
    - Fan-in: Collects results from parallel executors as a list and aggregates them

    All executors use simple @executor function pattern for consistency.
    No classes needed since executors don't maintain state across invocations.

    Message passing:
    - All executors send/receive WorkflowMessage for unified interface
    - Large payloads (schema, m_schema) stored in shared state, referenced by ID
    - Retry context included in message for visibility

    Based on Microsoft Agent Framework patterns:
    - aggregate_results_of_different_types.py: Fan-out/fan-in for parallel execution
    """

    # Build workflow
    # NOTE: Cycle warning is expected and safe here.
    # The workflow contains retry loops:
    #   - handle_syntax_error -> sql_generation (for SQL fixes)
    #   - handle_semantic_error -> schema_understanding (for schema re-analysis)
    # These loops are terminated by:
    #   1. Max retry limits enforced in executors (syntax: 2, semantic: 2)
    #   2. yield_output() calls in executors when limits are reached
    # See: handle_syntax_error and handle_semantic_error for termination logic
    workflow = (
        WorkflowBuilder()
        .set_start_executor(initialize_context)
        .add_edge(initialize_context, schema_understanding)
        .add_edge(schema_understanding, sql_generation)
        # Switch-case routing based on execution result
        .add_switch_case_edge_group(
            sql_generation,
            [
                Case(
                    condition=get_execution_status_condition("Success"),
                    target=handle_success,
                ),
                Case(
                    condition=get_execution_status_condition("SyntaxError"),
                    target=handle_syntax_error,
                ),
                Case(
                    condition=get_execution_status_condition("SemanticError"),
                    target=handle_semantic_error,
                ),
                Default(target=handle_execution_issue),
            ],
        )
        # Fan-out: Parallel execution for success case
        # Both executors run in parallel from handle_success
        .add_fan_out_edges(
            handle_success,
            [evaluate_sql_reasoning, generate_natural_language_response],
        )
        # Fan-in: Aggregate parallel results into single executor
        .add_fan_in_edges(
            [evaluate_sql_reasoning, generate_natural_language_response],
            aggregate_success_results,
        )
        # Retry loops (terminated by max retry limits in executors)
        .add_edge(handle_syntax_error, sql_generation)  # Max 2 syntax retries
        .add_edge(handle_semantic_error, schema_understanding)  # Max 2 semantic retries
        .build()
    )

    return workflow


async def run_nl2sql_workflow(
    question: str,
    selected_database: Optional[str] = None,
    selected_tables: Optional[list[str]] = None,
    return_natural_language: bool = False,
):
    """
    Run the NL2SQL workflow.

    Args:
        question: Natural language question
        selected_database: Pre-selected database (optional)
        selected_tables: Pre-selected tables (optional)
        return_natural_language: Whether to return natural language response

    Returns:
        NL2SQLOutput with SQL and execution results
    """
    workflow = build_nl2sql_workflow()

    input_data = NL2SQLInput(
        question=question,
        selected_database=selected_database,
        selected_tables=selected_tables,
        return_natural_language=return_natural_language,
    )

    events = await workflow.run(input_data)
    outputs = events.get_outputs()

    if not outputs:
        raise RuntimeError("Workflow did not produce any output")

    return outputs[0]


async def nl2sql_workflow(
    message: str,
    return_natural_language: bool = False,
    selected_database: Optional[str] = None,
    selected_tables: Optional[list[str]] = None,
):
    """
    API-compatible wrapper for the NL2SQL workflow.
    Yields workflow events for streaming to the client.

    This function is compatible with the /nl2sql endpoint in main.py.

    Args:
        message: Natural language question
        return_natural_language: Whether to return natural language response
        selected_database: Pre-selected database (optional)
        selected_tables: Pre-selected tables (optional)

    Yields:
        Workflow events (compatible with agent framework events)
    """
    workflow = build_nl2sql_workflow()

    input_data = NL2SQLInput(
        question=message,
        selected_database=selected_database,
        selected_tables=selected_tables,
        return_natural_language=return_natural_language,
    )

    # Run workflow and stream events
    async for event in workflow.run_stream(input_data):
        yield event
