# tests/chat/test_prompts.py
"""Tests for the RAG chat prompt template."""

import pytest

from session_scribe.chat.prompts import build_chat_prompt
from session_scribe.retrieval.retrieval import SearchResult


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
        {"role": "assistant", "content": "The main NPCs include Sylvie and Lord Maren."},
    ]


class TestBuildChatPrompt:
    def test_includes_question(self, sample_results, sample_history):
        question = "What do we know about Sylvie?"
        prompt = build_chat_prompt(question, sample_results, sample_history)
        assert question in prompt

    def test_includes_context_with_source_paths(self, sample_results, sample_history):
        question = "Tell me about the ruins."
        prompt = build_chat_prompt(question, sample_results, sample_history)

        # Source paths should appear in the prompt
        assert "NPCs/Sylvie.md" in prompt
        assert "Locations/Forest-Ruins.md" in prompt

        # Content should be included
        assert "silver hair" in prompt
        assert "elven runes" in prompt

    def test_includes_source_headings(self, sample_results, sample_history):
        question = "Describe the ruins."
        prompt = build_chat_prompt(question, sample_results, sample_history)

        # Headings should appear alongside paths
        assert "Description" in prompt
        assert "History" in prompt

    def test_includes_conversation_history(self, sample_results, sample_history):
        question = "What else do you know?"
        prompt = build_chat_prompt(question, sample_results, sample_history)

        assert "Who are the main NPCs?" in prompt
        assert "Sylvie and Lord Maren" in prompt

    def test_instructs_source_citation(self, sample_results, sample_history):
        question = "Tell me about Sylvie."
        prompt = build_chat_prompt(question, sample_results, sample_history)

        # Must instruct LLM to cite using wikilinks
        assert "[[" in prompt or "wikilink" in prompt.lower() or "cite" in prompt.lower()

    def test_instructs_no_hallucination(self, sample_results, sample_history):
        question = "Tell me about Sylvie."
        prompt = build_chat_prompt(question, sample_results, sample_history)

        # Must include the exact fallback phrase
        assert "I don't have information about that in the vault." in prompt

    def test_empty_context_results(self, sample_history):
        question = "Any info on dragons?"
        prompt = build_chat_prompt(question, [], sample_history)

        assert question in prompt
        # Should still instruct no hallucination
        assert "I don't have information about that in the vault." in prompt

    def test_empty_conversation_history(self, sample_results):
        question = "Who is Sylvie?"
        prompt = build_chat_prompt(question, sample_results, [])

        assert question in prompt
        assert "NPCs/Sylvie.md" in prompt
