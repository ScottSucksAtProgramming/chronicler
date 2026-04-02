"""Render Pydantic models into formatted Obsidian markdown with YAML frontmatter."""

from __future__ import annotations

from session_scribe.models.entities import (
    Faction,
    Location,
    LootItem,
    NPC,
    PlotThread,
)
from session_scribe.models.session import SessionRecap


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


def _yaml_list(items: list[str]) -> str:
    """Format a Python list as a YAML inline sequence string."""
    if not items:
        return "[]"
    serialized = ", ".join(f'"{item}"' for item in items)
    return f"[{serialized}]"


def _frontmatter(**fields: object) -> str:
    """Build a YAML frontmatter block from keyword arguments."""
    lines = ["---"]
    for key, value in fields.items():
        if isinstance(value, list):
            lines.append(f"{key}: {_yaml_list(value)}")
        elif value is None:
            lines.append(f"{key}: null")
        else:
            lines.append(f"{key}: {value}")
    lines.append("---")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# NPC
# ---------------------------------------------------------------------------


def render_npc_note(npc: NPC) -> str:
    """Render an NPC entity as an Obsidian markdown note."""
    fm = _frontmatter(
        type="npc",
        name=npc.name,
        status=npc.status.value,
        first_appeared=npc.first_appeared,
        aliases=npc.aliases,
        affiliations=npc.affiliations,
        tags=npc.tags,
    )

    body_lines = [
        f"# {npc.name}",
        "",
        f"**First Appeared:** {wikify(npc.first_appeared)}",
        f"**Status:** {npc.status.value}",
    ]

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


def render_location_note(loc: Location) -> str:
    """Render a Location entity as an Obsidian markdown note."""
    fm = _frontmatter(
        type="location",
        name=loc.name,
        first_appeared=loc.first_appeared,
        aliases=loc.aliases,
        connected_to=loc.connected_to,
        tags=loc.tags,
    )

    body_lines = [
        f"# {loc.name}",
        "",
        f"**First Appeared:** {wikify(loc.first_appeared)}",
    ]

    if loc.aliases:
        body_lines.append(f"**Aliases:** {', '.join(loc.aliases)}")

    if loc.connected_to:
        body_lines.append(f"**Connected To:** {wikify(loc.connected_to)}")

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
        aliases=faction.aliases,
        known_members=faction.known_members,
        tags=faction.tags,
    )

    body_lines = [
        f"# {faction.name}",
        "",
        f"**First Appeared:** {wikify(faction.first_appeared)}",
    ]

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
        held_by=item.held_by,
        tags=item.tags,
    )

    body_lines = [
        f"# {item.name}",
        "",
        f"**Found In:** {wikify(item.found_in)}",
    ]

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
) -> str:
    """Render a SessionRecap as an Obsidian session note."""
    session_id = f"Session-{recap.session_number:03d}"

    npc_names = [npc.name for npc in npcs]
    location_names = [loc.name for loc in locations]

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
        recap.summary,
    ]

    if recap.key_events:
        body_lines += ["", "## Key Events", ""]
        for event in recap.key_events:
            if event.timestamp:
                body_lines.append(f"- `{event.timestamp}` {event.description}")
            else:
                body_lines.append(f"- {event.description}")

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
        resolved_in=thread.resolved_in,
        related_entities=thread.related_entities,
        tags=thread.tags,
    )

    body_lines = [
        f"# {thread.title}",
        "",
        f"**Status:** {thread.status.value}",
        f"**Introduced In:** {wikify(thread.introduced_in)}",
    ]

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
        lines.append(
            f"- **{thread.title}** (introduced {wikify(thread.introduced_in)}): {thread.summary}"
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
