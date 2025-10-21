from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "nl2sql backend service"
    debug: bool = True

    # NL2SQL Agent Settings
    nl2sql_entity_extractor_model: str = "gpt-4o"
    nl2sql_schema_mapper_model: str = "gpt-4o"
    nl2sql_sql_generator_model: str = "gpt-4o"
    nl2sql_error_corrector_model: str = "gpt-4o"
    nl2sql_min_confidence_score: float = 70.0

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "allow"  # Allow extra fields from .env


settings = Settings()
