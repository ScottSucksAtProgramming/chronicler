# tests/chat/test_prompts.py
"""Tests for the RAG chat prompt template."""

import pytest

from chronicler.chat.prompts import build_chat_prompt
from chronicler.chat.context_loader import DirectVaultNote
from chronicler.retrieval.retrieval import SearchResult


@pytest.fixture
def sample_results():
    return [
        SearchResult(
            path="NPCs/Sylvie.md",
            heading="Description",
            content="A mysterious elf from the forest with silver hair.",
            score=0.12,
        ),
        SearchResult(
            path="Locations/Forest-Ruins.md",
            heading="History",
            content="Ancient ruins covered in elven runes, believed to be a portal site.",
            score=0.25,
        ),
    ]


@pytest.fixture
def sample_history():
    return [
        {"role": "user", "content": "Who are the main NPCs?"},
        {
            "role": "assistant",
            "content": "The main NPCs include Sylvie and Lord Maren.",
        },
    ]


class TestBuildChatPrompt:
    def test_includes_core_vault_context_and_supporting_notes(
        self, sample_results, sample_history
    ):
        prompt = build_chat_prompt(
            question="What do we know about the ship?",
            core_notes=[
                DirectVaultNote(
                    path="Party/Seven.md", content="Seven is a wizard in the party."
                ),
                DirectVaultNote(
                    path="_Agent/Memory/vault-guide.md",
                    content="Party/ is authoritative for player characters.",
                ),
            ],
            supporting_notes=[
                DirectVaultNote(
                    path="Sessions/Session-002.md",
                    content="The party boarded the Black Cherry.",
                ),
            ],
            retrieval_results=sample_results,
            conversation_history=sample_history,
        )

        assert "## Core Vault Context" in prompt
        assert "Party/Seven.md" in prompt
        assert "## Directly Read Supporting Notes" in prompt
        assert "Sessions/Session-002.md" in prompt

    def test_direct_vault_notes_are_described_as_more_authoritative(
        self, sample_results, sample_history
    ):
        prompt = build_chat_prompt(
            question="Tell me about Seven.",
            core_notes=[
                DirectVaultNote(path="Party/Seven.md", content="Seven is a wizard.")
            ],
            supporting_notes=[],
            retrieval_results=sample_results,
            conversation_history=sample_history,
        )

        assert "Direct vault notes are authoritative" in prompt
        assert "Missing retrieval is not the same as missing vault data" in prompt

    def test_prompt_requires_explicit_fact_vs_inference_language(
        self, sample_results, sample_history
    ):
        prompt = build_chat_prompt(
            question="What is the Black Cherry?",
            core_notes=[],
            supporting_notes=[],
            retrieval_results=sample_results,
            conversation_history=sample_history,
        )

        assert "The vault explicitly says" in prompt
        assert "I infer" in prompt
        assert "do not present inferred relationships as confirmed facts" in prompt

    def test_prompt_requires_definition_questions_to_admit_missing_direct_note(
        self, sample_results, sample_history
    ):
        prompt = build_chat_prompt(
            question="What is the Black Cherry?",
            core_notes=[],
            supporting_notes=[],
            retrieval_results=sample_results,
            conversation_history=sample_history,
        )

        assert "I don't see a note that directly defines" in prompt

    def test_includes_question(self, sample_results, sample_history):
        question = "What do we know about Sylvie?"
        prompt = build_chat_prompt(question, [], [], sample_results, sample_history)
        assert question in prompt

    def test_includes_context_with_source_paths(self, sample_results, sample_history):
        question = "Tell me about the ruins."
        prompt = build_chat_prompt(question, [], [], sample_results, sample_history)

        # Source paths should appear in the prompt
        assert "NPCs/Sylvie.md" in prompt
        assert "Locations/Forest-Ruins.md" in prompt

        # Content should be included
        assert "silver hair" in prompt
        assert "elven runes" in prompt

    def test_includes_source_headings(self, sample_results, sample_history):
        question = "Describe the ruins."
        prompt = build_chat_prompt(question, [], [], sample_results, sample_history)

        # Headings should appear alongside paths
        assert "Description" in prompt
        assert "History" in prompt

    def test_includes_conversation_history(self, sample_results, sample_history):
        question = "What else do you know?"
        prompt = build_chat_prompt(question, [], [], sample_results, sample_history)

        assert "Who are the main NPCs?" in prompt
        assert "Sylvie and Lord Maren" in prompt

    def test_instructs_source_citation(self, sample_results, sample_history):
        question = "Tell me about Sylvie."
        prompt = build_chat_prompt(question, [], [], sample_results, sample_history)

        # Must instruct LLM to cite using wikilinks
        assert (
            "[[" in prompt or "wikilink" in prompt.lower() or "cite" in prompt.lower()
        )

    def test_instructs_no_hallucination(self, sample_results, sample_history):
        question = "Tell me about Sylvie."
        prompt = build_chat_prompt(question, [], [], sample_results, sample_history)

        # Must include the exact fallback phrase
        assert "I don't have information about that in the vault." in prompt

    def test_empty_context_results(self, sample_history):
        question = "Any info on dragons?"
        prompt = build_chat_prompt(question, [], [], [], sample_history)

        assert question in prompt
        # Should still instruct no hallucination
        assert "I don't have information about that in the vault." in prompt

    def test_empty_conversation_history(self, sample_results):
        question = "Who is Sylvie?"
        prompt = build_chat_prompt(question, [], [], sample_results, [])

        assert question in prompt
        assert "NPCs/Sylvie.md" in prompt
