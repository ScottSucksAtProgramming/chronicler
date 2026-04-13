"""Tests for deterministic vault maintenance improvements."""

from unittest.mock import MagicMock

from chronicler.vault.improver import improve_vault


def _build_cli(snapshot: dict[str, str]) -> MagicMock:
    cli = MagicMock()
    cli.read_all_notes.return_value = snapshot
    cli.create = MagicMock()
    return cli


class TestImproveVault:
    def test_improve_backfills_location_parent_from_explicit_description(self):
        snapshot = {
            "Locations/Laguna Nera.md": (
                "---\n"
                "type: location\n"
                "name: Laguna Nera\n"
                "---\n"
                "# Laguna Nera\n"
            ),
            "Locations/Mist Alley.md": (
                "---\n"
                "type: location\n"
                "name: Mist Alley\n"
                "connected_to: [Laguna Nera]\n"
                "---\n"
                "# Mist Alley\n\n"
                "## Description\n\n"
                "A district in Laguna Nera containing the Perfumed Chapel.\n"
            ),
        }
        cli = _build_cli(snapshot)

        report = improve_vault(cli)

        assert report.changed_count >= 1
        updated = [
            call.args[1]
            for call in cli.create.call_args_list
            if call.args[0] == "Locations/Mist Alley.md"
        ][-1]
        assert 'parent_location: "[[Laguna Nera]]"' in updated
        assert "connected_to:" not in updated
        assert "**Belongs To:** [[Laguna Nera]]" in updated
        assert "## Location Relationships" not in updated

    def test_improve_rebuilds_parent_contains_links_from_existing_locations(self):
        snapshot = {
            "Locations/Laguna Nera.md": (
                "---\n"
                "type: location\n"
                "name: Laguna Nera\n"
                "---\n"
                "# Laguna Nera\n"
            ),
            "Locations/Mist Alley.md": (
                "---\n"
                "type: location\n"
                "name: Mist Alley\n"
                "connected_to: [Laguna Nera]\n"
                "---\n"
                "# Mist Alley\n\n"
                "## Description\n\n"
                "A district in Laguna Nera.\n"
            ),
            "Locations/Floating Market.md": (
                "---\n"
                "type: location\n"
                "name: Floating Market\n"
                "---\n"
                "# Floating Market\n\n"
                "## Description\n\n"
                "A district in Laguna Nera featuring markets on the water.\n"
            ),
        }
        cli = _build_cli(snapshot)

        improve_vault(cli)

        updated = [
            call.args[1]
            for call in cli.create.call_args_list
            if call.args[0] == "Locations/Laguna Nera.md"
        ][-1]
        assert "**Contains:** [[Floating Market]], [[Mist Alley]]" in updated
        assert "## Location Relationships" not in updated

    def test_improve_removes_visible_source_update_sections_from_locations(self):
        snapshot = {
            "Locations/Laguna Nera.md": (
                "---\n"
                "type: location\n"
                "name: Laguna Nera\n"
                "---\n"
                "# Laguna Nera\n\n"
                "## Description\n\n"
                "Original summary.\n\n"
                "## Source Updates\n\n"
                "<!-- chronicler:source-updates:start -->\n"
                "### Imported source: Laguna Nera.md\n\n"
                "A labyrinthine city of canals.\n"
                "<!-- chronicler:source-updates:end -->\n"
            ),
        }
        cli = _build_cli(snapshot)

        improve_vault(cli)

        updated = [
            call.args[1]
            for call in cli.create.call_args_list
            if call.args[0] == "Locations/Laguna Nera.md"
        ][-1]
        assert "## Source Updates" not in updated
        assert "### Imported source:" not in updated
        assert "A labyrinthine city of canals." in updated

    def test_improve_cleans_malformed_source_update_labels_and_keeps_single_description_heading(
        self,
    ):
        snapshot = {
            "Locations/Anchor Bridge.md": (
                "---\n"
                "type: location\n"
                "name: Anchor Bridge\n"
                "---\n"
                "# Anchor Bridge\n"
                "**Belongs To:** [[Sestiere Aureo]]\n\n"
                "## Description\n"
                "A point of interest located within The Rusted Docks district of Laguna Nera.\n\n"
                "## Source Updates\n\n"
                "<!-- chronicler:source-updates:start -->\n"
                "### Imported source: Laguna Nera.md\n\n"
                "A location within Sestiere Aureo district.### [[Laguna Nera]].md\n\n"
                "A landmark bridge over the canals.\n"
                "<!-- chronicler:source-updates:end -->\n"
            ),
        }
        cli = _build_cli(snapshot)

        improve_vault(cli)

        updated = [
            call.args[1]
            for call in cli.create.call_args_list
            if call.args[0] == "Locations/Anchor Bridge.md"
        ][-1]
        assert updated.count("## Description") == 1
        assert "### [[Laguna Nera]].md" not in updated
        assert "### Imported source:" not in updated
        assert "A landmark bridge over the canals." in updated

    def test_improve_cleans_inline_source_labels_already_baked_into_description(self):
        snapshot = {
            "Locations/Sestiere Aureo.md": (
                "---\n"
                "type: location\n"
                "name: Sestiere Aureo\n"
                'parent_location: "[[Laguna Nera]]"\n'
                "---\n"
                "# Sestiere Aureo\n\n"
                "**Belongs To:** [[Laguna Nera]]\n\n"
                "## Description\n\n"
                "A district in Laguna Nera.### [[Laguna Nera]].md\n\n"
                "A district in Laguna Nera, featuring golden architecture.\n"
            ),
        }
        cli = _build_cli(snapshot)

        improve_vault(cli)

        updated = [
            call.args[1]
            for call in cli.create.call_args_list
            if call.args[0] == "Locations/Sestiere Aureo.md"
        ][-1]
        assert "### [[Laguna Nera]].md" not in updated
        assert updated.count("## Description") == 1

    def test_improve_links_body_mentions_from_canonical_note_names(self):
        snapshot = {
            "NPCs/Salty McKeel.md": (
                "---\n"
                "type: npc\n"
                "name: Salty McKeel\n"
                'aliases: ["Salty"]\n'
                "first_appeared: Session-003\n"
                "---\n"
                "# Salty McKeel\n"
            ),
            "Sessions/Session-003.md": (
                "---\n"
                "type: session\n"
                "title: Escape\n"
                "---\n"
                "# Session 3: Escape\n\n"
                "## Summary\n\n"
                "The party met Salty McKeel below deck.\n"
            ),
        }
        cli = _build_cli(snapshot)

        improve_vault(cli)

        rewritten = next(
            call.args[1]
            for call in cli.create.call_args_list
            if call.args[0] == "Sessions/Session-003.md"
        )
        assert "The party met [[Salty McKeel]] below deck." in rewritten

    def test_improve_links_known_entities_in_supported_notes(self):
        snapshot = {
            "NPCs/Theron.md": (
                "---\n"
                "type: npc\n"
                "name: Theron\n"
                "first_appeared: Session-001\n"
                "---\n"
                "# Theron\n"
            ),
            "Locations/The Black Spire.md": (
                "---\n"
                "type: location\n"
                "name: The Black Spire\n"
                "first_appeared: Session-001\n"
                "---\n"
                "# The Black Spire\n"
            ),
            "Sessions/Session-002.md": (
                "---\n"
                "type: session\n"
                "title: Session 2\n"
                "---\n"
                "# Session 2\n\n"
                "## Summary\n\n"
                "Theron led the party to The Black Spire.\n"
            ),
        }
        cli = _build_cli(snapshot)

        report = improve_vault(cli)

        assert report.changed_count >= 1
        session_rewrite = next(
            call.args[1]
            for call in cli.create.call_args_list
            if call.args[0] == "Sessions/Session-002.md"
        )
        assert (
            session_rewrite == "---\n"
            "type: session\n"
            'title: "Session 2"\n'
            "---\n"
            "# Session 2\n\n"
            "## Summary\n\n"
            "[[Theron]] led the party to [[The Black Spire]].\n"
        )

    def test_improve_normalizes_reference_frontmatter(self):
        snapshot = {
            "NPCs/Theron.md": (
                "---\n"
                "type: npc\n"
                "name: Theron\n"
                "first_appeared: Session-001\n"
                "affiliations: [The Guild]\n"
                "---\n"
                "# Theron\n"
            ),
            "Factions/The Guild.md": (
                "---\n"
                "type: faction\n"
                "name: The Guild\n"
                "first_appeared: Session-001\n"
                "---\n"
                "# The Guild\n"
            ),
            "Sessions/Session-001.md": (
                "---\n" "type: session\n" "title: Intro\n" "---\n" "# Intro\n"
            ),
        }
        cli = _build_cli(snapshot)

        report = improve_vault(cli)

        assert report.changed_count >= 2
        rewritten_notes = [call.args[1] for call in cli.create.call_args_list]
        assert any(
            'first_appeared: "[[Session-001]]"' in note for note in rewritten_notes
        )
        assert any(
            'affiliations: ["[[The Guild]]"]' in note for note in rewritten_notes
        )

    def test_improve_creates_question_for_ambiguous_alias(self):
        snapshot = {
            "NPCs/Captain Rook.md": (
                "---\n"
                "type: npc\n"
                "name: Captain Rook\n"
                "aliases: [Rook]\n"
                "first_appeared: Session-001\n"
                "---\n"
                "# Captain Rook\n"
            ),
            "NPCs/Rook the Smuggler.md": (
                "---\n"
                "type: npc\n"
                "name: Rook the Smuggler\n"
                "aliases: [Rook]\n"
                "first_appeared: Session-002\n"
                "---\n"
                "# Rook the Smuggler\n"
            ),
            "Sessions/Session-003.md": (
                "---\n"
                "type: session\n"
                "title: Trouble at the Docks\n"
                "---\n"
                "# Trouble at the Docks\n\n"
                "## Summary\n\n"
                "Rook warned the party to stay quiet.\n"
            ),
        }
        cli = _build_cli(snapshot)

        report = improve_vault(cli)

        assert report.question_count == 1
        question_path, question_content = next(
            call.args
            for call in cli.create.call_args_list
            if call.args[0].startswith("_Agent/Questions/")
        )
        assert question_path.startswith("_Agent/Questions/")
        assert "ambiguous_entity_reference" in question_content
        assert "Rook" in question_content
        assert "Session-003.md" in question_content

    def test_improve_creates_high_signal_location_relationship_question(self):
        snapshot = {
            "Locations/Venom Alley.md": (
                "---\n"
                "type: location\n"
                "name: Venom Alley\n"
                "---\n"
                "# Venom Alley\n\n"
                "## Description\n\n"
                "A dangerous quarter near the Floating Market and Mist Alley.\n"
            ),
        }
        cli = _build_cli(snapshot)

        report = improve_vault(cli)

        assert report.question_count == 1
        question_path, question_content = next(
            call.args
            for call in cli.create.call_args_list
            if call.args[0].startswith("_Agent/Questions/")
        )
        assert "location_relationship_missing" in question_content
        assert "Venom Alley" in question_content
        assert "nearby locations" in question_content.lower()
        assert question_path.startswith("_Agent/Questions/")

    def test_improve_does_not_repeat_existing_location_relationship_question(self):
        snapshot = {
            "Locations/Venom Alley.md": (
                "---\n"
                "type: location\n"
                "name: Venom Alley\n"
                "---\n"
                "# Venom Alley\n\n"
                "## Description\n\n"
                "A district or notable area within Laguna Nera.\n"
            ),
            "_Agent/Questions/venom-alley-which-larger-location-does-venom-alley-belo.md": (
                "---\n"
                "type: agent-question\n"
                "priority: medium\n"
                "---\n\n"
                "# Which larger location does Venom Alley belong to?\n"
            ),
        }
        cli = _build_cli(snapshot)

        report = improve_vault(cli)

        assert report.question_count == 0

    def test_improve_caps_location_relationship_questions_per_run(self):
        snapshot = {
            f"Locations/District {i}.md": (
                "---\n"
                "type: location\n"
                f"name: District {i}\n"
                "---\n"
                f"# District {i}\n\n"
                "## Description\n\n"
                "A dangerous quarter near the Floating Market and Mist Alley.\n"
            )
            for i in range(1, 8)
        }
        cli = _build_cli(snapshot)

        report = improve_vault(cli)

        assert report.question_count == 5

    def test_improve_uses_agent_memory_aliases_when_unambiguous(self):
        snapshot = {
            "_Agent/Memory/entity-aliases.md": (
                "---\n"
                "type: agent-memory\n"
                "---\n\n"
                "The Black Cherry: Small Merchant Vessel\n"
            ),
            "Locations/Small Merchant Vessel.md": (
                "---\n"
                "type: location\n"
                "name: Small Merchant Vessel\n"
                "first_appeared: Session-002\n"
                "---\n"
                "# Small Merchant Vessel\n"
            ),
            "Sessions/Session-002.md": (
                "---\n"
                "type: session\n"
                "title: Escape\n"
                "---\n"
                "# Escape\n\n"
                "## Summary\n\n"
                "The Black Cherry carried the party to shore.\n"
            ),
        }
        cli = _build_cli(snapshot)

        report = improve_vault(cli)

        assert report.changed_count >= 1
        rewritten = [
            call.args[1]
            for call in cli.create.call_args_list
            if call.args[0] == "Sessions/Session-002.md"
        ][-1]
        assert (
            "[[Small Merchant Vessel|The Black Cherry]] carried the party to shore."
            in rewritten
        )

    def test_improve_normalizes_duplicated_session_heading(self):
        snapshot = {
            "Sessions/Session-003.md": (
                "---\n"
                "type: session\n"
                'title: "Session 3: The Sloop Dogg"\n'
                "---\n"
                "# Session 3: Session 3: The Sloop Dogg\n\n"
                "## Summary\n\n"
                "The party escaped.\n"
            ),
        }
        cli = _build_cli(snapshot)

        improve_vault(cli)

        rewritten = next(
            call.args[1]
            for call in cli.create.call_args_list
            if call.args[0] == "Sessions/Session-003.md"
        )
        assert "# Session 3: The Sloop Dogg" in rewritten
        assert "# Session 3: Session 3:" not in rewritten

    def test_improve_backfills_party_note_timeline_from_sessions(self):
        snapshot = {
            "Party/Celestine Silverleaf.md": (
                "---\n"
                "type: player-character\n"
                "player_name: Tina\n"
                "character_name: Celestine Silverleaf\n"
                "character_class: Sorcerer\n"
                'alias: ["Celestine"]\n'
                "---\n"
                "# Celestine Silverleaf\n\n"
                "## Overview\n\n"
                "Celestine Silverleaf is played by Tina. They are a Sorcerer.\n\n"
                "## Aliases\n\n"
                "- Celestine\n\n"
                "## Known Facts\n\n"
                "- **Player:** Tina\n"
                "- **Class:** Sorcerer\n\n"
                "## Timeline\n\n"
                "_No timeline entries yet._\n\n"
                "## Relationships\n\n"
                "_No relationships recorded yet._\n\n"
                "## Notable Items\n\n"
                "_No notable items recorded yet._\n\n"
                "## Open Questions\n\n"
                "_No open questions._\n"
            ),
            "Sessions/Session-003.md": (
                "---\n"
                "type: session\n"
                'title: "Session 3: Trouble at Sea"\n'
                "---\n"
                "# Session 3: Trouble at Sea\n\n"
                "## Summary\n\n"
                "Celestine paralyzed the Oracle with Hold Person.\n"
            ),
        }
        cli = _build_cli(snapshot)

        report = improve_vault(cli)

        assert report.changed_count >= 1
        updated_party = [
            call.args[1]
            for call in cli.create.call_args_list
            if call.args[0] == "Party/Celestine Silverleaf.md"
        ][-1]
        assert (
            "- [[Session-003]]: [[Celestine Silverleaf|Celestine]] paralyzed the Oracle with Hold Person."
            in updated_party
        )

    def test_improve_uses_party_alias_field_for_body_linking(self):
        snapshot = {
            "Party/Celestine Silverleaf.md": (
                "---\n"
                "type: player-character\n"
                "player_name: Tina\n"
                "character_name: Celestine Silverleaf\n"
                "character_class: Sorcerer\n"
                'alias: ["Celestine"]\n'
                "---\n"
                "# Celestine Silverleaf\n"
            ),
            "Sessions/Session-003.md": (
                "---\n"
                "type: session\n"
                'title: "Session 3: Trouble at Sea"\n'
                "---\n"
                "# Session 3: Trouble at Sea\n\n"
                "## Summary\n\n"
                "Celestine paralyzed the Oracle with Hold Person.\n"
            ),
        }
        cli = _build_cli(snapshot)

        improve_vault(cli)

        updated_session = next(
            call.args[1]
            for call in cli.create.call_args_list
            if call.args[0] == "Sessions/Session-003.md"
        )
        assert (
            "[[Celestine Silverleaf|Celestine]] paralyzed the Oracle with Hold Person."
            in updated_session
        )

    def test_improve_avoids_partial_links_inside_longer_party_names(self):
        snapshot = {
            "Party/Severian 'Seven' Emberwatch.md": (
                "---\n"
                "type: player-character\n"
                "player_name: Fabio\n"
                "character_name: Severian “Seven” Emberwatch\n"
                "character_class: Warlock\n"
                'alias: ["Seven", "Severian"]\n'
                "---\n"
                "# Severian “Seven” Emberwatch\n"
            ),
            "Party/Antoni 'Boney Toney' Deleoro.md": (
                "---\n"
                "type: player-character\n"
                "player_name: Zach\n"
                "character_name: Antoni ‘Boney Toney’ Deleoro\n"
                "character_class: Bard\n"
                'alias: ["Boney Toney"]\n'
                "---\n"
                "# Antoni ‘Boney Toney’ Deleoro\n"
            ),
            "Sessions/Session-003.md": (
                "---\n"
                "type: session\n"
                'title: "Session 3: Trouble at Sea"\n'
                "---\n"
                "# Session 3: Trouble at Sea\n\n"
                "## Summary\n\n"
                "Severian Emberwatch spoke with Anthony 'Boney Toney' Deleoro below deck.\n"
            ),
        }
        cli = _build_cli(snapshot)

        improve_vault(cli)

        updated_session = [
            call.args[1]
            for call in cli.create.call_args_list
            if call.args[0] == "Sessions/Session-003.md"
        ][-1]
        assert (
            "[[Severian 'Seven' Emberwatch|Severian Emberwatch]] spoke with"
            in updated_session
        )
        assert "Anthony '[[Antoni" not in updated_session
        assert (
            "[[Severian 'Seven' Emberwatch|Severian]] Emberwatch" not in updated_session
        )

    def test_improve_does_not_self_link_or_duplicate_alias_lines_in_party_notes(self):
        snapshot = {
            "Party/Hopscotch.md": (
                "---\n"
                "type: player-character\n"
                "player_name: Blaze\n"
                "character_name: Hopscotch\n"
                "character_class: Bard\n"
                'alias: ["Hop"]\n'
                "---\n"
                "# Hopscotch\n\n"
                "## Overview\n\n"
                "Hopscotch is played by Blaze. They are a Bard.\n\n"
                "## Aliases\n\n"
                "- Hop\n\n"
                "## Known Facts\n\n"
                "- **Player:** Blaze\n"
                "- **Class:** Bard\n\n"
                "## Timeline\n\n"
                "_No timeline entries yet._\n\n"
                "## Relationships\n\n"
                "_No relationships recorded yet._\n\n"
                "## Notable Items\n\n"
                "_No notable items recorded yet._\n\n"
                "## Open Questions\n\n"
                "_No open questions._\n"
            ),
        }
        cli = _build_cli(snapshot)

        improve_vault(cli)

        updated_party = [
            call.args[1]
            for call in cli.create.call_args_list
            if call.args[0] == "Party/Hopscotch.md"
        ][-1]
        assert "[[Hopscotch]] is played by Blaze" not in updated_party
        assert "- [[Hopscotch|Hop]]" not in updated_party
        assert updated_party.count("- Hop") == 1

    def test_improve_normalizes_legacy_quote_style_party_links(self):
        snapshot = {
            "Party/Severian 'Seven' Emberwatch.md": (
                "---\n"
                "type: player-character\n"
                "player_name: Fabio\n"
                "character_name: Severian “Seven” Emberwatch\n"
                "character_class: Warlock\n"
                'alias: ["Seven", "Severian"]\n'
                "---\n"
                "# Severian 'Seven' Emberwatch\n\n"
                "## Overview\n\n"
                "[[Severian “Seven” Emberwatch]] is played by Fabio. They are a Warlock.\n\n"
                "## Aliases\n\n"
                "- [[Severian “Seven” Emberwatch|Seven]]\n"
                "- [[Severian “Seven” Emberwatch|Severian]]\n"
                "- Seven\n"
                "- Severian\n\n"
                "## Known Facts\n\n"
                "- **Player:** Fabio\n"
                "- **Class:** Warlock\n\n"
                "## Timeline\n\n"
                "- [[Session-002]]: [[Severian 'Seven' Emberwatch|Seven]] snatches the chest from the pool\n\n"
                "## Relationships\n\n"
                "- [[Severian 'Seven' Emberwatch]]\n"
                "- [[Antoni 'Boney Toney' Deleoro]]\n\n"
                "## Notable Items\n\n"
                "_No notable items recorded yet._\n\n"
                "## Open Questions\n\n"
                "_No open questions._\n"
            ),
            "Party/Antoni 'Boney Toney' Deleoro.md": (
                "---\n"
                "type: player-character\n"
                "player_name: Zach\n"
                "character_name: Antoni ‘Boney Toney’ Deleoro\n"
                "character_class: Bard\n"
                'alias: ["Boney Toney"]\n'
                "---\n"
                "# Antoni 'Boney Toney' Deleoro\n"
            ),
        }
        cli = _build_cli(snapshot)

        improve_vault(cli)

        updated_party = [
            call.args[1]
            for call in cli.create.call_args_list
            if call.args[0] == "Party/Severian 'Seven' Emberwatch.md"
        ][-1]
        assert "[[Severian “Seven” Emberwatch|Seven]]" not in updated_party
        assert "[[Severian “Seven” Emberwatch]]" not in updated_party
        assert "[[Severian 'Seven' Emberwatch|Seven]]" in updated_party
        assert "[[Severian 'Seven' Emberwatch]]" not in updated_party
        assert "- [[Antoni 'Boney Toney' Deleoro]]" in updated_party

    def test_improve_cleans_session_quote_style_party_links(self):
        snapshot = {
            "Party/Severian 'Seven' Emberwatch.md": (
                "---\n"
                "type: player-character\n"
                "player_name: Fabio\n"
                "character_name: Severian “Seven” Emberwatch\n"
                "character_class: Warlock\n"
                'alias: ["Seven", "Severian"]\n'
                "---\n"
                "# Severian 'Seven' Emberwatch\n"
            ),
            "Party/Antoni 'Boney Toney' Deleoro.md": (
                "---\n"
                "type: player-character\n"
                "player_name: Zach\n"
                "character_name: Antoni ‘Boney Toney’ Deleoro\n"
                "character_class: Bard\n"
                'alias: ["Boney Toney"]\n'
                "---\n"
                "# Antoni 'Boney Toney' Deleoro\n"
            ),
            "Sessions/Session-003.md": (
                "---\n"
                "type: session\n"
                'title: "Session 3: Trouble at Sea"\n'
                "---\n"
                "# Session 3: Trouble at Sea\n\n"
                "## Summary\n\n"
                "[[Severian 'Seven' Emberwatch|Seven]] and Anthony '[[Antoni 'Boney Toney' Deleoro|Boney Toney]]' Deleoro spoke below deck.\n"
            ),
        }
        cli = _build_cli(snapshot)

        improve_vault(cli)

        updated_session = [
            call.args[1]
            for call in cli.create.call_args_list
            if call.args[0] == "Sessions/Session-003.md"
        ][-1]
        assert "[[Severian “Seven” Emberwatch|Seven]]" not in updated_session
        assert (
            "Anthony '[[Antoni 'Boney Toney' Deleoro|Boney Toney]]' Deleoro"
            not in updated_session
        )
        assert (
            "[[Severian 'Seven' Emberwatch|Severian Emberwatch]]" in updated_session
            or "[[Severian 'Seven' Emberwatch|Seven]]" in updated_session
        )
        assert (
            "[[Antoni 'Boney Toney' Deleoro|Anthony 'Boney Toney' Deleoro]]"
            in updated_session
            or "[[Antoni 'Boney Toney' Deleoro]]" in updated_session
        )

    def test_improve_relationships_are_canonical_plain_links_without_duplicates(self):
        snapshot = {
            "Party/Hopscotch.md": (
                "---\n"
                "type: player-character\n"
                "player_name: Blaze\n"
                "character_name: Hopscotch\n"
                "character_class: Bard\n"
                'alias: ["Hop"]\n'
                "---\n"
                "# Hopscotch\n\n"
                "## Overview\n\n"
                "Hopscotch is played by Blaze. They are a Bard.\n\n"
                "## Aliases\n\n"
                "- Hop\n\n"
                "## Known Facts\n\n"
                "- **Player:** Blaze\n"
                "- **Class:** Bard\n\n"
                "## Timeline\n\n"
                "_No timeline entries yet._\n\n"
                "## Relationships\n\n"
                '- [[Severian “Seven” Emberwatch|Severian "Seven" Emberwatch]]\n'
                '- [[Severian “Seven” Emberwatch|Severian "Seven" Emberwatch]]\n'
                "- [[Antoni ‘Boney Toney’ Deleoro|Antoni 'Boney Toney' Deleoro]]\n\n"
                "## Notable Items\n\n"
                "_No notable items recorded yet._\n\n"
                "## Open Questions\n\n"
                "_No open questions._\n"
            ),
            "Party/Severian 'Seven' Emberwatch.md": (
                "---\n"
                "type: player-character\n"
                "player_name: Fabio\n"
                "character_name: Severian “Seven” Emberwatch\n"
                "character_class: Warlock\n"
                'alias: ["Seven", "Severian"]\n'
                "---\n"
                "# Severian 'Seven' Emberwatch\n"
            ),
            "Party/Antoni 'Boney Toney' Deleoro.md": (
                "---\n"
                "type: player-character\n"
                "player_name: Zach\n"
                "character_name: Antoni ‘Boney Toney’ Deleoro\n"
                "character_class: Bard\n"
                'alias: ["Boney Toney"]\n'
                "---\n"
                "# Antoni 'Boney Toney' Deleoro\n"
            ),
        }
        cli = _build_cli(snapshot)

        improve_vault(cli)

        updated_party = [
            call.args[1]
            for call in cli.create.call_args_list
            if call.args[0] == "Party/Hopscotch.md"
        ][-1]
        assert "- [[Severian 'Seven' Emberwatch]]" in updated_party
        assert "- [[Antoni 'Boney Toney' Deleoro]]" in updated_party
        assert '|Severian "Seven" Emberwatch' not in updated_party
        assert "|Antoni 'Boney Toney' Deleoro" not in updated_party
        assert updated_party.count("- [[Severian 'Seven' Emberwatch]]") == 1

    def test_improve_party_timelines_dedupe_stale_variants_after_link_cleanup(self):
        snapshot = {
            "Party/Hopscotch.md": (
                "---\n"
                "type: player-character\n"
                "player_name: Blaze\n"
                "character_name: Hopscotch\n"
                "character_class: Bard\n"
                'alias: ["Hop"]\n'
                "---\n"
                "# Hopscotch\n\n"
                "## Overview\n\n"
                "Hopscotch is played by Blaze. They are a Bard.\n\n"
                "## Aliases\n\n"
                "- Hop\n\n"
                "## Known Facts\n\n"
                "- **Player:** Blaze\n"
                "- **Class:** Bard\n\n"
                "## Timeline\n\n"
                "- [[Session-002]]: Rather than fight head-on, the party executed a coordinated plan: [[Hopscotch|Hop]] created mirror images and performed a distracting serenade, Trevor dropped a Moonbeam on guards, Bastiën hurled a Cloud of Daggers at the Oracle, and [[Celestine Silverleaf|Celestine]] paralyzed the Oracle with Hold Person. A Crown of Madness spell then turned one of the large guards against his master, delivering a critical killing blow to the Oracle. In the chaos, [[Severian “Seven” Emberwatch|Seven]] snatched the chest.\n\n"
                "## Relationships\n\n"
                "_No relationships recorded yet._\n\n"
                "## Notable Items\n\n"
                "_No notable items recorded yet._\n\n"
                "## Open Questions\n\n"
                "_No open questions._\n"
            ),
            "Party/Severian 'Seven' Emberwatch.md": (
                "---\n"
                "type: player-character\n"
                "player_name: Fabio\n"
                "character_name: Severian “Seven” Emberwatch\n"
                "character_class: Warlock\n"
                'alias: ["Seven", "Severian"]\n'
                "---\n"
                "# Severian 'Seven' Emberwatch\n"
            ),
            "Party/Macarius Tideweaver.md": (
                "---\n"
                "type: player-character\n"
                "player_name: Trevor\n"
                "character_name: Macarius Tideweaver\n"
                "character_class: Cleric\n"
                'alias: ["Macarius"]\n'
                "---\n"
                "# Macarius Tideweaver\n"
            ),
            "Party/Bastièn Magne.md": (
                "---\n"
                "type: player-character\n"
                "player_name: Scott\n"
                "character_name: Bastièn Magne\n"
                "character_class: Monk\n"
                'alias: ["Bastien"]\n'
                "---\n"
                "# Bastièn Magne\n"
            ),
            "Party/Celestine Silverleaf.md": (
                "---\n"
                "type: player-character\n"
                "player_name: Tina\n"
                "character_name: Celestine Silverleaf\n"
                "character_class: Sorcerer\n"
                'alias: ["Celestine"]\n'
                "---\n"
                "# Celestine Silverleaf\n"
            ),
            "Sessions/Session-002.md": (
                "---\n"
                "type: session\n"
                'title: "Session 2: The Chest"\n'
                "---\n"
                "# Session 2: The Chest\n\n"
                "## Summary\n\n"
                "Rather than fight head-on, the party executed a coordinated plan: [[Hopscotch|Hop]] created mirror images and performed a distracting serenade, [[Macarius Tideweaver|Macarius]] dropped a Moonbeam on guards, [[Severian “Seven” Emberwatch|Seven]] hurled a Cloud of Daggers at the Oracle, and [[Celestine Silverleaf|Celestine]] paralyzed the Oracle with Hold Person. A Crown of Madness spell then turned one of the large guards against his master, delivering a critical killing blow to the Oracle. In the chaos, [[Severian “Seven” Emberwatch|Seven]] snatched the chest.\n"
            ),
        }
        cli = _build_cli(snapshot)

        improve_vault(cli)

        updated_party = [
            call.args[1]
            for call in cli.create.call_args_list
            if call.args[0] == "Party/Hopscotch.md"
        ][-1]
        assert updated_party.count("- [[Session-002]]:") == 1
        assert "Trevor dropped a Moonbeam" not in updated_party
        assert "Bastiën hurled a Cloud of Daggers" not in updated_party
        assert "[[Macarius Tideweaver|Macarius]] dropped a Moonbeam" in updated_party
        assert (
            "[[Severian 'Seven' Emberwatch|Seven]] hurled a Cloud of Daggers"
            in updated_party
        )

    def test_improve_removes_party_self_links_from_relationships(self):
        snapshot = {
            "Party/Severian 'Seven' Emberwatch.md": (
                "---\n"
                "type: player-character\n"
                "player_name: Fabio\n"
                "character_name: Severian “Seven” Emberwatch\n"
                "character_class: Warlock\n"
                'alias: ["Seven", "Severian"]\n'
                "---\n"
                "# Severian 'Seven' Emberwatch\n\n"
                "## Overview\n\n"
                "Severian “Seven” Emberwatch is played by Fabio. They are a Warlock.\n\n"
                "## Aliases\n\n"
                "- Seven\n"
                "- Severian\n\n"
                "## Known Facts\n\n"
                "- **Player:** Fabio\n"
                "- **Class:** Warlock\n\n"
                "## Timeline\n\n"
                "_No timeline entries yet._\n\n"
                "## Relationships\n\n"
                "- [[Severian “Seven” Emberwatch]]\n"
                "- [[Salty McKeel]]\n\n"
                "## Notable Items\n\n"
                "_No notable items recorded yet._\n\n"
                "## Open Questions\n\n"
                "_No open questions._\n"
            ),
        }
        cli = _build_cli(snapshot)

        improve_vault(cli)

        updated_party = [
            call.args[1]
            for call in cli.create.call_args_list
            if call.args[0] == "Party/Severian 'Seven' Emberwatch.md"
        ][-1]
        assert "- [[Severian 'Seven' Emberwatch]]" not in updated_party
        assert "- [[Salty McKeel]]" in updated_party

    def test_improve_cleans_timeline_quote_style_party_links(self):
        snapshot = {
            "Party/Severian 'Seven' Emberwatch.md": (
                "---\n"
                "type: player-character\n"
                "player_name: Fabio\n"
                "character_name: Severian “Seven” Emberwatch\n"
                "character_class: Warlock\n"
                'alias: ["Seven", "Severian"]\n'
                "---\n"
                "# Severian 'Seven' Emberwatch\n"
            ),
            "Party/Antoni 'Boney Toney' Deleoro.md": (
                "---\n"
                "type: player-character\n"
                "player_name: Zach\n"
                "character_name: Antoni ‘Boney Toney’ Deleoro\n"
                "character_class: Bard\n"
                'alias: ["Boney Toney"]\n'
                "---\n"
                "# Antoni 'Boney Toney' Deleoro\n"
            ),
            "Timeline.md": (
                "---\n"
                "type: index\n"
                "title: Timeline\n"
                "---\n\n"
                "# Timeline\n\n"
                "- [[Session-003]]: Below deck, [[Severian 'Seven' Emberwatch|Severian]] Emberwatch and Anthony '[[Antoni 'Boney Toney' Deleoro|Boney Toney]]' Deleoro exchanged introductions.\n"
            ),
        }
        cli = _build_cli(snapshot)

        improve_vault(cli)

        updated_timeline = [
            call.args[1]
            for call in cli.create.call_args_list
            if call.args[0] == "Timeline.md"
        ][-1]
        assert (
            "[[Severian “Seven” Emberwatch|Severian]] Emberwatch"
            not in updated_timeline
        )
        assert (
            "Anthony '[[Antoni 'Boney Toney' Deleoro|Boney Toney]]' Deleoro"
            not in updated_timeline
        )
        assert "[[Severian 'Seven' Emberwatch|Severian Emberwatch]]" in updated_timeline
        assert (
            "[[Antoni 'Boney Toney' Deleoro]]" in updated_timeline
            or "[[Antoni 'Boney Toney' Deleoro|Antoni 'Boney Toney' Deleoro]]"
            in updated_timeline
        )

    def test_improve_links_ascii_variant_of_accented_party_name(self):
        snapshot = {
            "Party/Bastièn Magne.md": (
                "---\n"
                "type: player-character\n"
                "player_name: Scott\n"
                "character_name: Bastièn Magne\n"
                "character_class: Monk\n"
                'alias: ["Bastièn", "Bast"]\n'
                "---\n"
                "# Bastièn Magne\n"
            ),
            "Sessions/Session-003.md": (
                "---\n"
                "type: session\n"
                'title: "Session 3: Trouble at Sea"\n'
                "---\n"
                "# Session 3: Trouble at Sea\n\n"
                "## Summary\n\n"
                "Bastien kept watch below deck.\n"
            ),
        }
        cli = _build_cli(snapshot)

        improve_vault(cli)

        updated_session = [
            call.args[1]
            for call in cli.create.call_args_list
            if call.args[0] == "Sessions/Session-003.md"
        ][-1]
        assert "[[Bastièn Magne|Bastien]] kept watch below deck." in updated_session
