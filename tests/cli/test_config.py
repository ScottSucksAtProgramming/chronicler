"""Tests for the config CLI commands."""

from pathlib import Path

import pytest
from typer.testing import CliRunner

from chronicler.cli.main import app
from chronicler.config.paths import set_config_path

runner = CliRunner()


@pytest.fixture(autouse=True)
def reset_config_path():
    set_config_path(None)
    yield
    set_config_path(None)


def _write_config(config_path: Path, lines: list[str]) -> None:
    config_path.write_text("\n".join(lines), encoding="utf-8")


class TestConfigCommand:
    def test_bare_config_invokes_show(self, tmp_path):
        vault_path = tmp_path / "vault"
        vault_path.mkdir()
        config_path = tmp_path / "config.toml"
        _write_config(
            config_path,
            [
                f'vault_path = "{vault_path}"',
                'vault_name = "Campaign Vault"',
            ],
        )
        set_config_path(config_path)

        bare_result = runner.invoke(app, ["config"])
        show_result = runner.invoke(app, ["config", "show"])

        assert bare_result.exit_code == 0
        assert show_result.exit_code == 0
        assert bare_result.output == show_result.output

    def test_config_show_marks_env_overrides(self, tmp_path, monkeypatch):
        vault_path = tmp_path / "vault"
        vault_path.mkdir()
        config_path = tmp_path / "config.toml"
        _write_config(
            config_path,
            [
                f'vault_path = "{vault_path}"',
                'log_level = "INFO"',
            ],
        )
        set_config_path(config_path)
        monkeypatch.setenv("CHRONICLER_LOG_LEVEL", "DEBUG")

        result = runner.invoke(app, ["config", "show"])

        assert result.exit_code == 0
        assert "Log level:        DEBUG (from env)" in result.output

    def test_config_show_marks_defaults_and_masks_api_key(self, tmp_path):
        vault_path = tmp_path / "vault"
        vault_path.mkdir()
        config_path = tmp_path / "config.toml"
        _write_config(
            config_path,
            [
                f'vault_path = "{vault_path}"',
                'llm_provider = "nanogpt"',
                'nanogpt_api_key = "super-secret-1234"',
            ],
        )
        set_config_path(config_path)

        result = runner.invoke(app, ["config", "show"])

        assert result.exit_code == 0
        assert "API key:          ***1234" in result.output
        assert "super-secret-1234" not in result.output
        assert "Log level:        INFO (default)" in result.output
        assert "Vault path exists." in result.output

    def test_config_show_missing_settings_points_to_config_init(
        self, tmp_path, monkeypatch
    ):
        set_config_path(tmp_path / "config.toml")
        monkeypatch.delenv("CHRONICLER_VAULT_PATH", raising=False)

        result = runner.invoke(app, ["config", "show"])

        assert result.exit_code == 1
        assert "chronicler config init" in result.output
