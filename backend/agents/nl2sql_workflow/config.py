"""Configuration and constants for NL2SQL workflow."""

# ============================================================================
# Shared State Keys
# ============================================================================

# Schema-related state
SCHEMA_STATE_PREFIX = "schema:"
CURRENT_SCHEMA_ID_KEY = "current_schema_id"
M_SCHEMA_CACHE_KEY = "m_schema_cache"

# Context state
RETRY_CONTEXT_KEY = "retry_context"
CURRENT_QUESTION_KEY = "current_question"
CURRENT_SQL_RESPONSE_KEY = "current_sql_response"  # Store SQLGenerationResponse

# Flags
RETURN_NL_KEY = "return_natural_language"


# ============================================================================
# Retry Configuration
# ============================================================================

MAX_SYNTAX_RETRIES = 2  # Max attempts to fix SQL syntax errors
MAX_SEMANTIC_RETRIES = 2  # Max attempts to fix schema selection errors


# ============================================================================
# SQL Execution Configuration
# ============================================================================

SQL_EXECUTION_TIMEOUT = 30.0  # seconds
MAX_ROWS_RETURNED = 1000  # Limit query result size
