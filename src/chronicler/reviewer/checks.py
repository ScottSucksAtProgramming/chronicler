"""Individual vault quality check functions.

Each function accepts a vault snapshot (dict mapping path → content) and returns
a list of ReviewFinding objects describing issues found.

The snapshot is loaded once by the orchestrator via ObsidianCLI.read_all_notes()
so that checks never make CLI subprocess calls themselves.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from chronicler.vault.dedup import find_match

# Regex to extract wikilink targets: [[Target]] or [[Target|Alias]]
_WIKILINK_RE = re.compile(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]")

# Folders that hold entity notes
_ENTITY_FOLDERS = ("NPCs/", "Locations/", "Factions/", "Loot/")

# Required H2 section headings by folder
_REQUIRED_SECTIONS: dict[str, list[str]] = {
    "NPCs/": ["Description"],
    "Locations/": ["Description"],
    "Factions/": ["Summary"],
    "Sessions/": ["Summary"],
}

# Type alias for the vault snapshot
VaultSnapshot = dict[str, str]  # path → content


class Severity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


@dataclass
class ReviewFinding:
    """A single quality issue discovered during a vault review."""

    check: str
    severity: Severity
    file: str
    detail: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _stem(path: str) -> str:
    """Return the filename stem (no directory, no extension)."""
    return Path(path).stem


def _extract_wikilinks(content: str) -> list[str]:
    """Return all wikilink targets found in *content*."""
    return _WIKILINK_RE.findall(content)


def _notes_in_folder(snapshot: VaultSnapshot, folder: str) -> dict[str, str]:
    """Filter snapshot to notes within a specific folder."""
    return {p: c for p, c in snapshot.items() if p.startswith(folder)}


# ---------------------------------------------------------------------------
# Check 1: broken wikilinks
# ---------------------------------------------------------------------------


def check_broken_wikilinks(snapshot: VaultSnapshot) -> list[ReviewFinding]:
    """Find [[wikilinks]] that do not resolve to any file in the vault."""
    known_stems = {_stem(f).lower() for f in snapshot}

    findings: list[ReviewFinding] = []
    for path, content in snapshot.items():
        for target in _extract_wikilinks(content):
            if target.lower() not in known_stems:
                findings.append(
                    ReviewFinding(
                        check="broken_wikilinks",
                        severity=Severity.WARNING,
                        file=path,
                        detail=f"Broken link: [[{target}]]",
                    )
                )
    return findings


# ---------------------------------------------------------------------------
# Check 2: missing required sections
# ---------------------------------------------------------------------------


def check_missing_fields(snapshot: VaultSnapshot) -> list[ReviewFinding]:
    """Check entity and session notes for missing Description/Summary sections."""
    findings: list[ReviewFinding] = []

    for folder, required_sections in _REQUIRED_SECTIONS.items():
        for path, content in _notes_in_folder(snapshot, folder).items():
            headings = {
                m.group(1).strip().lower()
                for m in re.finditer(r"^##\s+(.+)$", content, re.MULTILINE)
            }
            for section in required_sections:
                if section.lower() not in headings:
                    findings.append(
                        ReviewFinding(
                            check="missing_fields",
                            severity=Severity.WARNING,
                            file=path,
                            detail=f"Missing '{section}' section in {_stem(path)}",
                        )
                    )
    return findings


# ---------------------------------------------------------------------------
# Check 3: duplicate entities
# ---------------------------------------------------------------------------


def check_duplicate_entities(snapshot: VaultSnapshot, folder: str) -> list[ReviewFinding]:
    """Fuzzy-match filenames within *folder* to surface near-duplicates."""
    notes = list(_notes_in_folder(snapshot, folder).keys())
    stems = [_stem(p) for p in notes]

    findings: list[ReviewFinding] = []
    reported: set[frozenset[str]] = set()

    for i, stem in enumerate(stems):
        candidates = stems[:i]
        if not candidates:
            continue
        match = find_match(stem, candidates, threshold=80)
        if match and match != stem:
            pair = frozenset({stem, match})
            if pair not in reported:
                reported.add(pair)
                findings.append(
                    ReviewFinding(
                        check="duplicate_entities",
                        severity=Severity.WARNING,
                        file=folder,
                        detail=f"Possible duplicate: '{stem}' and '{match}'",
                    )
                )
    return findings


# ---------------------------------------------------------------------------
# Check 4: orphaned notes
# ---------------------------------------------------------------------------


def check_orphaned_notes(snapshot: VaultSnapshot) -> list[ReviewFinding]:
    """Find entity notes that are not linked from any other note."""
    entity_notes: dict[str, str] = {}
    for folder in _ENTITY_FOLDERS:
        entity_notes.update(_notes_in_folder(snapshot, folder))

    if not entity_notes:
        return []

    entity_stems = {_stem(p).lower(): p for p in entity_notes}

    # Collect all link targets from every note
    referenced: set[str] = set()
    for content in snapshot.values():
        for target in _extract_wikilinks(content):
            referenced.add(target.lower())

    findings: list[ReviewFinding] = []
    for stem_lower, path in entity_stems.items():
        if stem_lower not in referenced:
            findings.append(
                ReviewFinding(
                    check="orphaned_notes",
                    severity=Severity.INFO,
                    file=path,
                    detail=f"Orphaned note: '{_stem(path)}' is not linked from any other note",
                )
            )
    return findings


# ---------------------------------------------------------------------------
# Check 5: timeline gaps
# ---------------------------------------------------------------------------


def check_timeline_gaps(snapshot: VaultSnapshot) -> list[ReviewFinding]:
    """Find gaps in session numbering within the Sessions folder."""
    session_notes = _notes_in_folder(snapshot, "Sessions/")
    numbers: list[int] = []
    for path in session_notes:
        m = re.search(r"(\d+)", _stem(path))
        if m:
            numbers.append(int(m.group(1)))

    if len(numbers) < 2:
        return []

    numbers.sort()
    findings: list[ReviewFinding] = []
    for i in range(numbers[0], numbers[-1] + 1):
        if i not in numbers:
            findings.append(
                ReviewFinding(
                    check="timeline_gaps",
                    severity=Severity.WARNING,
                    file="Sessions/",
                    detail=f"Missing session: Session-{i:03d} not found in vault",
                )
            )
    return findings


# ---------------------------------------------------------------------------
# Check 6: inconsistencies
# ---------------------------------------------------------------------------


def check_inconsistencies(snapshot: VaultSnapshot) -> list[ReviewFinding]:
    """Check that NPC affiliation wikilinks resolve to real faction notes."""
    npc_notes = _notes_in_folder(snapshot, "NPCs/")
    faction_stems = {_stem(p).lower() for p in _notes_in_folder(snapshot, "Factions/")}

    findings: list[ReviewFinding] = []

    for path, content in npc_notes.items():
        for line in content.splitlines():
            if re.search(r"(?i)affiliation", line):
                for target in _extract_wikilinks(line):
                    if target.lower() not in faction_stems:
                        findings.append(
                            ReviewFinding(
                                check="inconsistencies",
                                severity=Severity.WARNING,
                                file=path,
                                detail=f"NPC '{_stem(path)}' references unknown faction: [[{target}]]",
                            )
                        )
    return findings
