# Milestone 4: Reviewer + Question Queue — Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a vault reviewer module that detects quality issues (broken wikilinks, duplicates, missing fields, inconsistencies) and a `scribe ask` command that lets the user view and answer the agent's pending questions — completing the human-in-the-loop feedback cycle.

**Architecture:** A new `reviewer/` module that reads vault state and runs quality checks. The `scribe ask` CLI command presents pending questions from `_Agent/Questions/`, accepts answers, and writes them back so the agent can use them in future extractions. The `scribe review` command triggers the reviewer. Both integrate with the existing VaultManager.

**Tech Stack:** Existing vault module (ObsidianCLI, VaultManager), typer CLI, rich for output formatting

**Spec:** `docs/superpowers/specs/2026-04-02-session-scribe-design.md` (Section 3 — Reviewer Module, Section 7 — Milestone 4)

**Depends on:** Milestone 3 complete (vault manager, CLI init/ingest)

**Already completed from M4 spec scope (in M3):**
- Pipeline wiring (ingestion → extraction → vault)
- Process Session 22 end-to-end
- Dashboard and Open Threads generation
- Question creation during extraction

---

## File Structure

```
src/session_scribe/
  reviewer/
    __init__.py           — exports: review_vault
    checks.py             — Individual quality check functions
    reviewer.py           — Orchestrates all checks, produces ReviewReport

tests/
  reviewer/
    __init__.py
    test_checks.py        — Tests for individual checks
    test_reviewer.py      — Tests for the orchestrator
  cli/
    test_ask.py           — Tests for the ask command
```

---

## Chunk 1: Reviewer Module

### Task 1: Quality Check Functions

**Files:**
- Create: `src/session_scribe/reviewer/__init__.py`
- Create: `src/session_scribe/reviewer/checks.py`
- Create: `tests/reviewer/__init__.py`
- Create: `tests/reviewer/test_checks.py`

Individual check functions that each examine one aspect of vault quality. Each returns a list of findings.

- [ ] **Step 1: Create directories**

```bash
mkdir -p src/session_scribe/reviewer tests/reviewer
touch src/session_scribe/reviewer/__init__.py tests/reviewer/__init__.py
```

- [ ] **Step 2: Write failing tests**

```python
# tests/reviewer/test_checks.py
"""Tests for individual vault quality checks."""

import pytest
from unittest.mock import MagicMock

from session_scribe.reviewer.checks import (
    check_broken_wikilinks,
    check_missing_fields,
    check_duplicate_entities,
    check_orphaned_notes,
    ReviewFinding,
    Severity,
)


@pytest.fixture
def mock_cli():
    cli = MagicMock()
    cli.vault_name = "Test Vault"
    return cli


class TestCheckBrokenWikilinks:
    def test_finds_broken_link(self, mock_cli):
        mock_cli.list_files.return_value = [
            "NPCs/Theron.md",
            "Sessions/Session-001.md",
        ]
        mock_cli.read.side_effect = lambda path: {
            "NPCs/Theron.md": "# Theron\n\nAffiliated with [[Nonexistent Faction]]",
            "Sessions/Session-001.md": "# Session 1\n\nMet [[Theron]]",
        }[path]

        findings = check_broken_wikilinks(mock_cli)

        broken = [f for f in findings if "Nonexistent Faction" in f.detail]
        assert len(broken) >= 1
        assert broken[0].severity == Severity.WARNING

    def test_no_broken_links(self, mock_cli):
        mock_cli.list_files.return_value = ["NPCs/Theron.md"]
        mock_cli.read.return_value = "# Theron\n\nA ranger."

        findings = check_broken_wikilinks(mock_cli)
        assert findings == []


class TestCheckMissingFields:
    def test_npc_missing_description(self, mock_cli):
        mock_cli.find_notes_in_folder.return_value = ["NPCs/Theron.md"]
        mock_cli.read.return_value = (
            "---\ntype: npc\nstatus: alive\nfirst_appeared: Session-001\n---\n"
            "# Theron\n"
        )

        findings = check_missing_fields(mock_cli)
        assert any("description" in f.detail.lower() for f in findings)

    def test_complete_npc_no_findings(self, mock_cli):
        mock_cli.find_notes_in_folder.return_value = ["NPCs/Theron.md"]
        mock_cli.read.return_value = (
            "---\ntype: npc\nstatus: alive\nfirst_appeared: Session-001\n---\n"
            "# Theron\n\n## Description\n\nA ranger from the north.\n"
        )

        findings = check_missing_fields(mock_cli)
        npc_findings = [f for f in findings if "Theron" in f.detail]
        assert npc_findings == []


class TestCheckDuplicateEntities:
    def test_finds_near_duplicate_npcs(self, mock_cli):
        mock_cli.find_notes_in_folder.return_value = [
            "NPCs/Sylvie.md",
            "NPCs/Sylvie Starwater.md",
        ]

        findings = check_duplicate_entities(mock_cli, "NPCs/")
        assert len(findings) >= 1
        assert findings[0].severity == Severity.WARNING

    def test_no_duplicates(self, mock_cli):
        mock_cli.find_notes_in_folder.return_value = [
            "NPCs/Theron.md",
            "NPCs/Sylvie.md",
        ]

        findings = check_duplicate_entities(mock_cli, "NPCs/")
        assert findings == []


class TestCheckOrphanedNotes:
    def test_finds_orphaned_npc(self, mock_cli):
        mock_cli.find_notes_in_folder.return_value = ["NPCs/Orphan.md"]
        # Read all files to check for links — none link to Orphan
        mock_cli.list_files.return_value = [
            "NPCs/Orphan.md",
            "Sessions/Session-001.md",
        ]
        mock_cli.read.side_effect = lambda path: {
            "NPCs/Orphan.md": "# Orphan\n\nNobody links here.",
            "Sessions/Session-001.md": "# Session 1\n\nMet [[Theron]].",
        }[path]

        findings = check_orphaned_notes(mock_cli)
        assert any("Orphan" in f.detail for f in findings)


class TestReviewFinding:
    def test_finding_creation(self):
        finding = ReviewFinding(
            check="broken_wikilinks",
            severity=Severity.WARNING,
            file="NPCs/Theron.md",
            detail="Broken link: [[Nonexistent Faction]]",
        )
        assert finding.check == "broken_wikilinks"
        assert finding.severity == Severity.WARNING
```

- [ ] **Step 3: Run tests to verify they fail**

- [ ] **Step 4: Implement quality checks**

```python
# src/session_scribe/reviewer/checks.py
"""Individual vault quality check functions.

Each check function takes an ObsidianCLI and returns a list of ReviewFindings.
"""

import re
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

from session_scribe.vault.dedup import find_match

if TYPE_CHECKING:
    from session_scribe.vault.obsidian_cli import ObsidianCLI


class Severity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


@dataclass
class ReviewFinding:
    """A single quality issue found during review."""

    check: str
    severity: Severity
    file: str
    detail: str


_WIKILINK_RE = re.compile(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]")


def check_broken_wikilinks(cli: "ObsidianCLI") -> list[ReviewFinding]:
    """Find wikilinks that don't resolve to any existing note."""
    findings: list[ReviewFinding] = []
    all_files = cli.list_files()

    # Build set of known note names (without .md extension and folder prefix)
    known_names = set()
    for f in all_files:
        name = f.rsplit("/", 1)[-1].replace(".md", "")
        known_names.add(name.lower())

    for file_path in all_files:
        try:
            content = cli.read(file_path)
        except Exception:
            continue

        links = _WIKILINK_RE.findall(content)
        for link_target in links:
            # Strip path prefix if present
            target_name = link_target.rsplit("/", 1)[-1]
            if target_name.lower() not in known_names:
                findings.append(ReviewFinding(
                    check="broken_wikilinks",
                    severity=Severity.WARNING,
                    file=file_path,
                    detail=f"Broken link: [[{link_target}]]",
                ))

    return findings


def check_missing_fields(cli: "ObsidianCLI") -> list[ReviewFinding]:
    """Check entity notes for missing required content."""
    findings: list[ReviewFinding] = []

    # Check NPCs
    for path in cli.find_notes_in_folder("NPCs/"):
        try:
            content = cli.read(path)
        except Exception:
            continue

        if "## Description" not in content or content.split("## Description")[-1].strip() == "":
            findings.append(ReviewFinding(
                check="missing_fields",
                severity=Severity.INFO,
                file=path,
                detail=f"NPC note missing description section: {path}",
            ))

    # Check Locations
    for path in cli.find_notes_in_folder("Locations/"):
        try:
            content = cli.read(path)
        except Exception:
            continue

        if "## Description" not in content or content.split("## Description")[-1].strip() == "":
            findings.append(ReviewFinding(
                check="missing_fields",
                severity=Severity.INFO,
                file=path,
                detail=f"Location note missing description: {path}",
            ))

    # Check Factions
    for path in cli.find_notes_in_folder("Factions/"):
        try:
            content = cli.read(path)
        except Exception:
            continue

        if "## Description" not in content:
            findings.append(ReviewFinding(
                check="missing_fields",
                severity=Severity.INFO,
                file=path,
                detail=f"Faction note missing description: {path}",
            ))

    # Check Sessions have frontmatter
    for path in cli.find_notes_in_folder("Sessions/"):
        try:
            content = cli.read(path)
        except Exception:
            continue

        if "## Summary" not in content:
            findings.append(ReviewFinding(
                check="missing_fields",
                severity=Severity.WARNING,
                file=path,
                detail=f"Session note missing summary section: {path}",
            ))

    return findings


def check_duplicate_entities(
    cli: "ObsidianCLI", folder: str
) -> list[ReviewFinding]:
    """Find potential duplicate entity notes within a folder using fuzzy matching."""
    findings: list[ReviewFinding] = []
    files = cli.find_notes_in_folder(folder)

    names = []
    for f in files:
        name = f.rsplit("/", 1)[-1].replace(".md", "")
        names.append((name, f))

    # Compare each pair
    checked = set()
    for i, (name_a, path_a) in enumerate(names):
        for j, (name_b, path_b) in enumerate(names):
            if i >= j:
                continue
            pair_key = tuple(sorted([path_a, path_b]))
            if pair_key in checked:
                continue
            checked.add(pair_key)

            match = find_match(name_a, [name_b], threshold=75)
            if match is not None:
                findings.append(ReviewFinding(
                    check="duplicate_entities",
                    severity=Severity.WARNING,
                    file=path_a,
                    detail=f"Possible duplicate: '{name_a}' and '{name_b}'",
                ))

    return findings


def check_orphaned_notes(cli: "ObsidianCLI") -> list[ReviewFinding]:
    """Find entity notes that no other note links to."""
    findings: list[ReviewFinding] = []
    all_files = cli.list_files()

    # Collect all wikilink targets across the vault
    all_link_targets: set[str] = set()
    for file_path in all_files:
        try:
            content = cli.read(file_path)
        except Exception:
            continue
        for target in _WIKILINK_RE.findall(content):
            all_link_targets.add(target.rsplit("/", 1)[-1].lower())

    # Check entity folders for notes nobody links to
    entity_folders = ["NPCs/", "Locations/", "Factions/", "Loot/"]
    for folder in entity_folders:
        for path in cli.find_notes_in_folder(folder):
            name = path.rsplit("/", 1)[-1].replace(".md", "")
            if name.lower() not in all_link_targets:
                findings.append(ReviewFinding(
                    check="orphaned_notes",
                    severity=Severity.INFO,
                    file=path,
                    detail=f"Orphaned note — no other note links to '{name}'",
                ))

    return findings


def check_timeline_gaps(cli: "ObsidianCLI") -> list[ReviewFinding]:
    """Check for gaps in session numbering (e.g., Session 1, 2, 5 — missing 3, 4)."""
    findings: list[ReviewFinding] = []
    session_files = cli.find_notes_in_folder("Sessions/")

    # Extract session numbers from filenames
    numbers = []
    for f in session_files:
        name = f.rsplit("/", 1)[-1].replace(".md", "")
        # Match "Session-NNN" or "Session NNN"
        for part in name.replace("-", " ").split():
            if part.isdigit():
                numbers.append(int(part))
                break

    if len(numbers) < 2:
        return findings

    numbers.sort()
    for i in range(len(numbers) - 1):
        gap = numbers[i + 1] - numbers[i]
        if gap > 1:
            missing = list(range(numbers[i] + 1, numbers[i + 1]))
            findings.append(ReviewFinding(
                check="timeline_gaps",
                severity=Severity.INFO,
                file="Sessions/",
                detail=f"Missing session(s): {missing} (gap between Session {numbers[i]} and {numbers[i+1]})",
            ))

    return findings


def check_inconsistencies(cli: "ObsidianCLI") -> list[ReviewFinding]:
    """Check for inconsistencies between related notes.

    For example: an NPC lists an affiliation to a faction that doesn't exist,
    or a location's connected_to references a non-existent location.
    """
    findings: list[ReviewFinding] = []

    # Check NPC affiliations reference real factions
    faction_files = cli.find_notes_in_folder("Factions/")
    faction_names = {f.rsplit("/", 1)[-1].replace(".md", "").lower() for f in faction_files}

    for path in cli.find_notes_in_folder("NPCs/"):
        try:
            content = cli.read(path)
        except Exception:
            continue

        # Parse frontmatter affiliations
        if "affiliations:" in content:
            # Simple extraction: find lines with [[ ]] in affiliations section
            for line in content.split("\n"):
                if "[[" in line and "affiliations" not in line.lower():
                    continue
                links = _WIKILINK_RE.findall(line)
                for link in links:
                    link_name = link.rsplit("/", 1)[-1]
                    if link_name.lower() not in faction_names and "Session" not in link:
                        findings.append(ReviewFinding(
                            check="inconsistencies",
                            severity=Severity.INFO,
                            file=path,
                            detail=f"NPC affiliations reference '{link_name}' which has no matching Faction note",
                        ))

    return findings
```

**Additional tests needed for the new checks — add to `test_checks.py`:**

```python
class TestCheckTimelineGaps:
    def test_finds_gap(self, mock_cli):
        mock_cli.find_notes_in_folder.return_value = [
            "Sessions/Session-001.md",
            "Sessions/Session-002.md",
            "Sessions/Session-005.md",
        ]

        findings = check_timeline_gaps(mock_cli)
        assert len(findings) >= 1
        assert "3" in findings[0].detail or "missing" in findings[0].detail.lower()

    def test_no_gap(self, mock_cli):
        mock_cli.find_notes_in_folder.return_value = [
            "Sessions/Session-001.md",
            "Sessions/Session-002.md",
            "Sessions/Session-003.md",
        ]

        findings = check_timeline_gaps(mock_cli)
        assert findings == []


class TestCheckInconsistencies:
    def test_finds_orphaned_affiliation(self, mock_cli):
        mock_cli.find_notes_in_folder.side_effect = lambda folder: {
            "NPCs/": ["NPCs/Theron.md"],
            "Factions/": [],
        }[folder]
        mock_cli.read.return_value = (
            "---\ntype: npc\n---\n# Theron\n\n"
            "**Affiliations:** [[Missing Faction]]"
        )

        findings = check_inconsistencies(mock_cli)
        assert any("Missing Faction" in f.detail for f in findings)
```

Also add the new imports to the test file:

```python
from session_scribe.reviewer.checks import (
    check_broken_wikilinks,
    check_missing_fields,
    check_duplicate_entities,
    check_orphaned_notes,
    check_timeline_gaps,
    check_inconsistencies,
    ReviewFinding,
    Severity,
)
```

- [ ] **Step 5: Run tests:** `uv run pytest tests/reviewer/test_checks.py -v`

- [ ] **Step 6: Run ALL tests:** `uv run pytest -v`

- [ ] **Step 7: Commit**

```bash
git add src/session_scribe/reviewer/ tests/reviewer/
git commit -m "feat: add vault quality checks — broken wikilinks, missing fields, duplicates, orphans"
```

---

### Task 2: Reviewer Orchestrator

**Files:**
- Create: `src/session_scribe/reviewer/reviewer.py`
- Create: `tests/reviewer/test_reviewer.py`
- Modify: `src/session_scribe/reviewer/__init__.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/reviewer/test_reviewer.py
"""Tests for the review orchestrator."""

import pytest
from unittest.mock import MagicMock, patch

from session_scribe.reviewer.reviewer import review_vault, ReviewReport
from session_scribe.reviewer.checks import ReviewFinding, Severity


class TestReviewVault:
    def test_review_produces_report(self):
        mock_cli = MagicMock()
        mock_cli.list_files.return_value = []
        mock_cli.find_notes_in_folder.return_value = []

        report = review_vault(mock_cli)

        assert isinstance(report, ReviewReport)
        assert isinstance(report.findings, list)
        assert report.total_findings >= 0

    def test_review_aggregates_findings(self):
        mock_cli = MagicMock()
        mock_cli.list_files.return_value = ["NPCs/Test.md"]
        mock_cli.find_notes_in_folder.return_value = ["NPCs/Test.md"]
        mock_cli.read.return_value = (
            "---\ntype: npc\n---\n# Test\n\n"
            "Linked to [[Nonexistent]]"
        )

        report = review_vault(mock_cli)

        # Should find at least the broken link
        assert report.total_findings > 0
        assert any(f.check == "broken_wikilinks" for f in report.findings)

    def test_report_summary(self):
        findings = [
            ReviewFinding(check="test", severity=Severity.WARNING, file="a.md", detail="warn"),
            ReviewFinding(check="test", severity=Severity.ERROR, file="b.md", detail="err"),
            ReviewFinding(check="test", severity=Severity.INFO, file="c.md", detail="info"),
        ]
        report = ReviewReport(findings=findings)

        assert report.total_findings == 3
        assert report.error_count == 1
        assert report.warning_count == 1
        assert report.info_count == 1
```

- [ ] **Step 2: Run tests to verify they fail**

- [ ] **Step 3: Implement reviewer**

```python
# src/session_scribe/reviewer/reviewer.py
"""Vault review orchestrator — runs all quality checks and produces a report."""

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from session_scribe.reviewer.checks import (
    ReviewFinding,
    Severity,
    check_broken_wikilinks,
    check_duplicate_entities,
    check_inconsistencies,
    check_missing_fields,
    check_orphaned_notes,
    check_timeline_gaps,
)

if TYPE_CHECKING:
    from session_scribe.vault.obsidian_cli import ObsidianCLI

logger = logging.getLogger(__name__)


@dataclass
class ReviewReport:
    """Summary of all findings from a vault review pass."""

    findings: list[ReviewFinding] = field(default_factory=list)

    @property
    def total_findings(self) -> int:
        return len(self.findings)

    @property
    def error_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == Severity.ERROR)

    @property
    def warning_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == Severity.WARNING)

    @property
    def info_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == Severity.INFO)


def review_vault(cli: "ObsidianCLI") -> ReviewReport:
    """Run all quality checks against the vault and return a report.

    Each check runs independently — a failure in one check does not
    prevent others from running.
    """
    all_findings: list[ReviewFinding] = []

    checks = [
        ("broken_wikilinks", lambda: check_broken_wikilinks(cli)),
        ("missing_fields", lambda: check_missing_fields(cli)),
        ("duplicate_npcs", lambda: check_duplicate_entities(cli, "NPCs/")),
        ("duplicate_locations", lambda: check_duplicate_entities(cli, "Locations/")),
        ("duplicate_factions", lambda: check_duplicate_entities(cli, "Factions/")),
        ("orphaned_notes", lambda: check_orphaned_notes(cli)),
        ("timeline_gaps", lambda: check_timeline_gaps(cli)),
        ("inconsistencies", lambda: check_inconsistencies(cli)),
    ]

    for name, check_fn in checks:
        try:
            findings = check_fn()
            all_findings.extend(findings)
            logger.info("Check '%s': %d findings", name, len(findings))
        except Exception as e:
            logger.warning("Check '%s' failed: %s", name, e)
            all_findings.append(ReviewFinding(
                check=name,
                severity=Severity.ERROR,
                file="",
                detail=f"Check failed: {e}",
            ))

    report = ReviewReport(findings=all_findings)
    logger.info(
        "Review complete: %d findings (%d errors, %d warnings, %d info)",
        report.total_findings, report.error_count, report.warning_count, report.info_count,
    )
    return report
```

- [ ] **Step 4: Update exports**

```python
# src/session_scribe/reviewer/__init__.py
"""Public API for the reviewer module."""
from session_scribe.reviewer.reviewer import review_vault, ReviewReport
from session_scribe.reviewer.checks import ReviewFinding, Severity
__all__ = ["review_vault", "ReviewReport", "ReviewFinding", "Severity"]
```

- [ ] **Step 5: Run tests:** `uv run pytest tests/reviewer/ -v`

- [ ] **Step 6: Commit**

```bash
git add src/session_scribe/reviewer/ tests/reviewer/
git commit -m "feat: add vault reviewer with quality checks and report aggregation"
```

---

## Chunk 2: CLI Commands (review + ask)

### Task 3: Wire `scribe review` Command

**Files:**
- Modify: `src/session_scribe/cli/main.py` — replace review stub with real implementation
- Create: `tests/cli/test_review.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/cli/test_review.py
"""Tests for the review CLI command."""

import pytest
from unittest.mock import patch, MagicMock
from typer.testing import CliRunner
from session_scribe.cli.main import app

runner = CliRunner()


class TestReviewCommand:
    def test_review_help(self):
        result = runner.invoke(app, ["review", "--help"])
        assert result.exit_code == 0
        assert "review" in result.output.lower() or "quality" in result.output.lower()

    def test_review_runs_and_reports(self):
        from session_scribe.reviewer.checks import ReviewFinding, Severity

        mock_report = MagicMock()
        mock_report.findings = [
            ReviewFinding(check="test", severity=Severity.WARNING, file="NPCs/Test.md", detail="Test warning"),
        ]
        mock_report.total_findings = 1
        mock_report.error_count = 0
        mock_report.warning_count = 1
        mock_report.info_count = 0

        with patch("session_scribe.cli.main.Settings") as MockSettings, \
             patch("session_scribe.cli.main.ObsidianCLI"), \
             patch("session_scribe.cli.main.review_vault", return_value=mock_report):
            MockSettings.return_value = MagicMock(vault_name="Test")
            result = runner.invoke(app, ["review"])
            assert result.exit_code == 0
            assert "1" in result.output  # finding count
```

- [ ] **Step 2: Implement the review command**

Replace the `review` stub in `main.py` with a real implementation that:
1. Loads Settings, validates vault_name
2. Creates ObsidianCLI
3. Calls `review_vault(cli)`
4. Prints findings with rich formatting: severity colors, file paths, details
5. Shows summary counts (errors/warnings/info)
6. Writes findings to `_Agent/Review-Log.md` in the vault

Add `from session_scribe.reviewer import review_vault` to imports.

- [ ] **Step 3: Run tests:** `uv run pytest tests/cli/test_review.py -v`

- [ ] **Step 4: Commit**

```bash
git add src/session_scribe/cli/main.py tests/cli/test_review.py
git commit -m "feat: wire scribe review command to vault reviewer"
```

---

### Task 4: Wire `scribe ask` Command

**Files:**
- Modify: `src/session_scribe/cli/main.py` — replace ask stub with real implementation
- Create: `tests/cli/test_ask.py`

The `scribe ask` command lets the user:
1. View all pending agent questions from `_Agent/Questions/`
2. Answer them one at a time interactively
3. Save answers back to the vault

- [ ] **Step 1: Write failing tests**

```python
# tests/cli/test_ask.py
"""Tests for the ask CLI command."""

import pytest
from unittest.mock import patch, MagicMock
from typer.testing import CliRunner
from session_scribe.cli.main import app

runner = CliRunner()


class TestAskCommand:
    def test_ask_help(self):
        result = runner.invoke(app, ["ask", "--help"])
        assert result.exit_code == 0

    def test_ask_no_questions(self):
        with patch("session_scribe.cli.main.Settings") as MockSettings, \
             patch("session_scribe.cli.main.ObsidianCLI") as MockCLI:
            MockSettings.return_value = MagicMock(vault_name="Test")
            mock_cli_instance = MockCLI.return_value
            mock_cli_instance.find_notes_in_folder.return_value = []

            result = runner.invoke(app, ["ask"])
            assert result.exit_code == 0
            assert "no pending questions" in result.output.lower()

    def test_ask_shows_questions(self):
        with patch("session_scribe.cli.main.Settings") as MockSettings, \
             patch("session_scribe.cli.main.ObsidianCLI") as MockCLI:
            MockSettings.return_value = MagicMock(vault_name="Test")
            mock_cli_instance = MockCLI.return_value
            mock_cli_instance.find_notes_in_folder.return_value = [
                "_Agent/Questions/q1.md",
            ]
            mock_cli_instance.read.return_value = (
                "---\ntype: agent-question\npriority: medium\nsource_session: 22\n---\n"
                "# Is Santiago an NPC or a player character?\n\n"
                "## Context\nUnclear from the transcript."
            )

            result = runner.invoke(app, ["ask"], input="\n")  # skip answering
            assert "Santiago" in result.output
```

- [ ] **Step 2: Implement the ask command**

Replace the `ask` stub with:
1. Load Settings, create ObsidianCLI
2. List files in `_Agent/Questions/`
3. If none, print "No pending questions" and exit
4. For each question:
   - Read the file, parse the question and context
   - Display with rich formatting (question, context, priority, source session)
   - Prompt user for answer (or Enter to skip)
   - If answered, append the answer to the question file and optionally move to an "answered" subfolder
5. Print summary of how many answered

**Answer persistence:** When the user answers a question:
1. Append `\n## Answer\n\n{answer_text}\n` to the question file
2. Set frontmatter property `answered: true` via `cli.set_property()`
3. Move the file from `_Agent/Questions/` to `_Agent/Questions/answered/` via filesystem rename
4. The `get_context_bundle()` method in VaultManager should eventually read answered questions to inform future extractions

For non-interactive mode (piped input), just list the questions without prompting.

- [ ] **Step 3: Run tests:** `uv run pytest tests/cli/test_ask.py -v`

- [ ] **Step 4: Run ALL tests:** `uv run pytest -v`

- [ ] **Step 5: Commit**

```bash
git add src/session_scribe/cli/main.py tests/cli/
git commit -m "feat: wire scribe ask command for viewing and answering agent questions"
```

---

## Chunk 3: Multi-Session Robustness + User-Style Testing

### Task 5: Multi-Session Integration Test

**Files:**
- Create: `tests/cli/test_pipeline_integration.py`

This test verifies that ingesting a second session correctly updates the vault — no duplicates, threads update, context carries forward.

- [ ] **Step 1: Write integration test**

```python
# tests/cli/test_pipeline_integration.py
"""Integration tests for multi-session pipeline robustness.

Run with: pytest -m integration tests/cli/test_pipeline_integration.py -v -s
"""

import pytest
from session_scribe.vault.obsidian_cli import ObsidianCLI
from session_scribe.vault.vault_manager import VaultManager
from session_scribe.config.settings import Settings
from session_scribe.models.entities import NPC, Location, EntityStatus
from session_scribe.models.session import SessionRecap
from session_scribe.models.extraction import ExtractionResult
from session_scribe.models.entities import PlotThread, ThreadStatus


@pytest.mark.integration
class TestMultiSessionPipeline:
    """Test that multiple sessions grow the vault correctly."""

    @pytest.fixture
    def real_cli(self):
        settings = Settings()
        assert settings.vault_name
        return ObsidianCLI(vault_name=settings.vault_name)

    @pytest.fixture
    def real_manager(self, real_cli):
        return VaultManager(cli=real_cli)

    def test_second_session_does_not_duplicate_npcs(self, real_manager, real_cli):
        """An NPC appearing in two sessions should have one note, not two."""
        npc = NPC(name="Dedup Test NPC", first_appeared="Session-001", status=EntityStatus.ALIVE)

        # Write once
        real_manager.write_npc(npc)

        # Write again (same name, different session)
        npc2 = NPC(name="Dedup Test NPC", first_appeared="Session-002", status=EntityStatus.ALIVE)
        real_manager.write_npc(npc2)

        # Should still be just one file
        results = real_cli.search("Dedup Test NPC")
        npc_results = [r for r in results if "NPCs/" in r and "Dedup Test" in r]
        assert len(npc_results) == 1

        # Clean up
        for path in results:
            if "Dedup Test" in path:
                real_cli.delete(path)

    def test_context_bundle_grows_with_sessions(self, real_manager):
        """Context bundle should reflect all processed sessions."""
        bundle = real_manager.get_context_bundle(session_number=23)
        # If Session 22 was previously ingested, we should have NPCs
        # This test validates the context bundle reads vault state
        assert bundle.session_number == 23
```

- [ ] **Step 2: Verify non-integration tests pass:** `uv run pytest -v`

- [ ] **Step 3: Commit**

```bash
git add tests/cli/test_pipeline_integration.py
git commit -m "test: add multi-session pipeline integration tests"
```

---

### Task 6: User-Style Testing

Execute manually after all code tasks are complete. All stories must pass.

**Prerequisite:** The vault "Tales from Laguna Nera" should have Session 22 already ingested from M3 testing. If not, run `scribe init` then `scribe ingest tests/fixtures/session_022/summary.pdf --session 22` first.

- [ ] **Story 1:** "I run `scribe review` — does it find real issues?"

```bash
uv run scribe review
```

Verify: Shows a report with any findings (broken links, missing fields, etc.). Color-coded by severity. Summary at the end. No crashes.

- [ ] **Story 2:** "I run `scribe ask` — can I see the agent's pending questions?"

```bash
uv run scribe ask
```

Verify: Lists questions from `_Agent/Questions/`. Shows question text, context, priority, source session. Can skip by pressing Enter. If I type an answer, it gets saved.

- [ ] **Story 3:** "I run `scribe review` after answering questions — does anything change?"

Verify: Review report may have fewer findings if answers resolved ambiguities.

- [ ] **Story 4:** "I run ingestion twice on Session 22 — does it update, not duplicate?"

```bash
uv run scribe ingest tests/fixtures/session_022/summary.pdf --session 22
```

Verify: No new duplicate NPC files appear. Existing notes may be updated. Total file count doesn't double.

- [ ] **Story 5:** "I manually edit an NPC note in Obsidian — does the next ingestion respect my change?"

Open Obsidian, edit an NPC description. Run ingestion again. Verify the agent doesn't overwrite the manual edit (dedup should see the existing note and skip, not recreate).

- [ ] **Story 6:** "Full test suite passes cleanly"

```bash
uv run pytest -v
```

Verify: All tests pass, no regressions.

Document all issues, fix them, re-test. Commit fixes.

---

## Summary

After completing all tasks, Milestone 4 adds:

- **Reviewer module:** 4 quality checks (broken wikilinks, missing fields, duplicate entities, orphaned notes)
- **`scribe review` command:** Runs reviewer, prints color-coded report, logs to vault
- **`scribe ask` command:** Interactive question queue — view, answer, and save agent questions
- **Multi-session robustness:** Dedup verified across sessions, context carries forward
- **User-style testing:** Manual QA on real vault with real Obsidian
