"""Helpers for maintaining evolving party notes."""

from __future__ import annotations

import re

import yaml

from chronicler.models.context import PlayerCharacter
from chronicler.vault.note_renderer import _yaml_scalar, _yaml_list

_SECTION_ORDER = [
    "Overview",
    "Aliases",
    "Known Facts",
    "Timeline",
    "Relationships",
    "Notable Items",
    "Open Questions",
]


def update_party_note_from_sessions(
    note_content: str,
    pc: PlayerCharacter,
    sessions: dict[str, str],
) -> str:
    """Merge explicit session evidence into a managed party note."""
    frontmatter, sections = _parse_party_note(note_content)
    aliases = _party_aliases(frontmatter, pc)
    sections["Overview"] = [_overview_line(pc)]
    sections["Aliases"] = [
        f"- {alias}" for alias in aliases if alias != pc.character_name
    ]
    sections["Known Facts"] = _known_facts(pc)
    timeline_entries: list[str] = []
    relationship_entries: list[str] = []

    for session_path, session_content in sorted(sessions.items()):
        session_id = _session_id(session_path, session_content)
        for line in _character_lines(session_content, aliases):
            timeline_entries.append(f"- [[{session_id}]]: {line}")
            relationship_entries.extend(_linked_relationships(line, aliases))

    if timeline_entries:
        sections["Timeline"] = _merge_unique([], timeline_entries)
    else:
        sections["Timeline"] = _merge_unique(sections["Timeline"], timeline_entries)
    sections["Relationships"] = _merge_unique(
        sections["Relationships"], relationship_entries
    )
    if aliases:
        sections["Aliases"] = [
            f"- {alias}" for alias in aliases if alias != pc.character_name
        ]

    return _render_party_note(frontmatter, pc, sections)


def _parse_party_note(content: str) -> tuple[dict, dict[str, list[str]]]:
    if content.startswith("---"):
        parts = content.split("---", 2)
        fm = yaml.safe_load(parts[1]) if len(parts) > 2 else {}
        body = parts[2].lstrip("\n") if len(parts) > 2 else content
    else:
        fm = {}
        body = content
    frontmatter = fm if isinstance(fm, dict) else {}

    sections: dict[str, list[str]] = {name: [] for name in _SECTION_ORDER}
    current: str | None = None
    for line in body.splitlines():
        if line.startswith("## "):
            heading = line[3:].strip()
            current = heading if heading in sections else None
            continue
        if current is None:
            continue
        stripped = line.strip()
        if not stripped or stripped.startswith("_No "):
            continue
        sections[current].append(stripped)
    return frontmatter, sections


def _party_aliases(frontmatter: dict, pc: PlayerCharacter) -> list[str]:
    aliases = [pc.character_name]
    for key in ("alias", "aliases"):
        value = frontmatter.get(key, [])
        if isinstance(value, str):
            aliases.append(value)
        elif isinstance(value, list):
            aliases.extend(str(item) for item in value)
    seen: list[str] = []
    for alias in aliases:
        cleaned = alias.strip()
        if cleaned and cleaned not in seen:
            seen.append(cleaned)
    return seen


def _session_id(path: str, content: str) -> str:
    match = re.search(r"Session-(\d+)\.md$", path)
    if match:
        return f"Session-{int(match.group(1)):03d}"
    fm = {}
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) > 2:
            loaded = yaml.safe_load(parts[1])
            if isinstance(loaded, dict):
                fm = loaded
    session_number = fm.get("session_number")
    if isinstance(session_number, int):
        return f"Session-{session_number:03d}"
    return path


def _character_lines(session_content: str, aliases: list[str]) -> list[str]:
    lines: list[str] = []
    body = (
        session_content.split("---", 2)[2].lstrip("\n")
        if session_content.startswith("---")
        else session_content
    )
    for raw_line in body.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("- "):
            line = line[2:]
        if _mentions_character(line, aliases):
            lines.append(line)
    return lines


def _mentions_character(text: str, aliases: list[str]) -> bool:
    for alias in sorted(aliases, key=len, reverse=True):
        if f"[[{alias}]]" in text or f"[[{alias}|" in text:
            return True
        if re.search(rf"(?<!\w){re.escape(alias)}(?!\w)", text):
            return True
    return False


def _linked_relationships(text: str, aliases: list[str]) -> list[str]:
    links = re.findall(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]", text)
    blocked = set(aliases)
    blocked.update({"The Party"})
    result = []
    for link in links:
        if link in blocked or link.startswith("Session-"):
            continue
        result.append(f"- [[{link}]]")
    return result


def _merge_unique(existing: list[str], additions: list[str]) -> list[str]:
    merged = list(existing)
    for item in additions:
        if item not in merged:
            merged.append(item)
    return merged


def _render_party_note(
    frontmatter: dict, pc: PlayerCharacter, sections: dict[str, list[str]]
) -> str:
    lines = [
        "---",
        "type: player-character",
        f"player_name: {_yaml_scalar(frontmatter.get('player_name', pc.player_name), key='player_name')}",
        f"character_name: {_yaml_scalar(frontmatter.get('character_name', pc.character_name), key='character_name')}",
    ]
    character_class = frontmatter.get("character_class", pc.character_class)
    if character_class:
        lines.append(
            f"character_class: {_yaml_scalar(character_class, key='character_class')}"
        )
    aliases = frontmatter.get("alias") or frontmatter.get("aliases")
    if isinstance(aliases, str):
        lines.append(f"alias: {_yaml_list([aliases])}")
    elif isinstance(aliases, list) and aliases:
        lines.append(f"alias: {_yaml_list([str(item) for item in aliases])}")
    lines += [
        "---",
        f"# {frontmatter.get('character_name', pc.character_name)}",
        "",
    ]

    for heading in _SECTION_ORDER:
        lines.append(f"## {heading}")
        lines.append("")
        entries = sections.get(heading, [])
        if entries:
            lines.extend(entries)
        else:
            lines.append(_empty_placeholder(heading, pc))
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def _empty_placeholder(heading: str, pc: PlayerCharacter) -> str:
    if heading == "Overview":
        return _overview_line(pc)
    if heading == "Known Facts":
        return "\n".join(_known_facts(pc))
    placeholders = {
        "Aliases": "_No aliases recorded yet._",
        "Timeline": "_No timeline entries yet._",
        "Relationships": "_No relationships recorded yet._",
        "Notable Items": "_No notable items recorded yet._",
        "Open Questions": "_No open questions._",
    }
    return placeholders[heading]


def _overview_line(pc: PlayerCharacter) -> str:
    parts = [f"{pc.character_name} is played by {pc.player_name}."]
    if pc.character_class:
        parts.append(f"They are a {pc.character_class}.")
    return " ".join(parts)


def _known_facts(pc: PlayerCharacter) -> list[str]:
    facts = [f"- **Player:** {pc.player_name}"]
    if pc.character_class:
        facts.append(f"- **Class:** {pc.character_class}")
    return facts
