"""Tests for rendering Pydantic models into Obsidian markdown notes."""

import pytest
from chronicler.vault.note_renderer import (
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
from chronicler.models.entities import NPC, Location, Faction, LootItem, PlotThread, EntityStatus, ThreadStatus
from chronicler.models.session import SessionRecap, KeyEvent


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

    def test_npc_tags_are_normalized_for_obsidian(self):
        npc = NPC(
            name="Theron",
            first_appeared="Session-001",
            tags=["main quest", "Quest-Giver", "Act 1"],
        )
        md = render_npc_note(npc)
        assert 'tags: ["main_quest", "quest_giver", "act_1"]' in md

    def test_npc_frontmatter_reference_fields_are_quoted_wikilinks(self):
        npc = NPC(
            name="Theron",
            first_appeared="Session-001",
            affiliations=["The Guild"],
        )
        md = render_npc_note(npc)
        assert 'first_appeared: "[[Session-001]]"' in md
        assert 'affiliations: ["[[The Guild]]"]' in md

    def test_render_npc_with_source_attribution_without_session(self):
        npc = NPC(
            name="Theron",
            source_attribution="DM Jared notes",
            description="Mentioned in background material.",
        )
        md = render_npc_note(npc)
        assert "source_attribution: DM Jared notes" in md
        assert "**Source Attribution:** DM Jared notes" in md
        assert "**First Appeared:**" not in md


class TestFrontmatterNormalization:
    def test_frontmatter_does_not_double_wrap_existing_reference_wikilinks(self):
        from chronicler.vault.note_renderer import _frontmatter

        md = _frontmatter(
            type="npc",
            name="Theron",
            first_appeared="[[Session-001]]",
            affiliations=["[[The Guild]]"],
        )

        assert 'first_appeared: "[[Session-001]]"' in md
        assert 'affiliations: ["[[The Guild]]"]' in md
        assert "[[[[" not in md

    def test_frontmatter_collapses_nested_reference_wikilinks(self):
        from chronicler.vault.note_renderer import _frontmatter

        md = _frontmatter(
            type="npc",
            name="Theron",
            first_appeared="[[[[Session-001]]]]",
            affiliations=["[[[[The Guild]]]]"],
        )

        assert 'first_appeared: "[[Session-001]]"' in md
        assert 'affiliations: ["[[The Guild]]"]' in md
        assert "[[[[" not in md


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

    def test_location_frontmatter_reference_fields_are_quoted_wikilinks(self):
        loc = Location(
            name="The Black Spire",
            first_appeared="Session-022",
            connected_to=["Underground Tunnels"],
        )
        md = render_location_note(loc)
        assert 'first_appeared: "[[Session-022]]"' in md
        assert 'connected_to: ["[[Underground Tunnels]]"]' in md

    def test_render_location_with_source_attribution_without_session(self):
        loc = Location(
            name="The Marsh Chapel",
            source_attribution="DM Jared notes",
        )
        md = render_location_note(loc)
        assert "source_attribution: DM Jared notes" in md
        assert "**Source Attribution:** DM Jared notes" in md
        assert "**First Appeared:**" not in md


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

    def test_faction_frontmatter_reference_fields_are_quoted_wikilinks(self):
        faction = Faction(
            name="Sylvie's Cult",
            first_appeared="Session-022",
            known_members=["Sylvie", "Bill Tidewater"],
        )
        md = render_faction_note(faction)
        assert 'first_appeared: "[[Session-022]]"' in md
        assert 'known_members: ["[[Sylvie]]", "[[Bill Tidewater]]"]' in md


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

    def test_loot_frontmatter_reference_fields_are_quoted_wikilinks(self):
        item = LootItem(
            name="Hallucinogen-Laced Poison",
            found_in="Session-022",
            held_by="Theron",
        )
        md = render_loot_note(item)
        assert 'found_in: "[[Session-022]]"' in md
        assert 'held_by: "[[Theron]]"' in md


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

    def test_session_summary_and_key_events_link_known_entities(self):
        recap = SessionRecap(
            session_number=22,
            title="No Loose Ends",
            summary="Theron led the party to The Black Spire and the Bronze Compass.",
            key_events=[
                KeyEvent(description="Theron warned the party about The Black Spire.", timestamp="00:17:15"),
            ],
        )
        npcs = [NPC(name="Theron", first_appeared="Session-022")]
        locations = [Location(name="The Black Spire", first_appeared="Session-022")]
        loot = [LootItem(name="Bronze Compass", found_in="Session-022")]

        md = render_session_note(recap, npcs, locations, factions=[], loot=loot, player_characters=[])

        assert "[[Theron]] led the party" in md
        assert "[[The Black Spire]]" in md
        assert "[[Bronze Compass]]" in md
        assert "`00:17:15` [[Theron]] warned the party about [[The Black Spire]]." in md

    def test_session_frontmatter_references_are_quoted_wikilinks(self):
        recap = SessionRecap(
            session_number=22,
            title="No Loose Ends",
            summary="Theron led the party to The Black Spire.",
            key_events=[],
        )
        npcs = [NPC(name="Theron", first_appeared="Session-022")]
        locations = [Location(name="The Black Spire", first_appeared="Session-022")]

        md = render_session_note(recap, npcs, locations, factions=[], loot=[], player_characters=[])

        assert 'npcs: ["[[Theron]]"]' in md
        assert 'locations: ["[[The Black Spire]]"]' in md

    def test_session_title_is_quoted_in_frontmatter_when_it_contains_colon(self):
        recap = SessionRecap(
            session_number=3,
            title="Session 3: The Sloop Dogg, Sea Horrors, and The Spying Card",
            summary="The party survived the crossing.",
            key_events=[],
        )

        md = render_session_note(recap, [], [])
        assert 'title: "Session 3: The Sloop Dogg, Sea Horrors, and The Spying Card"' in md


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
