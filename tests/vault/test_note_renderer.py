"""Tests for rendering Pydantic models into Obsidian markdown notes."""

import pytest
from session_scribe.vault.note_renderer import (
    render_npc_note,
    render_location_note,
    render_faction_note,
    render_loot_note,
    render_session_note,
    render_plot_thread_note,
    render_open_threads,
    render_dashboard,
    wikify,
)
from session_scribe.models.entities import NPC, Location, Faction, LootItem, PlotThread, EntityStatus, ThreadStatus
from session_scribe.models.session import SessionRecap, KeyEvent


class TestWikify:
    def test_wikify_simple_name(self):
        assert wikify("Theron") == "[[Theron]]"

    def test_wikify_list(self):
        result = wikify(["Theron", "Sylvie"])
        assert result == "[[Theron]], [[Sylvie]]"

    def test_wikify_empty_list(self):
        assert wikify([]) == ""


class TestRenderNPC:
    def test_render_minimal_npc(self):
        npc = NPC(name="Theron", first_appeared="Session-001")
        md = render_npc_note(npc)
        assert "# Theron" in md
        assert "[[Session-001]]" in md
        assert "status: unknown" in md
        assert "type: npc" in md

    def test_render_full_npc(self):
        npc = NPC(
            name="The Friendly Face",
            first_appeared="Session-022",
            status=EntityStatus.DEAD,
            description="A cult informant.",
            aliases=["the big guy"],
            affiliations=["Sylvie's Cult"],
            tags=["cult"],
            key_interactions=["Interrogated by the party"],
        )
        md = render_npc_note(npc)
        assert "status: dead" in md
        assert "[[Sylvie's Cult]]" in md
        assert "the big guy" in md
        assert "A cult informant." in md
        assert "Interrogated by the party" in md

    def test_npc_note_has_frontmatter(self):
        npc = NPC(name="Test", first_appeared="Session-001")
        md = render_npc_note(npc)
        assert md.startswith("---\n")
        assert "\n---\n" in md[3:]


class TestRenderLocation:
    def test_render_location(self):
        loc = Location(
            name="The Black Spire",
            first_appeared="Session-022",
            description="A cult site in the swamp.",
            connected_to=["Underground Tunnels"],
        )
        md = render_location_note(loc)
        assert "# The Black Spire" in md
        assert "type: location" in md
        assert "[[Underground Tunnels]]" in md
        assert "A cult site in the swamp." in md


class TestRenderFaction:
    def test_render_faction(self):
        faction = Faction(
            name="Sylvie's Cult",
            first_appeared="Session-022",
            description="A smuggling operation.",
            known_members=["Sylvie", "Bill Tidewater"],
        )
        md = render_faction_note(faction)
        assert "# Sylvie's Cult" in md
        assert "type: faction" in md
        assert "[[Sylvie]]" in md
        assert "[[Bill Tidewater]]" in md


class TestRenderLoot:
    def test_render_loot(self):
        item = LootItem(
            name="Hallucinogen-Laced Poison",
            found_in="Session-022",
            description="Poison found on dart traps.",
            held_by="Party",
            tags=["cult", "poison"],
        )
        md = render_loot_note(item)
        assert "# Hallucinogen-Laced Poison" in md
        assert "type: loot" in md
        assert "[[Session-022]]" in md
        assert "Party" in md


class TestRenderSession:
    def test_render_session_note(self):
        recap = SessionRecap(
            session_number=22,
            title="No Loose Ends",
            summary="The party tracked down an informant.",
            key_events=[
                KeyEvent(description="Found the safe house", timestamp="00:17:15"),
                KeyEvent(description="Interrogated the target", timestamp=None),
            ],
        )
        npcs = [NPC(name="Theron", first_appeared="Session-022")]
        locations = [Location(name="The Black Spire", first_appeared="Session-022")]

        md = render_session_note(recap, npcs, locations)
        assert "# Session 22" in md or "# No Loose Ends" in md
        assert "type: session" in md
        assert "The party tracked down" in md
        assert "Found the safe house" in md
        assert "[[Theron]]" in md
        assert "[[The Black Spire]]" in md


class TestRenderOpenThreads:
    def test_render_open_threads(self):
        threads = [
            PlotThread(title="The Black Spire", status=ThreadStatus.OPEN,
                       introduced_in="Session-022", summary="Cult site in swamp."),
            PlotThread(title="Missing Merchant", status=ThreadStatus.OPEN,
                       introduced_in="Session-020", summary="Still missing."),
        ]
        md = render_open_threads(threads)
        assert "The Black Spire" in md
        assert "Missing Merchant" in md
        assert "[[Session-022]]" in md


class TestRenderDashboard:
    def test_render_dashboard(self):
        md = render_dashboard(
            latest_session=22,
            npc_count=6,
            location_count=11,
            thread_count=5,
        )
        assert "Dashboard" in md
        assert "22" in md
