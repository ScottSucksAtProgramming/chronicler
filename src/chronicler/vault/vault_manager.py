"""High-level orchestrator for reading and writing campaign data to the Obsidian vault."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import TYPE_CHECKING

import yaml

from chronicler.models.context import (
    AgentMemory,
    ContextBundle,
    EntitySummary,
    PlayerCharacter,
    ThreadSummary,
)
from chronicler.models.entities import (
    Faction,
    Location,
    LootItem,
    NPC,
    PlotThread,
    ThreadStatus,
)
from chronicler.models.extraction import AgentQuestion, ExtractionResult, KnowledgeIngestResult
from chronicler.models.session import SessionRecap
from chronicler.vault.dedup import find_match
from chronicler.vault.note_renderer import (
    render_dashboard,
    render_faction_note,
    render_location_note,
    render_loot_note,
    render_npc_note,
    render_pc_note,
    render_open_threads,
    render_session_note,
)
from chronicler.vault.party_updater import update_party_note_from_sessions

if TYPE_CHECKING:
    from chronicler.vault.obsidian_cli import ObsidianCLI


# ---------------------------------------------------------------------------
# Vault folder / file constants
# ---------------------------------------------------------------------------

_FOLDERS = [
    "Sessions",
    "Party",
    "NPCs",
    "Locations",
    "Factions",
    "Loot",
    "Plot-Threads",
    "_Agent",
    "_Agent/Memory",
    "_Agent/Questions",
]

_INIT_FILES: dict[str, str] = {
    "_Dashboard.md": (
        "---\ntype: dashboard\ntitle: Campaign Dashboard\n---\n\n# Campaign Dashboard\n\n"
        "_Run an extraction to populate this dashboard._\n"
    ),
    "Timeline.md": (
        "---\ntype: index\ntitle: Timeline\n---\n\n# Timeline\n\n"
        "_Session events will appear here._\n"
    ),
    "Plot-Threads/_Open-Threads.md": (
        "---\ntype: index\ntitle: Open Plot Threads\n---\n\n# Open Plot Threads\n\n"
        "_No open threads yet._\n"
    ),
    "Plot-Threads/_Closed-Threads.md": (
        "---\ntype: index\ntitle: Closed Plot Threads\n---\n\n# Closed Plot Threads\n\n"
        "_No closed threads yet._\n"
    ),
    "_Agent/Review-Log.md": (
        "---\ntype: agent-log\ntitle: Review Log\n---\n\n# Review Log\n"
    ),
    "_Agent/Memory/entity-aliases.md": (
        "---\ntype: agent-memory\n---\n\n"
    ),
    "_Agent/Memory/player-characters.md": (
        "---\ntype: agent-memory\n---\n\n"
    ),
    "_Agent/Memory/extraction-rules.md": (
        "---\ntype: agent-memory\n---\n\n"
    ),
    "_Agent/Memory/campaign-patterns.md": (
        "---\ntype: agent-memory\n---\n\n"
    ),
    "_Agent/Memory/user-preferences.md": (
        "---\ntype: agent-memory\n---\n\n"
    ),
    "_Agent/Memory/vault-guide.md": (
        "---\ntype: agent-memory\ntitle: Vault Guide\n---\n\n"
        "# Vault Guide\n\n"
        "- `Party/` is authoritative for player characters.\n"
        "- `Sessions/` is authoritative for what happened in a session.\n"
        "- `Plot-Threads/_Open-Threads.md` tracks active objectives and unresolved threads.\n"
        "- `_Dashboard.md` and `Timeline.md` summarize campaign state.\n"
        "- `_Agent/Memory/` stores persistent agent memory and operating rules.\n"
        "- Direct vault notes are authoritative; retrieval is a discovery aid.\n"
    ),
}


class VaultManager:
    """High-level orchestrator for campaign vault operations.

    Wraps :class:`ObsidianCLI` with deduplication, rendering, and context
    assembly logic so that callers never need to worry about file paths or
    markdown formatting.
    """

    def __init__(self, cli: ObsidianCLI) -> None:
        self.cli = cli

    # ------------------------------------------------------------------
    # Vault initialisation
    # ------------------------------------------------------------------

    def init_vault(self) -> None:
        """Create the vault folder structure and seed files."""
        for path, content in _INIT_FILES.items():
            if path == "_Agent/Memory/vault-guide.md" and self.cli.note_exists(path):
                continue
            self.cli.create(path, content)

    # ------------------------------------------------------------------
    # Entity writers
    # ------------------------------------------------------------------

    def write_npc(self, npc: NPC, update_existing: bool = False) -> None:
        """Create (or optionally update) an NPC note in ``NPCs/``."""
        existing = self._find_existing(npc.name, "NPCs/")
        if existing and not update_existing:
            return
        path = existing or f"NPCs/{npc.name}.md"
        self.cli.create(path, render_npc_note(npc))

    def write_location(self, loc: Location, update_existing: bool = False) -> None:
        """Create (or optionally update) a Location note in ``Locations/``."""
        existing = self._find_existing(loc.name, "Locations/")
        if existing and not update_existing:
            return
        path = existing or f"Locations/{loc.name}.md"
        self.cli.create(path, render_location_note(loc))

    def write_faction(self, faction: Faction, update_existing: bool = False) -> None:
        """Create (or optionally update) a Faction note in ``Factions/``."""
        existing = self._find_existing(faction.name, "Factions/")
        if existing and not update_existing:
            return
        path = existing or f"Factions/{faction.name}.md"
        self.cli.create(path, render_faction_note(faction))

    def write_loot(self, item: LootItem) -> None:
        """Create a loot note in ``Loot/``."""
        path = f"Loot/{item.name}.md"
        self.cli.create(path, render_loot_note(item))

    def write_session(
        self,
        recap: SessionRecap,
        npcs: list[NPC],
        locations: list[Location],
        factions: list[Faction] | None = None,
        loot: list[LootItem] | None = None,
    ) -> None:
        """Create a session note in ``Sessions/``."""
        session_id = f"Session-{recap.session_number:03d}"
        path = f"Sessions/{session_id}.md"
        self.cli.create(
            path,
            render_session_note(
                recap,
                npcs,
                locations,
                factions=factions or [],
                loot=loot or [],
                player_characters=self.read_player_characters(),
            ),
        )

    def write_pc(self, pc: PlayerCharacter) -> None:
        """Create a Player Character note in ``Party/``."""
        path = f"Party/{pc.character_name}.md"
        self.cli.create(path, render_pc_note(pc))

    def remove_pc(self, character_name: str) -> None:
        """Remove a Player Character note from ``Party/``."""
        self.cli.delete(f"Party/{character_name}.md")

    # ------------------------------------------------------------------
    # Orchestrated write
    # ------------------------------------------------------------------

    def write_extraction_result(self, result: ExtractionResult) -> None:
        """Write every entity from an extraction result into the vault."""
        for npc in result.npcs:
            self.write_npc(npc)
        for loc in result.locations:
            self.write_location(loc)
        for faction in result.factions:
            self.write_faction(faction)
        for item in result.loot:
            self.write_loot(item)

        self.write_session(
            result.recap,
            result.npcs,
            result.locations,
            factions=result.factions,
            loot=result.loot,
        )
        self._update_party_notes_from_session(result.recap.session_number)

        # Update indexes
        open_threads = [t for t in result.plot_threads if t.status == ThreadStatus.OPEN]
        self.update_open_threads(open_threads)

        # Count totals (existing + new)
        existing_npcs = self.cli.find_notes_in_folder("NPCs/")
        existing_locs = self.cli.find_notes_in_folder("Locations/")
        self.update_dashboard(
            session_number=result.session_number,
            npc_count=len(existing_npcs) + len(result.npcs),
            location_count=len(existing_locs) + len(result.locations),
            thread_count=len(open_threads),
        )

        for question in result.questions:
            self.write_question(question)

    def write_source_ingest_result(self, result: KnowledgeIngestResult) -> None:
        """Write a knowledge-first ingest result into the vault."""
        for npc in result.npcs:
            self._write_source_npc(npc)
        for loc in result.locations:
            self._write_source_location(loc)
        for faction in result.factions:
            self._write_source_faction(faction)
        for item in result.loot:
            self._write_source_loot(item)

        open_threads = [t for t in result.plot_threads if t.status == ThreadStatus.OPEN]
        self.update_open_threads(open_threads)

        if result.session_number is not None and result.recap is not None:
            self.write_session(
                result.recap,
                result.npcs,
                result.locations,
                factions=result.factions,
                loot=result.loot,
            )
            existing_npcs = self.cli.find_notes_in_folder("NPCs/")
            existing_locs = self.cli.find_notes_in_folder("Locations/")
            self.update_dashboard(
                session_number=result.session_number,
                npc_count=len(existing_npcs) + len(result.npcs),
                location_count=len(existing_locs) + len(result.locations),
                thread_count=len(open_threads),
            )

        for question in result.questions:
            self.write_question(question)

    def _write_source_npc(self, npc: NPC) -> None:
        existing = self._find_existing(npc.name, "NPCs/")
        if existing and npc.source_attribution:
            self._merge_source_update(existing, npc.source_attribution, npc.description)
            return
        self.write_npc(npc)

    def _write_source_location(self, loc: Location) -> None:
        existing = self._find_existing(loc.name, "Locations/")
        if existing and loc.source_attribution:
            self._merge_source_update(existing, loc.source_attribution, loc.description)
            return
        self.write_location(loc)

    def _write_source_faction(self, faction: Faction) -> None:
        existing = self._find_existing(faction.name, "Factions/")
        if existing and faction.source_attribution:
            self._merge_source_update(existing, faction.source_attribution, faction.description)
            return
        self.write_faction(faction)

    def _write_source_loot(self, item: LootItem) -> None:
        existing = self._find_existing(item.name, "Loot/")
        if existing and item.source_attribution:
            self._merge_source_update(existing, item.source_attribution, item.description)
            return
        self.write_loot(item)

    def _merge_source_update(
        self,
        path: str,
        source_label: str,
        description: str | None,
    ) -> None:
        """Append or replace a managed source-update section without overwriting the note."""
        try:
            existing = self.cli.read(path)
        except Exception:
            existing = ""

        managed_header = "## Source Updates"
        start_marker = "<!-- chronicler:source-updates:start -->"
        end_marker = "<!-- chronicler:source-updates:end -->"
        entry_lines = [f"### {source_label}"]
        if description:
            entry_lines += ["", description]
        entry = "\n".join(entry_lines).strip()

        block_pattern = re.compile(
            rf"{re.escape(start_marker)}\n?(.*)\n?{re.escape(end_marker)}",
            re.DOTALL,
        )
        entry_pattern = re.compile(
            rf"(?ms)^### {re.escape(source_label)}\n.*?(?=^### |\Z)"
        )

        if start_marker in existing and end_marker in existing:
            match = block_pattern.search(existing)
            if match:
                block_content = match.group(1).strip()
                if entry_pattern.search(block_content):
                    new_block = entry_pattern.sub(entry, block_content).strip()
                else:
                    new_block = "\n\n".join(part for part in [block_content, entry] if part).strip()
                updated = block_pattern.sub(
                    f"{start_marker}\n{new_block}\n{end_marker}",
                    existing,
                )
                self.cli.create(path, updated)
                return

        section = "\n\n".join(
            [
                managed_header,
                start_marker,
                entry,
                end_marker,
            ]
        )
        updated = existing.rstrip() + "\n\n" + section + "\n"
        self.cli.create(path, updated)

    # ------------------------------------------------------------------
    # Index updates
    # ------------------------------------------------------------------

    def update_open_threads(self, threads: list[PlotThread]) -> None:
        """Rewrite ``Plot-Threads/_Open-Threads.md``."""
        self.cli.create("Plot-Threads/_Open-Threads.md", render_open_threads(threads))

    def update_dashboard(
        self,
        session_number: int,
        npc_count: int,
        location_count: int,
        thread_count: int,
    ) -> None:
        """Rewrite ``_Dashboard.md``."""
        self.cli.create(
            "_Dashboard.md",
            render_dashboard(session_number, npc_count, location_count, thread_count),
        )

    # ------------------------------------------------------------------
    # Context bundle
    # ------------------------------------------------------------------

    def get_context_bundle(self, session_number: int) -> ContextBundle:
        """Read vault state and assemble a :class:`ContextBundle`."""
        known_npcs = self._read_entity_summaries("NPCs/")
        known_locations = self._read_entity_summaries("Locations/")
        known_factions = self._read_entity_summaries("Factions/")
        active_threads = self._read_active_threads()
        recent_events = self._read_recent_events(session_number)
        entity_aliases = self._read_entity_aliases()
        player_characters = self.read_player_characters()

        return ContextBundle(
            session_number=session_number,
            known_npcs=known_npcs,
            known_locations=known_locations,
            known_factions=known_factions,
            active_threads=active_threads,
            recent_events=recent_events,
            entity_aliases=entity_aliases,
            player_characters=player_characters,
        )

    # ------------------------------------------------------------------
    # Agent memory
    # ------------------------------------------------------------------

    def write_question(self, question: AgentQuestion) -> None:
        """Write a question to ``_Agent/Questions/``."""
        ts = datetime.now(tz=timezone.utc).strftime("%Y%m%d-%H%M%S")
        slug = re.sub(r"[^a-z0-9]+", "-", question.question.lower())[:40].strip("-")
        filename = f"{ts}-{slug}.md"
        path = f"_Agent/Questions/{filename}"

        lines = [
            "---",
            "type: agent-question",
            f"priority: {question.priority.value}",
        ]
        if question.source_session is not None:
            lines.append(f"source_session: {question.source_session}")
        lines += [
            "---",
            "",
            f"# {question.question}",
            "",
            f"**Context:** {question.context}",
            "",
        ]
        if question.answer:
            lines += [f"**Answer:** {question.answer}", ""]

        self.cli.create(path, "\n".join(lines))

    def read_agent_memory(self) -> AgentMemory:
        """Read all ``_Agent/Memory/`` files and return an :class:`AgentMemory`."""
        entity_aliases = self._read_entity_aliases()
        player_characters = self._read_player_characters()
        extraction_rules = self._read_memory_list("_Agent/Memory/extraction-rules.md")
        campaign_patterns = self._read_memory_list("_Agent/Memory/campaign-patterns.md")
        user_preferences = self._read_memory_list("_Agent/Memory/user-preferences.md")

        return AgentMemory(
            entity_aliases=entity_aliases,
            player_characters=player_characters,
            extraction_rules=extraction_rules,
            campaign_patterns=campaign_patterns,
            user_preferences=user_preferences,
        )

    def update_entity_aliases(self, aliases: dict[str, str]) -> None:
        """Overwrite ``_Agent/Memory/entity-aliases.md``."""
        lines = ["---", "type: agent-memory", "---", ""]
        for entity, alias in aliases.items():
            lines.append(f"{entity}: {alias}")
        self.cli.create("_Agent/Memory/entity-aliases.md", "\n".join(lines) + "\n")

    def update_player_characters(self, pcs: list[PlayerCharacter]) -> None:
        """Overwrite ``_Agent/Memory/player-characters.md``."""
        lines = ["---", "type: agent-memory", "---", ""]
        for pc in pcs:
            lines.append(f"- player_name: {pc.player_name}")
            lines.append(f"  character_name: {pc.character_name}")
            if pc.character_class:
                lines.append(f"  character_class: {pc.character_class}")
        self.cli.create(
            "_Agent/Memory/player-characters.md", "\n".join(lines) + "\n"
        )

    def read_player_characters(self) -> list[PlayerCharacter]:
        """Read player characters from ``Party/``, falling back to agent memory."""
        pcs: list[PlayerCharacter] = []
        for path in self.cli.find_notes_in_folder("Party/"):
            try:
                content = self.cli.read(path)
            except Exception:
                continue

            fm = self._parse_frontmatter(content)
            if fm.get("type") != "player-character":
                continue

            player_name = fm.get("player_name")
            character_name = fm.get("character_name")
            if not player_name or not character_name:
                continue

            pcs.append(
                PlayerCharacter(
                    player_name=player_name,
                    character_name=character_name,
                    character_class=fm.get("character_class"),
                )
            )

        if pcs:
            return pcs

        return self._read_player_characters()

    # ------------------------------------------------------------------
    # Frontmatter parsing
    # ------------------------------------------------------------------

    def _parse_frontmatter(self, content: str) -> dict:
        """Parse YAML frontmatter from note content.

        Returns an empty dict if no frontmatter is found.
        """
        if not content or not content.startswith("---"):
            return {}
        parts = content.split("---", 2)
        if len(parts) < 3:
            return {}
        try:
            result = yaml.safe_load(parts[1])
            return result if isinstance(result, dict) else {}
        except yaml.YAMLError:
            return {}

    # ------------------------------------------------------------------
    # Dedup helper
    # ------------------------------------------------------------------

    def _find_existing(self, name: str, folder: str) -> str | None:
        """Search the vault for an existing note matching *name* in *folder*.

        Uses :func:`find_match` for fuzzy deduplication against filenames.
        Returns the full note path or ``None``.
        """
        notes = self.cli.find_notes_in_folder(folder)
        if not notes:
            return None

        # Build name -> path map from filenames
        name_map: dict[str, str] = {}
        for note_path in notes:
            # "NPCs/The Friendly Face.md" -> "The Friendly Face"
            fname = note_path.rsplit("/", 1)[-1]
            if fname.endswith(".md"):
                fname = fname[:-3]
            name_map[fname] = note_path

        matched_name = find_match(name, list(name_map.keys()))
        if matched_name:
            return name_map[matched_name]
        return None

    # ------------------------------------------------------------------
    # Private readers
    # ------------------------------------------------------------------

    def _read_entity_summaries(self, folder: str) -> list[EntitySummary]:
        """Read notes in *folder* and return lightweight summaries."""
        notes = self.cli.find_notes_in_folder(folder)
        summaries: list[EntitySummary] = []
        for note_path in notes:
            try:
                content = self.cli.read(note_path)
            except Exception:
                continue
            fm = self._parse_frontmatter(content)
            name = fm.get("name")
            if not name:
                # Derive from filename
                fname = note_path.rsplit("/", 1)[-1]
                name = fname[:-3] if fname.endswith(".md") else fname
            summaries.append(
                EntitySummary(
                    name=name,
                    aliases=fm.get("aliases", []),
                    status=fm.get("status"),
                )
            )
        return summaries

    def _read_active_threads(self) -> list[ThreadSummary]:
        """Parse ``Plot-Threads/_Open-Threads.md`` into thread summaries."""
        try:
            content = self.cli.read("Plot-Threads/_Open-Threads.md")
        except Exception:
            return []
        if not content:
            return []

        threads: list[ThreadSummary] = []
        for line in content.splitlines():
            line = line.strip()
            if not line.startswith("- **"):
                continue
            # Pattern: - **Title** (introduced [[Session-XXX]]): Summary
            match = re.match(r"^- \*\*(.+?)\*\*.*?:\s*(.+)$", line)
            if match:
                threads.append(
                    ThreadSummary(title=match.group(1), summary=match.group(2))
                )
        return threads

    def _read_recent_events(self, session_number: int) -> list[str]:
        """Read the last 2-3 session notes and extract summaries."""
        session_files = self.cli.find_notes_in_folder("Sessions/")
        if not session_files:
            return []

        # Sort and take the last 3
        session_files = sorted(session_files)[-3:]

        events: list[str] = []
        for path in session_files:
            try:
                content = self.cli.read(path)
            except Exception:
                continue
            fm = self._parse_frontmatter(content)
            title = fm.get("title", "")
            snum = fm.get("session_number", "")

            # Extract Summary section
            summary = self._extract_section(content, "Summary")
            if summary:
                prefix = f"Session {snum}" if snum else path
                events.append(f"{prefix}: {summary}")

        return events

    def _read_entity_aliases(self) -> dict[str, str]:
        """Parse ``_Agent/Memory/entity-aliases.md`` into a dict."""
        try:
            content = self.cli.read("_Agent/Memory/entity-aliases.md")
        except Exception:
            return {}
        body = self._strip_frontmatter(content)
        aliases: dict[str, str] = {}
        for line in body.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if ":" in line:
                key, _, value = line.partition(":")
                aliases[key.strip()] = value.strip()
        return aliases

    def _update_party_notes_from_session(self, session_number: int) -> None:
        session_path = f"Sessions/Session-{session_number:03d}.md"
        try:
            session_content = self.cli.read(session_path)
        except Exception:
            return

        sessions = {session_path: session_content}
        for pc in self.read_player_characters():
            party_path = f"Party/{pc.character_name}.md"
            try:
                note_content = self.cli.read(party_path)
            except Exception:
                continue
            updated = update_party_note_from_sessions(note_content, pc, sessions)
            if updated != note_content:
                self.cli.create(party_path, updated)

    def _read_player_characters(self) -> list[PlayerCharacter]:
        """Parse ``_Agent/Memory/player-characters.md`` into PC objects."""
        try:
            content = self.cli.read("_Agent/Memory/player-characters.md")
        except Exception:
            return []
        body = self._strip_frontmatter(content)
        if not body.strip():
            return []
        try:
            data = yaml.safe_load(body)
        except yaml.YAMLError:
            return []
        if not isinstance(data, list):
            return []
        pcs: list[PlayerCharacter] = []
        for entry in data:
            if isinstance(entry, dict) and "player_name" in entry and "character_name" in entry:
                pcs.append(PlayerCharacter(**entry))
        return pcs

    def _read_memory_list(self, path: str) -> list[str]:
        """Read a YAML list from an agent memory file."""
        try:
            content = self.cli.read(path)
        except Exception:
            return []
        body = self._strip_frontmatter(content)
        if not body.strip():
            return []
        try:
            data = yaml.safe_load(body)
        except yaml.YAMLError:
            return []
        if isinstance(data, list):
            return [str(item) for item in data]
        return []

    # ------------------------------------------------------------------
    # Text helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _strip_frontmatter(content: str) -> str:
        """Remove YAML frontmatter and return the body."""
        if not content or not content.startswith("---"):
            return content
        parts = content.split("---", 2)
        if len(parts) >= 3:
            return parts[2]
        return content

    @staticmethod
    def _extract_section(content: str, heading: str) -> str:
        """Extract text under a ``## heading`` until the next heading."""
        lines = content.splitlines()
        capture = False
        result: list[str] = []
        for line in lines:
            if line.strip().lower() == f"## {heading.lower()}":
                capture = True
                continue
            if capture:
                if line.strip().startswith("## "):
                    break
                result.append(line)
        return " ".join(l.strip() for l in result if l.strip())
