"""Tests for extraction prompt templates."""

from session_scribe.extraction.prompts import (
    build_extraction_prompt,
    build_recap_prompt,
    build_quality_judge_prompt,
)
from session_scribe.models.context import ContextBundle, EntitySummary


class TestPromptTemplates:
    def test_extraction_prompt_includes_session_content(self):
        prompt = build_extraction_prompt(
            summary_text="The party explored a dungeon.",
            transcript_text="We go into the cave.",
            context=ContextBundle(session_number=5),
        )
        assert "party explored a dungeon" in prompt
        assert "cave" in prompt

    def test_extraction_prompt_includes_context(self):
        context = ContextBundle(
            session_number=5,
            known_npcs=[],
            entity_aliases={"the tavern": "Smoked Eel Tavern"},
        )
        prompt = build_extraction_prompt(
            summary_text="Session content.",
            transcript_text=None,
            context=context,
        )
        assert "Smoked Eel Tavern" in prompt

    def test_extraction_prompt_handles_no_transcript(self):
        prompt = build_extraction_prompt(
            summary_text="Summary only.",
            transcript_text=None,
            context=ContextBundle(session_number=1),
        )
        assert "Summary only" in prompt

    def test_extraction_prompt_includes_player_characters_warning(self):
        from session_scribe.models.context import PlayerCharacter
        context = ContextBundle(
            session_number=5,
            player_characters=[
                PlayerCharacter(player_name="Scott", character_name="Seven", character_class="Wizard"),
            ],
        )
        prompt = build_extraction_prompt(
            summary_text="Content.",
            transcript_text=None,
            context=context,
        )
        assert "Seven" in prompt
        assert "NOT" in prompt  # should warn not to extract PCs as NPCs

    def test_extraction_prompt_requests_json(self):
        prompt = build_extraction_prompt(
            summary_text="Content.",
            transcript_text=None,
            context=ContextBundle(session_number=1),
        )
        assert "JSON" in prompt
        assert "npcs" in prompt
        assert "locations" in prompt
        assert "plot_threads" in prompt
        assert "key_interactions" in prompt  # NPC field that must be in schema
        assert "held_by" in prompt  # LootItem field that must be in schema

    def test_recap_prompt_includes_content(self):
        prompt = build_recap_prompt(
            summary_text="The party fought a dragon.",
            session_number=10,
        )
        assert "dragon" in prompt
        assert "10" in prompt

    def test_quality_judge_prompt_includes_extraction(self):
        prompt = build_quality_judge_prompt(
            source_text="Original session text.",
            extraction_json='{"npcs": []}',
        )
        assert "Original session text" in prompt
        assert '{"npcs": []}' in prompt
        assert "completeness" in prompt.lower()
        assert "accuracy" in prompt.lower()
