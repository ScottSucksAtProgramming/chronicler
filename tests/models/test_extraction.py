"""Tests for extraction result data models."""

import pytest
from session_scribe.models.extraction import (
    ExtractionResult,
    AgentQuestion,
    QuestionPriority,
    QualityScore,
)
from session_scribe.models.entities import NPC, Location, Faction, LootItem, PlotThread, ThreadStatus
from session_scribe.models.session import SessionRecap, KeyEvent


class TestExtractionResult:
    def test_create_extraction_result(self):
        result = ExtractionResult(
            session_number=22,
            npcs=[NPC(name="The Friendly Face", first_appeared="Session-022")],
            locations=[Location(name="The Black Spire", first_appeared="Session-022")],
            factions=[],
            loot=[],
            plot_threads=[
                PlotThread(
                    title="The Black Spire",
                    status=ThreadStatus.OPEN,
                    introduced_in="Session-022",
                    summary="Core cult site in the swamp.",
                ),
            ],
            recap=SessionRecap(
                session_number=22,
                title="No Loose Ends",
                summary="The party tracked down an informant.",
                key_events=[],
            ),
            questions=[],
        )
        assert len(result.npcs) == 1
        assert len(result.plot_threads) == 1
        assert result.recap.session_number == 22

    def test_extraction_result_with_questions(self):
        result = ExtractionResult(
            session_number=22,
            npcs=[],
            locations=[],
            factions=[],
            loot=[],
            plot_threads=[],
            recap=SessionRecap(
                session_number=22,
                title="Session 22",
                summary="Summary.",
                key_events=[],
            ),
            questions=[
                AgentQuestion(
                    question="Is 'the big guy' the same person as 'The Friendly Face'?",
                    context="Both terms used in Session 22 to describe the informant.",
                    priority=QuestionPriority.MEDIUM,
                    source_session=22,
                ),
            ],
        )
        assert len(result.questions) == 1
        assert result.questions[0].priority == QuestionPriority.MEDIUM


class TestQualityScore:
    def test_create_quality_score(self):
        score = QualityScore(
            completeness=4,
            accuracy=5,
            coherence=4,
            relevance=5,
            linking_quality=3,
        )
        assert score.average == pytest.approx(4.2)

    def test_quality_score_fails_below_threshold(self):
        score = QualityScore(
            completeness=2,
            accuracy=5,
            coherence=4,
            relevance=5,
            linking_quality=4,
        )
        assert score.has_failures is True
        assert "completeness" in score.failed_dimensions

    def test_quality_score_passes(self):
        score = QualityScore(
            completeness=4,
            accuracy=4,
            coherence=3,
            relevance=5,
            linking_quality=3,
        )
        assert score.has_failures is False

    def test_quality_score_rejects_out_of_range(self):
        with pytest.raises(Exception):
            QualityScore(completeness=0, accuracy=5, coherence=5, relevance=5, linking_quality=5)

        with pytest.raises(Exception):
            QualityScore(completeness=6, accuracy=5, coherence=5, relevance=5, linking_quality=5)
