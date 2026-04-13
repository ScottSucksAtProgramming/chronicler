"""Tests for the config init wizard."""

import tomllib
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from chronicler.cli.main import app
from chronicler.config.paths import set_config_path
from chronicler.config.settings import Settings

runner = CliRunner()


@pytest.fixture(autouse=True)
def reset_config_path():
    set_config_path(None)
    yield
    set_config_path(None)


def _wizard_input(*lines: str) -> str:
    return "\n".join(lines) + "\n"


class TestConfigInitCommand:
    def test_config_init_happy_path_writes_valid_toml(self, tmp_path):
        vault_path = tmp_path / "campaign-vault"
        vault_path.mkdir()
        config_path = tmp_path / "nested" / "config.toml"
        set_config_path(config_path)

        result = runner.invoke(
            app,
            ["config", "init"],
            input=_wizard_input(
                str(vault_path),
                "",
                "nanogpt",
                "super-secret-1234",
                "",
                "",
                "",
                "",
                "y",
            ),
        )

        assert result.exit_code == 0
        assert config_path.exists()
        assert str(config_path) in result.output

        with config_path.open("rb") as config_file:
            data = tomllib.load(config_file)

        assert data["vault_path"] == str(vault_path)
        assert data["vault_name"] == vault_path.name
        assert data["llm_provider"] == "nanogpt"
        assert data["nanogpt_api_key"] == "super-secret-1234"
        assert "lm_studio_base_url" not in data
        assert Settings().vault_path == vault_path

    def test_config_init_reprompts_for_invalid_vault_path(self, tmp_path):
        vault_path = tmp_path / "campaign-vault"
        vault_path.mkdir()
        config_path = tmp_path / "config.toml"
        set_config_path(config_path)

        result = runner.invoke(
            app,
            ["config", "init"],
            input=_wizard_input(
                str(tmp_path / "missing"),
                str(vault_path),
                "",
                "kimi",
                "",
                "",
                "",
                "y",
            ),
        )

        assert result.exit_code == 0
        assert "does not exist" in result.output
        assert config_path.exists()

    def test_config_init_warns_before_overwriting_existing_file(self, tmp_path):
        vault_path = tmp_path / "campaign-vault"
        vault_path.mkdir()
        config_path = tmp_path / "config.toml"
        config_path.write_text('vault_path = "/tmp/original"\n', encoding="utf-8")
        set_config_path(config_path)

        result = runner.invoke(app, ["config", "init"], input="n\n")

        assert result.exit_code == 0
        assert (
            config_path.read_text(encoding="utf-8") == 'vault_path = "/tmp/original"\n'
        )
        assert "already exists" in result.output

    def test_config_init_aborts_at_summary_without_writing(self, tmp_path):
        vault_path = tmp_path / "campaign-vault"
        vault_path.mkdir()
        config_path = tmp_path / "config.toml"
        set_config_path(config_path)

        result = runner.invoke(
            app,
            ["config", "init"],
            input=_wizard_input(
                str(vault_path),
                "",
                "kimi",
                "",
                "",
                "",
                "n",
            ),
        )

        assert result.exit_code == 0
        assert not config_path.exists()
        assert "Aborted" in result.output

    def test_config_init_warns_when_kimi_is_not_on_path(self, tmp_path):
        vault_path = tmp_path / "campaign-vault"
        vault_path.mkdir()
        config_path = tmp_path / "config.toml"
        set_config_path(config_path)

        with patch("chronicler.cli.main.shutil.which", return_value=None):
            result = runner.invoke(
                app,
                ["config", "init"],
                input=_wizard_input(
                    str(vault_path),
                    "",
                    "kimi",
                    "",
                    "",
                    "",
                    "y",
                ),
            )

        assert result.exit_code == 0
        assert "not found on PATH" in result.output
