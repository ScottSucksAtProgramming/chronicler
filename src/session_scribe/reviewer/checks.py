"""Individual vault quality check functions.

Each function accepts an ObsidianCLI instance and returns a list of
ReviewFinding objects describing issues found in the vault.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from session_scribe.vault.dedup import find_match

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


def _path_to_link_target(path: str) -> str:
    """Convert a vault path like 'NPCs/Theron.md' to 'Theron'."""
    return _stem(path)


# ---------------------------------------------------------------------------
# Check 1: broken wikilinks
# ---------------------------------------------------------------------------


def check_broken_wikilinks(cli) -> list[ReviewFinding]:
    """Find [[wikilinks]] that do not resolve to any file in the vault.

    A link resolves if its target (case-insensitively) matches the stem of
    any file currently in the vault.

    Args:
        cli: An ObsidianCLI instance.

    Returns:
        List of ReviewFinding with severity WARNING for each broken link.
    """
    all_files = cli.list_files()
    # Build a set of known stems (lower-cased) for O(1) lookup
    known_stems = {_stem(f).lower() for f in all_files}

    findings: list[ReviewFinding] = []
    for path in all_files:
        try:
            content = cli.read(path)
        except Exception:
            continue
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


def check_missing_fields(cli) -> list[ReviewFinding]:
    """Check entity and session notes for missing Description/Summary sections.

    Inspects NPCs, Locations, Factions, and Sessions folders. A note is
    flagged when none of its ``## Heading`` lines match the required section
    for that folder type.

    Args:
        cli: An ObsidianCLI instance.

    Returns:
        List of ReviewFinding with severity WARNING for each missing section.
    """
    findings: list[ReviewFinding] = []

    for folder, required_sections in _REQUIRED_SECTIONS.items():
        notes = cli.find_notes_in_folder(folder)
        for path in notes:
            # Only check notes that actually belong to this folder
            if not path.startswith(folder):
                continue
            try:
                content = cli.read(path)
            except Exception:
                continue
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
                            detail=(
                                f"Missing '{section}' section in {_stem(path)}"
                            ),
                        )
                    )
    return findings


# ---------------------------------------------------------------------------
# Check 3: duplicate entities
# ---------------------------------------------------------------------------


def check_duplicate_entities(cli, folder: str) -> list[ReviewFinding]:
    """Fuzzy-match filenames within *folder* to surface near-duplicates.

    Each filename stem is compared against all previously-seen stems using
    ``find_match``.  A pair is only reported once.

    Args:
        cli: An ObsidianCLI instance.
        folder: Vault folder to inspect (e.g. ``"NPCs/"``).

    Returns:
        List of ReviewFinding with severity WARNING for each suspected pair.
    """
    notes = cli.find_notes_in_folder(folder)
    stems = [_stem(p) for p in notes]

    findings: list[ReviewFinding] = []
    reported: set[frozenset[str]] = set()

    for i, stem in enumerate(stems):
        candidates = stems[:i]  # only previously-seen stems
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


def check_orphaned_notes(cli) -> list[ReviewFinding]:
    """Find entity notes that are not linked from any other note.

    Collects all notes in the entity folders, then scans every note in the
    vault for wikilinks.  Any entity whose stem never appears as a link target
    is considered orphaned.

    Args:
        cli: An ObsidianCLI instance.

    Returns:
        List of ReviewFinding with severity INFO for each orphaned note.
    """
    # Gather entity notes
    entity_notes: list[str] = []
    for folder in _ENTITY_FOLDERS:
        entity_notes.extend(cli.find_notes_in_folder(folder))

    if not entity_notes:
        return []

    entity_stems = {_stem(p).lower(): p for p in entity_notes}

    # Collect all link targets from every note in the vault
    all_files = cli.list_files()
    referenced: set[str] = set()
    for path in all_files:
        try:
            content = cli.read(path)
        except Exception:
            continue
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


def check_timeline_gaps(cli) -> list[ReviewFinding]:
    """Find gaps in session numbering within the Sessions folder.

    Extracts the integer suffix from each session filename (e.g.
    ``Session-003.md`` → 3) and reports any missing numbers in the sequence.

    Args:
        cli: An ObsidianCLI instance.

    Returns:
        List of ReviewFinding with severity WARNING for each gap.
    """
    session_notes = cli.find_notes_in_folder("Sessions/")
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
# Check 6: inconsistencies (NPC affiliations reference missing factions)
# ---------------------------------------------------------------------------


def check_inconsistencies(cli) -> list[ReviewFinding]:
    """Check that NPC affiliation wikilinks resolve to real faction notes.

    Reads every NPC note and looks for affiliation patterns
    (``**Affiliations:**`` or ``Affiliation:`` lines).  Any wikilink target
    on those lines that does not match a file in the Factions folder is
    flagged.

    Args:
        cli: An ObsidianCLI instance.

    Returns:
        List of ReviewFinding with severity WARNING for each missing faction.
    """
    npc_notes = cli.find_notes_in_folder("NPCs/")
    faction_notes = cli.find_notes_in_folder("Factions/")
    faction_stems = {_stem(p).lower() for p in faction_notes}

    # Also build a set of ALL vault file stems for broader resolution
    findings: list[ReviewFinding] = []

    _affiliation_line_re = re.compile(
        r"(?i)(affiliation[s]?\s*[:*]+|^\s*affiliation[s]?\s*:)", re.MULTILINE
    )

    for path in npc_notes:
        try:
            content = cli.read(path)
        except Exception:
            continue

        for line in content.splitlines():
            if re.search(r"(?i)affiliation", line):
                for target in _extract_wikilinks(line):
                    if target.lower() not in faction_stems:
                        findings.append(
                            ReviewFinding(
                                check="inconsistencies",
                                severity=Severity.WARNING,
                                file=path,
                                detail=(
                                    f"NPC '{_stem(path)}' references unknown faction: "
                                    f"[[{target}]]"
                                ),
                            )
                        )
    return findings
