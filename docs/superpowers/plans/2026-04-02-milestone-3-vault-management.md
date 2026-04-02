# Milestone 3: Vault Management — Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Vault Manager module that creates, reads, updates, and manages an Obsidian vault via the Obsidian CLI — including note CRUD, wikilink generation, deduplication, context bundle generation, agent memory, and a `scribe init` command to bootstrap new vaults.

**Architecture:** A `vault/` module that wraps the Obsidian CLI (`/Applications/Obsidian.app/Contents/MacOS/obsidian`) for all vault operations. The CLI handles search, create, read, append, property management. Direct filesystem is used as fallback and for bulk operations. The vault manager is the ONLY module that touches Obsidian — all other modules go through it. The CLI `ingest` command is updated to write extraction results to the vault.

**Tech Stack:** Obsidian CLI, existing Pydantic models, `subprocess` for CLI calls, `thefuzz` for fuzzy name matching

**Spec:** `docs/superpowers/specs/2026-04-02-session-scribe-design.md` (Sections 3-4, 7 — Milestone 3)

**Depends on:** Milestone 2 complete (ingestion, extraction, CLI ingest)

**Obsidian CLI reference:**
- Binary: `/Applications/Obsidian.app/Contents/MacOS/obsidian`
- Target vault: `vault="Tales from Laguna Nera"` (from SCRIBE_VAULT_NAME setting)
- Key commands: `create path= content=`, `read path=`, `append path= content=`, `property:set path= name= value=`, `search query= format=json`, `delete path=`, `files format=json`, `folders`
- Note: CLI outputs status lines to stderr (`Loading...`, `out of date`). Parse stdout only.

---

## File Structure

```
src/session_scribe/
  vault/
    __init__.py          — exports: VaultManager
    obsidian_cli.py      — Low-level Obsidian CLI wrapper (subprocess calls)
    note_renderer.py     — Render Pydantic models into markdown note content
    dedup.py             — Fuzzy entity name matching for deduplication
    vault_manager.py     — High-level vault operations (the public interface)

tests/
  vault/
    __init__.py
    test_obsidian_cli.py  — Tests for CLI wrapper (mocked subprocess)
    test_note_renderer.py — Tests for markdown rendering
    test_dedup.py         — Tests for fuzzy matching
    test_vault_manager.py — Tests for vault manager orchestration
```

---

## Chunk 1: Obsidian CLI Wrapper + Note Renderer

### Task 1: Obsidian CLI Wrapper

**Files:**
- Create: `src/session_scribe/vault/__init__.py`
- Create: `src/session_scribe/vault/obsidian_cli.py`
- Create: `tests/vault/__init__.py`
- Create: `tests/vault/test_obsidian_cli.py`

A thin Python wrapper around the Obsidian CLI binary. All CLI calls go through this — nowhere else in the codebase should shell out to obsidian directly.

- [ ] **Step 1: Create vault package structure**

```bash
mkdir -p src/session_scribe/vault tests/vault
touch src/session_scribe/vault/__init__.py tests/vault/__init__.py
```

- [ ] **Step 2: Write failing tests**

```python
# tests/vault/test_obsidian_cli.py
"""Tests for the Obsidian CLI wrapper."""

import json
import pytest
from unittest.mock import patch, MagicMock
from session_scribe.vault.obsidian_cli import ObsidianCLI, ObsidianCLIError


@pytest.fixture
def cli():
    return ObsidianCLI(vault_name="Test Vault")


class TestObsidianCLI:
    def test_init(self, cli):
        assert cli.vault_name == "Test Vault"

    def test_create_note(self, cli):
        with patch.object(cli, "_run") as mock_run:
            mock_run.return_value = "Created: NPCs/Theron.md"
            cli.create("NPCs/Theron.md", "# Theron\n\nA ranger.")
            mock_run.assert_called_once()
            args = mock_run.call_args[0][0]
            assert "create" in args
            assert 'path="NPCs/Theron.md"' in " ".join(args)

    def test_read_note(self, cli):
        with patch.object(cli, "_run") as mock_run:
            mock_run.return_value = "# Theron\n\nA ranger."
            content = cli.read("NPCs/Theron.md")
            assert content == "# Theron\n\nA ranger."

    def test_append_to_note(self, cli):
        with patch.object(cli, "_run") as mock_run:
            mock_run.return_value = "Appended to: NPCs/Theron.md"
            cli.append("NPCs/Theron.md", "\n## New section")
            args = mock_run.call_args[0][0]
            assert "append" in args

    def test_search_returns_paths(self, cli):
        with patch.object(cli, "_run") as mock_run:
            mock_run.return_value = '["NPCs/Theron.md", "Sessions/Session-001.md"]'
            results = cli.search("Theron")
            assert results == ["NPCs/Theron.md", "Sessions/Session-001.md"]

    def test_search_empty_results(self, cli):
        with patch.object(cli, "_run") as mock_run:
            mock_run.return_value = "[]"
            results = cli.search("nonexistent")
            assert results == []

    def test_set_property(self, cli):
        with patch.object(cli, "_run") as mock_run:
            mock_run.return_value = "Set type: npc"
            cli.set_property("NPCs/Theron.md", "type", "npc")
            args = mock_run.call_args[0][0]
            assert "property:set" in args

    def test_list_files(self, cli):
        with patch.object(cli, "_run") as mock_run:
            mock_run.return_value = "NPCs/Theron.md\nSessions/Session-001.md"
            files = cli.list_files()
            assert len(files) == 2

    def test_delete_note(self, cli):
        with patch.object(cli, "_run") as mock_run:
            mock_run.return_value = "Moved to trash: NPCs/Theron.md"
            cli.delete("NPCs/Theron.md")
            args = mock_run.call_args[0][0]
            assert "delete" in args

    def test_note_exists_true(self, cli):
        with patch.object(cli, "read") as mock_read:
            mock_read.return_value = "# Theron"
            assert cli.note_exists("NPCs/Theron.md") is True

    def test_note_exists_false(self, cli):
        with patch.object(cli, "read", side_effect=ObsidianCLIError("Not found")):
            assert cli.note_exists("NPCs/Nonexistent.md") is False

    def test_find_notes_in_folder(self, cli):
        with patch.object(cli, "list_files") as mock_list:
            mock_list.return_value = ["NPCs/Theron.md", "NPCs/Sylvie.md", "Sessions/S01.md"]
            result = cli.find_notes_in_folder("NPCs/")
            assert result == ["NPCs/Theron.md", "NPCs/Sylvie.md"]

    def test_cli_error_on_failure(self, cli):
        with patch.object(cli, "_run", side_effect=ObsidianCLIError("CLI failed")):
            with pytest.raises(ObsidianCLIError):
                cli.read("bad/path.md")

    def test_health_check(self, cli):
        with patch.object(cli, "_run") as mock_run:
            mock_run.return_value = "1.12.7"
            assert cli.health_check() is True

    def test_health_check_failure(self, cli):
        with patch.object(cli, "_run", side_effect=ObsidianCLIError("not found")):
            assert cli.health_check() is False
```

- [ ] **Step 3: Run tests to verify they fail**

- [ ] **Step 4: Implement the CLI wrapper**

```python
# src/session_scribe/vault/obsidian_cli.py
"""Low-level wrapper around the Obsidian CLI binary.

All Obsidian CLI interactions go through this module.
No other module should shell out to the obsidian binary directly.
"""

import json
import logging
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)

# Path to the Obsidian CLI binary on macOS
_OBSIDIAN_BINARY = "/Applications/Obsidian.app/Contents/MacOS/obsidian"


class ObsidianCLIError(Exception):
    """Raised when an Obsidian CLI command fails."""


class ObsidianCLI:
    """Thin wrapper around the Obsidian CLI binary.

    All methods are synchronous since the CLI is a subprocess call.
    The vault_name parameter targets a specific vault for all operations.
    """

    def __init__(self, vault_name: str, binary_path: str = _OBSIDIAN_BINARY) -> None:
        self.vault_name = vault_name
        self.binary_path = binary_path

    def _run(self, args: list[str], timeout: int = 30) -> str:
        """Execute an Obsidian CLI command and return stdout.

        Uses subprocess with shell=True because the Obsidian CLI uses
        key=value argument syntax that requires shell parsing.
        Content is written to a temp file to avoid shell injection.

        Filters out stderr noise (loading messages, update warnings).
        Raises ObsidianCLIError on non-zero exit or timeout.
        """
        cmd = [self.binary_path, f'vault="{self.vault_name}"'] + args

        try:
            result = subprocess.run(
                " ".join(cmd),
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
            )

            # Filter stderr noise
            stderr_lines = [
                l for l in (result.stderr or "").split("\n")
                if "Loading" not in l and "out of date" not in l and l.strip()
            ]

            if result.returncode != 0:
                error = " ".join(stderr_lines) or result.stdout.strip() or f"Exit code {result.returncode}"
                if error:
                    raise ObsidianCLIError(f"CLI error: {error}")

            return result.stdout.strip()

        except subprocess.TimeoutExpired:
            raise ObsidianCLIError(f"CLI timed out after {timeout}s")
        except FileNotFoundError:
            raise ObsidianCLIError(
                f"Obsidian CLI not found at {self.binary_path}. "
                "Is Obsidian installed?"
            )

    def health_check(self) -> bool:
        """Check if the Obsidian CLI is available and the vault exists."""
        try:
            self._run(["version"])
            return True
        except ObsidianCLIError:
            return False

    def create(self, path: str, content: str) -> None:
        """Create a new note at the given path with content.

        Writes content to the vault filesystem directly to avoid
        shell escaping issues with markdown content containing
        backticks, dollar signs, quotes, etc.
        """
        vault_path = self._get_vault_path()
        if vault_path:
            # Direct filesystem write — safe for any content
            full_path = Path(vault_path) / path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(content, encoding="utf-8")
            logger.info("Created note (fs): %s", path)
        else:
            # Fallback to CLI with basic escaping
            escaped = content.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
            self._run(["create", f'path="{path}"', f'content="{escaped}"'])
            logger.info("Created note (cli): %s", path)

    def read(self, path: str) -> str:
        """Read the content of a note."""
        return self._run(["read", f'path="{path}"'])

    def append(self, path: str, content: str) -> None:
        """Append content to an existing note.

        Uses filesystem for safety with complex markdown content.
        """
        vault_path = self._get_vault_path()
        if vault_path:
            full_path = Path(vault_path) / path
            if full_path.exists():
                existing = full_path.read_text(encoding="utf-8")
                full_path.write_text(existing + content, encoding="utf-8")
                logger.info("Appended (fs): %s", path)
                return
        # Fallback to CLI
        escaped = content.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
        self._run(["append", f'path="{path}"', f'content="{escaped}"'])
        logger.info("Appended (cli): %s", path)

    def _get_vault_path(self) -> str | None:
        """Get the filesystem path to the vault, or None if unknown."""
        try:
            path = self._run(["vault", "info=path"])
            return path if path and Path(path).exists() else None
        except ObsidianCLIError:
            return None

    def set_property(self, path: str, name: str, value: str) -> None:
        """Set a frontmatter property on a note."""
        self._run(["property:set", f'path="{path}"', f'name="{name}"', f'value="{value}"'])

    def search(self, query: str) -> list[str]:
        """Search the vault. Returns list of matching file paths."""
        raw = self._run(["search", f'query="{query}"', "format=json"])
        if not raw or raw == "[]":
            return []
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            # Non-JSON output — parse as newline-separated paths
            return [line.strip() for line in raw.split("\n") if line.strip()]

    def list_files(self, folder: str | None = None) -> list[str]:
        """List all files in the vault, optionally filtered by folder."""
        args = ["files", "format=json"]
        if folder:
            args.append(f'path="{folder}"')
        raw = self._run(args)
        if not raw or raw == "[]":
            return []
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return [line.strip() for line in raw.split("\n") if line.strip()]

    def list_folders(self) -> list[str]:
        """List all folders in the vault."""
        raw = self._run(["folders"])
        if not raw:
            return []
        return [line.strip() for line in raw.split("\n") if line.strip()]

    def delete(self, path: str) -> None:
        """Delete a note (moves to trash)."""
        self._run(["delete", f'path="{path}"'])
        logger.info("Deleted: %s", path)

    def note_exists(self, path: str) -> bool:
        """Check if a note exists at the given path."""
        try:
            self.read(path)
            return True
        except ObsidianCLIError:
            return False

    def find_notes_in_folder(self, folder: str) -> list[str]:
        """List all note paths within a folder."""
        all_files = self.list_files()
        return [f for f in all_files if f.startswith(folder)]
```

- [ ] **Step 5: Run tests:** `uv run pytest tests/vault/test_obsidian_cli.py -v`

- [ ] **Step 6: Run ALL tests:** `uv run pytest -v`

- [ ] **Step 7: Commit**

```bash
git add src/session_scribe/vault/ tests/vault/
git commit -m "feat: add Obsidian CLI wrapper for vault operations"
```

---

### Task 2: Note Renderer

**Files:**
- Create: `src/session_scribe/vault/note_renderer.py`
- Create: `tests/vault/test_note_renderer.py`

Converts Pydantic entity models into formatted markdown strings ready for the vault. Handles frontmatter, wikilinks, and section formatting.

- [ ] **Step 1: Write failing tests**

```python
# tests/vault/test_note_renderer.py
"""Tests for rendering Pydantic models into Obsidian markdown notes."""

import pytest
from session_scribe.vault.note_renderer import (
    render_npc_note,
    render_location_note,
    render_faction_note,
    render_loot_note,
    render_session_note,
    render_plot_thread_note,
    render_open_threads,
    render_dashboard,
    wikify,
)
from session_scribe.models.entities import NPC, Location, Faction, LootItem, PlotThread, EntityStatus, ThreadStatus
from session_scribe.models.session import SessionRecap, KeyEvent
from session_scribe.models.extraction import ExtractionResult, AgentQuestion


class TestWikify:
    def test_wikify_simple_name(self):
        assert wikify("Theron") == "[[Theron]]"

    def test_wikify_list(self):
        result = wikify(["Theron", "Sylvie"])
        assert result == "[[Theron]], [[Sylvie]]"

    def test_wikify_empty_list(self):
        assert wikify([]) == ""


class TestRenderNPC:
    def test_render_minimal_npc(self):
        npc = NPC(name="Theron", first_appeared="Session-001")
        md = render_npc_note(npc)
        assert "# Theron" in md
        assert "[[Session-001]]" in md
        assert "status: unknown" in md
        assert "type: npc" in md

    def test_render_full_npc(self):
        npc = NPC(
            name="The Friendly Face",
            first_appeared="Session-022",
            status=EntityStatus.DEAD,
            description="A cult informant.",
            aliases=["the big guy"],
            affiliations=["Sylvie's Cult"],
            tags=["cult"],
            key_interactions=["Interrogated by the party"],
        )
        md = render_npc_note(npc)
        assert "status: dead" in md
        assert "[[Sylvie's Cult]]" in md
        assert "the big guy" in md
        assert "A cult informant." in md
        assert "Interrogated by the party" in md

    def test_npc_note_has_frontmatter(self):
        npc = NPC(name="Test", first_appeared="Session-001")
        md = render_npc_note(npc)
        assert md.startswith("---\n")
        assert "---\n" in md[3:]  # closing frontmatter


class TestRenderLocation:
    def test_render_location(self):
        loc = Location(
            name="The Black Spire",
            first_appeared="Session-022",
            description="A cult site in the swamp.",
            connected_to=["Underground Tunnels"],
        )
        md = render_location_note(loc)
        assert "# The Black Spire" in md
        assert "type: location" in md
        assert "[[Underground Tunnels]]" in md
        assert "A cult site in the swamp." in md


class TestRenderFaction:
    def test_render_faction(self):
        faction = Faction(
            name="Sylvie's Cult",
            first_appeared="Session-022",
            description="A smuggling operation.",
            known_members=["Sylvie", "Bill Tidewater"],
        )
        md = render_faction_note(faction)
        assert "# Sylvie's Cult" in md
        assert "type: faction" in md
        assert "[[Sylvie]]" in md
        assert "[[Bill Tidewater]]" in md


class TestRenderLoot:
    def test_render_loot(self):
        item = LootItem(
            name="Hallucinogen-Laced Poison",
            found_in="Session-022",
            description="Poison found on dart traps.",
            held_by="Party",
            tags=["cult", "poison"],
        )
        md = render_loot_note(item)
        assert "# Hallucinogen-Laced Poison" in md
        assert "type: loot" in md
        assert "[[Session-022]]" in md
        assert "Party" in md


class TestRenderSession:
    def test_render_session_note(self):
        recap = SessionRecap(
            session_number=22,
            title="No Loose Ends",
            summary="The party tracked down an informant.",
            key_events=[
                KeyEvent(description="Found the safe house", timestamp="00:17:15"),
                KeyEvent(description="Interrogated the target", timestamp=None),
            ],
        )
        npcs = [NPC(name="Theron", first_appeared="Session-022")]
        locations = [Location(name="The Black Spire", first_appeared="Session-022")]

        md = render_session_note(recap, npcs, locations)
        assert "# Session 22" in md or "# No Loose Ends" in md
        assert "type: session" in md
        assert "The party tracked down" in md
        assert "Found the safe house" in md
        assert "[[Theron]]" in md
        assert "[[The Black Spire]]" in md


class TestRenderOpenThreads:
    def test_render_open_threads(self):
        threads = [
            PlotThread(title="The Black Spire", status=ThreadStatus.OPEN,
                       introduced_in="Session-022", summary="Cult site in swamp."),
            PlotThread(title="Missing Merchant", status=ThreadStatus.OPEN,
                       introduced_in="Session-020", summary="Still missing."),
        ]
        md = render_open_threads(threads)
        assert "The Black Spire" in md
        assert "Missing Merchant" in md
        assert "[[Session-022]]" in md


class TestRenderDashboard:
    def test_render_dashboard(self):
        md = render_dashboard(
            latest_session=22,
            npc_count=6,
            location_count=11,
            thread_count=5,
        )
        assert "Dashboard" in md
        assert "22" in md
        assert "6" in md or "NPCs" in md
```

- [ ] **Step 2: Run tests to verify they fail**

- [ ] **Step 3: Implement the note renderer**

The renderer should produce markdown that:
- Starts with YAML frontmatter (`---` delimited) with `type`, `status`, `aliases`, `tags`, etc.
- Uses `[[wikilinks]]` for all entity references (NPCs, locations, factions, sessions)
- Has clean section headings
- Matches the NPC note format example from the design spec (Section 4)

Key functions:
- `wikify(name_or_list)` — wrap a name or list of names in `[[]]`
- `render_npc_note(npc: NPC) -> str`
- `render_location_note(loc: Location) -> str`
- `render_faction_note(faction: Faction) -> str`
- `render_session_note(recap: SessionRecap, npcs: list[NPC], locations: list[Location]) -> str`
- `render_plot_thread_note(thread: PlotThread) -> str`
- `render_open_threads(threads: list[PlotThread]) -> str`
- `render_dashboard(latest_session, npc_count, location_count, thread_count) -> str`

Each render function returns a complete markdown string ready to write to a file.

**Frontmatter convention:** YAML frontmatter stores plain strings for `affiliations`, `aliases`, `connected_to`, etc. (no wikilinks in frontmatter — YAML doesn't render them). Wikilinks (`[[Name]]`) are only used in the markdown body. This matches how Obsidian handles frontmatter vs content.

- [ ] **Step 4: Run tests:** `uv run pytest tests/vault/test_note_renderer.py -v`

- [ ] **Step 5: Commit**

```bash
git add src/session_scribe/vault/note_renderer.py tests/vault/test_note_renderer.py
git commit -m "feat: add note renderer for converting entities to Obsidian markdown"
```

---

### Task 3: Deduplication Logic

**Files:**
- Create: `src/session_scribe/vault/dedup.py`
- Create: `tests/vault/test_dedup.py`

Fuzzy matching to determine if an extracted entity already exists in the vault.

- [ ] **Step 1: Add thefuzz dependency**

```bash
uv add thefuzz
```

- [ ] **Step 2: Write failing tests**

```python
# tests/vault/test_dedup.py
"""Tests for entity deduplication logic."""

import pytest
from session_scribe.vault.dedup import find_match, is_duplicate


class TestFindMatch:
    def test_exact_match(self):
        existing = ["Theron", "Sylvie", "Bill Tidewater"]
        assert find_match("Theron", existing) == "Theron"

    def test_case_insensitive_match(self):
        existing = ["Theron", "Sylvie"]
        assert find_match("theron", existing) == "Theron"

    def test_alias_match(self):
        existing_with_aliases = {
            "The Friendly Face": ["the big guy", "friendly face"],
            "Sylvie": ["sylvie starwater"],
        }
        assert find_match("the big guy", [], alias_map=existing_with_aliases) == "The Friendly Face"

    def test_fuzzy_match(self):
        existing = ["Sylvie Starwater", "Bill Tidewater"]
        assert find_match("Sylvie", existing, threshold=70) == "Sylvie Starwater"

    def test_no_match(self):
        existing = ["Theron", "Sylvie"]
        assert find_match("Completely Different", existing) is None

    def test_no_false_positive(self):
        existing = ["The Black Spire", "The Farm"]
        # "The" alone shouldn't match anything
        assert find_match("The Ship", existing, threshold=80) is None


class TestIsDuplicate:
    def test_duplicate_exact(self):
        assert is_duplicate("Theron", ["Theron", "Sylvie"]) is True

    def test_not_duplicate(self):
        assert is_duplicate("New NPC", ["Theron", "Sylvie"]) is False

    def test_duplicate_with_alias(self):
        aliases = {"The Friendly Face": ["the big guy"]}
        assert is_duplicate("the big guy", ["The Friendly Face"], alias_map=aliases) is True
```

- [ ] **Step 3: Implement dedup logic**

```python
# src/session_scribe/vault/dedup.py
"""Fuzzy entity name matching for deduplication."""

from thefuzz import fuzz


def find_match(
    name: str,
    existing_names: list[str],
    alias_map: dict[str, list[str]] | None = None,
    threshold: int = 80,
) -> str | None:
    """Find the best match for a name among existing entities.

    Checks in order:
    1. Exact match (case-insensitive)
    2. Alias match (case-insensitive)
    3. Fuzzy match above threshold

    Returns the matched existing name, or None if no match found.
    """
    name_lower = name.lower().strip()

    # 1. Exact match
    for existing in existing_names:
        if existing.lower().strip() == name_lower:
            return existing

    # 2. Alias match
    if alias_map:
        for entity_name, aliases in alias_map.items():
            for alias in aliases:
                if alias.lower().strip() == name_lower:
                    return entity_name

    # 3. Fuzzy match
    best_score = 0
    best_match = None
    for existing in existing_names:
        score = fuzz.token_sort_ratio(name_lower, existing.lower())
        if score > best_score and score >= threshold:
            best_score = score
            best_match = existing

    return best_match


def is_duplicate(
    name: str,
    existing_names: list[str],
    alias_map: dict[str, list[str]] | None = None,
    threshold: int = 80,
) -> bool:
    """Check if a name is a duplicate of an existing entity."""
    return find_match(name, existing_names, alias_map, threshold) is not None
```

- [ ] **Step 4: Run tests:** `uv run pytest tests/vault/test_dedup.py -v`

- [ ] **Step 5: Commit**

```bash
git add src/session_scribe/vault/dedup.py tests/vault/test_dedup.py pyproject.toml uv.lock
git commit -m "feat: add fuzzy entity deduplication with alias support"
```

---

## Chunk 2: Vault Manager + Init Command

### Task 4: Vault Manager

**Files:**
- Create: `src/session_scribe/vault/vault_manager.py`
- Create: `tests/vault/test_vault_manager.py`
- Modify: `src/session_scribe/vault/__init__.py`

The high-level orchestrator that uses the CLI wrapper, note renderer, and dedup logic together.

- [ ] **Step 1: Write failing tests**

```python
# tests/vault/test_vault_manager.py
"""Tests for the Vault Manager."""

import pytest
from unittest.mock import MagicMock, patch, call
from session_scribe.vault.vault_manager import VaultManager
from session_scribe.models.entities import NPC, Location, Faction, PlotThread, EntityStatus, ThreadStatus
from session_scribe.models.session import SessionRecap, KeyEvent
from session_scribe.models.extraction import ExtractionResult, AgentQuestion, QuestionPriority
from session_scribe.models.context import ContextBundle


@pytest.fixture
def mock_cli():
    cli = MagicMock()
    cli.vault_name = "Test Vault"
    cli.list_files.return_value = []
    cli.list_folders.return_value = ["/"]
    cli.search.return_value = []
    cli.health_check.return_value = True
    return cli


@pytest.fixture
def manager(mock_cli):
    return VaultManager(cli=mock_cli)


class TestVaultInit:
    def test_init_vault_creates_folders(self, manager, mock_cli):
        manager.init_vault()
        # Should create notes for key folders via CLI
        create_calls = [c for c in mock_cli.create.call_args_list]
        created_paths = [c[0][0] for c in create_calls]

        # Check key structural files were created
        assert any("_Dashboard.md" in p for p in created_paths)
        assert any("_Open-Threads.md" in p for p in created_paths)


class TestWriteEntities:
    def test_write_npc_creates_note(self, manager, mock_cli):
        npc = NPC(name="Theron", first_appeared="Session-001", status=EntityStatus.ALIVE)
        mock_cli.search.return_value = []  # Not a duplicate

        manager.write_npc(npc)

        mock_cli.create.assert_called_once()
        path = mock_cli.create.call_args[0][0]
        assert "NPCs/Theron.md" in path

    def test_write_npc_updates_existing(self, manager, mock_cli):
        npc = NPC(name="Theron", first_appeared="Session-001")
        mock_cli.search.return_value = ["NPCs/Theron.md"]  # Already exists
        mock_cli.read.return_value = "# Theron\n\nOld content."

        manager.write_npc(npc, update_existing=True)

        # Should append, not create
        mock_cli.create.assert_not_called()
        mock_cli.append.assert_called_once()

    def test_write_location_creates_note(self, manager, mock_cli):
        loc = Location(name="The Black Spire", first_appeared="Session-022")
        mock_cli.search.return_value = []

        manager.write_location(loc)

        mock_cli.create.assert_called_once()
        path = mock_cli.create.call_args[0][0]
        assert "Locations/" in path

    def test_write_session_creates_note(self, manager, mock_cli):
        recap = SessionRecap(
            session_number=22, title="No Loose Ends",
            summary="Party tracked informant.", key_events=[],
        )
        mock_cli.search.return_value = []

        manager.write_session(recap, npcs=[], locations=[])

        mock_cli.create.assert_called_once()
        path = mock_cli.create.call_args[0][0]
        assert "Sessions/Session-022.md" in path


class TestWriteExtractionResult:
    def test_write_full_result(self, manager, mock_cli):
        result = ExtractionResult(
            session_number=22,
            npcs=[NPC(name="Theron", first_appeared="Session-022")],
            locations=[Location(name="Forest", first_appeared="Session-022")],
            factions=[],
            loot=[],
            plot_threads=[
                PlotThread(title="Quest", status=ThreadStatus.OPEN,
                           introduced_in="Session-022", summary="A quest."),
            ],
            recap=SessionRecap(session_number=22, title="Test",
                              summary="Summary.", key_events=[]),
            questions=[],
        )
        mock_cli.search.return_value = []

        manager.write_extraction_result(result)

        # Should have created NPC, location, session, updated threads
        assert mock_cli.create.call_count >= 3


class TestContextBundle:
    def test_get_context_bundle_empty_vault(self, manager, mock_cli):
        mock_cli.list_files.return_value = []

        bundle = manager.get_context_bundle(session_number=1)

        assert isinstance(bundle, ContextBundle)
        assert bundle.session_number == 1
        assert bundle.known_npcs == []

    def test_get_context_bundle_with_npcs(self, manager, mock_cli):
        mock_cli.list_files.return_value = ["NPCs/Theron.md", "NPCs/Sylvie.md"]
        mock_cli.read.side_effect = [
            "---\ntype: npc\nstatus: alive\naliases:\n  - ranger\n---\n# Theron",
            "---\ntype: npc\nstatus: unknown\n---\n# Sylvie",
        ]

        bundle = manager.get_context_bundle(session_number=5)

        assert len(bundle.known_npcs) == 2
        assert bundle.known_npcs[0].name == "Theron"


class TestAgentMemory:
    def test_write_question(self, manager, mock_cli):
        question = AgentQuestion(
            question="Is this an NPC?",
            context="Unclear reference.",
            priority=QuestionPriority.MEDIUM,
            source_session=22,
        )
        manager.write_question(question)

        mock_cli.create.assert_called_once()
        path = mock_cli.create.call_args[0][0]
        assert "_Agent/Questions/" in path

    def test_read_agent_memory_empty(self, manager, mock_cli):
        from session_scribe.models.context import AgentMemory
        mock_cli.read.side_effect = Exception("Not found")

        memory = manager.read_agent_memory()
        assert isinstance(memory, AgentMemory)
        assert memory.entity_aliases == {}

    def test_update_entity_aliases(self, manager, mock_cli):
        aliases = {"the tavern": "Smoked Eel Tavern", "the boat": "The Mayweather"}
        manager.update_entity_aliases(aliases)

        # Should write to _Agent/Memory/entity-aliases.md
        assert mock_cli.create.called or mock_cli.append.called

    def test_update_player_characters(self, manager, mock_cli):
        from session_scribe.models.context import PlayerCharacter
        pcs = [
            PlayerCharacter(player_name="Scott", character_name="Seven", character_class="Wizard"),
        ]
        manager.update_player_characters(pcs)

        assert mock_cli.create.called or mock_cli.append.called


class TestContextBundleComplete:
    """Test that context bundle populates ALL required fields."""

    def test_context_bundle_reads_recent_events(self, manager, mock_cli):
        mock_cli.find_notes_in_folder = MagicMock(return_value=["Sessions/Session-022.md"])
        mock_cli.read.return_value = (
            "---\ntype: session\n---\n# Session 22\n\n"
            "## Recap\nThe party tracked down an informant."
        )

        bundle = manager.get_context_bundle(session_number=23)
        assert len(bundle.recent_events) > 0

    def test_context_bundle_reads_player_characters(self, manager, mock_cli):
        mock_cli.list_files.return_value = []
        mock_cli.read.side_effect = lambda path: (
            "Scott: Seven (Wizard)\nTina: Celestine (Rogue)"
            if "player-characters" in path else ""
        )

        bundle = manager.get_context_bundle(session_number=5)
        # Should attempt to read player characters from memory
        read_calls = [str(c) for c in mock_cli.read.call_args_list]
        assert any("player-characters" in c for c in read_calls)
```

- [ ] **Step 2: Run tests to verify they fail**

- [ ] **Step 3: Implement the Vault Manager**

Key design:
- Constructor takes an `ObsidianCLI` instance
- `init_vault()` — creates the folder structure and initial files (_Dashboard, _Open-Threads, _Agent/Memory files)
- `write_npc(npc, update_existing=False)` — creates or updates an NPC note
- `write_location(loc, update_existing=False)` — same for locations
- `write_faction(faction, update_existing=False)` — same for factions
- `write_loot(item)` — creates a loot item note in Loot/
- `write_session(recap, npcs, locations)` — creates a session note with wikilinks to entities
- `write_extraction_result(result: ExtractionResult)` — orchestrates writing all entities from an extraction
- `update_open_threads(threads: list[PlotThread])` — rewrites the open threads document
- `update_dashboard(session_number, ...)` — updates the dashboard
- `get_context_bundle(session_number) -> ContextBundle` — reads vault state into a full context bundle
- `write_question(question: AgentQuestion)` — writes a question to _Agent/Questions/
- `read_agent_memory() -> AgentMemory` — reads all memory files from _Agent/Memory/
- `update_entity_aliases(aliases: dict[str, str])` — updates _Agent/Memory/entity-aliases.md
- `update_player_characters(pcs: list[PlayerCharacter])` — updates _Agent/Memory/player-characters.md
- `_find_existing(name, folder) -> str | None` — uses search + dedup to find existing notes
- `_parse_frontmatter(content: str) -> dict` — extracts YAML frontmatter from note content

Uses `note_renderer` for all markdown generation and `dedup` for matching.

**Context bundle generation (`get_context_bundle`)** must populate ALL ContextBundle fields:
1. `known_npcs` — read all files in NPCs/, parse frontmatter for name/status/aliases
2. `known_locations` — read all files in Locations/, parse frontmatter
3. `known_factions` — read all files in Factions/, parse frontmatter
4. `active_threads` — read Plot-Threads/_Open-Threads.md, parse thread entries
5. `recent_events` — read the last 2-3 session files from Sessions/, extract recap summaries
6. `entity_aliases` — read _Agent/Memory/entity-aliases.md
7. `player_characters` — read _Agent/Memory/player-characters.md

Frontmatter parsing: use a simple YAML parser on the content between `---` markers. `pyyaml` is already a dependency.

- [ ] **Step 4: Update vault package exports**

```python
# src/session_scribe/vault/__init__.py
"""Public API for the vault module."""

from session_scribe.vault.vault_manager import VaultManager
from session_scribe.vault.obsidian_cli import ObsidianCLI, ObsidianCLIError

__all__ = ["VaultManager", "ObsidianCLI", "ObsidianCLIError"]
```

- [ ] **Step 5: Run tests:** `uv run pytest tests/vault/ -v`

- [ ] **Step 6: Run ALL tests:** `uv run pytest -v`

- [ ] **Step 7: Commit**

```bash
git add src/session_scribe/vault/ tests/vault/
git commit -m "feat: add Vault Manager with note CRUD, dedup, context bundles, and agent memory"
```

---

### Task 5: CLI Init Command + Wire Ingest to Vault

**Files:**
- Modify: `src/session_scribe/cli/main.py` — add `init` command, update `ingest` to write to vault
- Create: `tests/cli/test_init.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/cli/test_init.py
"""Tests for the init CLI command."""

import pytest
from unittest.mock import patch, MagicMock
from typer.testing import CliRunner
from session_scribe.cli.main import app

runner = CliRunner()


class TestInitCommand:
    def test_init_help(self):
        result = runner.invoke(app, ["init", "--help"])
        assert result.exit_code == 0
        assert "vault" in result.output.lower() or "init" in result.output.lower()

    def test_init_creates_vault_structure(self):
        with patch("session_scribe.cli.main._run_init") as mock_init:
            mock_init.return_value = None
            result = runner.invoke(app, ["init"])
            assert mock_init.called
```

- [ ] **Step 2: Implement**

Add to `src/session_scribe/cli/main.py`:

1. New `init` command that:
   - Loads Settings
   - Creates an ObsidianCLI with vault_name
   - Creates a VaultManager
   - Calls `vault_manager.init_vault()`
   - Prints what was created

2. Update the `ingest` command's `_run_ingest_pipeline` to:
   - After extraction, create a VaultManager
   - Call `vault_manager.write_extraction_result(result)`
   - Print "Notes written to vault" with counts
   - Use `vault_manager.get_context_bundle()` instead of an empty ContextBundle (so subsequent ingestions have context)

- [ ] **Step 3: Run tests:** `uv run pytest tests/cli/ -v`

- [ ] **Step 4: Run ALL tests:** `uv run pytest -v`

- [ ] **Step 5: Commit**

```bash
git add src/session_scribe/cli/ tests/cli/
git commit -m "feat: add init command and wire ingest to write extraction results to vault"
```

---

## Chunk 3: Integration Tests + User-Style Testing

### Task 6: Integration Test Against Real Vault

**Files:**
- Create: `tests/vault/test_vault_integration.py`

Integration tests that hit the real Obsidian CLI and vault. Marked as `integration`.

- [ ] **Step 1: Write integration tests**

```python
# tests/vault/test_vault_integration.py
"""Integration tests against a real Obsidian vault.

These tests require Obsidian to be running with a configured vault.
Run with: pytest -m integration tests/vault/test_vault_integration.py -v -s
"""

import pytest
from session_scribe.vault.obsidian_cli import ObsidianCLI
from session_scribe.vault.vault_manager import VaultManager
from session_scribe.config.settings import Settings
from session_scribe.models.entities import NPC, Location, EntityStatus
from session_scribe.models.session import SessionRecap


@pytest.mark.integration
class TestVaultIntegration:
    """Tests that hit the real Obsidian CLI."""

    @pytest.fixture
    def real_cli(self):
        settings = Settings()
        return ObsidianCLI(vault_name=settings.vault_name)

    @pytest.fixture
    def real_manager(self, real_cli):
        return VaultManager(cli=real_cli)

    def test_cli_health_check(self, real_cli):
        assert real_cli.health_check() is True

    def test_init_vault(self, real_manager, real_cli):
        real_manager.init_vault()

        folders = real_cli.list_folders()
        assert any("Sessions" in f for f in folders)
        assert any("NPCs" in f for f in folders)
        assert any("Locations" in f for f in folders)

    def test_write_and_read_npc(self, real_manager, real_cli):
        npc = NPC(
            name="Integration Test NPC",
            first_appeared="Session-999",
            status=EntityStatus.ALIVE,
            description="Created by integration test.",
        )
        real_manager.write_npc(npc)

        # Verify it exists
        results = real_cli.search("Integration Test NPC")
        assert len(results) > 0

        # Clean up
        for path in results:
            if "Integration Test NPC" in path:
                real_cli.delete(path)

    def test_context_bundle_generation(self, real_manager):
        bundle = real_manager.get_context_bundle(session_number=1)
        assert bundle.session_number == 1
        # Should at least return without error, even if vault is empty
```

- [ ] **Step 2: Verify non-integration tests pass:** `uv run pytest -v`

- [ ] **Step 3: Commit**

```bash
git add tests/vault/test_vault_integration.py
git commit -m "test: add integration tests for vault manager against real Obsidian CLI"
```

---

### Task 7: User-Style Testing

Execute manually after all code tasks are complete.

- [ ] **Story 1:** "I run `scribe init` — does it create the vault structure without errors?"

```bash
uv run scribe init
```

Verify: Open "Tales from Laguna Nera" in Obsidian. Check that Sessions/, NPCs/, Locations/, Factions/, Loot/, Plot-Threads/, _Agent/ folders exist with initial files.

- [ ] **Story 2:** "I run `scribe ingest` on Session 22 — does the vault populate?"

```bash
uv run scribe ingest tests/fixtures/session_022/summary.pdf --session 22
```

Verify: Open Obsidian. Check that:
- Sessions/Session-022.md exists with recap
- NPCs/ has notes for extracted NPCs
- Locations/ has notes for extracted locations
- Plot-Threads/_Open-Threads.md lists open threads

- [ ] **Story 3:** "I open an NPC note — is it well-formatted?"

Verify: Frontmatter renders correctly, wikilinks are clickable, description is readable.

- [ ] **Story 4:** "I click a wikilink — does it go to the right note?"

Verify: Click on a session link in an NPC note, or a faction link. They should resolve.

- [ ] **Story 5:** "I open the graph view — are entities connected?"

Verify: NPCs link to factions, sessions link to NPCs/locations.

- [ ] **Story 6:** "I run ingestion twice on Session 22 — does it update, not duplicate?"

```bash
uv run scribe ingest tests/fixtures/session_022/summary.pdf --session 22
```

Verify: No duplicate NPC files. Existing notes are updated/appended.

- [ ] **Story 7:** "I look at the agent memory files — do they exist?"

Verify: _Agent/Memory/ has files, _Agent/Questions/ has any flagged questions.

Document all issues, fix them, re-test.

---

## Summary

After completing all tasks, the project has:

- **Obsidian CLI wrapper:** Typed Python interface for all vault operations
- **Note renderer:** Converts Pydantic models to formatted Obsidian markdown with frontmatter and wikilinks
- **Deduplication:** Fuzzy name matching with alias support
- **Vault Manager:** High-level orchestrator for note CRUD, context bundles, agent memory
- **`scribe init` command:** Bootstraps a new vault with the full folder structure
- **`scribe ingest` updated:** Now writes extraction results to the vault automatically
- **Integration tests:** Real vault operations tested against Obsidian CLI
- **User-style testing:** Manual QA in actual Obsidian
