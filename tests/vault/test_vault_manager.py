"""Tests for the Vault Manager."""

import pytest
import yaml
from unittest.mock import MagicMock, patch, call
from session_scribe.vault.vault_manager import VaultManager
from session_scribe.models.entities import (
    NPC,
    Location,
    Faction,
    LootItem,
    PlotThread,
    EntityStatus,
    ThreadStatus,
)
from session_scribe.models.session import SessionRecap, KeyEvent
from session_scribe.models.extraction import (
    ExtractionResult,
    AgentQuestion,
    QuestionPriority,
)
from session_scribe.models.context import (
    ContextBundle,
    AgentMemory,
    PlayerCharacter,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_cli():
    cli = MagicMock()
    cli.vault_name = "Test Vault"
    cli.list_files.return_value = []
    cli.list_folders.return_value = ["/"]
    cli.search.return_value = []
    cli.health_check.return_value = True
    cli.find_notes_in_folder.return_value = []
    cli.read.return_value = ""
    cli.note_exists.return_value = False
    return cli


@pytest.fixture
def manager(mock_cli):
    return VaultManager(cli=mock_cli)


def _sample_npc(**overrides) -> NPC:
    defaults = dict(
        name="Theron",
        first_appeared="Session-001",
        status=EntityStatus.ALIVE,
        description="A mysterious stranger.",
        aliases=["The Stranger"],
        affiliations=["The Guild"],
        tags=["quest-giver"],
        key_interactions=["Gave the party a quest"],
    )
    defaults.update(overrides)
    return NPC(**defaults)


def _sample_location(**overrides) -> Location:
    defaults = dict(
        name="Thornwall",
        first_appeared="Session-001",
        description="A frontier town.",
        aliases=["The Wall"],
        connected_to=["The Wilds"],
        tags=["town"],
    )
    defaults.update(overrides)
    return Location(**defaults)


def _sample_faction(**overrides) -> Faction:
    defaults = dict(
        name="The Guild",
        first_appeared="Session-001",
        description="A merchants' guild.",
        known_members=["Theron"],
        aliases=["Merchant Guild"],
        tags=["faction"],
    )
    defaults.update(overrides)
    return Faction(**defaults)


def _sample_loot(**overrides) -> LootItem:
    defaults = dict(
        name="Sword of Flames",
        found_in="Session-001",
        description="A flaming longsword.",
        held_by="Arin",
        tags=["magic-item"],
    )
    defaults.update(overrides)
    return LootItem(**defaults)


def _sample_thread(**overrides) -> PlotThread:
    defaults = dict(
        title="The Missing Heir",
        status=ThreadStatus.OPEN,
        introduced_in="Session-001",
        summary="The heir to the throne has vanished.",
        related_entities=["Theron", "Thornwall"],
        tags=["main-quest"],
    )
    defaults.update(overrides)
    return PlotThread(**defaults)


def _sample_recap(**overrides) -> SessionRecap:
    defaults = dict(
        session_number=1,
        title="The Beginning",
        summary="The party met in a tavern.",
        key_events=[
            KeyEvent(description="Party met Theron", timestamp="00:15:00"),
        ],
    )
    defaults.update(overrides)
    return SessionRecap(**defaults)


# ---------------------------------------------------------------------------
# TestVaultInit
# ---------------------------------------------------------------------------


class TestVaultInit:
    """Tests for init_vault()."""

    def test_init_vault_creates_dashboard(self, manager, mock_cli):
        manager.init_vault()
        # Should have created _Dashboard.md
        created_paths = [c.args[0] for c in mock_cli.create.call_args_list]
        assert any("_Dashboard.md" in p for p in created_paths)

    def test_init_vault_creates_open_threads(self, manager, mock_cli):
        manager.init_vault()
        created_paths = [c.args[0] for c in mock_cli.create.call_args_list]
        assert any("_Open-Threads.md" in p for p in created_paths)

    def test_init_vault_creates_agent_memory_files(self, manager, mock_cli):
        manager.init_vault()
        created_paths = [c.args[0] for c in mock_cli.create.call_args_list]
        assert any("entity-aliases.md" in p for p in created_paths)
        assert any("player-characters.md" in p for p in created_paths)
        assert any("extraction-rules.md" in p for p in created_paths)
        assert any("campaign-patterns.md" in p for p in created_paths)
        assert any("user-preferences.md" in p for p in created_paths)

    def test_init_vault_creates_timeline(self, manager, mock_cli):
        manager.init_vault()
        created_paths = [c.args[0] for c in mock_cli.create.call_args_list]
        assert any("Timeline.md" in p for p in created_paths)

    def test_init_vault_creates_review_log(self, manager, mock_cli):
        manager.init_vault()
        created_paths = [c.args[0] for c in mock_cli.create.call_args_list]
        assert any("Review-Log.md" in p for p in created_paths)


# ---------------------------------------------------------------------------
# TestWriteEntities
# ---------------------------------------------------------------------------


class TestWriteEntities:
    """Tests for write_npc, write_location, write_faction, write_loot, write_session."""

    def test_write_npc_creates_note(self, manager, mock_cli):
        npc = _sample_npc()
        manager.write_npc(npc)
        mock_cli.create.assert_called_once()
        path_arg = mock_cli.create.call_args[0][0]
        assert path_arg == "NPCs/Theron.md"

    def test_write_npc_skips_duplicate(self, manager, mock_cli):
        npc = _sample_npc()
        mock_cli.find_notes_in_folder.return_value = ["NPCs/Theron.md"]
        manager.write_npc(npc, update_existing=False)
        mock_cli.create.assert_not_called()

    def test_write_npc_updates_existing(self, manager, mock_cli):
        npc = _sample_npc()
        mock_cli.find_notes_in_folder.return_value = ["NPCs/Theron.md"]
        manager.write_npc(npc, update_existing=True)
        mock_cli.create.assert_called_once()

    def test_write_location_creates_note(self, manager, mock_cli):
        loc = _sample_location()
        manager.write_location(loc)
        mock_cli.create.assert_called_once()
        path_arg = mock_cli.create.call_args[0][0]
        assert path_arg == "Locations/Thornwall.md"

    def test_write_location_skips_duplicate(self, manager, mock_cli):
        loc = _sample_location()
        mock_cli.find_notes_in_folder.return_value = ["Locations/Thornwall.md"]
        manager.write_location(loc, update_existing=False)
        mock_cli.create.assert_not_called()

    def test_write_faction_creates_note(self, manager, mock_cli):
        faction = _sample_faction()
        manager.write_faction(faction)
        mock_cli.create.assert_called_once()
        path_arg = mock_cli.create.call_args[0][0]
        assert path_arg == "Factions/The Guild.md"

    def test_write_loot_creates_note(self, manager, mock_cli):
        item = _sample_loot()
        manager.write_loot(item)
        mock_cli.create.assert_called_once()
        path_arg = mock_cli.create.call_args[0][0]
        assert path_arg == "Loot/Sword of Flames.md"

    def test_write_session_creates_note(self, manager, mock_cli):
        recap = _sample_recap()
        npcs = [_sample_npc()]
        locs = [_sample_location()]
        manager.write_session(recap, npcs, locs)
        mock_cli.create.assert_called_once()
        path_arg = mock_cli.create.call_args[0][0]
        assert path_arg == "Sessions/Session-001.md"

    def test_write_npc_content_contains_frontmatter(self, manager, mock_cli):
        npc = _sample_npc()
        manager.write_npc(npc)
        content = mock_cli.create.call_args[0][1]
        assert content.startswith("---")
        assert "type: npc" in content

    def test_write_session_has_session_number_in_path(self, manager, mock_cli):
        recap = _sample_recap(session_number=42)
        manager.write_session(recap, [], [])
        path_arg = mock_cli.create.call_args[0][0]
        assert path_arg == "Sessions/Session-042.md"


# ---------------------------------------------------------------------------
# TestWriteExtractionResult
# ---------------------------------------------------------------------------


class TestWriteExtractionResult:
    """Tests for write_extraction_result."""

    def test_write_full_result_creates_multiple_notes(self, manager, mock_cli):
        result = ExtractionResult(
            session_number=1,
            npcs=[_sample_npc()],
            locations=[_sample_location()],
            factions=[_sample_faction()],
            loot=[_sample_loot()],
            plot_threads=[_sample_thread()],
            recap=_sample_recap(),
            questions=[
                AgentQuestion(
                    question="Who is Theron?",
                    context="Appeared in session 1",
                    priority=QuestionPriority.HIGH,
                    source_session=1,
                )
            ],
        )
        manager.write_extraction_result(result)
        # Should create: 1 NPC + 1 location + 1 faction + 1 loot + 1 session
        # + open threads + dashboard + 1 question = at least 5 entity notes
        created_paths = [c.args[0] for c in mock_cli.create.call_args_list]
        assert any("NPCs/" in p for p in created_paths)
        assert any("Locations/" in p for p in created_paths)
        assert any("Factions/" in p for p in created_paths)
        assert any("Loot/" in p for p in created_paths)
        assert any("Sessions/" in p for p in created_paths)

    def test_write_extraction_result_updates_open_threads(self, manager, mock_cli):
        thread = _sample_thread()
        result = ExtractionResult(
            session_number=1,
            npcs=[],
            locations=[],
            factions=[],
            loot=[],
            plot_threads=[thread],
            recap=_sample_recap(),
        )
        manager.write_extraction_result(result)
        created_paths = [c.args[0] for c in mock_cli.create.call_args_list]
        assert any("_Open-Threads.md" in p for p in created_paths)

    def test_write_extraction_result_updates_dashboard(self, manager, mock_cli):
        result = ExtractionResult(
            session_number=1,
            npcs=[_sample_npc()],
            locations=[_sample_location()],
            factions=[],
            loot=[],
            plot_threads=[_sample_thread()],
            recap=_sample_recap(),
        )
        manager.write_extraction_result(result)
        created_paths = [c.args[0] for c in mock_cli.create.call_args_list]
        assert any("_Dashboard.md" in p for p in created_paths)

    def test_write_extraction_result_writes_questions(self, manager, mock_cli):
        question = AgentQuestion(
            question="Who is Theron?",
            context="Appeared in session 1",
            priority=QuestionPriority.HIGH,
            source_session=1,
        )
        result = ExtractionResult(
            session_number=1,
            npcs=[],
            locations=[],
            factions=[],
            loot=[],
            plot_threads=[],
            recap=_sample_recap(),
            questions=[question],
        )
        manager.write_extraction_result(result)
        created_paths = [c.args[0] for c in mock_cli.create.call_args_list]
        assert any("_Agent/Questions/" in p for p in created_paths)


# ---------------------------------------------------------------------------
# TestOpenThreadsAndDashboard
# ---------------------------------------------------------------------------


class TestOpenThreadsAndDashboard:
    """Tests for update_open_threads and update_dashboard."""

    def test_update_open_threads_writes_index(self, manager, mock_cli):
        threads = [_sample_thread()]
        manager.update_open_threads(threads)
        mock_cli.create.assert_called_once()
        path = mock_cli.create.call_args[0][0]
        assert path == "Plot-Threads/_Open-Threads.md"
        content = mock_cli.create.call_args[0][1]
        assert "The Missing Heir" in content

    def test_update_dashboard_writes_stats(self, manager, mock_cli):
        manager.update_dashboard(
            session_number=5, npc_count=10, location_count=3, thread_count=2
        )
        mock_cli.create.assert_called_once()
        path = mock_cli.create.call_args[0][0]
        assert path == "_Dashboard.md"
        content = mock_cli.create.call_args[0][1]
        assert "10" in content
        assert "Session 5" in content


# ---------------------------------------------------------------------------
# TestContextBundle
# ---------------------------------------------------------------------------


class TestContextBundle:
    """Tests for get_context_bundle."""

    def test_empty_vault_returns_empty_bundle(self, manager, mock_cli):
        mock_cli.find_notes_in_folder.return_value = []
        bundle = manager.get_context_bundle(session_number=1)
        assert isinstance(bundle, ContextBundle)
        assert bundle.session_number == 1
        assert bundle.known_npcs == []
        assert bundle.known_locations == []
        assert bundle.known_factions == []
        assert bundle.active_threads == []
        assert bundle.recent_events == []
        assert bundle.entity_aliases == {}
        assert bundle.player_characters == []

    def test_vault_with_npcs_populates_known_npcs(self, manager, mock_cli):
        npc_frontmatter = "---\ntype: npc\nname: Theron\nstatus: alive\naliases: [\"The Stranger\"]\n---\n# Theron"
        mock_cli.find_notes_in_folder.side_effect = lambda folder: {
            "NPCs/": ["NPCs/Theron.md"],
            "Locations/": [],
            "Factions/": [],
            "Sessions/": [],
        }.get(folder, [])
        mock_cli.read.side_effect = lambda path: {
            "NPCs/Theron.md": npc_frontmatter,
            "Plot-Threads/_Open-Threads.md": "",
            "_Agent/Memory/entity-aliases.md": "",
            "_Agent/Memory/player-characters.md": "",
        }.get(path, "")
        bundle = manager.get_context_bundle(session_number=2)
        assert len(bundle.known_npcs) == 1
        assert bundle.known_npcs[0].name == "Theron"
        assert bundle.known_npcs[0].status == "alive"
        assert "The Stranger" in bundle.known_npcs[0].aliases

    def test_vault_with_locations_populates_known_locations(self, manager, mock_cli):
        loc_frontmatter = "---\ntype: location\nname: Thornwall\naliases: [\"The Wall\"]\n---\n# Thornwall"
        mock_cli.find_notes_in_folder.side_effect = lambda folder: {
            "NPCs/": [],
            "Locations/": ["Locations/Thornwall.md"],
            "Factions/": [],
            "Sessions/": [],
        }.get(folder, [])
        mock_cli.read.side_effect = lambda path: {
            "Locations/Thornwall.md": loc_frontmatter,
            "Plot-Threads/_Open-Threads.md": "",
            "_Agent/Memory/entity-aliases.md": "",
            "_Agent/Memory/player-characters.md": "",
        }.get(path, "")
        bundle = manager.get_context_bundle(session_number=2)
        assert len(bundle.known_locations) == 1
        assert bundle.known_locations[0].name == "Thornwall"

    def test_context_bundle_reads_sessions_for_recent_events(self, manager, mock_cli):
        session_content = "---\ntype: session\nsession_number: 1\ntitle: The Beginning\n---\n# Session 1\n\n## Summary\n\nThe party met in a tavern."
        mock_cli.find_notes_in_folder.side_effect = lambda folder: {
            "NPCs/": [],
            "Locations/": [],
            "Factions/": [],
            "Sessions/": ["Sessions/Session-001.md"],
        }.get(folder, [])
        mock_cli.read.side_effect = lambda path: {
            "Sessions/Session-001.md": session_content,
            "Plot-Threads/_Open-Threads.md": "",
            "_Agent/Memory/entity-aliases.md": "",
            "_Agent/Memory/player-characters.md": "",
        }.get(path, "")
        bundle = manager.get_context_bundle(session_number=2)
        assert len(bundle.recent_events) >= 1

    def test_context_bundle_reads_entity_aliases(self, manager, mock_cli):
        aliases_content = "---\ntype: agent-memory\n---\n\nTheron: The Stranger\nGarrick: Old Man G"
        mock_cli.find_notes_in_folder.side_effect = lambda folder: {
            "NPCs/": [],
            "Locations/": [],
            "Factions/": [],
            "Sessions/": [],
        }.get(folder, [])
        mock_cli.read.side_effect = lambda path: {
            "Plot-Threads/_Open-Threads.md": "",
            "_Agent/Memory/entity-aliases.md": aliases_content,
            "_Agent/Memory/player-characters.md": "",
        }.get(path, "")
        bundle = manager.get_context_bundle(session_number=1)
        assert bundle.entity_aliases.get("Theron") == "The Stranger"

    def test_context_bundle_reads_player_characters(self, manager, mock_cli):
        pc_content = "---\ntype: agent-memory\n---\n\n- player_name: Scott\n  character_name: Arin\n  character_class: Fighter"
        mock_cli.find_notes_in_folder.side_effect = lambda folder: {
            "NPCs/": [],
            "Locations/": [],
            "Factions/": [],
            "Sessions/": [],
        }.get(folder, [])
        mock_cli.read.side_effect = lambda path: {
            "Plot-Threads/_Open-Threads.md": "",
            "_Agent/Memory/entity-aliases.md": "",
            "_Agent/Memory/player-characters.md": pc_content,
        }.get(path, "")
        bundle = manager.get_context_bundle(session_number=1)
        assert len(bundle.player_characters) == 1
        assert bundle.player_characters[0].player_name == "Scott"
        assert bundle.player_characters[0].character_name == "Arin"


# ---------------------------------------------------------------------------
# TestAgentMemory
# ---------------------------------------------------------------------------


class TestAgentMemory:
    """Tests for write_question, read_agent_memory, update_entity_aliases, update_player_characters."""

    def test_write_question(self, manager, mock_cli):
        question = AgentQuestion(
            question="Who is the king?",
            context="Referenced in session 3",
            priority=QuestionPriority.HIGH,
            source_session=3,
        )
        manager.write_question(question)
        mock_cli.create.assert_called_once()
        path = mock_cli.create.call_args[0][0]
        assert path.startswith("_Agent/Questions/")
        assert path.endswith(".md")

    def test_read_agent_memory_empty(self, manager, mock_cli):
        mock_cli.read.return_value = ""
        memory = manager.read_agent_memory()
        assert isinstance(memory, AgentMemory)
        assert memory.entity_aliases == {}
        assert memory.player_characters == []

    def test_read_agent_memory_with_data(self, manager, mock_cli):
        def _read(path):
            if "entity-aliases" in path:
                return "---\ntype: agent-memory\n---\n\nTheron: The Stranger"
            if "player-characters" in path:
                return "---\ntype: agent-memory\n---\n\n- player_name: Scott\n  character_name: Arin\n  character_class: Fighter"
            if "extraction-rules" in path:
                return "---\ntype: agent-memory\n---\n\n- Always check for name variants"
            if "campaign-patterns" in path:
                return "---\ntype: agent-memory\n---\n\n- The party tends to split"
            if "user-preferences" in path:
                return "---\ntype: agent-memory\n---\n\n- Prefer short summaries"
            return ""

        mock_cli.read.side_effect = _read
        memory = manager.read_agent_memory()
        assert memory.entity_aliases.get("Theron") == "The Stranger"
        assert len(memory.player_characters) == 1
        assert len(memory.extraction_rules) == 1
        assert len(memory.campaign_patterns) == 1
        assert len(memory.user_preferences) == 1

    def test_update_entity_aliases(self, manager, mock_cli):
        aliases = {"Theron": "The Stranger", "Garrick": "Old Man G"}
        manager.update_entity_aliases(aliases)
        mock_cli.create.assert_called_once()
        path = mock_cli.create.call_args[0][0]
        assert path == "_Agent/Memory/entity-aliases.md"
        content = mock_cli.create.call_args[0][1]
        assert "Theron" in content
        assert "The Stranger" in content

    def test_update_player_characters(self, manager, mock_cli):
        pcs = [
            PlayerCharacter(
                player_name="Scott",
                character_name="Arin",
                character_class="Fighter",
            )
        ]
        manager.update_player_characters(pcs)
        mock_cli.create.assert_called_once()
        path = mock_cli.create.call_args[0][0]
        assert path == "_Agent/Memory/player-characters.md"
        content = mock_cli.create.call_args[0][1]
        assert "Scott" in content
        assert "Arin" in content


# ---------------------------------------------------------------------------
# TestFrontmatterParsing
# ---------------------------------------------------------------------------


class TestFrontmatterParsing:
    """Tests for _parse_frontmatter."""

    def test_parse_valid_frontmatter(self, manager):
        content = "---\ntype: npc\nname: Theron\nstatus: alive\n---\n# Theron"
        result = manager._parse_frontmatter(content)
        assert result["type"] == "npc"
        assert result["name"] == "Theron"
        assert result["status"] == "alive"

    def test_parse_no_frontmatter_returns_empty(self, manager):
        content = "# Just a heading\n\nSome body text."
        result = manager._parse_frontmatter(content)
        assert result == {}

    def test_parse_frontmatter_with_lists(self, manager):
        content = '---\naliases: ["The Stranger", "Mysterious One"]\ntags: ["npc"]\n---\n# Test'
        result = manager._parse_frontmatter(content)
        assert result["aliases"] == ["The Stranger", "Mysterious One"]

    def test_parse_empty_content(self, manager):
        result = manager._parse_frontmatter("")
        assert result == {}


# ---------------------------------------------------------------------------
# TestFindExisting
# ---------------------------------------------------------------------------


class TestFindExisting:
    """Tests for _find_existing."""

    def test_find_existing_exact_match(self, manager, mock_cli):
        mock_cli.find_notes_in_folder.return_value = ["NPCs/Theron.md"]
        result = manager._find_existing("Theron", "NPCs/")
        assert result == "NPCs/Theron.md"

    def test_find_existing_no_match(self, manager, mock_cli):
        mock_cli.find_notes_in_folder.return_value = ["NPCs/Garrick.md"]
        result = manager._find_existing("Theron", "NPCs/")
        assert result is None

    def test_find_existing_fuzzy_match(self, manager, mock_cli):
        mock_cli.find_notes_in_folder.return_value = ["NPCs/Theron the Bold.md"]
        # "Theron the Bold" vs "Theron The Bold" should fuzzy match
        result = manager._find_existing("Theron The Bold", "NPCs/")
        assert result == "NPCs/Theron the Bold.md"
