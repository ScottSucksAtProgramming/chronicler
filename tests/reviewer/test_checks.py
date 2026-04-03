"""Tests for individual vault quality checks."""

import pytest

from session_scribe.reviewer.checks import (
    check_broken_wikilinks,
    check_missing_fields,
    check_duplicate_entities,
    check_orphaned_notes,
    check_timeline_gaps,
    check_inconsistencies,
    ReviewFinding,
    Severity,
    VaultSnapshot,
)


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
    def test_finds_broken_link(self):
        snapshot: VaultSnapshot = {
            "NPCs/Theron.md": "# Theron\n\nAffiliated with [[Nonexistent Faction]]",
            "Sessions/Session-001.md": "# Session 1\n\nMet [[Theron]]",
        }
        findings = check_broken_wikilinks(snapshot)
        broken = [f for f in findings if "Nonexistent Faction" in f.detail]
        assert len(broken) >= 1
        assert broken[0].severity == Severity.WARNING

    def test_no_broken_links(self):
        snapshot: VaultSnapshot = {
            "NPCs/Theron.md": "# Theron\n\nA ranger.",
        }
        findings = check_broken_wikilinks(snapshot)
        assert findings == []

    def test_valid_link_resolves(self):
        snapshot: VaultSnapshot = {
            "NPCs/Theron.md": "# Theron\n\nSee [[Sylvie]].",
            "NPCs/Sylvie.md": "# Sylvie\n\nA leader.",
        }
        findings = check_broken_wikilinks(snapshot)
        assert findings == []


class TestCheckMissingFields:
    def test_npc_missing_description(self):
        snapshot: VaultSnapshot = {
            "NPCs/Theron.md": "---\ntype: npc\n---\n# Theron\n",
        }
        findings = check_missing_fields(snapshot)
        assert any("description" in f.detail.lower() for f in findings)

    def test_complete_npc_no_findings(self):
        snapshot: VaultSnapshot = {
            "NPCs/Theron.md": (
                "---\ntype: npc\n---\n# Theron\n\n"
                "## Description\n\nA ranger from the north.\n"
            ),
        }
        findings = check_missing_fields(snapshot)
        npc_findings = [f for f in findings if "Theron" in f.detail]
        assert npc_findings == []

    def test_session_missing_summary(self):
        snapshot: VaultSnapshot = {
            "Sessions/Session-001.md": "---\ntype: session\n---\n# Session 1\n",
        }
        findings = check_missing_fields(snapshot)
        assert any("summary" in f.detail.lower() for f in findings)


class TestCheckDuplicateEntities:
    def test_finds_near_duplicate_npcs(self):
        snapshot: VaultSnapshot = {
            "NPCs/Sylvie.md": "# Sylvie",
            "NPCs/Sylvie Starwater.md": "# Sylvie Starwater",
        }
        findings = check_duplicate_entities(snapshot, "NPCs/")
        assert len(findings) >= 1
        assert findings[0].severity == Severity.WARNING

    def test_no_duplicates(self):
        snapshot: VaultSnapshot = {
            "NPCs/Theron.md": "# Theron",
            "NPCs/Sylvie.md": "# Sylvie",
        }
        findings = check_duplicate_entities(snapshot, "NPCs/")
        assert findings == []


class TestCheckOrphanedNotes:
    def test_finds_orphaned_npc(self):
        snapshot: VaultSnapshot = {
            "NPCs/Orphan.md": "# Orphan\n\nNobody links here.",
            "Sessions/Session-001.md": "# Session 1\n\nMet [[Theron]].",
        }
        findings = check_orphaned_notes(snapshot)
        assert any("Orphan" in f.detail for f in findings)

    def test_linked_note_not_orphaned(self):
        snapshot: VaultSnapshot = {
            "NPCs/Theron.md": "# Theron",
            "Sessions/Session-001.md": "# Session 1\n\nMet [[Theron]].",
        }
        findings = check_orphaned_notes(snapshot)
        theron_findings = [f for f in findings if "Theron" in f.detail]
        assert theron_findings == []


class TestCheckTimelineGaps:
    def test_finds_gap(self):
        snapshot: VaultSnapshot = {
            "Sessions/Session-001.md": "",
            "Sessions/Session-002.md": "",
            "Sessions/Session-005.md": "",
        }
        findings = check_timeline_gaps(snapshot)
        assert len(findings) >= 1
        assert any("003" in f.detail for f in findings)

    def test_no_gap(self):
        snapshot: VaultSnapshot = {
            "Sessions/Session-001.md": "",
            "Sessions/Session-002.md": "",
            "Sessions/Session-003.md": "",
        }
        findings = check_timeline_gaps(snapshot)
        assert findings == []

    def test_single_session_no_findings(self):
        snapshot: VaultSnapshot = {
            "Sessions/Session-022.md": "",
        }
        findings = check_timeline_gaps(snapshot)
        assert findings == []


class TestCheckInconsistencies:
    def test_finds_orphaned_affiliation(self):
        snapshot: VaultSnapshot = {
            "NPCs/Theron.md": (
                "---\ntype: npc\n---\n# Theron\n\n"
                "**Affiliations:** [[Missing Faction]]"
            ),
        }
        findings = check_inconsistencies(snapshot)
        assert any("Missing Faction" in f.detail for f in findings)

    def test_valid_affiliation_no_finding(self):
        snapshot: VaultSnapshot = {
            "NPCs/Theron.md": (
                "---\ntype: npc\n---\n# Theron\n\n"
                "**Affiliations:** [[The Cult]]"
            ),
            "Factions/The Cult.md": "# The Cult",
        }
        findings = check_inconsistencies(snapshot)
        assert findings == []
