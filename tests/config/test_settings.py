"""Tests for application configuration."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from chronicler.config.paths import set_config_path
from chronicler.config.settings import Settings


@pytest.fixture(autouse=True)
def isolate_config_path(tmp_path):
    """Point config path at a non-existent temp file so tests are isolated from the real config."""
    set_config_path(tmp_path / "config.toml")
    yield
    set_config_path(None)


class TestSettings:
    def test_load_default_settings_from_init_kwargs(self):
        settings = Settings(vault_path=Path("/tmp/test-vault"))

        assert settings.vault_path == Path("/tmp/test-vault")
        assert settings.llm_provider == "kimi"

    def test_load_nanogpt_settings_from_init_kwargs(self):
        settings = Settings(
            vault_path=Path("/tmp/test-vault"),
            llm_provider="nanogpt",
            nanogpt_api_key="test-key-123",
        )

        assert settings.nanogpt_api_key == "test-key-123"
        assert settings.nanogpt_model == "chatgpt-4o-latest"

    def test_settings_load_from_toml_file(self, tmp_path):
        config_path = tmp_path / "config.toml"
        config_path.write_text(
            "\n".join(
                [
                    'vault_path = "/tmp/file-vault"',
                    'vault_name = "Campaign Vault"',
                    'log_level = "WARNING"',
                ]
            ),
            encoding="utf-8",
        )
        set_config_path(config_path)

        settings = Settings()

        assert settings.vault_path == Path("/tmp/file-vault")
        assert settings.vault_name == "Campaign Vault"
        assert settings.log_level == "WARNING"

    def test_env_var_overrides_toml(self, tmp_path, monkeypatch):
        config_path = tmp_path / "config.toml"
        config_path.write_text(
            "\n".join(
                [
                    'vault_path = "/tmp/file-vault"',
                    'log_level = "INFO"',
                ]
            ),
            encoding="utf-8",
        )
        set_config_path(config_path)
        monkeypatch.setenv("CHRONICLER_LOG_LEVEL", "DEBUG")

        settings = Settings()

        assert settings.vault_path == Path("/tmp/file-vault")
        assert settings.log_level == "DEBUG"

    def test_settings_from_env_without_config_file(self, monkeypatch):
        monkeypatch.setenv("CHRONICLER_VAULT_PATH", "/tmp/env-vault")
        monkeypatch.setenv("CHRONICLER_NANOGPT_API_KEY", "env-key-456")
        monkeypatch.setenv("CHRONICLER_NANOGPT_MODEL", "claude-3-opus")

        settings = Settings()

        assert settings.vault_path == Path("/tmp/env-vault")
        assert settings.nanogpt_api_key == "env-key-456"
        assert settings.nanogpt_model == "claude-3-opus"

    def test_settings_validates_vault_path_type(self):
        settings = Settings(
            vault_path="/tmp/string-path",
            nanogpt_api_key="key",
        )

        assert isinstance(settings.vault_path, Path)

    def test_lm_studio_defaults(self):
        settings = Settings(
            vault_path=Path("/tmp/test"),
            nanogpt_api_key="key",
        )

        assert settings.lm_studio_base_url == "http://localhost:1234/v1"
        assert settings.embedding_model == "text-embedding-nomic-embed-text-v1.5"

    def test_missing_required_fields_raises_without_env_or_toml(
        self, monkeypatch, tmp_path
    ):
        set_config_path(tmp_path / "missing.toml")
        monkeypatch.delenv("CHRONICLER_VAULT_PATH", raising=False)
        monkeypatch.delenv("CHRONICLER_NANOGPT_API_KEY", raising=False)

        with pytest.raises(ValidationError) as exc_info:
            Settings()

        assert "vault_path" in str(exc_info.value)
