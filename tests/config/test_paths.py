"""Tests for config path resolution."""

from pathlib import Path

from chronicler.config.paths import get_config_path, set_config_path


def test_get_config_path_returns_override(tmp_path):
    override_path = tmp_path / "config.toml"

    try:
        set_config_path(override_path)
        assert get_config_path() == override_path
    finally:
        set_config_path(None)


def test_set_config_path_reset_restores_default():
    original_path = get_config_path()

    try:
        set_config_path(Path("/tmp/chronicler-test-config.toml"))
        set_config_path(None)
        assert get_config_path() == original_path
    finally:
        set_config_path(None)
