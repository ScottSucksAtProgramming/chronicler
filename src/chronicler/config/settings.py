"""Application configuration loaded from kwargs, environment variables, or TOML."""

from pathlib import Path

from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    TomlConfigSettingsSource,
)

from chronicler.config.paths import get_config_path


class Settings(BaseSettings):
    """Chronicler configuration.

    Values can be set via environment variables prefixed with CHRONICLER_
    or passed directly to the constructor.
    """

    model_config = SettingsConfigDict(
        env_prefix="CHRONICLER_",
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return (
            init_settings,
            env_settings,
            TomlConfigSettingsSource(settings_cls, toml_file=get_config_path()),
            file_secret_settings,
        )

    # Required
    vault_path: Path
    vault_name: str = ""  # Obsidian vault name for CLI commands

    # LLM provider: "kimi" or "nanogpt"
    llm_provider: str = "kimi"

    # nano-gpt.com settings (only required when llm_provider="nanogpt")
    nanogpt_api_key: str = ""
    nanogpt_base_url: str = "https://nano-gpt.com/api/v1"
    nanogpt_model: str = "chatgpt-4o-latest"

    # Kimi CLI settings (only required when llm_provider="kimi")
    kimi_model: str = ""  # empty = use kimi's default model

    # LM Studio (local embeddings)
    lm_studio_base_url: str = "http://localhost:1234/v1"
    embedding_model: str = "text-embedding-nomic-embed-text-v1.5"

    # Operational
    log_level: str = "INFO"
    llm_timeout_seconds: int = 120
    llm_max_retries: int = 3
