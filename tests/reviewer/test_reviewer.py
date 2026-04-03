"""Tests for the review orchestrator."""

import pytest
from unittest.mock import MagicMock

from session_scribe.reviewer.reviewer import review_vault, ReviewReport
from session_scribe.reviewer.checks import ReviewFinding, Severity


class TestReviewVault:
    def test_review_produces_report(self):
        mock_cli = MagicMock()
        mock_cli.read_all_notes.return_value = {}

        report = review_vault(mock_cli)

        assert isinstance(report, ReviewReport)
        assert isinstance(report.findings, list)
        assert report.total_findings >= 0

    def test_review_aggregates_findings(self):
        mock_cli = MagicMock()
        mock_cli.read_all_notes.return_value = {
            "NPCs/Test.md": "---\ntype: npc\n---\n# Test\n\nLinked to [[Nonexistent]]",
        }

        report = review_vault(mock_cli)
        assert report.total_findings > 0
        assert any(f.check == "broken_wikilinks" for f in report.findings)

    def test_report_summary_counts(self):
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

    def test_review_handles_load_failure(self):
        """If read_all_notes fails, return an error report."""
        mock_cli = MagicMock()
        mock_cli.read_all_notes.side_effect = Exception("CLI down")

        report = review_vault(mock_cli)
        assert any(f.severity == Severity.ERROR for f in report.findings)
        assert any("load" in f.detail.lower() for f in report.findings)
