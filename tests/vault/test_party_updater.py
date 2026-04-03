"""Tests for party note maintenance."""

from chronicler.models.context import PlayerCharacter
from chronicler.vault.note_renderer import render_pc_note
from chronicler.vault.party_updater import update_party_note_from_sessions


def test_party_note_backfills_timeline_and_relationships_from_sessions() -> None:
    pc = PlayerCharacter(
        player_name="Tina",
        character_name="Celestine Silverleaf",
        character_class="Sorcerer",
    )
    note = render_pc_note(pc)
    sessions = {
        "Sessions/Session-003.md": (
            "---\n"
            "type: session\n"
            'title: "Session 3: Trouble at Sea"\n'
            "---\n"
            "# Session 3: Trouble at Sea\n\n"
            "## Summary\n\n"
            "[[Celestine Silverleaf]] paralyzed the Oracle with Hold Person.\n\n"
            "## Key Events\n\n"
            "- [[Celestine Silverleaf]] argued with [[Denjin Karr]] about the chest\n"
        )
    }

    updated = update_party_note_from_sessions(note, pc, sessions)

    assert "- [[Session-003]]: [[Celestine Silverleaf]] paralyzed the Oracle with Hold Person." in updated
    assert "- [[Session-003]]: [[Celestine Silverleaf]] argued with [[Denjin Karr]] about the chest" in updated
    assert "- [[Denjin Karr]]" in updated


def test_party_note_updates_are_idempotent() -> None:
    pc = PlayerCharacter(
        player_name="Tina",
        character_name="Celestine Silverleaf",
        character_class="Sorcerer",
    )
    note = render_pc_note(pc)
    sessions = {
        "Sessions/Session-003.md": (
            "---\n"
            "type: session\n"
            'title: "Session 3: Trouble at Sea"\n'
            "---\n"
            "# Session 3: Trouble at Sea\n\n"
            "## Summary\n\n"
            "[[Celestine Silverleaf]] paralyzed the Oracle with Hold Person.\n"
        )
    }

    once = update_party_note_from_sessions(note, pc, sessions)
    twice = update_party_note_from_sessions(once, pc, sessions)

    assert twice.count("[[Session-003]]: [[Celestine Silverleaf]] paralyzed the Oracle with Hold Person.") == 1
