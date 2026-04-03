"""Vault review orchestrator.

Loads all notes once via ObsidianCLI.read_all_notes() and passes the
snapshot to each quality check — avoiding per-check CLI subprocess calls.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from session_scribe.reviewer.checks import (
    ReviewFinding,
    Severity,
    VaultSnapshot,
    check_broken_wikilinks,
    check_duplicate_entities,
    check_inconsistencies,
    check_missing_fields,
    check_orphaned_notes,
    check_timeline_gaps,
)

logger = logging.getLogger(__name__)

_DUPLICATE_FOLDERS = ("NPCs/", "Locations/", "Factions/")


@dataclass
class ReviewReport:
    """Aggregated results from a full vault review."""

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


def _run_check(name: str, fn, *args) -> list[ReviewFinding]:
    """Run a single check, converting exceptions to ERROR findings."""
    try:
        return fn(*args)
    except Exception as exc:
        logger.warning("Check '%s' raised an exception: %s", name, exc)
        return [
            ReviewFinding(
                check=name,
                severity=Severity.ERROR,
                file="",
                detail=f"Check failed with exception: {exc}",
            )
        ]


def review_vault(cli) -> ReviewReport:
    """Run all quality checks against the vault and return a ReviewReport.

    Loads all notes once via cli.read_all_notes() for performance,
    then passes the snapshot to each check function.
    """
    all_findings: list[ReviewFinding] = []

    # Load all notes once (filesystem bulk read — fast)
    try:
        snapshot: VaultSnapshot = cli.read_all_notes()
        logger.info("Loaded %d notes for review", len(snapshot))
    except Exception as exc:
        logger.error("Failed to load vault notes: %s", exc)
        return ReviewReport(findings=[
            ReviewFinding(
                check="load_vault",
                severity=Severity.ERROR,
                file="",
                detail=f"Failed to load vault: {exc}",
            )
        ])

    # Run all checks against the snapshot
    all_findings.extend(_run_check("broken_wikilinks", check_broken_wikilinks, snapshot))
    all_findings.extend(_run_check("missing_fields", check_missing_fields, snapshot))
    all_findings.extend(_run_check("orphaned_notes", check_orphaned_notes, snapshot))
    all_findings.extend(_run_check("timeline_gaps", check_timeline_gaps, snapshot))
    all_findings.extend(_run_check("inconsistencies", check_inconsistencies, snapshot))

    for folder in _DUPLICATE_FOLDERS:
        all_findings.extend(
            _run_check("duplicate_entities", check_duplicate_entities, snapshot, folder)
        )

    report = ReviewReport(findings=all_findings)
    logger.info(
        "Vault review complete: %d findings (%d errors, %d warnings, %d info)",
        report.total_findings, report.error_count, report.warning_count, report.info_count,
    )
    return report
