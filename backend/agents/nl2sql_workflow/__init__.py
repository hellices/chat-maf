"""
NL2SQL Workflow Package.

Refactored structure with reflection pattern:
- Global utilities moved to /backend/middleware and /backend/utils
- Business logic kept in nl2sql_workflow package
- Simplified executors (init, schema, sql_generation, sql_reviewer, success)
- Reflection pattern for iterative SQL improvement
"""

from .models import NL2SQLInput, NL2SQLOutput
from .workflow import build_nl2sql_workflow, nl2sql_workflow, run_nl2sql_workflow

__all__ = [
    "nl2sql_workflow",
    "run_nl2sql_workflow",
    "build_nl2sql_workflow",
    "NL2SQLInput",
    "NL2SQLOutput",
]
