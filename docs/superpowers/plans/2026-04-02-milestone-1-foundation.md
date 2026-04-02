# Milestone 1: Foundation — Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Scaffold the Session Scribe project with package structure, data models, LLM Gateway, config system, and CLI entry point — everything needed so that Milestone 2 can start building ingestion and extraction on a solid foundation.

**Architecture:** Modular Python package (`session_scribe/`) with clean separation between domain models, infrastructure (LLM Gateway, config), and CLI. All external services behind abstractions. Pydantic v2 for all data structures.

**Tech Stack:** Python 3.12+, uv, pytest, typer, Pydantic v2, nano-gpt.com API, rich

**Spec:** `docs/superpowers/specs/2026-04-02-session-scribe-design.md`

**Core Principles (from spec):**
- Clean Architecture: dependencies point inward, domain never depends on infrastructure
- Testability First: TDD, every module independently testable
- Explicit Over Clever: type hints everywhere, no magic, no raw dicts
- Small Files: no file over ~300 lines, clear public interfaces
- Fail Loudly: never swallow errors silently

---

## Chunk 1: Project Scaffolding + Data Models

### Task 1: Initialize Project with uv

**Files:**
- Create: `pyproject.toml`
- Create: `.python-version`
- Create: `src/session_scribe/__init__.py`
- Create: `src/session_scribe/py.typed`
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`

- [ ] **Step 1: Initialize project with uv**

```bash
cd /Users/scottkostolni/programming_projects/dnd_notes_organizaer
uv init --lib --name session-scribe
```

- [ ] **Step 2: Set Python version**

```bash
echo "3.12" > .python-version
```

- [ ] **Step 3: Configure pyproject.toml**

Replace the generated `pyproject.toml` with:

```toml
[project]
name = "session-scribe"
version = "0.1.0"
description = "D&D Session Scribe — AI agent for campaign note management"
requires-python = ">=3.12"
dependencies = [
    "pydantic>=2.0",
    "typer>=0.12",
    "rich>=13.0",
    "httpx>=0.27",
    "pyyaml>=6.0",
]

[project.scripts]
scribe = "session_scribe.cli.main:app"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/session_scribe"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]
markers = [
    "integration: marks tests that require external services (deselect with '-m \"not integration\"')",
]

[dependency-groups]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.23",
]
```

- [ ] **Step 4: Create package structure**

```bash
mkdir -p src/session_scribe/{cli,models,gateway,config}
mkdir -p tests/{models,gateway,config,cli}
touch src/session_scribe/__init__.py
touch src/session_scribe/py.typed
touch src/session_scribe/cli/__init__.py
touch src/session_scribe/models/__init__.py
touch src/session_scribe/gateway/__init__.py
touch src/session_scribe/config/__init__.py
touch tests/__init__.py
touch tests/conftest.py
touch tests/models/__init__.py
touch tests/gateway/__init__.py
touch tests/config/__init__.py
touch tests/cli/__init__.py
```

- [ ] **Step 5: Install dependencies**

```bash
uv sync
```

Expected: Clean install, no errors.

- [ ] **Step 6: Populate shared test fixtures**

```python
# tests/conftest.py
"""Shared test fixtures for session_scribe tests."""

import pytest
from pathlib import Path


@pytest.fixture
def settings():
    """Create a test Settings instance with dummy values."""
    from session_scribe.config.settings import Settings

    return Settings(
        vault_path=Path("/tmp/test-vault"),
        nanogpt_api_key="test-key-123",
        _env_file=None,  # Don't load .env in tests
    )


@pytest.fixture
def tmp_vault(tmp_path):
    """Create a temporary vault directory structure for testing."""
    vault = tmp_path / "campaign"
    vault.mkdir()
    (vault / "Sessions").mkdir()
    (vault / "NPCs").mkdir()
    (vault / "Locations").mkdir()
    (vault / "Factions").mkdir()
    (vault / "Loot").mkdir()
    (vault / "Plot-Threads").mkdir()
    (vault / "_Agent" / "Memory").mkdir(parents=True)
    (vault / "_Agent" / "Questions").mkdir(parents=True)
    (vault / "Transcripts" / "raw").mkdir(parents=True)
    (vault / "Transcripts" / "normalized").mkdir(parents=True)
    return vault
```

- [ ] **Step 7: Verify pytest runs**

```bash
uv run pytest --co
```

Expected: "no tests ran" or similar — confirms pytest is configured correctly.

- [ ] **Step 7: Commit**

```bash
git add pyproject.toml .python-version src/ tests/ uv.lock
git commit -m "chore: scaffold project structure with uv, pytest, and package layout"
```

---

### Task 2: Entity Data Models

**Files:**
- Create: `src/session_scribe/models/entities.py`
- Create: `tests/models/test_entities.py`

- [ ] **Step 1: Write failing tests for entity models**

```python
# tests/models/test_entities.py
"""Tests for D&D campaign entity data models."""

import pytest
from session_scribe.models.entities import (
    NPC,
    Location,
    Faction,
    LootItem,
    PlotThread,
    ThreadStatus,
    EntityStatus,
)


class TestNPC:
    def test_create_minimal_npc(self):
        npc = NPC(name="Theron", first_appeared="Session-001")
        assert npc.name == "Theron"
        assert npc.first_appeared == "Session-001"
        assert npc.status == EntityStatus.UNKNOWN
        assert npc.aliases == []
        assert npc.affiliations == []
        assert npc.tags == []

    def test_create_full_npc(self):
        npc = NPC(
            name="The Friendly Face",
            first_appeared="Session-022",
            status=EntityStatus.ALIVE,
            description="A man hired by the cult to confront the party.",
            aliases=["the friendly face", "big guy"],
            affiliations=["Sylvie's Cult"],
            tags=["cult", "informant"],
        )
        assert npc.status == EntityStatus.ALIVE
        assert "the friendly face" in npc.aliases
        assert len(npc.affiliations) == 1

    def test_npc_requires_name(self):
        with pytest.raises(Exception):
            NPC(first_appeared="Session-001")  # type: ignore

    def test_npc_requires_first_appeared(self):
        with pytest.raises(Exception):
            NPC(name="Theron")  # type: ignore

    def test_invalid_status_raises(self):
        with pytest.raises(Exception):
            NPC(name="Test", first_appeared="Session-001", status="banana")


class TestLocation:
    def test_create_minimal_location(self):
        loc = Location(name="The Black Spire", first_appeared="Session-022")
        assert loc.name == "The Black Spire"
        assert loc.aliases == []
        assert loc.description is None

    def test_create_full_location(self):
        loc = Location(
            name="Underground Tunnel Network",
            first_appeared="Session-022",
            description="Six earthen tunnels with cold saltwater, beneath the safe house.",
            aliases=["the tunnels", "smuggling grid"],
            connected_to=["City Docks", "The Farm", "Wine Cellar"],
            tags=["cult", "smuggling"],
        )
        assert len(loc.connected_to) == 3


class TestFaction:
    def test_create_faction(self):
        faction = Faction(
            name="Sylvie's Cult",
            first_appeared="Session-022",
            description="Smuggling operation run by Sylvie.",
            known_members=["Sylvie", "Bill Tidewater", "The Friendly Face"],
        )
        assert len(faction.known_members) == 3


class TestLootItem:
    def test_create_loot_item(self):
        item = LootItem(
            name="Hallucinogen-Laced Poison",
            found_in="Session-022",
            description="Poison commonly used by the cult, found on dart traps.",
        )
        assert item.name == "Hallucinogen-Laced Poison"


class TestPlotThread:
    def test_create_open_thread(self):
        thread = PlotThread(
            title="The Black Spire",
            status=ThreadStatus.OPEN,
            introduced_in="Session-022",
            summary="A core cult site in the swamp. Location confirmed by informant.",
        )
        assert thread.status == ThreadStatus.OPEN
        assert thread.resolved_in is None

    def test_create_closed_thread(self):
        thread = PlotThread(
            title="Find the Friendly Face",
            status=ThreadStatus.CLOSED,
            introduced_in="Session-020",
            resolved_in="Session-022",
            summary="Tracked down and interrogated. Killed by his own clone.",
        )
        assert thread.resolved_in == "Session-022"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/models/test_entities.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'session_scribe.models.entities'`

- [ ] **Step 3: Implement entity models**

```python
# src/session_scribe/models/entities.py
"""Pydantic data models for D&D campaign entities."""

from enum import Enum

from pydantic import BaseModel, Field


class EntityStatus(str, Enum):
    """Status of an NPC or other entity."""

    ALIVE = "alive"
    DEAD = "dead"
    UNKNOWN = "unknown"


class ThreadStatus(str, Enum):
    """Status of a plot thread."""

    OPEN = "open"
    CLOSED = "closed"


class NPC(BaseModel):
    """A non-player character in the campaign."""

    name: str
    first_appeared: str
    status: EntityStatus = EntityStatus.UNKNOWN
    description: str | None = None
    aliases: list[str] = Field(default_factory=list)
    affiliations: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    key_interactions: list[str] = Field(default_factory=list)


class Location(BaseModel):
    """A location in the campaign world."""

    name: str
    first_appeared: str
    description: str | None = None
    aliases: list[str] = Field(default_factory=list)
    connected_to: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)


class Faction(BaseModel):
    """A faction or organization in the campaign."""

    name: str
    first_appeared: str
    description: str | None = None
    known_members: list[str] = Field(default_factory=list)
    aliases: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)


class LootItem(BaseModel):
    """A notable item or piece of loot."""

    name: str
    found_in: str
    description: str | None = None
    held_by: str | None = None
    tags: list[str] = Field(default_factory=list)


class PlotThread(BaseModel):
    """A plot thread or story hook in the campaign."""

    title: str
    status: ThreadStatus
    introduced_in: str
    summary: str
    resolved_in: str | None = None
    related_entities: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/models/test_entities.py -v
```

Expected: All tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/session_scribe/models/entities.py tests/models/test_entities.py
git commit -m "feat: add Pydantic data models for campaign entities (NPC, Location, Faction, Loot, PlotThread)"
```

---

### Task 3: Session and Extraction Data Models

**Files:**
- Create: `src/session_scribe/models/session.py`
- Create: `src/session_scribe/models/extraction.py`
- Create: `tests/models/test_session.py`
- Create: `tests/models/test_extraction.py`

- [ ] **Step 1: Write failing tests for session models**

```python
# tests/models/test_session.py
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
```

- [ ] **Step 2: Write failing tests for extraction models**

```python
# tests/models/test_extraction.py
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
```

- [ ] **Step 3: Run tests to verify they fail**

```bash
uv run pytest tests/models/ -v
```

Expected: New tests FAIL, Task 2 tests still pass.

- [ ] **Step 4: Implement session models**

```python
# src/session_scribe/models/session.py
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
```

- [ ] **Step 5: Implement extraction models**

```python
# src/session_scribe/models/extraction.py
"""Data models for extraction results and quality evaluation."""

from enum import Enum

from pydantic import BaseModel, Field, computed_field

from session_scribe.models.entities import (
    NPC,
    Location,
    Faction,
    LootItem,
    PlotThread,
)
from session_scribe.models.session import SessionRecap


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

    @computed_field  # type: ignore[prop-decorator]
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

    @computed_field  # type: ignore[prop-decorator]
    @property
    def has_failures(self) -> bool:
        return len(self.failed_dimensions) > 0

    @computed_field  # type: ignore[prop-decorator]
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
```

- [ ] **Step 6: Run tests to verify they pass**

```bash
uv run pytest tests/models/ -v
```

Expected: All tests PASS.

- [ ] **Step 7: Commit**

```bash
git add src/session_scribe/models/ tests/models/
git commit -m "feat: add session, extraction, and quality score data models"
```

---

### Task 4: Context Bundle and Agent Memory Models

**Files:**
- Create: `src/session_scribe/models/context.py`
- Create: `tests/models/test_context.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/models/test_context.py
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/models/test_context.py -v
```

Expected: FAIL — module not found.

- [ ] **Step 3: Implement context models**

```python
# src/session_scribe/models/context.py
"""Data models for context bundles and agent memory structures."""

from pydantic import BaseModel, Field


class EntitySummary(BaseModel):
    """Lightweight summary of a known entity for context bundles."""

    name: str
    aliases: list[str] = Field(default_factory=list)
    status: str | None = None


class ThreadSummary(BaseModel):
    """Lightweight summary of an active plot thread."""

    title: str
    summary: str


class PlayerCharacter(BaseModel):
    """Mapping between a player and their character."""

    player_name: str
    character_name: str
    character_class: str | None = None


class ContextBundle(BaseModel):
    """Snapshot of campaign state passed to the extraction module.

    Built by the Vault Manager from current vault contents.
    The extraction module receives this as input — it never queries the vault directly.
    """

    session_number: int
    known_npcs: list[EntitySummary] = Field(default_factory=list)
    known_locations: list[EntitySummary] = Field(default_factory=list)
    known_factions: list[EntitySummary] = Field(default_factory=list)
    active_threads: list[ThreadSummary] = Field(default_factory=list)
    recent_events: list[str] = Field(default_factory=list)
    entity_aliases: dict[str, str] = Field(default_factory=dict)
    player_characters: list[PlayerCharacter] = Field(default_factory=list)


class AgentMemory(BaseModel):
    """Persistent agent memory stored in the vault.

    Accumulates learned rules, patterns, and preferences across sessions.
    Stored as markdown files in the vault's _Agent/Memory/ folder.
    """

    extraction_rules: list[str] = Field(default_factory=list)
    entity_aliases: dict[str, str] = Field(default_factory=dict)
    player_characters: list[PlayerCharacter] = Field(default_factory=list)
    campaign_patterns: list[str] = Field(default_factory=list)
    user_preferences: list[str] = Field(default_factory=list)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/models/ -v
```

Expected: All tests PASS.

- [ ] **Step 5: Export all models from package**

```python
# src/session_scribe/models/__init__.py
"""Public API for session_scribe data models."""

from session_scribe.models.entities import (
    NPC,
    Location,
    Faction,
    LootItem,
    PlotThread,
    EntityStatus,
    ThreadStatus,
)
from session_scribe.models.session import (
    NormalizedSession,
    TranscriptSegment,
    SessionRecap,
    KeyEvent,
)
from session_scribe.models.extraction import (
    ExtractionResult,
    AgentQuestion,
    QuestionPriority,
    QualityScore,
)
from session_scribe.models.context import (
    AgentMemory,
    ContextBundle,
    EntitySummary,
    ThreadSummary,
    PlayerCharacter,
)

__all__ = [
    "NPC",
    "Location",
    "Faction",
    "LootItem",
    "PlotThread",
    "EntityStatus",
    "ThreadStatus",
    "NormalizedSession",
    "TranscriptSegment",
    "SessionRecap",
    "KeyEvent",
    "ExtractionResult",
    "AgentQuestion",
    "QuestionPriority",
    "QualityScore",
    "AgentMemory",
    "ContextBundle",
    "EntitySummary",
    "ThreadSummary",
    "PlayerCharacter",
]
```

- [ ] **Step 6: Verify imports work**

```bash
uv run python -c "from session_scribe.models import NPC, ExtractionResult, ContextBundle, AgentMemory; print('All models import OK')"
```

Expected: `All models import OK`

- [ ] **Step 7: Commit**

```bash
git add src/session_scribe/models/ tests/models/
git commit -m "feat: add context bundle and agent memory models, export all models from package"
```

---

## Chunk 2: Config System + LLM Gateway

### Task 5: Config System

**Files:**
- Create: `src/session_scribe/config/settings.py`
- Create: `tests/config/test_settings.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/config/test_settings.py
"""Tests for application configuration."""

import os
import pytest
from pathlib import Path


class TestSettings:
    def test_load_default_settings(self):
        from session_scribe.config.settings import Settings

        settings = Settings(
            vault_path=Path("/tmp/test-vault"),
            nanogpt_api_key="test-key-123",
        )
        assert settings.vault_path == Path("/tmp/test-vault")
        assert settings.nanogpt_api_key == "test-key-123"
        assert settings.nanogpt_model is not None  # has a default

    def test_settings_from_env(self, monkeypatch):
        from session_scribe.config.settings import Settings

        monkeypatch.setenv("SCRIBE_VAULT_PATH", "/tmp/env-vault")
        monkeypatch.setenv("SCRIBE_NANOGPT_API_KEY", "env-key-456")
        monkeypatch.setenv("SCRIBE_NANOGPT_MODEL", "claude-3-opus")

        settings = Settings()  # type: ignore  # loads from env
        assert settings.vault_path == Path("/tmp/env-vault")
        assert settings.nanogpt_api_key == "env-key-456"
        assert settings.nanogpt_model == "claude-3-opus"

    def test_settings_validates_vault_path_type(self):
        from session_scribe.config.settings import Settings

        settings = Settings(
            vault_path="/tmp/string-path",  # type: ignore  # string should coerce to Path
            nanogpt_api_key="key",
        )
        assert isinstance(settings.vault_path, Path)

    def test_lm_studio_defaults(self):
        from session_scribe.config.settings import Settings

        settings = Settings(
            vault_path=Path("/tmp/test"),
            nanogpt_api_key="key",
        )
        assert settings.lm_studio_base_url == "http://localhost:1234/v1"
        assert settings.embedding_model == "text-embedding-nomic-embed-text-v1.5"

    def test_missing_required_fields_raises(self, monkeypatch):
        from session_scribe.config.settings import Settings

        # Clear any env vars that could satisfy required fields
        monkeypatch.delenv("SCRIBE_VAULT_PATH", raising=False)
        monkeypatch.delenv("SCRIBE_NANOGPT_API_KEY", raising=False)

        with pytest.raises(Exception):
            Settings(_env_file=None)  # type: ignore  # skip .env file, no env vars
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/config/test_settings.py -v
```

Expected: FAIL.

- [ ] **Step 3: Implement settings**

```python
# src/session_scribe/config/settings.py
"""Application configuration loaded from environment variables or explicit values."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Session Scribe configuration.

    Values can be set via environment variables prefixed with SCRIBE_
    or passed directly to the constructor.
    """

    model_config = SettingsConfigDict(
        env_prefix="SCRIBE_",
        env_file=".env",
        env_file_encoding="utf-8",
    )

    # Required
    vault_path: Path
    nanogpt_api_key: str

    # LLM settings
    nanogpt_base_url: str = "https://nano-gpt.com/api/v1"
    nanogpt_model: str = "chatgpt-4o-latest"

    # LM Studio (local embeddings)
    lm_studio_base_url: str = "http://localhost:1234/v1"
    embedding_model: str = "text-embedding-nomic-embed-text-v1.5"

    # Operational
    log_level: str = "INFO"
    llm_timeout_seconds: int = 30
    llm_max_retries: int = 3
```

- [ ] **Step 4: Add pydantic-settings dependency**

```bash
uv add pydantic-settings
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
uv run pytest tests/config/test_settings.py -v
```

Expected: All tests PASS.

- [ ] **Step 6: Commit**

```bash
git add src/session_scribe/config/ tests/config/ pyproject.toml uv.lock
git commit -m "feat: add config system with env var support and sensible defaults"
```

---

### Task 6: LLM Gateway — Interface and Types

**Files:**
- Create: `src/session_scribe/gateway/llm_gateway.py`
- Create: `src/session_scribe/gateway/types.py`
- Create: `tests/gateway/test_llm_gateway.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/gateway/test_llm_gateway.py
"""Tests for the LLM Gateway."""

import json
import pytest
import httpx
from unittest.mock import AsyncMock, patch, MagicMock
from pydantic import BaseModel

from session_scribe.gateway.types import LLMRequest, LLMResponse, LLMUsage
from session_scribe.gateway.llm_gateway import LLMGateway
from session_scribe.config.settings import Settings


class SampleOutput(BaseModel):
    name: str
    age: int


# Note: `settings` fixture is provided by tests/conftest.py


class TestLLMTypes:
    def test_create_request(self):
        req = LLMRequest(
            messages=[{"role": "user", "content": "Hello"}],
            model="test-model",
        )
        assert len(req.messages) == 1
        assert req.temperature == 0.0  # default for extraction

    def test_create_response(self):
        resp = LLMResponse(
            content="Hello back",
            model="test-model",
            usage=LLMUsage(prompt_tokens=10, completion_tokens=5),
        )
        assert resp.content == "Hello back"
        assert resp.usage.total_tokens == 15


class TestLLMGateway:
    def test_gateway_init(self, settings):
        gateway = LLMGateway(settings)
        assert gateway.settings.nanogpt_api_key == "test-key"

    @pytest.mark.asyncio
    async def test_complete_returns_response(self, settings):
        gateway = LLMGateway(settings)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "test response"}}],
            "model": "test-model",
            "usage": {"prompt_tokens": 10, "completion_tokens": 5},
        }

        with patch.object(gateway, "_client") as mock_client:
            mock_client.post = AsyncMock(return_value=mock_response)
            result = await gateway.complete(
                LLMRequest(
                    messages=[{"role": "user", "content": "test"}],
                    model="test-model",
                )
            )
            assert result.content == "test response"
            assert result.usage.total_tokens == 15

    @pytest.mark.asyncio
    async def test_complete_retries_on_http_error(self, settings):
        gateway = LLMGateway(settings)

        fail_response = MagicMock()
        fail_response.status_code = 500
        fail_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Server Error", request=MagicMock(), response=fail_response
        )

        success_response = MagicMock()
        success_response.status_code = 200
        success_response.json.return_value = {
            "choices": [{"message": {"content": "recovered"}}],
            "model": "test-model",
            "usage": {"prompt_tokens": 5, "completion_tokens": 3},
        }
        success_response.raise_for_status.return_value = None

        with patch.object(gateway, "_client") as mock_client:
            mock_client.post = AsyncMock(side_effect=[fail_response, success_response])
            result = await gateway.complete(
                LLMRequest(messages=[{"role": "user", "content": "test"}], model="test-model")
            )
            assert result.content == "recovered"
            assert mock_client.post.call_count == 2

    @pytest.mark.asyncio
    async def test_complete_raises_after_retries_exhausted(self, settings):
        from session_scribe.gateway.llm_gateway import LLMGatewayError

        gateway = LLMGateway(settings)

        fail_response = MagicMock()
        fail_response.status_code = 500
        fail_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Server Error", request=MagicMock(), response=fail_response
        )

        with patch.object(gateway, "_client") as mock_client:
            mock_client.post = AsyncMock(return_value=fail_response)
            with pytest.raises(LLMGatewayError, match="failed after"):
                await gateway.complete(
                    LLMRequest(messages=[{"role": "user", "content": "test"}], model="test-model")
                )

    @pytest.mark.asyncio
    async def test_complete_structured_invalid_json_retries(self, settings):
        from session_scribe.gateway.llm_gateway import LLMGatewayError

        gateway = LLMGateway(settings)

        bad_response = MagicMock()
        bad_response.status_code = 200
        bad_response.json.return_value = {
            "choices": [{"message": {"content": "not json at all"}}],
            "model": "test-model",
            "usage": {"prompt_tokens": 5, "completion_tokens": 3},
        }
        bad_response.raise_for_status.return_value = None

        # Second call also returns bad JSON — should raise
        with patch.object(gateway, "_client") as mock_client:
            mock_client.post = AsyncMock(return_value=bad_response)
            with pytest.raises(LLMGatewayError, match="parsing failed after correction"):
                await gateway.complete_structured(
                    LLMRequest(messages=[{"role": "user", "content": "test"}], model="test-model"),
                    output_type=SampleOutput,
                )

    @pytest.mark.asyncio
    async def test_complete_structured_parses_to_model(self, settings):
        gateway = LLMGateway(settings)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": '{"name": "Bob", "age": 30}'}}],
            "model": "test-model",
            "usage": {"prompt_tokens": 10, "completion_tokens": 5},
        }

        with patch.object(gateway, "_client") as mock_client:
            mock_client.post = AsyncMock(return_value=mock_response)
            result = await gateway.complete_structured(
                LLMRequest(
                    messages=[{"role": "user", "content": "test"}],
                    model="test-model",
                ),
                output_type=SampleOutput,
            )
            assert isinstance(result, SampleOutput)
            assert result.name == "Bob"
            assert result.age == 30
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/gateway/test_llm_gateway.py -v
```

Expected: FAIL.

- [ ] **Step 3: Implement gateway types**

```python
# src/session_scribe/gateway/types.py
"""Types for LLM Gateway requests and responses."""

from pydantic import BaseModel, Field, computed_field


class LLMUsage(BaseModel):
    """Token usage for an LLM call."""

    prompt_tokens: int
    completion_tokens: int

    @computed_field  # type: ignore[prop-decorator]
    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens


class LLMRequest(BaseModel):
    """A request to the LLM."""

    messages: list[dict[str, str]]
    model: str
    temperature: float = 0.0
    max_tokens: int | None = None


class LLMResponse(BaseModel):
    """A response from the LLM."""

    content: str
    model: str
    usage: LLMUsage
```

- [ ] **Step 4: Implement LLM Gateway**

```python
# src/session_scribe/gateway/llm_gateway.py
"""LLM Gateway — single integration point for all LLM calls."""

import asyncio
import json
import logging
import time
from typing import TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from session_scribe.config.settings import Settings
from session_scribe.gateway.types import LLMRequest, LLMResponse, LLMUsage

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class LLMGatewayError(Exception):
    """Raised when an LLM call fails after retries."""


class LLMGateway:
    """Single integration point for all LLM API calls.

    Handles nano-gpt.com communication, retries, timeout,
    response validation, and usage logging.
    """

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._client = httpx.AsyncClient(
            base_url=settings.nanogpt_base_url,
            headers={
                "Authorization": f"Bearer {settings.nanogpt_api_key}",
                "Content-Type": "application/json",
            },
            timeout=settings.llm_timeout_seconds,
        )

    async def complete(self, request: LLMRequest) -> LLMResponse:
        """Send a completion request to the LLM API with retries."""
        last_error: Exception | None = None
        backoff = 1.0

        for attempt in range(self.settings.llm_max_retries + 1):
            try:
                start = time.monotonic()
                response = await self._client.post(
                    "/chat/completions",
                    json={
                        "model": request.model,
                        "messages": request.messages,
                        "temperature": request.temperature,
                        **({"max_tokens": request.max_tokens} if request.max_tokens else {}),
                    },
                )
                latency = time.monotonic() - start

                response.raise_for_status()
                data = response.json()

                result = LLMResponse(
                    content=data["choices"][0]["message"]["content"],
                    model=data.get("model", request.model),
                    usage=LLMUsage(
                        prompt_tokens=data["usage"]["prompt_tokens"],
                        completion_tokens=data["usage"]["completion_tokens"],
                    ),
                )

                logger.info(
                    "LLM call: model=%s tokens=%d latency=%.2fs",
                    result.model,
                    result.usage.total_tokens,
                    latency,
                )
                return result

            except (httpx.HTTPError, KeyError) as e:
                last_error = e
                if attempt < self.settings.llm_max_retries:
                    logger.warning(
                        "LLM call failed (attempt %d/%d): %s. Retrying in %.1fs.",
                        attempt + 1,
                        self.settings.llm_max_retries + 1,
                        str(e),
                        backoff,
                    )
                    await asyncio.sleep(backoff)
                    backoff *= 2

        raise LLMGatewayError(
            f"LLM call failed after {self.settings.llm_max_retries + 1} attempts: {last_error}"
        )

    async def complete_structured(
        self,
        request: LLMRequest,
        output_type: type[T],
    ) -> T:
        """Send a completion request and parse the response into a Pydantic model.

        On validation failure, retries once with a corrective prompt.
        """
        response = await self.complete(request)

        try:
            # Try to parse JSON from the response content
            content = response.content.strip()
            # Handle markdown code blocks
            if content.startswith("```"):
                content = content.split("\n", 1)[1].rsplit("```", 1)[0].strip()
            parsed = json.loads(content)
            return output_type.model_validate(parsed)
        except (json.JSONDecodeError, ValidationError) as e:
            logger.warning("Structured output parsing failed: %s. Retrying with correction.", str(e))

            # Retry with corrective prompt
            corrective_messages = request.messages + [
                {"role": "assistant", "content": response.content},
                {
                    "role": "user",
                    "content": (
                        f"Your response could not be parsed as valid JSON matching the expected schema. "
                        f"Error: {str(e)}. Please respond with ONLY valid JSON, no markdown formatting."
                    ),
                },
            ]
            corrective_request = LLMRequest(
                messages=corrective_messages,
                model=request.model,
                temperature=request.temperature,
            )
            retry_response = await self.complete(corrective_request)

            try:
                content = retry_response.content.strip()
                if content.startswith("```"):
                    content = content.split("\n", 1)[1].rsplit("```", 1)[0].strip()
                parsed = json.loads(content)
                return output_type.model_validate(parsed)
            except (json.JSONDecodeError, ValidationError) as retry_error:
                raise LLMGatewayError(
                    f"Structured output parsing failed after correction: {retry_error}"
                ) from retry_error

    async def close(self) -> None:
        """Close the HTTP client."""
        await self._client.aclose()
```

- [ ] **Step 5: Export from gateway package**

```python
# src/session_scribe/gateway/__init__.py
"""Public API for the LLM Gateway."""

from session_scribe.gateway.llm_gateway import LLMGateway, LLMGatewayError
from session_scribe.gateway.types import LLMRequest, LLMResponse, LLMUsage

__all__ = [
    "LLMGateway",
    "LLMGatewayError",
    "LLMRequest",
    "LLMResponse",
    "LLMUsage",
]
```

- [ ] **Step 6: Run tests to verify they pass**

```bash
uv run pytest tests/gateway/test_llm_gateway.py -v
```

Expected: All tests PASS.

- [ ] **Step 7: Commit**

```bash
git add src/session_scribe/gateway/ tests/gateway/
git commit -m "feat: add LLM Gateway with nano-gpt.com integration, retries, and structured output parsing"
```

---

## Chunk 3: CLI Entry Point + Integration Verification

### Task 7: CLI Entry Point

**Files:**
- Create: `src/session_scribe/cli/main.py`
- Create: `tests/cli/test_main.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/cli/test_main.py
"""Tests for the CLI entry point."""

from typer.testing import CliRunner
from session_scribe.cli.main import app

runner = CliRunner()


class TestCLI:
    def test_help_shows_commands(self):
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "ingest" in result.output
        assert "chat" in result.output
        assert "review" in result.output
        assert "ask" in result.output
        assert "stats" in result.output
        assert "config" in result.output
        assert "reindex" in result.output

    def test_version(self):
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert "0.1.0" in result.output

    def test_ingest_requires_files(self):
        result = runner.invoke(app, ["ingest"])
        assert result.exit_code != 0  # should fail without file arguments

    def test_stats_runs(self):
        result = runner.invoke(app, ["stats"])
        assert result.exit_code == 0
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/cli/test_main.py -v
```

Expected: FAIL.

- [ ] **Step 3: Implement CLI**

```python
# src/session_scribe/cli/main.py
"""Session Scribe CLI — entry point for all user interaction."""

from pathlib import Path
from typing import Annotated, Optional

import typer
from rich.console import Console

app = typer.Typer(
    name="scribe",
    help="D&D Session Scribe — AI-powered campaign note management.",
    no_args_is_help=True,
)
console = Console()


def version_callback(value: bool) -> None:
    if value:
        console.print("session-scribe v0.1.0")
        raise typer.Exit()


@app.callback()
def main(
    version: Annotated[
        Optional[bool],
        typer.Option("--version", "-v", callback=version_callback, is_eager=True),
    ] = None,
) -> None:
    """D&D Session Scribe — AI-powered campaign note management."""


@app.command()
def ingest(
    files: Annotated[
        list[Path],
        typer.Argument(help="PLAUD PDF summary and/or transcript .txt files to ingest."),
    ],
    session_number: Annotated[
        Optional[int],
        typer.Option("--session", "-s", help="Session number. Auto-detected if not provided."),
    ] = None,
) -> None:
    """Ingest PLAUD session files into the campaign vault."""
    console.print(f"[bold]Ingesting {len(files)} file(s)...[/bold]")
    for f in files:
        if not f.exists():
            console.print(f"[red]Error: File not found: {f}[/red]")
            raise typer.Exit(1)
        console.print(f"  - {f.name}")
    # TODO: Wire to ingestion pipeline in Milestone 2
    console.print("[yellow]Ingestion pipeline not yet implemented.[/yellow]")


@app.command()
def chat() -> None:
    """Open interactive campaign Q&A chat."""
    # TODO: Wire to Textual TUI in Milestone 5
    console.print("[yellow]Chat TUI not yet implemented.[/yellow]")


@app.command()
def review() -> None:
    """Run a quality review pass over the vault."""
    # TODO: Wire to reviewer module in Milestone 4
    console.print("[yellow]Reviewer not yet implemented.[/yellow]")


@app.command()
def ask() -> None:
    """Review and answer the agent's pending questions."""
    # TODO: Wire to question queue in Milestone 4
    console.print("[yellow]Question queue not yet implemented.[/yellow]")


@app.command()
def reindex() -> None:
    """Rebuild the vector store index from current vault contents."""
    # TODO: Wire to retrieval layer in Milestone 5
    console.print("[yellow]Reindexing not yet implemented.[/yellow]")


@app.command()
def config() -> None:
    """Show current configuration and verify setup."""
    try:
        from session_scribe.config.settings import Settings

        settings = Settings()  # type: ignore
        console.print("[bold]Session Scribe Configuration[/bold]")
        console.print(f"  Vault path:       {settings.vault_path}")
        console.print(f"  nano-gpt model:   {settings.nanogpt_model}")
        console.print(f"  LM Studio URL:    {settings.lm_studio_base_url}")
        console.print(f"  Embedding model:  {settings.embedding_model}")
        console.print(f"  Log level:        {settings.log_level}")

        if not settings.vault_path.exists():
            console.print(f"\n[yellow]Warning: Vault path does not exist: {settings.vault_path}[/yellow]")
        else:
            console.print(f"\n[green]Vault path exists.[/green]")
    except Exception as e:
        console.print(f"[red]Configuration error: {e}[/red]")
        console.print("\nCopy .env.example to .env and fill in your values:")
        console.print("  cp .env.example .env")
        raise typer.Exit(1)


@app.command()
def stats() -> None:
    """Show LLM usage statistics and cost tracking."""
    # TODO: Wire to LLM Gateway stats in Milestone 2
    console.print("[bold]Session Scribe Stats[/bold]")
    console.print("No usage data yet.")
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/cli/test_main.py -v
```

Expected: All tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/session_scribe/cli/ tests/cli/
git commit -m "feat: add CLI entry point with typer — ingest, chat, review, ask, stats commands"
```

---

### Task 8: Create .env.example and Verify Full Install

**Files:**
- Create: `.env.example`
- Modify: `.gitignore`

- [ ] **Step 1: Create .env.example**

```bash
# .env.example — copy to .env and fill in your values
SCRIBE_VAULT_PATH=/path/to/your/obsidian/campaign/vault
SCRIBE_NANOGPT_API_KEY=your-nanogpt-api-key-here
SCRIBE_NANOGPT_MODEL=chatgpt-4o-latest
SCRIBE_LM_STUDIO_BASE_URL=http://localhost:1234/v1
SCRIBE_EMBEDDING_MODEL=text-embedding-nomic-embed-text-v1.5
SCRIBE_LOG_LEVEL=INFO
```

- [ ] **Step 2: Add .env to .gitignore (already there, verify)**

```bash
grep "^\.env$" .gitignore
```

Expected: `.env` is already in .gitignore.

- [ ] **Step 3: Run the full test suite**

```bash
uv run pytest -v
```

Expected: ALL tests pass.

- [ ] **Step 4: Verify CLI installs and runs**

```bash
uv run scribe --help
uv run scribe --version
```

Expected: Help text shows all commands. Version shows `0.1.0`.

- [ ] **Step 5: Commit**

```bash
git add .env.example .gitignore
git commit -m "chore: add .env.example with config documentation"
```

---

### Task 9: User-Style Testing

This is NOT automated — the developer must manually execute these stories and verify the experience.

- [ ] **Story 1: "I clone the repo and run `uv sync` — does everything install cleanly?"**

```bash
# Simulate fresh install
uv sync
```

Verify: No errors, all dependencies resolve.

- [ ] **Story 2: "I run `scribe --help` — do I see clear, understandable commands?"**

```bash
uv run scribe --help
```

Verify: Output lists all commands (ingest, chat, review, ask, reindex, stats) with clear descriptions. No confusing jargon.

- [ ] **Story 3: "I run `scribe --version` — do I see the version?"**

```bash
uv run scribe --version
```

Verify: Shows `session-scribe v0.1.0`.

- [ ] **Story 4: "I run `scribe ingest nonexistent.pdf` — does it fail clearly?"**

```bash
uv run scribe ingest nonexistent.pdf
```

Verify: Clear error message about file not found. Non-zero exit code.

- [ ] **Story 5: "I misconfigure my .env — does it tell me what's wrong?"**

```bash
# Create .env with missing required field
echo "SCRIBE_VAULT_PATH=/tmp/test" > .env
uv run scribe config
```

Verify: The `config` command loads Settings and shows a clear error about missing `SCRIBE_NANOGPT_API_KEY`. Suggests copying `.env.example`. Not a raw Python traceback.

```bash
# Clean up
rm .env
```

- [ ] **Story 6: Document any issues found, fix them, re-test.**

Log all issues in `context/lessons.md` with today's date.

- [ ] **Step 7: Final commit after fixes**

```bash
git add -A
git commit -m "fix: address user-style testing issues from Milestone 1"
```

(Only if fixes were needed.)

---

## Summary

After completing all tasks, the project has:

- **Package structure:** `src/session_scribe/` with `models/`, `gateway/`, `config/`, `cli/` subpackages
- **15 Pydantic models** covering all entity types, session data, extraction results, quality scores, context bundles, and agent memory
- **LLM Gateway** with nano-gpt.com integration, retries, timeout, structured output parsing
- **Config system** with env var support and sensible defaults
- **CLI entry point** with all commands stubbed (ingest, chat, review, ask, reindex, stats)
- **Full test suite** passing
- **User-style testing** completed

This provides the foundation for Milestone 2 (Ingestion + Extraction) to build on.
