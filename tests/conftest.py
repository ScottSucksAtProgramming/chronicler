"""Shared test fixtures for session_scribe tests."""

import pytest
from pathlib import Path


@pytest.fixture
def settings():
    """Create a test Settings instance with dummy values."""
    from session_scribe.config.settings import Settings

    return Settings(
        vault_path=Path("/tmp/test-vault"),
        nanogpt_api_key="test-key-123",
        _env_file=None,
    )


@pytest.fixture
def tmp_vault(tmp_path):
    """Create a temporary vault directory structure for testing."""
    vault = tmp_path / "campaign"
    vault.mkdir()
    (vault / "Sessions").mkdir()
    (vault / "NPCs").mkdir()
    (vault / "Locations").mkdir()
    (vault / "Factions").mkdir()
    (vault / "Loot").mkdir()
    (vault / "Plot-Threads").mkdir()
    (vault / "_Agent" / "Memory").mkdir(parents=True)
    (vault / "_Agent" / "Questions").mkdir(parents=True)
    (vault / "Transcripts" / "raw").mkdir(parents=True)
    (vault / "Transcripts" / "normalized").mkdir(parents=True)
    return vault
