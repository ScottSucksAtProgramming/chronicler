"""Integration tests against a real Obsidian vault.

Run with: pytest -m integration tests/vault/test_vault_integration.py -v -s
"""

import pytest
from chronicler.vault.obsidian_cli import ObsidianCLI
from chronicler.vault.vault_manager import VaultManager
from chronicler.config.settings import Settings
from chronicler.models.entities import NPC, Location, EntityStatus


@pytest.mark.integration
class TestVaultIntegration:
    """Tests that hit the real Obsidian CLI."""

    @pytest.fixture
    def real_cli(self):
        settings = Settings()
        assert settings.vault_name, "CHRONICLER_VAULT_NAME must be set for integration tests"
        return ObsidianCLI(vault_name=settings.vault_name)

    @pytest.fixture
    def real_manager(self, real_cli):
        return VaultManager(cli=real_cli)

    def test_cli_health_check(self, real_cli):
        assert real_cli.health_check() is True

    def test_init_vault(self, real_manager, real_cli):
        real_manager.init_vault()

        folders = real_cli.list_folders()
        assert any("Sessions" in f for f in folders)
        assert any("NPCs" in f for f in folders)
        assert any("Locations" in f for f in folders)

    def test_write_and_read_npc(self, real_manager, real_cli):
        npc = NPC(
            name="Integration Test NPC",
            first_appeared="Session-999",
            status=EntityStatus.ALIVE,
            description="Created by integration test.",
        )
        real_manager.write_npc(npc)

        # Verify it exists via search
        results = real_cli.search("Integration Test NPC")
        assert len(results) > 0

        # Clean up
        for path in results:
            if "Integration Test NPC" in path:
                real_cli.delete(path)

    def test_context_bundle_generation(self, real_manager):
        bundle = real_manager.get_context_bundle(session_number=1)
        assert bundle.session_number == 1
