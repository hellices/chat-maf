from typing import Optional

from agent_framework import WorkflowBuilder

from .executors import (
    aggregate_success_results,
    evaluate_sql_reasoning,
    generate_natural_language_response,
    handle_success,
    initialize_context,
    schema_understanding,
    sql_generation,
    sql_reviewer,
)
from .models import (
    NL2SQLInput,
)


def build_nl2sql_workflow():
    """
    Build the NL2SQL workflow with reflection pattern for iterative improvement.

    Workflow structure (Reflection Pattern - from workflow_as_agent_reflection_pattern.py):
    1. initialize_context (function executor)
    2. schema_understanding (function executor: LLM call + processing)
    3. sql_generation (Worker) ↔ sql_reviewer (Reviewer)
       - sql_generation generates SQL and sends to reviewer
       - sql_reviewer evaluates SQL quality
       - If approved → handle_success (terminal)
       - If not approved → sends feedback back to sql_generation for retry
    4. handle_success → FAN-OUT:
        ├─ evaluate_sql_reasoning ────┐
        └─ generate_natural_language_response ─┴─> FAN-IN: aggregate_success_results (terminal)

    Reflection Pattern Benefits:
    - Cleaner retry logic: Worker-Reviewer bidirectional cycle
    - Self-correcting: SQL is iteratively improved based on feedback
    - Max retries enforced by Reviewer (no separate error handlers needed)
    - Approved results automatically proceed to success path

    Based on Microsoft Agent Framework patterns:
    - workflow_as_agent_reflection_pattern.py: Worker ↔ Reviewer cycle
    - aggregate_results_of_different_types.py: Fan-out/fan-in for parallel execution
    """

    # Build workflow with reflection pattern
    workflow = (
        WorkflowBuilder()
        .set_start_executor(initialize_context)
        .add_edge(initialize_context, schema_understanding)
        .add_edge(schema_understanding, sql_generation)
        # Reflection cycle: SQL Generation (Worker) ↔ SQL Reviewer
        .add_edge(sql_generation, sql_reviewer)  # Worker → Reviewer
        .add_edge(sql_reviewer, sql_generation)  # Reviewer → Worker (feedback)
        # Success path: Reviewer approves → handle_success
        .add_edge(sql_reviewer, handle_success)
        # Fan-out: Parallel execution for success case
        .add_fan_out_edges(
            handle_success,
            [evaluate_sql_reasoning, generate_natural_language_response],
        )
        # Fan-in: Aggregate parallel results into single executor
        .add_fan_in_edges(
            [evaluate_sql_reasoning, generate_natural_language_response],
            aggregate_success_results,
        )
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
