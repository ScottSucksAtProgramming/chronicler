"""Data models for session documents and recaps."""

from pydantic import BaseModel, Field


class TranscriptSegment(BaseModel):
    """A segment of transcript with metadata."""

    timestamp: str
    text: str
    is_in_game: bool = True


class KeyEvent(BaseModel):
    """A significant event during a session."""

    description: str
    timestamp: str | None = None


class NormalizedSession(BaseModel):
    """A normalized session document ready for extraction."""

    session_number: int
    title: str
    summary_text: str | None = None
    transcript_segments: list[TranscriptSegment] = Field(default_factory=list)


class SessionRecap(BaseModel):
    """A generated recap of a session."""

    session_number: int
    title: str
    summary: str
    key_events: list[KeyEvent] = Field(default_factory=list)
