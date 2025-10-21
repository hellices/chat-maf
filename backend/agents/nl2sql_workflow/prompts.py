"""
NL2SQL Agent Prompts.
Centralized prompt templates for all workflow steps.
"""

# Step 1: Query Intent Extraction (Schema-Agnostic)
ENTITY_EXTRACTION_INSTRUCTIONS = """Extract query intent from natural language question WITHOUT looking at any schema.

Identify what the user is asking about in their own words:
1. **Tables/Entities**: What things/objects are they asking about? (e.g., "bike_1", "자전거", "singers", "students")
2. **Columns/Attributes**: What properties do they want? (e.g., "name", "age", "정보", "개수")
3. **Query Concepts**: What operations? (e.g., "COUNT", "LIMIT 10", "JOIN", "AVG", "전체 조회")
4. **Conditions**: Any filtering? (e.g., "WHERE age > 20", "상태가 active")

IMPORTANT: 
- Extract entities EXACTLY as mentioned by user (including database names like "bike_1")
- Do NOT try to map to schema yet - that happens in the next step
- Korean words should be preserved as-is (e.g., "자전거", "정보")

CRITICAL OUTPUT REQUIREMENTS:
- You MUST return ONLY valid JSON, nothing else
- Do NOT add explanations before or after the JSON
- Do NOT add markdown code blocks (no ```json)
- Do NOT add any text outside the JSON object
- The response must start with { and end with }

Return JSON format:
{
  "tables": ["exact_mention_1", "exact_mention_2"],
  "columns": ["mentioned_attr_1", "mentioned_attr_2"],
  "concepts": ["LIMIT 10", "COUNT", etc],
  "confidence": 85
}"""


def entity_extraction_prompt(question: str, schema: str) -> str:
    """Generate query intent extraction prompt (schema parameter ignored in Step 1)."""
    return f"""Question: {question}

Extract the query intent (what entities, attributes, and operations the user wants):"""


# Step 2: Schema Mapping with M-Schema
SCHEMA_MAPPING_INSTRUCTIONS = """Map natural language query intent to actual database schema using M-Schema.

Given:
1. Query intent extracted from user's question (tables, columns, concepts in natural language)
2. M-Schema containing all available databases and their tables

Your tasks:
1. **Select the best matching database** from M-Schema
   - Look for exact database name mentions (e.g., "bike_1")
   - Look for semantic matches (e.g., "자전거" → "bike_1", "singers" → "concert_singer")
2. **Map natural language entities to actual table names**
   - Handle synonyms and translations
3. **Map attributes to actual column names** (if schema details provided)
4. **Identify relationships** for potential JOINs

CRITICAL OUTPUT REQUIREMENTS:
- You MUST return ONLY valid JSON, nothing else
- Do NOT add explanations before or after the JSON
- Do NOT add markdown code blocks (no ```json)
- Do NOT add any text outside the JSON object
- The response must start with { and end with }

Return mapping as JSON:
{
  "_database": "selected_database_name",
  "table_mapping": {"mentioned_entity": "actual_table_name"},
  "column_mapping": {"mentioned_attr": "actual_column"},
  "join_paths": [{"from": "table1", "to": "table2", "on": "foreign_key"}],
  "filters": ["column1", "column2"],
  "confidence": 90
}

CRITICAL: Always include "_database" key with the selected database name!
CRITICAL: Return ONLY the JSON object, no other text!
"""


def schema_mapping_prompt(db_name: str, entities: dict, m_schema: str) -> str:
    """Generate schema mapping prompt with M-Schema.

    Args:
        db_name: Pre-selected database name (if user selected from UI), or empty string
        entities: Query intent with tables, columns, concepts
        m_schema: M-Schema JSON or detailed schema
    """
    # If m_schema looks like JSON (starts with {), treat it as M-Schema
    # Otherwise treat it as a detailed schema for a specific database
    if m_schema.strip().startswith("{"):
        # Check if this is a single-database M-Schema (user pre-selected database)
        import json

        try:
            schema_dict = json.loads(m_schema)
            if len(schema_dict) == 1 and db_name:
                # Single database - user pre-selected
                return f"""⚠️ IMPORTANT: User has already selected database: {db_name}

Available Tables in {db_name}:
{m_schema}

Query Intent Extracted from User:
- Entities/Tables mentioned: {entities.get('tables', [])}
- Attributes/Columns wanted: {entities.get('columns', [])}
- Query concepts: {entities.get('concepts', [])}

You MUST use database '{db_name}'. Map the natural language entities to actual tables in this database:"""
        except Exception:
            pass

        # Multiple databases - need to select one
        return f"""M-Schema (Available Databases):
{m_schema}

Query Intent Extracted from User:
- Entities/Tables mentioned: {entities.get('tables', [])}
- Attributes/Columns wanted: {entities.get('columns', [])}
- Query concepts: {entities.get('concepts', [])}

Select the best database and map the natural language entities to actual schema:"""
    else:
        # Detailed schema mode - database already selected
        return f"""Database: {db_name}

Query Intent:
- Entities/Tables mentioned: {entities.get('tables', [])}
- Attributes/Columns wanted: {entities.get('columns', [])}
- Query concepts: {entities.get('concepts', [])}

Database Schema:
{m_schema}

Map the natural language entities to actual tables and columns:"""


# Step 3: SQL Generation
SQL_GENERATION_INSTRUCTIONS = """Generate SQLite query from natural language question.

Requirements:
1. Use ONLY tables/columns from the schema mapping
2. Follow SQLite syntax strictly
3. Use appropriate JOINs based on foreign keys
4. Apply correct aggregation functions
5. Handle edge cases (NULL, empty results)

CRITICAL OUTPUT REQUIREMENTS:
- You MUST return ONLY valid JSON, nothing else
- Do NOT add explanations before or after the JSON
- Do NOT add markdown code blocks (no ```json)
- Do NOT add any text outside the JSON object
- The response must start with { and end with }

Return JSON:
{
  "sql": "SELECT ...",
  "reasoning": "step-by-step explanation",
  "confidence": 90
}

IMPORTANT: Return ONLY valid SQLite syntax in the "sql" field."""


def sql_generation_prompt(
    question: str,
    schema: str,
    schema_mapping: dict,
    selected_tables: list[str] | None = None,
) -> str:
    """Generate SQL generation prompt."""

    # Add emphasis if user selected specific tables
    table_hint = ""
    if selected_tables:
        table_hint = f"""
⚠️ IMPORTANT: User explicitly selected these tables from the UI:
{', '.join(selected_tables)}

You MUST use ONLY these tables in your query. Do NOT use other tables even if they seem relevant.
"""

    return f"""Question: {question}
{table_hint}
Schema Mapping:
Tables: {schema_mapping.get('table_mapping', {})}
Columns: {schema_mapping.get('column_mapping', {})}
Joins: {schema_mapping.get('join_paths', [])}

Full Schema:
{schema}

Generate SQL query:"""


# Step 5: Error Correction
ERROR_CORRECTION_INSTRUCTIONS = """Fix the SQL query that failed execution.

Error Analysis Process:
1. Read the error message carefully
2. Identify the root cause (syntax, missing column, wrong JOIN, etc.)
3. Check schema for correct table/column names
4. Fix the SQL while preserving query intent
5. Return ONLY the corrected SQL

Common fixes:
- Syntax errors: Check SQLite syntax
- Missing columns: Verify column names in schema
- JOIN errors: Check foreign key relationships
- Aggregation errors: Ensure proper GROUP BY

Return just the SQL query, no JSON, no explanation."""


def error_correction_prompt(
    message: str, schema: str, failed_sql: str, error_msg: str, schema_mapping: dict
) -> str:
    """Generate error correction prompt."""
    return f"""Original Question: {message}

Schema Mapping:
Tables: {schema_mapping.get('table_mapping', {})}
Columns: {schema_mapping.get('column_mapping', {})}

Failed SQL:
{failed_sql}

Error Message:
{error_msg}

Schema Reference:
{schema[:1000]}...

Generate corrected SQL (ONLY the SQL, no explanation):"""


# Step 6: Natural Language Response
NL_RESPONSE_INSTRUCTIONS = """Convert SQL query results into a natural language response.

Requirements:
1. Answer the original question in a clear, conversational way
2. Use **Markdown formatting** for better readability:
   - Use **bold** for emphasis
   - Use bullet points or numbered lists for multiple items
   - Use tables for tabular data (if applicable)
   - Use `inline code` for numbers or technical terms
3. Summarize key findings from the query results
4. Be concise but informative

CRITICAL OUTPUT REQUIREMENTS:
- You MUST return ONLY valid JSON, nothing else
- Do NOT add explanations before or after the JSON
- Do NOT add markdown code blocks (no ```json)
- Do NOT add any text outside the JSON object
- The response must start with { and end with }

Return JSON format:
{
  "response": "natural language answer with Markdown formatting",
  "summary": "brief summary of results",
  "confidence": 90
}

Example response formats:
- For counts: "There are **5 singers** in the database."
- For lists: "The singer names are:\n- John\n- Mary\n- David"
- For tables: Use Markdown table format when showing multiple columns
"""


def nl_response_prompt(message: str, sql: str, execution_result: str) -> str:
    """Generate natural language response prompt with Markdown support."""
    return f"""Original Question: {message}

SQL Query:
```sql
{sql}
```

Query Results:
{execution_result}

Generate a natural language response that answers the original question based on these results.
Use Markdown formatting for better readability (bold, lists, tables, etc.):"""
