"""Utilities for reading config file state."""

import os
import tomllib
from typing import Literal

from chronicler.config.paths import get_config_path
from chronicler.config.settings import Settings

FieldSource = Literal["env", "file", "default"]


def load_config_file() -> dict[str, object]:
    """Read the flat TOML config file, or return an empty mapping."""
    config_path = get_config_path()
    if not config_path.exists():
        return {}

    with config_path.open("rb") as config_file:
        data = tomllib.load(config_file)

    return {key: value for key, value in data.items() if isinstance(key, str)}


def get_field_sources() -> dict[str, FieldSource]:
    """Report whether each settings field comes from env, file, or defaults."""
    config_data = load_config_file()
    env_prefix = Settings.model_config.get("env_prefix", "")

    field_sources: dict[str, FieldSource] = {}
    for field_name in Settings.model_fields:
        env_var = f"{env_prefix}{field_name.upper()}"
        if env_var in os.environ:
            field_sources[field_name] = "env"
        elif field_name in config_data:
            field_sources[field_name] = "file"
        else:
            field_sources[field_name] = "default"

    return field_sources
