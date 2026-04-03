"""Tests for D&D campaign entity data models."""

import pytest
from chronicler.models.entities import (
    NPC,
    Location,
    Faction,
    LootItem,
    PlotThread,
    ThreadStatus,
    EntityStatus,
)


class TestNPC:
    def test_create_minimal_npc(self):
        npc = NPC(name="Theron", first_appeared="Session-001")
        assert npc.name == "Theron"
        assert npc.first_appeared == "Session-001"
        assert npc.status == EntityStatus.UNKNOWN
        assert npc.aliases == []
        assert npc.affiliations == []
        assert npc.tags == []

    def test_create_full_npc(self):
        npc = NPC(
            name="The Friendly Face",
            first_appeared="Session-022",
            status=EntityStatus.ALIVE,
            description="A man hired by the cult to confront the party.",
            aliases=["the friendly face", "big guy"],
            affiliations=["Sylvie's Cult"],
            tags=["cult", "informant"],
        )
        assert npc.status == EntityStatus.ALIVE
        assert "the friendly face" in npc.aliases
        assert len(npc.affiliations) == 1

    def test_npc_requires_name(self):
        with pytest.raises(Exception):
            NPC(first_appeared="Session-001")

    def test_npc_requires_session_or_source_provenance(self):
        with pytest.raises(Exception):
            NPC(name="Theron")

    def test_npc_can_use_source_attribution_without_session(self):
        npc = NPC(name="Theron", source_attribution="DM Jared notes")
        assert npc.first_appeared is None
        assert npc.source_attribution == "DM Jared notes"

    def test_invalid_status_raises(self):
        with pytest.raises(Exception):
            NPC(name="Test", first_appeared="Session-001", status="banana")


class TestLocation:
    def test_create_minimal_location(self):
        loc = Location(name="The Black Spire", first_appeared="Session-022")
        assert loc.name == "The Black Spire"
        assert loc.aliases == []
        assert loc.description is None

    def test_create_full_location(self):
        loc = Location(
            name="Underground Tunnel Network",
            first_appeared="Session-022",
            description="Six earthen tunnels with cold saltwater, beneath the safe house.",
            aliases=["the tunnels", "smuggling grid"],
            connected_to=["City Docks", "The Farm", "Wine Cellar"],
            tags=["cult", "smuggling"],
        )
        assert len(loc.connected_to) == 3


class TestFaction:
    def test_create_faction(self):
        faction = Faction(
            name="Sylvie's Cult",
            first_appeared="Session-022",
            description="Smuggling operation run by Sylvie.",
            known_members=["Sylvie", "Bill Tidewater", "The Friendly Face"],
        )
        assert len(faction.known_members) == 3

    def test_faction_requires_name(self):
        with pytest.raises(Exception):
            Faction(first_appeared="Session-022")

    def test_faction_requires_session_or_source_provenance(self):
        with pytest.raises(Exception):
            Faction(name="Test Faction")


class TestLootItem:
    def test_create_loot_item(self):
        item = LootItem(
            name="Hallucinogen-Laced Poison",
            found_in="Session-022",
            description="Poison commonly used by the cult, found on dart traps.",
        )
        assert item.name == "Hallucinogen-Laced Poison"

    def test_loot_requires_name(self):
        with pytest.raises(Exception):
            LootItem(found_in="Session-022")

    def test_loot_requires_session_or_source_provenance(self):
        with pytest.raises(Exception):
            LootItem(name="Magic Sword")


class TestPlotThread:
    def test_create_open_thread(self):
        thread = PlotThread(
            title="The Black Spire",
            status=ThreadStatus.OPEN,
            introduced_in="Session-022",
            summary="A core cult site in the swamp. Location confirmed by informant.",
        )
        assert thread.status == ThreadStatus.OPEN
        assert thread.resolved_in is None

    def test_create_closed_thread(self):
        thread = PlotThread(
            title="Find the Friendly Face",
            status=ThreadStatus.CLOSED,
            introduced_in="Session-020",
            resolved_in="Session-022",
            summary="Tracked down and interrogated. Killed by his own clone.",
        )
        assert thread.resolved_in == "Session-022"

    def test_plot_thread_can_use_source_attribution_without_session(self):
        thread = PlotThread(
            title="The Marsh Chapel",
            status=ThreadStatus.OPEN,
            source_attribution="DM Jared notes",
            summary="A hidden shrine beneath the chapel.",
        )
        assert thread.introduced_in is None
        assert thread.source_attribution == "DM Jared notes"
