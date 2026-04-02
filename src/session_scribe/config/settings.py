"""Application configuration loaded from environment variables or explicit values."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Session Scribe configuration.

    Values can be set via environment variables prefixed with SCRIBE_
    or passed directly to the constructor.
    """

    model_config = SettingsConfigDict(
        env_prefix="SCRIBE_",
        env_file=".env",
        env_file_encoding="utf-8",
    )

    # Required
    vault_path: Path
    nanogpt_api_key: str

    # LLM settings
    nanogpt_base_url: str = "https://nano-gpt.com/api/v1"
    nanogpt_model: str = "chatgpt-4o-latest"

    # LM Studio (local embeddings)
    lm_studio_base_url: str = "http://localhost:1234/v1"
    embedding_model: str = "text-embedding-nomic-embed-text-v1.5"

    # Operational
    log_level: str = "INFO"
    llm_timeout_seconds: int = 30
    llm_max_retries: int = 3
