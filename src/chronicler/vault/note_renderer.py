"""Render Pydantic models into formatted Obsidian markdown with YAML frontmatter."""

from __future__ import annotations
import re

from chronicler.models.entities import (
    Faction,
    Location,
    LootItem,
    NPC,
    PlotThread,
)
from chronicler.models.context import PlayerCharacter
from chronicler.models.session import SessionRecap


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def wikify(name_or_list: str | list[str]) -> str:
    """Return Obsidian wikilink(s) for a name or list of names."""
    if isinstance(name_or_list, list):
        if not name_or_list:
            return ""
        return ", ".join(f"[[{n}]]" for n in name_or_list)
    return f"[[{name_or_list}]]"


def _wikify_yaml_value(name_or_list: str | list[str]) -> str | list[str]:
    """Return wikilinked values suitable for YAML frontmatter."""
    if isinstance(name_or_list, list):
        return [wikify(item) for item in name_or_list]
    return wikify(name_or_list)


def _yaml_list(items: list[str]) -> str:
    """Format a Python list as a YAML inline sequence string."""
    if not items:
        return "[]"
    serialized = ", ".join(f'"{item}"' for item in items)
    return f"[{serialized}]"


_REFERENCE_SCALAR_KEYS = {
    "first_appeared",
    "found_in",
    "held_by",
    "introduced_in",
    "parent_location",
    "resolved_in",
}

_REFERENCE_LIST_KEYS = {
    "affiliations",
    "adjacent_to",
    "connected_to",
    "known_members",
    "related_entities",
    "npcs",
    "locations",
}


def _normalize_tag(tag: str) -> str:
    """Convert a tag to an Obsidian-safe lowercase snake_case token."""
    normalized = re.sub(r"[^a-z0-9]+", "_", tag.lower()).strip("_")
    return normalized or "tag"


def _strip_wikilink(value: str) -> str:
    """Return the wikilink target from ``[[Target]]`` or the original string."""
    cleaned = value.strip()
    while cleaned.startswith("[[") and cleaned.endswith("]]"):
        cleaned = cleaned[2:-2].strip()
    if "|" in cleaned:
        cleaned = cleaned.split("|", 1)[0].strip()
    return cleaned


def _build_link_map(
    npc_names: list[str],
    location_names: list[str],
    faction_names: list[str],
    loot_names: list[str],
    player_character_names: list[str],
) -> dict[str, str]:
    names = npc_names + location_names + faction_names + loot_names + player_character_names
    return {name: wikify(name) for name in names if name}


def _link_text(text: str, link_map: dict[str, str]) -> str:
    """Link every exact known entity mention while preserving existing wikilinks."""
    if not text or not link_map:
        return text

    placeholders: list[str] = []

    def _stash(match: re.Match[str]) -> str:
        placeholders.append(match.group(0))
        return f"__WIKILINK_PLACEHOLDER_{len(placeholders) - 1}__"

    protected = re.sub(r"\[\[[^\]]+\]\]", _stash, text)

    for name in sorted(link_map, key=len, reverse=True):
        pattern = re.compile(rf"(?<![\w'\"“”‘’]){re.escape(name)}(?![\w'\"“”‘’])")
        protected = pattern.sub(lambda _: _stash(re.match(r".*", link_map[name])), protected)

    for i, original in enumerate(placeholders):
        protected = protected.replace(f"__WIKILINK_PLACEHOLDER_{i}__", original)

    return protected


def _yaml_scalar(value: object, key: str | None = None) -> str:
    """Format a scalar value for YAML frontmatter."""
    if isinstance(value, str):
        needs_quotes = (
            ":" in value
            or value != value.strip()
            or value.startswith("[[")
            or key == "title"
        )
        escaped = value.replace('"', '\\"')
        return f'"{escaped}"' if needs_quotes else value
    return str(value)


def _frontmatter(**fields: object) -> str:
    """Build a YAML frontmatter block from keyword arguments."""
    lines = ["---"]
    for key, value in fields.items():
        if isinstance(value, list):
            if key == "tags":
                value = [_normalize_tag(str(item)) for item in value]
            elif key in _REFERENCE_LIST_KEYS:
                value = [wikify(_strip_wikilink(str(item))) for item in value]
            lines.append(f"{key}: {_yaml_list(value)}")
        elif value is None:
            lines.append(f"{key}: null")
        else:
            if key in _REFERENCE_SCALAR_KEYS and isinstance(value, str):
                value = wikify(_strip_wikilink(value))
            lines.append(f"{key}: {_yaml_scalar(value, key=key)}")
    lines.append("---")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# NPC
# ---------------------------------------------------------------------------


def render_pc_note(pc: PlayerCharacter) -> str:
    """Render a Player Character note."""
    frontmatter_lines = [
        "---",
        "type: player-character",
        f"player_name: {pc.player_name}",
        f"character_name: {pc.character_name}",
    ]
    if pc.character_class:
        frontmatter_lines.append(f"character_class: {pc.character_class}")
    frontmatter_lines.append("---")
    fm = "\n".join(frontmatter_lines)

    body_lines = [
        f"# {pc.character_name}",
        "",
        "## Overview",
        "",
        f"{pc.character_name} is played by {pc.player_name}."
    ]
    if pc.character_class:
        body_lines[-1] += f" They are a {pc.character_class}."
    body_lines += [
        "",
        "## Aliases",
        "",
        "_No aliases recorded yet._",
        "",
        "## Known Facts",
        "",
        f"- **Player:** {pc.player_name}",
    ]
    if pc.character_class:
        body_lines.append(f"- **Class:** {pc.character_class}")
    body_lines += [
        "",
        "## Timeline",
        "",
        "_No timeline entries yet._",
        "",
        "## Relationships",
        "",
        "_No relationships recorded yet._",
        "",
        "## Notable Items",
        "",
        "_No notable items recorded yet._",
        "",
        "## Open Questions",
        "",
        "_No open questions._",
    ]

    body = "\n".join(body_lines)
    return f"{fm}\n{body}\n"


def render_npc_note(npc: NPC) -> str:
    """Render an NPC entity as an Obsidian markdown note."""
    fm = _frontmatter(
        type="npc",
        name=npc.name,
        status=npc.status.value,
        first_appeared=npc.first_appeared,
        source_attribution=npc.source_attribution,
        aliases=npc.aliases,
        affiliations=npc.affiliations,
        tags=npc.tags,
    )

    body_lines = [
        f"# {npc.name}",
        "",
        f"**Status:** {npc.status.value}",
    ]
    if npc.first_appeared:
        body_lines.insert(2, f"**First Appeared:** {wikify(npc.first_appeared)}")
    elif npc.source_attribution:
        body_lines.insert(2, f"**Source Attribution:** {npc.source_attribution}")

    if npc.aliases:
        body_lines.append(f"**Aliases:** {', '.join(npc.aliases)}")

    if npc.affiliations:
        body_lines.append(f"**Affiliations:** {wikify(npc.affiliations)}")

    if npc.description:
        body_lines += ["", "## Description", "", npc.description]

    if npc.key_interactions:
        body_lines += ["", "## Key Interactions", ""]
        for interaction in npc.key_interactions:
            body_lines.append(f"- {interaction}")

    body = "\n".join(body_lines)
    return f"{fm}\n{body}\n"


# ---------------------------------------------------------------------------
# Location
# ---------------------------------------------------------------------------


def render_location_note(loc: Location, child_locations: list[str] | None = None) -> str:
    """Render a Location entity as an Obsidian markdown note."""
    adjacency_links = loc.adjacent_to or loc.connected_to
    fm = _frontmatter(
        type="location",
        name=loc.name,
        first_appeared=loc.first_appeared,
        source_attribution=loc.source_attribution,
        aliases=loc.aliases,
        parent_location=loc.parent_location,
        adjacent_to=adjacency_links,
        connected_to=loc.connected_to,
        tags=loc.tags,
    )

    body_lines = [
        f"# {loc.name}",
        "",
    ]
    if loc.first_appeared:
        body_lines.append(f"**First Appeared:** {wikify(loc.first_appeared)}")
    elif loc.source_attribution:
        body_lines.append(f"**Source Attribution:** {loc.source_attribution}")

    if loc.aliases:
        body_lines.append(f"**Aliases:** {', '.join(loc.aliases)}")

    if loc.parent_location:
        body_lines.append(f"**Contained In:** {wikify(loc.parent_location)}")

    if adjacency_links:
        body_lines.append(f"**Adjacent To:** {wikify(adjacency_links)}")

    if child_locations:
        body_lines.append(f"**Contains:** {wikify(child_locations)}")

    if loc.description:
        body_lines += ["", "## Description", "", loc.description]

    body = "\n".join(body_lines)
    return f"{fm}\n{body}\n"


# ---------------------------------------------------------------------------
# Faction
# ---------------------------------------------------------------------------


def render_faction_note(faction: Faction) -> str:
    """Render a Faction entity as an Obsidian markdown note."""
    fm = _frontmatter(
        type="faction",
        name=faction.name,
        first_appeared=faction.first_appeared,
        source_attribution=faction.source_attribution,
        aliases=faction.aliases,
        known_members=faction.known_members,
        tags=faction.tags,
    )

    body_lines = [
        f"# {faction.name}",
        "",
    ]
    if faction.first_appeared:
        body_lines.append(f"**First Appeared:** {wikify(faction.first_appeared)}")
    elif faction.source_attribution:
        body_lines.append(f"**Source Attribution:** {faction.source_attribution}")

    if faction.aliases:
        body_lines.append(f"**Aliases:** {', '.join(faction.aliases)}")

    if faction.known_members:
        body_lines.append(f"**Known Members:** {wikify(faction.known_members)}")

    if faction.description:
        body_lines += ["", "## Description", "", faction.description]

    body = "\n".join(body_lines)
    return f"{fm}\n{body}\n"


# ---------------------------------------------------------------------------
# Loot
# ---------------------------------------------------------------------------


def render_loot_note(item: LootItem) -> str:
    """Render a LootItem entity as an Obsidian markdown note."""
    fm = _frontmatter(
        type="loot",
        name=item.name,
        found_in=item.found_in,
        source_attribution=item.source_attribution,
        held_by=item.held_by,
        tags=item.tags,
    )

    body_lines = [
        f"# {item.name}",
        "",
    ]
    if item.found_in:
        body_lines.append(f"**Found In:** {wikify(item.found_in)}")
    elif item.source_attribution:
        body_lines.append(f"**Source Attribution:** {item.source_attribution}")

    if item.held_by:
        body_lines.append(f"**Held By:** {item.held_by}")

    if item.description:
        body_lines += ["", "## Description", "", item.description]

    body = "\n".join(body_lines)
    return f"{fm}\n{body}\n"


# ---------------------------------------------------------------------------
# Session
# ---------------------------------------------------------------------------


def render_session_note(
    recap: SessionRecap,
    npcs: list[NPC],
    locations: list[Location],
    factions: list[Faction] | None = None,
    loot: list[LootItem] | None = None,
    player_characters: list[PlayerCharacter] | None = None,
) -> str:
    """Render a SessionRecap as an Obsidian session note."""
    session_id = f"Session-{recap.session_number:03d}"

    npc_names = [npc.name for npc in npcs]
    location_names = [loc.name for loc in locations]
    faction_names = [faction.name for faction in (factions or [])]
    loot_names = [item.name for item in (loot or [])]
    player_character_names = [pc.character_name for pc in (player_characters or [])]
    link_map = _build_link_map(
        npc_names,
        location_names,
        faction_names,
        loot_names,
        player_character_names,
    )

    fm = _frontmatter(
        type="session",
        session_number=recap.session_number,
        title=recap.title,
        npcs=npc_names,
        locations=location_names,
    )

    body_lines = [
        f"# Session {recap.session_number}: {recap.title}",
        "",
        "## Summary",
        "",
        _link_text(recap.summary, link_map),
    ]

    if recap.key_events:
        body_lines += ["", "## Key Events", ""]
        for event in recap.key_events:
            linked_description = _link_text(event.description, link_map)
            if event.timestamp:
                body_lines.append(f"- `{event.timestamp}` {linked_description}")
            else:
                body_lines.append(f"- {linked_description}")

    if npcs:
        body_lines += ["", "## NPCs", ""]
        body_lines.append(wikify(npc_names))

    if locations:
        body_lines += ["", "## Locations", ""]
        body_lines.append(wikify(location_names))

    body = "\n".join(body_lines)
    return f"{fm}\n{body}\n"


# ---------------------------------------------------------------------------
# Plot Thread
# ---------------------------------------------------------------------------


def render_plot_thread_note(thread: PlotThread) -> str:
    """Render a PlotThread as an Obsidian markdown note."""
    fm = _frontmatter(
        type="plot_thread",
        title=thread.title,
        status=thread.status.value,
        introduced_in=thread.introduced_in,
        source_attribution=thread.source_attribution,
        resolved_in=thread.resolved_in,
        related_entities=thread.related_entities,
        tags=thread.tags,
    )

    body_lines = [
        f"# {thread.title}",
        "",
        f"**Status:** {thread.status.value}",
    ]
    if thread.introduced_in:
        body_lines.append(f"**Introduced In:** {wikify(thread.introduced_in)}")
    elif thread.source_attribution:
        body_lines.append(f"**Source Attribution:** {thread.source_attribution}")

    if thread.resolved_in:
        body_lines.append(f"**Resolved In:** {wikify(thread.resolved_in)}")

    body_lines += ["", "## Summary", "", thread.summary]

    if thread.related_entities:
        body_lines += ["", "## Related Entities", ""]
        body_lines.append(wikify(thread.related_entities))

    body = "\n".join(body_lines)
    return f"{fm}\n{body}\n"


# ---------------------------------------------------------------------------
# Open Threads Index
# ---------------------------------------------------------------------------


def render_open_threads(threads: list[PlotThread]) -> str:
    """Render a markdown index of open plot threads."""
    lines = [
        "---",
        "type: index",
        "title: Open Plot Threads",
        "---",
        "",
        "# Open Plot Threads",
        "",
    ]

    for thread in threads:
        provenance = (
            f"introduced {wikify(thread.introduced_in)}"
            if thread.introduced_in
            else f"source {thread.source_attribution}"
        )
        lines.append(
            f"- **{thread.title}** ({provenance}): {thread.summary}"
        )

    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------


def render_dashboard(
    latest_session: int,
    npc_count: int,
    location_count: int,
    thread_count: int,
) -> str:
    """Render a campaign dashboard overview note."""
    lines = [
        "---",
        "type: dashboard",
        "title: Campaign Dashboard",
        "---",
        "",
        "# Campaign Dashboard",
        "",
        f"**Latest Session:** {wikify(f'Session-{latest_session:03d}')} (Session {latest_session})",
        "",
        "## Stats",
        "",
        f"| Category   | Count |",
        f"|------------|-------|",
        f"| NPCs       | {npc_count} |",
        f"| Locations  | {location_count} |",
        f"| Threads    | {thread_count} |",
    ]

    return "\n".join(lines) + "\n"
