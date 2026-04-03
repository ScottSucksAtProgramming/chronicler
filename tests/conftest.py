"""Shared test fixtures for chronicler tests."""

import json
import pytest
from pathlib import Path

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def settings():
    """Create a test Settings instance with dummy values."""
    from chronicler.config.settings import Settings

    return Settings(
        vault_path=Path("/tmp/test-vault"),
        llm_provider="nanogpt",
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


@pytest.fixture
def session_022_dir():
    """Path to Session 022 fixture files."""
    return FIXTURES_DIR / "session_022"


@pytest.fixture
def session_022_golden(session_022_dir):
    """Load the golden fixture for Session 022."""
    golden_path = session_022_dir / "golden.json"
    return json.loads(golden_path.read_text())
