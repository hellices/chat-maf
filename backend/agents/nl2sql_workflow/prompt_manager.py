"""Prompt management for NL2SQL workflow."""

from pathlib import Path

import yaml


class PromptManager:
    """Manages prompt templates from YAML file."""

    def __init__(self):
        prompts_path = Path(__file__).parent / "prompts.yaml"
        with open(prompts_path, "r", encoding="utf-8") as f:
            self.prompts = yaml.safe_load(f)

    def get_schema_understanding_prompt(
        self,
        question: str,
        m_schema_json: str,
        selected_database: str | None = None,
        selected_tables: list[str] | None = None,
    ) -> str:
        """Generate prompt for schema understanding agent."""
        template = self.prompts["schema_understanding"]

        # Build hints
        hint_database = ""
        if selected_database:
            hint_database = template["hint_database_template"].format(
                database=selected_database
            )

        hint_tables = ""
        if selected_tables:
            hint_tables = template["hint_tables_template"].format(
                tables=selected_tables
            )

        return template["user_template"].format(
            question=question,
            m_schema_json=m_schema_json,
            hint_database=hint_database,
            hint_tables=hint_tables,
        )

    def get_sql_generation_prompt(
        self,
        question: str,
        detailed_schema: str,
        selected_tables: list[str] | None = None,
    ) -> str:
        """Generate prompt for SQL generation agent."""
        template = self.prompts["sql_generation"]
        return template["user_template"].format(
            question=question,
            detailed_schema=detailed_schema,
            selected_tables=selected_tables,
        )

    def get_syntax_error_correction_prompt(
        self,
        question: str,
        detailed_schema: str,
        failed_sql: str,
        error_message: str,
    ) -> str:
        """Generate prompt for syntax error correction."""
        template = self.prompts["syntax_error_correction"]
        return template["user_template"].format(
            question=question,
            detailed_schema=detailed_schema,
            failed_sql=failed_sql,
            error_message=error_message,
        )

    def get_semantic_error_correction_prompt(
        self,
        question: str,
        database: str,
        m_schema_json: str,
        failed_sql: str,
        error_message: str,
    ) -> str:
        """Generate prompt for semantic error correction."""
        template = self.prompts["semantic_error_correction"]
        return template["user_template"].format(
            question=question,
            database=database,
            m_schema_json=m_schema_json,
            failed_sql=failed_sql,
            error_message=error_message,
        )

    def get_natural_language_response_prompt(
        self,
        question: str,
        sql: str,
        formatted_results: str,
        format_instruction_type: str = "table",  # "table", "single", or "none"
    ) -> str:
        """Generate prompt for natural language response.

        Args:
            question: The original user question
            sql: The SQL query that was executed
            formatted_results: Pre-formatted results (markdown table or other format)
            format_instruction_type: Type of format instruction to use
        """
        template = self.prompts["natural_language_response"]

        # Get appropriate format instruction
        format_instruction_key = f"format_instruction_{format_instruction_type}"
        format_instruction = template.get(
            format_instruction_key, template.get("format_instruction_table", "")
        )

        return template["user_template"].format(
            question=question,
            sql=sql,
            formatted_results=formatted_results,
            format_instruction=format_instruction,
        )

    def get_system_prompt(self, agent_type: str) -> str:
        """Get system prompt for an agent."""
        return self.prompts[agent_type].get("system", "")

    def get_reasoning_evaluation_prompt(
        self,
        question: str,
        sql: str,
        reasoning: str,
        confidence: float,
        formatted_results: str,
        row_count: int,
        execution_time_ms: float,
        m_schema_subset: str = "",
        schema_system_prompt: str = "",
        sql_generation_system_prompt: str = "",
    ) -> str:
        """Generate prompt for reasoning evaluation.

        Args:
            question: The original user question
            sql: The generated SQL query
            reasoning: The agent's reasoning about the query
            confidence: The agent's confidence score
            formatted_results: Pre-formatted query results
            row_count: Number of rows returned
            execution_time_ms: Query execution time in milliseconds
            m_schema_subset: Relevant portion of m_schema that was used
            schema_system_prompt: System prompt used for schema understanding
            sql_generation_system_prompt: System prompt used for SQL generation
        """
        template = self.prompts["reasoning_evaluation"]
        return template["user_template"].format(
            question=question,
            sql=sql,
            reasoning=reasoning,
            confidence=confidence,
            formatted_results=formatted_results,
            row_count=row_count,
            execution_time_ms=execution_time_ms,
            m_schema_subset=m_schema_subset,
            schema_system_prompt=schema_system_prompt,
            sql_generation_system_prompt=sql_generation_system_prompt,
        )


# Global instance
prompt_manager = PromptManager()
