"""
SuperML DataTruth - Configuration Module

Loads environment variables and application settings.
"""

from pathlib import Path
from typing import List, Union, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env", 
        env_file_encoding="utf-8", 
        case_sensitive=False,
        extra="ignore"  # Ignore extra fields from .env file
    )

    # Internal Database Configuration (DataTruth metadata)
    internal_db_host: str = "localhost"
    internal_db_port: int = 5432
    internal_db_name: str = "datatruth_internal"
    internal_db_user: str = "postgres"
    internal_db_password: str = "postgres"
    
    # Internal DB Admin (for migrations only)
    internal_db_admin_user: str = "postgres"
    internal_db_admin_password: str = "postgres"
    
    # External Demo Database Configuration (optional)
    external_demo_db_host: str = "localhost"
    external_demo_db_port: int = 5432
    external_demo_db_name: str = "datatruth_external"
    external_demo_db_user: str = "postgres"
    external_demo_db_password: str = "postgres"
    
    # Legacy Database Configuration (backward compatibility)
    # These point to external demo database by default
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "datatruth_internal"
    postgres_user: str = "postgres"
    postgres_password: str = "postgres"

    # Admin Database (for migrations only)
    postgres_admin_user: str = "postgres"
    postgres_admin_password: str = "postgres"

    # OpenAI Configuration - Optional until setup wizard completes
    openai_api_key: str = ""  # Will be set by setup wizard
    openai_model: str = "gpt-4o-mini"  # Changed from gpt-4 to support JSON mode
    openai_temperature: float = 0.1
    openai_max_tokens: int = 2000

    # Azure OpenAI (optional)
    azure_openai_api_key: str | None = None
    azure_openai_endpoint: str | None = None
    azure_openai_deployment: str | None = None
    azure_openai_api_version: str | None = None

    # Application Configuration
    app_env: str = "development"
    app_debug: bool = True
    app_log_level: str = "INFO"

    # API Configuration
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_cors_origins: Union[str, List[str]] = ["http://localhost:3000", "http://localhost:8000"]

    # Query Execution Limits
    query_timeout_seconds: int = 30
    query_max_rows: int = 10000
    query_max_retries: int = 3

    # Semantic Layer Configuration
    semantic_layer_path: str = "./config/semantic-layer"

    # Audit Configuration
    enable_audit_log: bool = True
    audit_log_path: str = "./logs/audit.log"

    # Redis Configuration (Phase 2)
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: str = ""

    # Cache Configuration (Phase 2)
    cache_enabled: bool = False
    cache_ttl_seconds: int = 3600

    # Vector DB Configuration (Phase 3 & 4)
    vector_db_enabled: bool = True
    vector_db_persist_path: str = "./data/chroma"

    @property
    def database_url(self) -> str:
        """Get PostgreSQL connection string."""
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def admin_database_url(self) -> str:
        """Get admin PostgreSQL connection string."""
        return (
            f"postgresql://{self.postgres_admin_user}:{self.postgres_admin_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def semantic_layer_dir(self) -> Path:
        """Get semantic layer directory as Path object."""
        return Path(self.semantic_layer_path)

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.app_env.lower() == "production"

    @property
    def use_azure_openai(self) -> bool:
        """Check if Azure OpenAI should be used."""
        return bool(self.azure_openai_api_key and self.azure_openai_endpoint)

    @property
    def llm_provider(self) -> str:
        """Get LLM provider (openai or azure)."""
        return "azure" if self.use_azure_openai else "openai"

    @property
    def llm_model(self) -> str:
        """Get LLM model name."""
        if self.use_azure_openai:
            return self.azure_openai_deployment or self.openai_model
        return self.openai_model

    @property
    def llm_temperature(self) -> float:
        """Get LLM temperature setting."""
        return self.openai_temperature

    @property
    def llm_max_tokens(self) -> int:
        """Get LLM max tokens setting."""
        return self.openai_max_tokens


# Global settings instance - will be initialized by application startup
settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get the global settings instance."""
    global settings
    if settings is None:
        settings = Settings()
    return settings


def _create_settings() -> Settings:
    """Create a new settings instance. Used for testing or reinitialization."""
    return Settings()
