"""Integration tests for multi-session pipeline robustness.

Run with: pytest -m integration tests/cli/test_pipeline_integration.py -v -s
"""

import pytest
from session_scribe.vault.obsidian_cli import ObsidianCLI
from session_scribe.vault.vault_manager import VaultManager
from session_scribe.config.settings import Settings
from session_scribe.models.entities import NPC, Location, EntityStatus


@pytest.mark.integration
class TestMultiSessionPipeline:
    """Test that multiple sessions grow the vault correctly."""

    @pytest.fixture
    def real_cli(self):
        settings = Settings()
        assert settings.vault_name
        return ObsidianCLI(vault_name=settings.vault_name)

    @pytest.fixture
    def real_manager(self, real_cli):
        return VaultManager(cli=real_cli)

    def test_second_write_does_not_duplicate_npcs(self, real_manager, real_cli):
        """An NPC written twice should have one note, not two."""
        npc = NPC(name="Dedup Test NPC", first_appeared="Session-001", status=EntityStatus.ALIVE)

        real_manager.write_npc(npc)
        real_manager.write_npc(npc)  # second write should be skipped

        results = real_cli.search("Dedup Test NPC")
        npc_results = [r for r in results if "NPCs/" in r and "Dedup Test" in r]
        assert len(npc_results) == 1

        # Clean up
        for path in results:
            if "Dedup Test" in path:
                real_cli.delete(path)

    def test_context_bundle_generation(self, real_manager):
        bundle = real_manager.get_context_bundle(session_number=23)
        assert bundle.session_number == 23
