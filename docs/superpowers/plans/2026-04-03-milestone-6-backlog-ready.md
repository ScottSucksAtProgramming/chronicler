# Milestone 6: Backlog-Ready — Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Player Character management, auto-reindex after ingest, quality metrics tracking, and chat-based corrections — making the system ready for Scott to interactively process the 22-session backlog with the agent.

**Architecture:** A new `Party/` folder in the vault for PC notes. A `scribe party` command to configure player characters (which feeds into extraction context so PCs aren't extracted as NPCs). Auto-reindex after each ingest so chat is always current. Quality metrics logged per session. Chat supports correction commands to update vault content.

**Tech Stack:** Existing modules (vault manager, extraction, retrieval, chat), minor additions

**Spec:** `docs/superpowers/specs/2026-04-02-session-scribe-design.md` (Section 7 — Milestone 6)

**Depends on:** Milestone 5 complete (retrieval + chat working)

**Key insight:** The backlog won't be batch-processed automatically. Scott will work WITH the agent — ingesting sessions one at a time from various sources (old vault, transcripts, notes), providing extra context, and answering questions. The code needs to support this interactive workflow.

---

## File Structure

```
src/session_scribe/
  vault/
    vault_manager.py     — Add PC management methods, auto-reindex hook
    note_renderer.py     — Add render_pc_note
  cli/
    main.py              — Add `party` command, update `ingest` for auto-reindex
  retrieval/
    indexer.py           — (no changes, already supports reindex)
  chat/
    app.py               — Add correction commands (/correct, /alias, /forget)

tests/
  vault/
    test_pc_management.py
  cli/
    test_party.py
```

---

## Chunk 1: Player Character Management

### Task 1: PC Note Renderer + Vault Manager Methods

**Files:**
- Modify: `src/session_scribe/vault/note_renderer.py` — add `render_pc_note`
- Modify: `src/session_scribe/vault/vault_manager.py` — add PC write/read methods, update `init_vault` to create Party/ folder
- Create: `tests/vault/test_pc_management.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/vault/test_pc_management.py
"""Tests for Player Character management."""

import pytest
from unittest.mock import MagicMock
from session_scribe.vault.vault_manager import VaultManager
from session_scribe.vault.note_renderer import render_pc_note
from session_scribe.models.context import PlayerCharacter


class TestRenderPCNote:
    def test_render_pc_note(self):
        pc = PlayerCharacter(
            player_name="Scott",
            character_name="Seven",
            character_class="Wizard",
        )
        md = render_pc_note(pc)
        assert "# Seven" in md or "# Severian" in md
        assert "Scott" in md
        assert "Wizard" in md
        assert "type: player-character" in md

    def test_render_pc_note_minimal(self):
        pc = PlayerCharacter(
            player_name="Unknown",
            character_name="Bastion",
        )
        md = render_pc_note(pc)
        assert "# Bastion" in md
        assert "Unknown" in md


class TestVaultManagerPC:
    @pytest.fixture
    def mock_cli(self):
        cli = MagicMock()
        cli.vault_name = "Test Vault"
        cli.list_files.return_value = []
        cli.find_notes_in_folder.return_value = []
        cli.search.return_value = []
        return cli

    @pytest.fixture
    def manager(self, mock_cli):
        return VaultManager(cli=mock_cli)

    def test_write_pc(self, manager, mock_cli):
        pc = PlayerCharacter(
            player_name="Scott",
            character_name="Seven",
            character_class="Wizard",
        )
        manager.write_pc(pc)

        mock_cli.create.assert_called_once()
        path = mock_cli.create.call_args[0][0]
        assert "Party/" in path
        assert "Seven" in path

    def test_read_pcs(self, manager, mock_cli):
        mock_cli.find_notes_in_folder.return_value = ["Party/Seven.md"]
        mock_cli.read.return_value = (
            "---\ntype: player-character\nplayer_name: Scott\n"
            "character_name: Seven\ncharacter_class: Wizard\n---\n"
            "# Seven\n"
        )

        pcs = manager.read_player_characters()
        assert len(pcs) == 1
        assert pcs[0].character_name == "Seven"
        assert pcs[0].player_name == "Scott"

    def test_pcs_in_context_bundle(self, manager, mock_cli):
        mock_cli.find_notes_in_folder.side_effect = lambda folder: {
            "Party/": ["Party/Seven.md"],
        }.get(folder, [])
        mock_cli.read.return_value = (
            "---\ntype: player-character\nplayer_name: Scott\n"
            "character_name: Seven\ncharacter_class: Wizard\n---\n"
        )
        mock_cli.list_files.return_value = ["Party/Seven.md"]

        bundle = manager.get_context_bundle(session_number=1)
        assert len(bundle.player_characters) >= 1
```

- [ ] **Step 2: Run tests to verify they fail**

- [ ] **Step 3: Implement**

Add to `note_renderer.py`:

```python
def render_pc_note(pc: PlayerCharacter) -> str:
    """Render a Player Character note."""
    lines = [
        "---",
        "type: player-character",
        f"player_name: {pc.player_name}",
        f"character_name: {pc.character_name}",
    ]
    if pc.character_class:
        lines.append(f"character_class: {pc.character_class}")
    lines.extend(["---", "", f"# {pc.character_name}", ""])
    lines.append(f"**Player:** {pc.player_name}")
    if pc.character_class:
        lines.append(f"**Class:** {pc.character_class}")
    lines.append("")
    lines.append("## Notes")
    lines.append("")
    return "\n".join(lines)
```

Add to `vault_manager.py`:

```python
def write_pc(self, pc: PlayerCharacter) -> None:
    """Create a Player Character note in Party/."""
    path = f"Party/{pc.character_name}.md"
    self.cli.create(path, render_pc_note(pc))

def read_player_characters(self) -> list[PlayerCharacter]:
    """Read all PC notes from Party/ folder."""
    pcs = []
    for path in self.cli.find_notes_in_folder("Party/"):
        try:
            content = self.cli.read(path)
            fm = self._parse_frontmatter(content)
            if fm.get("type") == "player-character":
                pcs.append(PlayerCharacter(
                    player_name=fm.get("player_name", ""),
                    character_name=fm.get("character_name", ""),
                    character_class=fm.get("character_class"),
                ))
        except Exception:
            continue
    return pcs
```

Update `init_vault()` to include `"Party/"` in the folders created.

Update `get_context_bundle()` to call `read_player_characters()` and populate `bundle.player_characters`.

- [ ] **Step 4: Run tests:** `uv run pytest tests/vault/test_pc_management.py -v`
- [ ] **Step 5: Run ALL tests:** `uv run pytest -v`
- [ ] **Step 6: Commit**

```bash
git add src/session_scribe/vault/ tests/vault/
git commit -m "feat: add Player Character management — notes, vault methods, context bundle integration"
```

---

### Task 2: `scribe party` CLI Command

**Files:**
- Modify: `src/session_scribe/cli/main.py` — add `party` command
- Create: `tests/cli/test_party.py`

The `party` command lets the user:
- `scribe party list` — show current PCs
- `scribe party add --player "Scott" --character "Seven" --class "Wizard"` — add a PC
- `scribe party remove --character "Seven"` — remove a PC

- [ ] **Step 1: Write failing tests**

```python
# tests/cli/test_party.py
"""Tests for the party CLI command."""

import pytest
from unittest.mock import patch, MagicMock
from typer.testing import CliRunner
from session_scribe.cli.main import app

runner = CliRunner()


class TestPartyCommand:
    def test_party_help(self):
        result = runner.invoke(app, ["party", "--help"])
        assert result.exit_code == 0

    def test_party_list_empty(self):
        with patch("session_scribe.cli.main.Settings") as MockSettings, \
             patch("session_scribe.cli.main.ObsidianCLI") as MockCLI, \
             patch("session_scribe.cli.main.VaultManager") as MockVM:
            MockSettings.return_value = MagicMock(vault_name="Test")
            MockVM.return_value.read_player_characters.return_value = []
            result = runner.invoke(app, ["party", "list"])
            assert result.exit_code == 0
            assert "no player characters" in result.output.lower() or "empty" in result.output.lower()

    def test_party_add(self):
        with patch("session_scribe.cli.main.Settings") as MockSettings, \
             patch("session_scribe.cli.main.ObsidianCLI") as MockCLI, \
             patch("session_scribe.cli.main.VaultManager") as MockVM:
            MockSettings.return_value = MagicMock(vault_name="Test")
            mock_vm = MockVM.return_value
            result = runner.invoke(app, [
                "party", "add",
                "--player", "Scott",
                "--character", "Seven",
                "--class", "Wizard",
            ])
            assert result.exit_code == 0
            mock_vm.write_pc.assert_called_once()
```

- [ ] **Step 2: Implement `party` command**

Use a typer sub-app:
```python
party_app = typer.Typer(help="Manage player characters.")
app.add_typer(party_app, name="party")

@party_app.command("list")
def party_list():
    ...

@party_app.command("add")
def party_add(player: str, character: str, character_class: str = typer.Option("", "--class")):
    ...

@party_app.command("remove")
def party_remove(character: str):
    ...
```

- [ ] **Step 3: Run tests:** `uv run pytest tests/cli/test_party.py -v`
- [ ] **Step 4: Commit**

```bash
git add src/session_scribe/cli/ tests/cli/
git commit -m "feat: add scribe party command for PC management (list, add, remove)"
```

---

## Chunk 2: Auto-Reindex + Quality Tracking

### Task 3: Auto-Reindex After Ingest

**Files:**
- Modify: `src/session_scribe/cli/main.py` — add reindex step after ingest writes to vault

After `vault_manager.write_extraction_result(result)` in the ingest pipeline, automatically reindex the vault so the chat is always current.

- [ ] **Step 1: Update `_run_ingest_pipeline` in main.py**

After the vault write step, add:
```python
# Step 6: Auto-reindex for chat
if vault_manager is not None:
    try:
        console.print("[cyan]Updating search index...[/cyan]")
        embed_client = EmbeddingClient(
            base_url=settings.lm_studio_base_url,
            model=settings.embedding_model,
        )
        if embed_client.health_check():
            import chromadb
            chroma_client = chromadb.PersistentClient(
                path=str(settings.vault_path / ".scribe" / "chromadb")
            )
            collection = chroma_client.get_or_create_collection("vault_notes")
            indexer = VaultIndexer(cli, embed_client, collection)
            chunk_count = await indexer.index_vault(vault_path=str(settings.vault_path))
            console.print(f"[green]Search index updated:[/green] {chunk_count} chunks")
        else:
            console.print("[dim]LM Studio not running — skipping search index update[/dim]")
    except Exception as exc:
        console.print(f"[dim]Search index update skipped: {exc}[/dim]")
```

- [ ] **Step 2: Test by running ingest and then immediately using chat**

- [ ] **Step 3: Commit**

```bash
git add src/session_scribe/cli/main.py
git commit -m "feat: auto-reindex vault after ingest so chat is always current"
```

---

### Task 4: Quality Metrics Tracking

**Files:**
- Create: `src/session_scribe/vault/metrics.py`
- Create: `tests/vault/test_metrics.py`
- Modify: `src/session_scribe/cli/main.py` — update `stats` command

Track per-session quality metrics and display them via `scribe stats`.

- [ ] **Step 1: Write failing tests**

```python
# tests/vault/test_metrics.py
"""Tests for quality metrics tracking."""

import json
import pytest
from session_scribe.vault.metrics import QualityMetrics, SessionMetric


class TestQualityMetrics:
    def test_add_metric(self, tmp_path):
        metrics = QualityMetrics(storage_path=tmp_path / "metrics.json")
        metrics.add(SessionMetric(
            session_number=22,
            npc_count=8,
            location_count=11,
            faction_count=2,
            thread_count=5,
            question_count=3,
            quality_score=4.2,
            reviewer_findings=14,
        ))

        assert len(metrics.all()) == 1
        assert metrics.all()[0].session_number == 22

    def test_metrics_persist(self, tmp_path):
        path = tmp_path / "metrics.json"

        metrics1 = QualityMetrics(storage_path=path)
        metrics1.add(SessionMetric(session_number=1, npc_count=3, location_count=2,
                                    faction_count=1, thread_count=2, question_count=0,
                                    quality_score=3.5, reviewer_findings=5))

        metrics2 = QualityMetrics(storage_path=path)
        assert len(metrics2.all()) == 1

    def test_metrics_summary(self, tmp_path):
        metrics = QualityMetrics(storage_path=tmp_path / "metrics.json")
        metrics.add(SessionMetric(session_number=1, npc_count=3, location_count=2,
                                    faction_count=1, thread_count=2, question_count=1,
                                    quality_score=3.5, reviewer_findings=10))
        metrics.add(SessionMetric(session_number=2, npc_count=5, location_count=4,
                                    faction_count=1, thread_count=3, question_count=0,
                                    quality_score=4.0, reviewer_findings=6))

        summary = metrics.summary()
        assert summary["sessions_processed"] == 2
        assert summary["avg_quality"] == pytest.approx(3.75)
        assert summary["findings_trend"] == "decreasing"
```

- [ ] **Step 2: Implement metrics**

```python
# src/session_scribe/vault/metrics.py
"""Quality metrics tracking per session."""

import json
from dataclasses import dataclass, asdict
from pathlib import Path


@dataclass
class SessionMetric:
    session_number: int
    npc_count: int
    location_count: int
    faction_count: int
    thread_count: int
    question_count: int
    quality_score: float  # average from QualityScore
    reviewer_findings: int


class QualityMetrics:
    """Persistent quality metrics stored as JSON."""

    def __init__(self, storage_path: Path) -> None:
        self._path = storage_path
        self._data: list[SessionMetric] = self._load()

    def _load(self) -> list[SessionMetric]:
        if self._path.exists():
            raw = json.loads(self._path.read_text())
            return [SessionMetric(**item) for item in raw]
        return []

    def _save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps([asdict(m) for m in self._data], indent=2))

    def add(self, metric: SessionMetric) -> None:
        self._data.append(metric)
        self._save()

    def all(self) -> list[SessionMetric]:
        return list(self._data)

    def summary(self) -> dict:
        if not self._data:
            return {"sessions_processed": 0}

        scores = [m.quality_score for m in self._data]
        findings = [m.reviewer_findings for m in self._data]

        # Determine trend
        trend = "stable"
        if len(findings) >= 2:
            if findings[-1] < findings[0]:
                trend = "decreasing"
            elif findings[-1] > findings[0]:
                trend = "increasing"

        return {
            "sessions_processed": len(self._data),
            "avg_quality": sum(scores) / len(scores),
            "total_npcs": sum(m.npc_count for m in self._data),
            "total_locations": sum(m.location_count for m in self._data),
            "findings_trend": trend,
        }
```

- [ ] **Step 3: Wire into `scribe ingest` — log metrics after each extraction**
- [ ] **Step 4: Wire into `scribe stats` — display metrics summary**
- [ ] **Step 5: Run tests:** `uv run pytest tests/vault/test_metrics.py -v`
- [ ] **Step 6: Commit**

```bash
git add src/session_scribe/vault/metrics.py tests/vault/test_metrics.py src/session_scribe/cli/main.py
git commit -m "feat: add quality metrics tracking per session with scribe stats display"
```

---

## Chunk 3: Chat Corrections + User-Style Testing

### Task 5: Chat Correction Commands

**Files:**
- Modify: `src/session_scribe/chat/app.py` — add `/correct`, `/alias`, `/forget` commands

When chatting with the agent, Scott needs to be able to:
- `/correct NPC "friendly face" name="The Friendly Face"` — rename/fix an entity
- `/alias "the tavern" "Smoked Eel Tavern"` — teach the agent an alias
- `/forget "Sebastian"` — tell the agent to ignore a false extraction

- [ ] **Step 1: Add command handling to ChatApp**

In `handle_input`, before the normal query flow, check if the input starts with `/`:

```python
if query.startswith("/"):
    self._handle_command(query)
    return
```

Implement `_handle_command`:
- `/alias "term" "entity"` — calls `vault_manager.update_entity_aliases()` and confirms
- `/quit` — exits (already done)
- `/help` — shows available commands
- Any unrecognized command — "Unknown command. Type /help for available commands."

For V1, keep it simple: `/alias` and `/help` are the most useful. `/correct` and `/forget` can be added later since they require more vault manipulation.

- [ ] **Step 2: The chat app needs access to VaultManager**

Update `ChatApp.__init__` to accept an optional `vault_manager` parameter. Update the CLI `chat` command to pass it.

- [ ] **Step 3: Test by running chat and trying `/help` and `/alias`**
- [ ] **Step 4: Commit**

```bash
git add src/session_scribe/chat/ src/session_scribe/cli/
git commit -m "feat: add /alias and /help commands to chat TUI for interactive corrections"
```

---

### Task 6: User-Style Testing (ALL stories must pass)

Execute manually. Every story verified.

- [ ] **Story 1:** "I run `scribe party add --player 'Scott' --character 'Seven' --class 'Wizard'` — does it create a PC note?"

Verify: Party/Seven.md exists in vault with correct frontmatter.

- [ ] **Story 2:** "I run `scribe party list` — does it show all PCs?"

Verify: Lists PCs with player name, character name, class.

- [ ] **Story 3:** "I ingest a session — does the extraction know who the PCs are?"

Run `scribe ingest` after adding PCs. Check that PC names don't appear as NPCs in the extraction.

- [ ] **Story 4:** "After ingest, can I immediately use chat without running reindex?"

Verify: Auto-reindex runs after ingest. Chat finds the new session content.

- [ ] **Story 5:** "I run `scribe stats` — does it show quality metrics?"

Verify: Shows sessions processed, average quality, entity counts, trend.

- [ ] **Story 6:** "In chat, I type `/help` — does it show available commands?"

Verify: Lists /alias, /quit, /help.

- [ ] **Story 7:** "In chat, I type `/alias 'the tavern' 'Smoked Eel Tavern'` — does it save?"

Verify: Alias saved to agent memory. Future queries resolve "the tavern" correctly.

- [ ] **Story 8:** "I process sessions out of order (e.g., skip session 8) — does it handle the gap?"

Run `scribe review` after processing non-sequential sessions. Verify: Timeline gaps check reports the missing session.

- [ ] **Story 9:** "Full test suite passes"

```bash
uv run pytest -v
```

Document all issues, fix them, re-test. Commit fixes.

---

## Summary

After completing all tasks, Milestone 6 adds:

- **Player Character management:** Party/ folder, `scribe party` command (list, add, remove), PCs in context bundle
- **Auto-reindex after ingest:** Chat is always current after processing a session
- **Quality metrics:** Per-session tracking, `scribe stats` command with trends
- **Chat corrections:** `/alias`, `/help` commands for interactive vault refinement
- **Ready for backlog processing:** Scott can now work with the agent interactively to process 22 sessions
