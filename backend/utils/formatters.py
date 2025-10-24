"""Utility functions for formatting data."""

from typing import Any, Dict, List


def format_results_as_markdown_table(
    rows: List[Dict[str, Any]], max_rows: int = 10
) -> str:
    """
    Format query results as a markdown table.

    Args:
        rows: List of result rows (dicts)
        max_rows: Maximum number of rows to include in table

    Returns:
        Markdown formatted table string
    """
    if not rows:
        return "No results found."

    # Get column names from first row
    columns = list(rows[0].keys())

    # Start building markdown table
    lines = []

    # Header row
    header = "| " + " | ".join(columns) + " |"
    lines.append(header)

    # Separator row
    separator = "| " + " | ".join(["---" for _ in columns]) + " |"
    lines.append(separator)

    # Data rows (limited to max_rows)
    displayed_rows = rows[:max_rows]
    for row in displayed_rows:
        values = []
        for col in columns:
            value = row.get(col)
            # Handle None values
            if value is None:
                values.append("NULL")
            # Convert to string and escape pipe characters
            else:
                str_value = str(value).replace("|", "\\|")
                values.append(str_value)

        row_str = "| " + " | ".join(values) + " |"
        lines.append(row_str)

    # Add note if there are more rows
    if len(rows) > max_rows:
        lines.append(f"\n*Showing {max_rows} of {len(rows)} total rows*")

    return "\n".join(lines)


def format_single_value(rows: List[Dict[str, Any]]) -> str:
    """
    Format a single value result (e.g., COUNT, SUM).

    Args:
        rows: List of result rows

    Returns:
        Formatted string
    """
    if not rows or not rows[0]:
        return "No result"

    first_row = rows[0]
    values = list(first_row.values())

    if len(values) == 1:
        return f"**{values[0]}**"

    # Multiple columns in single row
    parts = [f"**{k}**: {v}" for k, v in first_row.items()]
    return ", ".join(parts)


def should_use_table_format(rows: List[Dict[str, Any]]) -> bool:
    """
    Determine if results should be formatted as a table.

    Returns True if:
    - Multiple rows exist
    - OR single row with multiple columns

    Args:
        rows: List of result rows

    Returns:
        Boolean indicating if table format should be used
    """
    if not rows:
        return False

    # Multiple rows -> use table
    if len(rows) > 1:
        return True

    # Single row with multiple columns -> use table
    if len(rows[0]) > 1:
        return True

    # Single row, single column -> use single value format
    return False
