"""Tests for the entity extraction orchestrator."""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock

from chronicler.extraction.extractor import extract_session
from chronicler.models.session import NormalizedSession, TranscriptSegment
from chronicler.models.context import ContextBundle
from chronicler.models.extraction import ExtractionResult


MOCK_EXTRACTION_RESPONSE = json.dumps({
    "npcs": [
        {
            "name": "Theron",
            "first_appeared": "Session-001",
            "status": "alive",
            "description": "A ranger from the north.",
            "aliases": [],
            "affiliations": [],
            "tags": ["ranger"],
            "key_interactions": ["Met the party in the forest"],
        }
    ],
    "locations": [
        {
            "name": "The Dark Forest",
            "first_appeared": "Session-001",
            "description": "A dense forest.",
            "aliases": ["dark forest"],
            "connected_to": [],
            "tags": [],
        }
    ],
    "factions": [],
    "loot": [],
    "plot_threads": [
        {
            "title": "Missing Merchant",
            "status": "open",
            "introduced_in": "Session-001",
            "summary": "A merchant went missing in the forest.",
        }
    ],
    "questions": [],
})

MOCK_RECAP_RESPONSE = json.dumps({
    "title": "Into the Dark Forest",
    "summary": "The party ventured into the forest and met Theron.",
    "key_events": [
        {"description": "Met Theron the ranger", "timestamp": "00:15:00"},
    ],
})

MOCK_QUALITY_RESPONSE = json.dumps({
    "completeness": 4,
    "accuracy": 5,
    "coherence": 4,
    "relevance": 5,
    "linking_quality": 4,
    "notes": "Good extraction.",
})


@pytest.fixture
def sample_session():
    return NormalizedSession(
        session_number=1,
        title="Test Session",
        summary_text="The party went into the dark forest and met Theron the ranger.",
        transcript_segments=[
            TranscriptSegment(timestamp="00:15:00", text="You see a ranger ahead.", is_in_game=True),
        ],
    )


@pytest.fixture
def mock_gateway():
    gateway = MagicMock()
    gateway.complete = AsyncMock(
        side_effect=[
            MagicMock(content=MOCK_EXTRACTION_RESPONSE, usage=MagicMock(total_tokens=500)),
            MagicMock(content=MOCK_RECAP_RESPONSE, usage=MagicMock(total_tokens=200)),
            MagicMock(content=MOCK_QUALITY_RESPONSE, usage=MagicMock(total_tokens=100)),
        ]
    )
    return gateway


class TestExtractSession:
    @pytest.mark.asyncio
    async def test_extract_produces_result(self, sample_session, mock_gateway):
        context = ContextBundle(session_number=1)
        result = await extract_session(
            session=sample_session,
            context=context,
            gateway=mock_gateway,
            model="test-model",
        )

        assert isinstance(result, ExtractionResult)
        assert result.session_number == 1
        assert len(result.npcs) == 1
        assert result.npcs[0].name == "Theron"
        assert len(result.locations) == 1
        assert len(result.plot_threads) == 1
        assert result.recap is not None
        assert result.recap.title == "Into the Dark Forest"
        assert result.quality_score is not None
        assert result.quality_score.has_failures is False

    @pytest.mark.asyncio
    async def test_extract_makes_three_llm_calls(self, sample_session, mock_gateway):
        context = ContextBundle(session_number=1)
        await extract_session(
            session=sample_session,
            context=context,
            gateway=mock_gateway,
            model="test-model",
        )
        assert mock_gateway.complete.call_count == 3

    @pytest.mark.asyncio
    async def test_extract_passes_context_to_prompt(self, sample_session, mock_gateway):
        context = ContextBundle(
            session_number=1,
            entity_aliases={"the forest": "The Dark Forest"},
        )
        await extract_session(
            session=sample_session,
            context=context,
            gateway=mock_gateway,
            model="test-model",
        )

        first_call_messages = mock_gateway.complete.call_args_list[0][0][0].messages
        prompt_text = first_call_messages[0]["content"]
        assert "The Dark Forest" in prompt_text
