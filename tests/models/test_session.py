"""Tests for session-related data models."""

import pytest
from session_scribe.models.session import (
    NormalizedSession,
    TranscriptSegment,
    SessionRecap,
    KeyEvent,
)


class TestTranscriptSegment:
    def test_create_segment(self):
        seg = TranscriptSegment(
            timestamp="00:14:32",
            text="You meet Theron, a ranger from the northern woods.",
            is_in_game=True,
        )
        assert seg.timestamp == "00:14:32"
        assert seg.is_in_game is True

    def test_out_of_game_segment(self):
        seg = TranscriptSegment(
            timestamp="00:02:00",
            text="Did she get your steak tacos or did you get hers?",
            is_in_game=False,
        )
        assert seg.is_in_game is False


class TestNormalizedSession:
    def test_create_session(self):
        session = NormalizedSession(
            session_number=22,
            title="No Loose Ends Investigation",
            summary_text="The players conducted a late-night investigation...",
            transcript_segments=[
                TranscriptSegment(
                    timestamp="00:00:00",
                    text="Captain, and then you haven't gone back...",
                    is_in_game=True,
                ),
            ],
        )
        assert session.session_number == 22
        assert len(session.transcript_segments) == 1

    def test_session_without_transcript(self):
        session = NormalizedSession(
            session_number=22,
            title="No Loose Ends Investigation",
            summary_text="The players conducted a late-night investigation...",
        )
        assert session.transcript_segments == []

    def test_session_without_summary(self):
        session = NormalizedSession(
            session_number=22,
            title="Session 22",
            transcript_segments=[
                TranscriptSegment(
                    timestamp="00:00:00",
                    text="Some game content.",
                    is_in_game=True,
                ),
            ],
        )
        assert session.summary_text is None


class TestSessionRecap:
    def test_create_recap(self):
        recap = SessionRecap(
            session_number=22,
            title="No Loose Ends Investigation",
            summary="The party tracked down the friendly face informant...",
            key_events=[
                KeyEvent(
                    description="Party infiltrated booby-trapped safe house",
                    timestamp="00:23:28",
                ),
                KeyEvent(
                    description="Informant assassinated by his own clone",
                    timestamp="01:45:00",
                ),
            ],
        )
        assert len(recap.key_events) == 2
