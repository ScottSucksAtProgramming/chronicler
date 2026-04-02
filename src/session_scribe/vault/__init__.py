"""Public API for the vault module."""

from session_scribe.vault.vault_manager import VaultManager
from session_scribe.vault.obsidian_cli import ObsidianCLI, ObsidianCLIError

__all__ = ["VaultManager", "ObsidianCLI", "ObsidianCLIError"]
