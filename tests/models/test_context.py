"""Tests for context bundle and agent memory models."""

import pytest
from session_scribe.models.context import (
    AgentMemory,
    ContextBundle,
    EntitySummary,
    ThreadSummary,
    PlayerCharacter,
)


class TestEntitySummary:
    def test_create_entity_summary(self):
        entity = EntitySummary(
            name="The Friendly Face",
            aliases=["the big guy", "friendly face"],
            status="alive",
        )
        assert entity.name == "The Friendly Face"
        assert len(entity.aliases) == 2


class TestContextBundle:
    def test_create_empty_bundle(self):
        bundle = ContextBundle(session_number=1)
        assert bundle.known_npcs == []
        assert bundle.known_locations == []
        assert bundle.active_threads == []

    def test_create_full_bundle(self):
        bundle = ContextBundle(
            session_number=23,
            known_npcs=[
                EntitySummary(name="Sylvie", aliases=[], status="alive"),
                EntitySummary(name="The Friendly Face", aliases=["big guy"], status="dead"),
            ],
            known_locations=[
                EntitySummary(name="The Black Spire", aliases=["the spire"]),
            ],
            known_factions=[
                EntitySummary(name="Sylvie's Cult", aliases=["the cult"]),
            ],
            active_threads=[
                ThreadSummary(title="Smuggling Operation", summary="Cult is smuggling chemicals."),
            ],
            recent_events=["Session 22: Party interrogated the friendly face informant."],
            entity_aliases={"the tavern": "Smoked Eel Tavern", "the boat": "The Mayweather"},
            player_characters=[
                PlayerCharacter(player_name="Scott", character_name="Seven", character_class="Wizard"),
            ],
        )
        assert len(bundle.known_npcs) == 2
        assert bundle.entity_aliases["the tavern"] == "Smoked Eel Tavern"
        assert bundle.player_characters[0].character_name == "Seven"


class TestPlayerCharacter:
    def test_create_player_character(self):
        pc = PlayerCharacter(
            player_name="Scott",
            character_name="Seven",
            character_class="Wizard",
        )
        assert pc.player_name == "Scott"
        assert pc.character_class == "Wizard"

    def test_player_character_minimal(self):
        pc = PlayerCharacter(
            player_name="Unknown",
            character_name="Bastion",
        )
        assert pc.character_class is None


class TestAgentMemory:
    def test_create_empty_memory(self):
        memory = AgentMemory()
        assert memory.extraction_rules == []
        assert memory.entity_aliases == {}
        assert memory.player_characters == []
        assert memory.campaign_patterns == []
        assert memory.user_preferences == []

    def test_create_populated_memory(self):
        memory = AgentMemory(
            extraction_rules=["NPCs are usually introduced by the DM with a name and description."],
            entity_aliases={"the tavern": "Smoked Eel Tavern", "the boat": "The Mayweather"},
            player_characters=[
                PlayerCharacter(player_name="Scott", character_name="Seven", character_class="Wizard"),
            ],
            campaign_patterns=["DM uses 'friendly face' as a recurring alias pattern."],
            user_preferences=["Prefer concise session recaps over detailed ones."],
        )
        assert len(memory.extraction_rules) == 1
        assert memory.entity_aliases["the tavern"] == "Smoked Eel Tavern"
        assert len(memory.player_characters) == 1
