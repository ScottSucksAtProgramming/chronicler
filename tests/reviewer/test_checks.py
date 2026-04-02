"""Tests for individual vault quality checks."""

import pytest
from unittest.mock import MagicMock

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


@pytest.fixture
def mock_cli():
    cli = MagicMock()
    cli.vault_name = "Test Vault"
    cli.list_files.return_value = []
    cli.find_notes_in_folder.return_value = []
    return cli


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
        mock_cli.find_notes_in_folder.side_effect = lambda folder: {
            "NPCs/": ["NPCs/Orphan.md"],
            "Locations/": [],
            "Factions/": [],
            "Loot/": [],
        }.get(folder, [])
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
        }.get(folder, [])
        mock_cli.read.return_value = (
            "---\ntype: npc\n---\n# Theron\n\n"
            "**Affiliations:** [[Missing Faction]]"
        )
        findings = check_inconsistencies(mock_cli)
        assert any("Missing Faction" in f.detail for f in findings)
