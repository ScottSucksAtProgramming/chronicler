"""Vault review orchestrator.

Runs all quality checks against a vault and returns a consolidated
ReviewReport with aggregated findings.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

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

logger = logging.getLogger(__name__)

# Entity folders that get individual duplicate-entity checks
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
    """Run a single check function, catching any exception and returning an
    ERROR finding in its place so the rest of the review can continue."""
    try:
        return fn(*args)
    except Exception as exc:  # noqa: BLE001
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

    Each check is isolated — if one raises an exception the others still run.

    Args:
        cli: An ObsidianCLI instance.

    Returns:
        A ReviewReport containing all findings from every check.
    """
    all_findings: list[ReviewFinding] = []

    # Core checks (single-argument)
    all_findings.extend(_run_check("broken_wikilinks", check_broken_wikilinks, cli))
    all_findings.extend(_run_check("missing_fields", check_missing_fields, cli))
    all_findings.extend(_run_check("orphaned_notes", check_orphaned_notes, cli))
    all_findings.extend(_run_check("timeline_gaps", check_timeline_gaps, cli))
    all_findings.extend(_run_check("inconsistencies", check_inconsistencies, cli))

    # Duplicate-entity checks per folder
    for folder in _DUPLICATE_FOLDERS:
        all_findings.extend(
            _run_check("duplicate_entities", check_duplicate_entities, cli, folder)
        )

    report = ReviewReport(findings=all_findings)
    logger.info(
        "Vault review complete: %d findings (%d errors, %d warnings, %d info)",
        report.total_findings,
        report.error_count,
        report.warning_count,
        report.info_count,
    )
    return report
