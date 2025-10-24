"""
SQL Security Utilities
Provides basic SQL sanitization and validation.
"""

import re
from typing import List


# Dangerous SQL keywords that should not be allowed
DANGEROUS_KEYWORDS = [
    "DROP",
    "DELETE",
    "TRUNCATE",
    "ALTER",
    "CREATE",
    "INSERT",
    "UPDATE",
    "EXEC",
    "EXECUTE",
    "GRANT",
    "REVOKE",
]


def sanitize_sql(sql: str) -> str:
    """
    Basic SQL sanitization to prevent dangerous operations.

    Args:
        sql: SQL query string

    Returns:
        Sanitized SQL string

    Raises:
        ValueError: If dangerous SQL keywords are detected
    """
    sql_upper = sql.upper()

    # Check for dangerous keywords
    for keyword in DANGEROUS_KEYWORDS:
        # Use word boundary to avoid false positives
        pattern = r"\b" + keyword + r"\b"
        if re.search(pattern, sql_upper):
            raise ValueError(
                f"Dangerous SQL operation detected: {keyword}. "
                f"Only SELECT queries are allowed."
            )

    # Ensure it's a SELECT query
    sql_stripped = sql.strip()
    if not sql_stripped.upper().startswith("SELECT"):
        raise ValueError("Only SELECT queries are allowed")

    return sql


def validate_table_name(table_name: str, allowed_tables: List[str]) -> bool:
    """
    Validate that a table name is in the allowed list.

    Args:
        table_name: Name of the table to validate
        allowed_tables: List of allowed table names

    Returns:
        True if valid, False otherwise
    """
    return table_name in allowed_tables


def is_read_only_query(sql: str) -> bool:
    """
    Check if SQL query is read-only (SELECT only).

    Args:
        sql: SQL query string

    Returns:
        True if query is read-only, False otherwise
    """
    sql_upper = sql.strip().upper()

    # Check if it starts with SELECT
    if not sql_upper.startswith("SELECT"):
        return False

    # Check for any write operations
    write_operations = [
        "INSERT",
        "UPDATE",
        "DELETE",
        "DROP",
        "CREATE",
        "ALTER",
        "TRUNCATE",
    ]

    for operation in write_operations:
        pattern = r"\b" + operation + r"\b"
        if re.search(pattern, sql_upper):
            return False

    return True
