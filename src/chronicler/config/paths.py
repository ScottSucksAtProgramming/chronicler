"""Helpers for locating Chronicler's config file."""

from pathlib import Path

from platformdirs import user_config_dir

_config_path_override: Path | None = None


def get_config_path() -> Path:
    """Return the active config file path."""
    if _config_path_override is not None:
        return _config_path_override

    return Path(user_config_dir("chronicler")) / "config.toml"


def set_config_path(path: Path | None) -> None:
    """Override the config file path for tests."""
    global _config_path_override
    _config_path_override = path
