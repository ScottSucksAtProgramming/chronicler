"""Tests for the entity extraction orchestrator."""

import json
from pathlib import Path
import pytest
from unittest.mock import AsyncMock, MagicMock

from chronicler.extraction.extractor import extract_session
from chronicler.models.session import NormalizedSession, TranscriptSegment
from chronicler.models.context import ContextBundle
from chronicler.models.extraction import ExtractionResult, KnowledgeIngestResult
from chronicler.models.source_document import (
    SourceClassification,
    SourceDocument,
    DocumentType,
)
from chronicler.extraction.source_extractor import extract_source_document

MOCK_EXTRACTION_RESPONSE = json.dumps(
    {
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
    }
)

MOCK_RECAP_RESPONSE = json.dumps(
    {
        "title": "Into the Dark Forest",
        "summary": "The party ventured into the forest and met Theron.",
        "key_events": [
            {"description": "Met Theron the ranger", "timestamp": "00:15:00"},
        ],
    }
)

MOCK_QUALITY_RESPONSE = json.dumps(
    {
        "completeness": 4,
        "accuracy": 5,
        "coherence": 4,
        "relevance": 5,
        "linking_quality": 4,
        "notes": "Good extraction.",
    }
)

MOCK_SOURCE_EXTRACTION_RESPONSE = json.dumps(
    {
        "npcs": [
            {
                "name": "Theron",
                "first_appeared": None,
                "source_attribution": "DM Jared notes",
                "status": "alive",
                "description": "A ranger from the north.",
                "aliases": [],
                "affiliations": [],
                "tags": ["ranger"],
                "key_interactions": ["Mentioned in old campaign notes"],
            }
        ],
        "locations": [
            {
                "name": "The Dark Forest",
                "first_appeared": None,
                "source_attribution": "DM Jared notes",
                "description": "A dense forest.",
                "aliases": ["dark forest"],
                "parent_location": "Northern Reach",
                "adjacent_to": ["Hunter's Road"],
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
                "introduced_in": None,
                "source_attribution": "DM Jared notes",
                "summary": "A merchant went missing in the forest.",
            }
        ],
        "questions": [],
    }
)

MOCK_SOURCE_EXTRACTION_NO_PROVENANCE_RESPONSE = json.dumps(
    {
        "npcs": [
            {
                "name": "Theron",
                "first_appeared": None,
                "source_attribution": None,
                "status": "alive",
                "description": "A ranger from the north.",
                "aliases": [],
                "affiliations": [],
                "tags": ["ranger"],
                "key_interactions": ["Mentioned in old campaign notes"],
            }
        ],
        "locations": [
            {
                "name": "The Dark Forest",
                "first_appeared": None,
                "source_attribution": None,
                "description": "A dense forest.",
                "aliases": ["dark forest"],
                "parent_location": None,
                "adjacent_to": [],
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
                "introduced_in": None,
                "source_attribution": None,
                "summary": "A merchant went missing in the forest.",
            }
        ],
        "questions": [],
    }
)

MOCK_SOURCE_EXTRACTION_WITH_IMPLICIT_PARENT_RESPONSE = json.dumps(
    {
        "npcs": [],
        "locations": [
            {
                "name": "Mist Alley",
                "first_appeared": None,
                "source_attribution": "DM Jared notes",
                "description": "A district in Laguna Nera containing the Perfumed Chapel and Redcap's Remedies.",
                "aliases": [],
                "parent_location": None,
                "adjacent_to": [],
                "connected_to": ["Laguna Nera"],
                "tags": ["district"],
            }
        ],
        "factions": [],
        "loot": [],
        "plot_threads": [],
        "questions": [],
    }
)


@pytest.fixture
def sample_session():
    return NormalizedSession(
        session_number=1,
        title="Test Session",
        summary_text="The party went into the dark forest and met Theron the ranger.",
        transcript_segments=[
            TranscriptSegment(
                timestamp="00:15:00", text="You see a ranger ahead.", is_in_game=True
            ),
        ],
    )


@pytest.fixture
def mock_gateway():
    gateway = MagicMock()
    gateway.complete = AsyncMock(
        side_effect=[
            MagicMock(
                content=MOCK_EXTRACTION_RESPONSE, usage=MagicMock(total_tokens=500)
            ),
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


class TestExtractSourceDocument:
    @pytest.mark.asyncio
    async def test_extract_source_updates_entities_without_session_recap(self):
        context = ContextBundle(session_number=0)
        gateway = MagicMock()
        gateway.complete = AsyncMock(
            side_effect=[
                MagicMock(
                    content=MOCK_SOURCE_EXTRACTION_RESPONSE,
                    usage=MagicMock(total_tokens=500),
                ),
                MagicMock(
                    content=MOCK_QUALITY_RESPONSE, usage=MagicMock(total_tokens=100)
                ),
            ]
        )
        source_document = SourceDocument(
            source_path=Path("tests/fixtures/imports/legacy_note.md"),
            original_filename="legacy_note.md",
            media_type="text/markdown",
            extracted_text="The party met Theron near the hidden shrine.",
            classification=SourceClassification(
                document_type=DocumentType.LEGACY_NOTE,
                confidence=0.8,
            ),
        )

        result = await extract_source_document(
            document=source_document,
            context=context,
            gateway=gateway,
            model="test-model",
        )

        assert isinstance(result, KnowledgeIngestResult)
        assert result.session_number is None
        assert result.recap is None
        assert len(result.npcs) == 1
        assert result.npcs[0].first_appeared is None
        assert result.npcs[0].source_attribution == "DM Jared notes"
        assert result.locations[0].parent_location == "Northern Reach"
        assert result.locations[0].adjacent_to == ["Hunter's Road"]
        assert result.quality_score is not None

    @pytest.mark.asyncio
    async def test_extract_source_can_emit_session_recap_when_anchored(self):
        context = ContextBundle(session_number=22)
        gateway = MagicMock()
        gateway.complete = AsyncMock(
            side_effect=[
                MagicMock(
                    content=MOCK_EXTRACTION_RESPONSE, usage=MagicMock(total_tokens=500)
                ),
                MagicMock(
                    content=MOCK_RECAP_RESPONSE, usage=MagicMock(total_tokens=200)
                ),
                MagicMock(
                    content=MOCK_QUALITY_RESPONSE, usage=MagicMock(total_tokens=100)
                ),
            ]
        )
        source_document = SourceDocument(
            source_path=Path("tests/fixtures/imports/legacy_note.md"),
            original_filename="legacy_note.md",
            media_type="text/markdown",
            extracted_text="Session 22 notes about Theron and the swamp trail.",
            classification=SourceClassification(
                document_type=DocumentType.SESSION_SUPPORT,
                confidence=1.0,
                session_anchor=22,
            ),
        )

        result = await extract_source_document(
            document=source_document,
            context=context,
            gateway=gateway,
            model="test-model",
        )

        assert result.session_number == 22
        assert result.recap is not None
        assert result.recap.title == "Into the Dark Forest"

    @pytest.mark.asyncio
    async def test_extract_source_emits_question_when_provenance_needed_but_missing(
        self,
    ):
        context = ContextBundle(session_number=0)
        gateway = MagicMock()
        gateway.complete = AsyncMock(
            side_effect=[
                MagicMock(
                    content=MOCK_SOURCE_EXTRACTION_NO_PROVENANCE_RESPONSE,
                    usage=MagicMock(total_tokens=500),
                ),
                MagicMock(
                    content=MOCK_QUALITY_RESPONSE, usage=MagicMock(total_tokens=100)
                ),
            ]
        )
        source_document = SourceDocument(
            source_path=Path("tests/fixtures/imports/legacy_note.md"),
            original_filename="legacy_note.md",
            media_type="text/markdown",
            extracted_text="Old campaign notes about Theron and the hidden shrine.",
            classification=SourceClassification(
                document_type=DocumentType.LEGACY_NOTE,
                confidence=0.8,
            ),
        )

        result = await extract_source_document(
            document=source_document,
            context=context,
            gateway=gateway,
            model="test-model",
        )

        assert result.questions
        assert "source attribution" in result.questions[0].question.lower()
        assert result.npcs[0].source_attribution == "Imported source: legacy_note.md"

    @pytest.mark.asyncio
    async def test_extract_source_prompt_requests_questions_for_uncertain_geography(
        self,
    ):
        context = ContextBundle(session_number=0)
        gateway = MagicMock()
        gateway.complete = AsyncMock(
            side_effect=[
                MagicMock(
                    content=MOCK_SOURCE_EXTRACTION_RESPONSE,
                    usage=MagicMock(total_tokens=500),
                ),
                MagicMock(
                    content=MOCK_QUALITY_RESPONSE, usage=MagicMock(total_tokens=100)
                ),
            ]
        )
        source_document = SourceDocument(
            source_path=Path("tests/fixtures/imports/legacy_note.md"),
            original_filename="legacy_note.md",
            media_type="text/markdown",
            extracted_text="The Silkmarket District lies within Laguna Nera near Harbor District.",
            classification=SourceClassification(
                document_type=DocumentType.LEGACY_NOTE,
                confidence=0.95,
            ),
        )

        await extract_source_document(
            document=source_document,
            context=context,
            gateway=gateway,
            model="test-model",
        )

        prompt_text = gateway.complete.call_args_list[0][0][0].messages[0]["content"]
        assert "parent_location" in prompt_text
        assert "adjacent_to" in prompt_text
        assert "unclear geography" in prompt_text.lower()

    @pytest.mark.asyncio
    async def test_extract_source_infers_parent_location_from_explicit_description(
        self,
    ):
        context = ContextBundle(session_number=0)
        gateway = MagicMock()
        gateway.complete = AsyncMock(
            side_effect=[
                MagicMock(
                    content=MOCK_SOURCE_EXTRACTION_WITH_IMPLICIT_PARENT_RESPONSE,
                    usage=MagicMock(total_tokens=500),
                ),
                MagicMock(
                    content=MOCK_QUALITY_RESPONSE, usage=MagicMock(total_tokens=100)
                ),
            ]
        )
        source_document = SourceDocument(
            source_path=Path("tests/fixtures/imports/legacy_note.md"),
            original_filename="legacy_note.md",
            media_type="text/markdown",
            extracted_text="Mist Alley is a district in Laguna Nera.",
            classification=SourceClassification(
                document_type=DocumentType.LEGACY_NOTE,
                confidence=0.95,
            ),
        )

        result = await extract_source_document(
            document=source_document,
            context=context,
            gateway=gateway,
            model="test-model",
        )

        assert result.locations[0].parent_location == "Laguna Nera"
