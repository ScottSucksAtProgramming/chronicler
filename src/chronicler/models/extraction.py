"""Data models for extraction results and quality evaluation."""

from enum import Enum

from pydantic import BaseModel, Field, computed_field

from chronicler.models.entities import (
    NPC,
    Location,
    Faction,
    LootItem,
    PlotThread,
)
from chronicler.models.session import SessionRecap


class QuestionPriority(str, Enum):
    """Priority level for agent questions."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class AgentQuestion(BaseModel):
    """A question the agent wants to ask the user."""

    question: str
    context: str
    priority: QuestionPriority = QuestionPriority.MEDIUM
    source_session: int | None = None
    answer: str | None = None


_QUALITY_THRESHOLD = 3


class QualityScore(BaseModel):
    """Quality evaluation of an extraction run. Each dimension scored 1-5."""

    completeness: int = Field(ge=1, le=5)
    accuracy: int = Field(ge=1, le=5)
    coherence: int = Field(ge=1, le=5)
    relevance: int = Field(ge=1, le=5)
    linking_quality: int = Field(ge=1, le=5)

    @computed_field
    @property
    def average(self) -> float:
        scores = [
            self.completeness,
            self.accuracy,
            self.coherence,
            self.relevance,
            self.linking_quality,
        ]
        return sum(scores) / len(scores)

    @computed_field
    @property
    def has_failures(self) -> bool:
        return len(self.failed_dimensions) > 0

    @computed_field
    @property
    def failed_dimensions(self) -> list[str]:
        failures = []
        for name in ["completeness", "accuracy", "coherence", "relevance", "linking_quality"]:
            if getattr(self, name) < _QUALITY_THRESHOLD:
                failures.append(name)
        return failures


class ExtractionResult(BaseModel):
    """Complete extraction output for a single session."""

    session_number: int
    npcs: list[NPC]
    locations: list[Location]
    factions: list[Faction]
    loot: list[LootItem]
    plot_threads: list[PlotThread]
    recap: SessionRecap
    questions: list[AgentQuestion] = Field(default_factory=list)
    quality_score: QualityScore | None = None


class KnowledgeIngestResult(BaseModel):
    """Extraction output for a general source document import."""

    session_number: int | None = None
    npcs: list[NPC]
    locations: list[Location]
    factions: list[Faction]
    loot: list[LootItem]
    plot_threads: list[PlotThread]
    recap: SessionRecap | None = None
    questions: list[AgentQuestion] = Field(default_factory=list)
    quality_score: QualityScore | None = None
