"""Tests for application configuration."""

import os
import pytest
from pathlib import Path


class TestSettings:
    def test_load_default_settings(self):
        from session_scribe.config.settings import Settings

        settings = Settings(
            vault_path=Path("/tmp/test-vault"),
            nanogpt_api_key="test-key-123",
            _env_file=None,
        )
        assert settings.vault_path == Path("/tmp/test-vault")
        assert settings.nanogpt_api_key == "test-key-123"
        assert settings.nanogpt_model is not None

    def test_settings_from_env(self, monkeypatch):
        from session_scribe.config.settings import Settings

        monkeypatch.setenv("SCRIBE_VAULT_PATH", "/tmp/env-vault")
        monkeypatch.setenv("SCRIBE_NANOGPT_API_KEY", "env-key-456")
        monkeypatch.setenv("SCRIBE_NANOGPT_MODEL", "claude-3-opus")

        settings = Settings(_env_file=None)
        assert settings.vault_path == Path("/tmp/env-vault")
        assert settings.nanogpt_api_key == "env-key-456"
        assert settings.nanogpt_model == "claude-3-opus"

    def test_settings_validates_vault_path_type(self):
        from session_scribe.config.settings import Settings

        settings = Settings(
            vault_path="/tmp/string-path",
            nanogpt_api_key="key",
            _env_file=None,
        )
        assert isinstance(settings.vault_path, Path)

    def test_lm_studio_defaults(self):
        from session_scribe.config.settings import Settings

        settings = Settings(
            vault_path=Path("/tmp/test"),
            nanogpt_api_key="key",
            _env_file=None,
        )
        assert settings.lm_studio_base_url == "http://localhost:1234/v1"
        assert settings.embedding_model == "text-embedding-nomic-embed-text-v1.5"

    def test_missing_required_fields_raises(self, monkeypatch):
        from session_scribe.config.settings import Settings

        monkeypatch.delenv("SCRIBE_VAULT_PATH", raising=False)
        monkeypatch.delenv("SCRIBE_NANOGPT_API_KEY", raising=False)

        with pytest.raises(Exception):
            Settings(_env_file=None)
