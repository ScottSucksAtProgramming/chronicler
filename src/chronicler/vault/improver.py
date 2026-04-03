"""Deterministic vault maintenance helpers."""

from __future__ import annotations

from dataclasses import dataclass, field
import re
from pathlib import Path
import unicodedata

import yaml

from chronicler.models.context import PlayerCharacter
from chronicler.models.extraction import AgentQuestion, QuestionPriority
from chronicler.vault.note_renderer import _frontmatter, _link_text, wikify
from chronicler.vault.party_updater import update_party_note_from_sessions

_SUPPORTED_FOLDERS = (
    "Sessions/",
    "Party/",
    "NPCs/",
    "Locations/",
    "Factions/",
    "Loot/",
)

_SUPPORTED_ROOT_NOTES = {
    "Timeline.md",
}

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


@dataclass
class ImproveReport:
    changed_count: int = 0
    question_count: int = 0
    changed_files: list[str] = field(default_factory=list)
    question_files: list[str] = field(default_factory=list)


@dataclass
class _CanonicalIndex:
    link_map: dict[str, str]
    ambiguous_terms: set[str]
    term_to_canonical: dict[str, str]
    canonical_names: set[str]


def improve_vault(cli) -> ImproveReport:
    """Apply deterministic vault improvements and emit questions for ambiguity."""
    snapshot = cli.read_all_notes()
    index = _build_canonical_index(snapshot)
    report = ImproveReport()
    updated_snapshot = dict(snapshot)

    for path, content in snapshot.items():
        if not _is_supported_note(path):
            continue

        updated, questions = _improve_note(path, content, index)
        if updated != content:
            cli.create(path, updated)
            report.changed_count += 1
            report.changed_files.append(path)
            updated_snapshot[path] = updated

        for question in questions:
            question_path = _question_path(path, question.question)
            cli.create(question_path, _render_question(question, path))
            report.question_count += 1
            report.question_files.append(question_path)

    session_notes = {
        path: content
        for path, content in updated_snapshot.items()
        if path.startswith("Sessions/")
    }
    for path, content in updated_snapshot.items():
        if not path.startswith("Party/"):
            continue
        frontmatter = _parse_frontmatter(content)
        player_name = frontmatter.get("player_name")
        character_name = frontmatter.get("character_name")
        if not isinstance(player_name, str) or not isinstance(character_name, str):
            continue
        pc = PlayerCharacter(
            player_name=player_name,
            character_name=character_name,
            character_class=frontmatter.get("character_class"),
        )
        updated = update_party_note_from_sessions(content, pc, session_notes)
        updated = _canonicalize_party_timeline(updated, index)
        updated = _canonicalize_party_relationships(updated, index, Path(path).stem)
        updated = _repair_mixed_name_links(updated, index)
        updated = _normalize_existing_links(updated, index)
        if updated != content:
            cli.create(path, updated)
            if path not in report.changed_files:
                report.changed_count += 1
                report.changed_files.append(path)
            updated_snapshot[path] = updated

    location_updates = _refresh_location_relationships(updated_snapshot)
    for path, updated in location_updates.items():
        if updated == updated_snapshot.get(path):
            continue
        cli.create(path, updated)
        if path not in report.changed_files:
            report.changed_count += 1
            report.changed_files.append(path)
        updated_snapshot[path] = updated

    return report


def _refresh_location_relationships(snapshot: dict[str, str]) -> dict[str, str]:
    """Backfill location hierarchy and derived parent-child relationship sections."""
    location_data: dict[str, tuple[dict, str, str, str | None]] = {}
    children_by_parent: dict[str, list[str]] = {}

    for path, content in snapshot.items():
        if not path.startswith("Locations/"):
            continue
        frontmatter = _parse_frontmatter(content)
        body = _strip_frontmatter(content)
        body = _merge_source_updates_into_description(body)
        body = _sanitize_location_body(body)
        name = _canonical_name(path, frontmatter)
        parent = _infer_parent_location(frontmatter, body, name)
        location_data[path] = (frontmatter, body, name, parent)
        if parent:
            children_by_parent.setdefault(parent, []).append(name)

    updates: dict[str, str] = {}
    for path, (frontmatter, body, name, parent) in location_data.items():
        updated_frontmatter = dict(frontmatter)
        adjacency = updated_frontmatter.pop("adjacent_to", None)
        connected = updated_frontmatter.pop("connected_to", None)
        nearby = adjacency or connected or []
        if isinstance(nearby, list):
            nearby = [_strip_wikilink(str(item)) for item in nearby]
            if parent:
                nearby = [item for item in nearby if _strip_wikilink(item) != parent]
            if nearby:
                updated_frontmatter["adjacent_to"] = nearby
        if parent:
            updated_frontmatter["parent_location"] = parent

        child_locations = sorted(set(children_by_parent.get(name, [])))
        updated_body = _upsert_location_relationship_section(
            body,
            parent,
            child_locations,
            nearby if isinstance(nearby, list) else [],
        )
        rebuilt = _frontmatter(**updated_frontmatter)
        if updated_body and not updated_body.startswith("\n"):
            candidate = f"{rebuilt}\n{updated_body}"
        else:
            candidate = f"{rebuilt}{updated_body}"
        updates[path] = candidate

    return updates


def _infer_parent_location(frontmatter: dict, body: str, name: str) -> str | None:
    """Infer a location's parent from frontmatter or explicit body phrases."""
    parent = frontmatter.get("parent_location")
    if isinstance(parent, str) and parent.strip():
        return _strip_wikilink(parent.strip())

    contained_match = re.search(r"\*\*(?:Contained In|Belongs To):\*\*\s+\[\[([^\]]+)\]\]", body)
    if contained_match:
        return _strip_wikilink(contained_match.group(1))

    description = _extract_section(body, "Description") or body
    description = re.sub(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]", r"\1", description)
    match = re.search(
        r"\b(?:district|location|area|quarter|ward|market|settlement|point of interest|notable area)\s+(?:in|within)\s+([A-Z][A-Za-z' -]+?)(?:\s+(?:containing|contains|featuring|known|with|near)\b|[.\n,]|$)",
        description,
        re.IGNORECASE,
    )
    if not match:
        return None

    candidate = match.group(1).strip()
    if candidate and candidate != name:
        return candidate
    return None


def _upsert_location_relationship_section(
    body: str,
    parent: str | None,
    child_locations: list[str],
    nearby_locations: list[str],
) -> str:
    """Place location relationships in the top note metadata block."""
    body = re.sub(
        r"\n*## Location Relationships\n\n<!-- chronicler:location-relationships:start -->\n.*?\n<!-- chronicler:location-relationships:end -->\n*",
        "\n\n",
        body,
        flags=re.DOTALL,
    )
    lines = body.splitlines()
    skip_prefixes = (
        "**Connected To:**",
        "**Contained In:**",
        "**Adjacent To:**",
        "**Belongs To:**",
        "**Nearby Locations:**",
        "**Contains:**",
    )
    filtered = [line for line in lines if not line.strip().startswith(skip_prefixes)]
    relationship_lines: list[str] = []
    if parent:
        relationship_lines.append(f"**Belongs To:** [[{parent}]]")
    if child_locations:
        relationship_lines.append(f"**Contains:** {', '.join(f'[[{child}]]' for child in child_locations)}")
    if nearby_locations:
        relationship_lines.append(f"**Nearby Locations:** {', '.join(f'[[{name}]]' for name in nearby_locations)}")
    if not relationship_lines:
        return "\n".join(filtered).rstrip() + "\n"
    title_idx = next((i for i, line in enumerate(filtered) if line.startswith("# ")), None)
    if title_idx is None:
        return "\n".join(filtered).rstrip() + "\n"
    insert_at = title_idx + 2 if title_idx + 1 < len(filtered) and filtered[title_idx + 1] == "" else title_idx + 1
    while insert_at < len(filtered) and filtered[insert_at].startswith("**"):
        insert_at += 1
    if insert_at < len(filtered) and filtered[insert_at] != "":
        filtered.insert(insert_at, "")
    for offset, line in enumerate(relationship_lines):
        filtered.insert(insert_at + offset, line)
    if insert_at + len(relationship_lines) < len(filtered) and filtered[insert_at + len(relationship_lines)] != "":
        filtered.insert(insert_at + len(relationship_lines), "")
    return "\n".join(filtered).rstrip() + "\n"


def _extract_section(body: str, heading: str) -> str:
    """Extract text under a ``## heading`` until the next heading."""
    lines = body.splitlines()
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
    return " ".join(line.strip() for line in result if line.strip())


def _strip_wikilink(value: str) -> str:
    cleaned = value.strip()
    while cleaned.startswith("[[") and cleaned.endswith("]]"):
        cleaned = cleaned[2:-2].strip()
    if "|" in cleaned:
        cleaned = cleaned.split("|", 1)[0].strip()
    return cleaned


def _merge_source_updates_into_description(body: str) -> str:
    """Remove visible source-update sections and fold their prose into Description."""
    pattern = re.compile(
        r"\n*## Source Updates\n\n<!-- chronicler:source-updates:start -->\n(.*?)\n<!-- chronicler:source-updates:end -->\n*",
        re.DOTALL,
    )
    match = pattern.search(body)
    if not match:
        return body

    source_block = match.group(1)
    source_block = re.sub(r"(?<!\n)(###\s+)", r"\n\1", source_block)
    paragraphs = []
    for paragraph in re.split(r"\n\s*\n", source_block):
        cleaned = re.sub(r"^### .*$", "", paragraph, flags=re.MULTILINE).strip()
        if cleaned:
            paragraphs.append(cleaned)

    body_without_block = pattern.sub("\n\n", body).rstrip()
    if not paragraphs:
        return body_without_block + ("\n" if body_without_block else "")

    description_addition = "\n\n".join(paragraphs)
    if "## Description\n" in body_without_block:
        section_pattern = re.compile(r"(## Description\n(?:\n)?)(.*?)(\n## |\Z)", re.DOTALL)
        match = section_pattern.search(body_without_block)
        if match:
            existing_description = match.group(2).rstrip()
            merged_description = existing_description
            if description_addition not in existing_description:
                merged_description = (
                    existing_description if not existing_description else f"{existing_description}\n\n{description_addition}"
                )
            replacement = f"{match.group(1)}{merged_description}{match.group(3)}"
            return section_pattern.sub(replacement, body_without_block, count=1).rstrip() + "\n"

    return body_without_block + f"\n\n## Description\n\n{description_addition}\n"


def _sanitize_location_body(body: str) -> str:
    """Remove stale inline source labels and collapse duplicate description headings."""
    cleaned = re.sub(r"###\s+(?:Imported source:[^\n]*|\[\[[^\]]+\]\]\.md)", "", body)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)

    parts = re.split(r"\n## Description\n(?:\n)?", cleaned)
    if len(parts) <= 2:
        return cleaned

    prefix = parts[0]
    description_parts = [part.strip() for part in parts[1:] if part.strip()]
    merged_description = "\n\n".join(description_parts)
    return prefix.rstrip() + "\n\n## Description\n\n" + merged_description + "\n"


def _build_canonical_index(snapshot: dict[str, str]) -> _CanonicalIndex:
    mapping: dict[str, set[str]] = {}

    for path, content in snapshot.items():
        if not _is_supported_note(path):
            continue
        frontmatter = _parse_frontmatter(content)
        canonical_name = _canonical_name(path, frontmatter)
        _add_mapping(mapping, canonical_name, canonical_name)
        stem_name = Path(path).stem
        if stem_name and stem_name != canonical_name:
            _add_mapping(mapping, stem_name, canonical_name)
            for variant in _name_variants(stem_name):
                _add_mapping(mapping, variant, canonical_name)
        for variant in _name_variants(canonical_name):
            _add_mapping(mapping, variant, canonical_name)

        aliases = frontmatter.get("aliases", [])
        if isinstance(aliases, list):
            for alias in aliases:
                if isinstance(alias, str) and alias.strip():
                    cleaned = alias.strip()
                    _add_mapping(mapping, cleaned, canonical_name)
                    for variant in _name_variants(cleaned):
                        _add_mapping(mapping, variant, canonical_name)
        singular_alias = frontmatter.get("alias")
        if isinstance(singular_alias, str) and singular_alias.strip():
            cleaned = singular_alias.strip()
            _add_mapping(mapping, cleaned, canonical_name)
            for variant in _name_variants(cleaned):
                _add_mapping(mapping, variant, canonical_name)
        elif isinstance(singular_alias, list):
            for alias in singular_alias:
                if isinstance(alias, str) and alias.strip():
                    cleaned = alias.strip()
                    _add_mapping(mapping, cleaned, canonical_name)
                    for variant in _name_variants(cleaned):
                        _add_mapping(mapping, variant, canonical_name)

    for alias, canonical in _read_agent_aliases(snapshot).items():
        if canonical in {next(iter(targets)) for targets in mapping.values() if len(targets) == 1}:
            _add_mapping(mapping, alias, canonical)

    link_map: dict[str, str] = {}
    ambiguous_terms: set[str] = set()
    for term, targets in mapping.items():
        if len(targets) == 1:
            canonical = next(iter(targets))
            link_map[term] = wikify(canonical) if term == canonical else f"[[{canonical}|{term}]]"
        elif len(targets) > 1:
            ambiguous_terms.add(term)

    canonical_names = {next(iter(targets)) for targets in mapping.values() if len(targets) == 1}
    term_to_canonical: dict[str, str] = {}
    for term, targets in mapping.items():
        if len(targets) != 1:
            continue
        canonical = next(iter(targets))
        term_to_canonical[term] = canonical
        term_to_canonical[_normalize_quote_style(term)] = canonical
    return _CanonicalIndex(
        link_map=link_map,
        ambiguous_terms=ambiguous_terms,
        term_to_canonical=term_to_canonical,
        canonical_names=canonical_names,
    )


def _name_variants(name: str) -> list[str]:
    variants: set[str] = set()
    normalized = (
        name.replace("“", '"')
        .replace("”", '"')
        .replace("‘", "'")
        .replace("’", "'")
    )
    variants.add(normalized)
    ascii_folded = unicodedata.normalize("NFKD", normalized).encode("ascii", "ignore").decode("ascii")
    if ascii_folded and ascii_folded != normalized:
        variants.add(ascii_folded)
    quote_swap = re.sub(r"'([^']+)'", r'"\1"', normalized)
    if quote_swap and quote_swap != normalized:
        variants.add(quote_swap)
    quote_swap_back = re.sub(r'"([^"]+)"', r"'\1'", normalized)
    if quote_swap_back and quote_swap_back != normalized:
        variants.add(quote_swap_back)
    stripped = re.sub(r'\s*["\'][^"\']+["\']\s*', " ", normalized).strip()
    stripped = re.sub(r"\s{2,}", " ", stripped)
    if stripped and stripped != normalized:
        variants.add(stripped)
        stripped_ascii = unicodedata.normalize("NFKD", stripped).encode("ascii", "ignore").decode("ascii")
        if stripped_ascii and stripped_ascii != stripped:
            variants.add(stripped_ascii)
    return [variant for variant in variants if variant and variant != name]


def _add_mapping(mapping: dict[str, set[str]], term: str, canonical: str) -> None:
    cleaned_term = term.strip()
    cleaned_canonical = canonical.strip()
    if not cleaned_term or not cleaned_canonical:
        return
    mapping.setdefault(cleaned_term, set()).add(cleaned_canonical)


def _read_agent_aliases(snapshot: dict[str, str]) -> dict[str, str]:
    content = snapshot.get("_Agent/Memory/entity-aliases.md", "")
    body = _strip_frontmatter(content)
    aliases: dict[str, str] = {}
    for line in body.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        alias, _, canonical = line.partition(":")
        aliases[alias.strip()] = canonical.strip()
    return aliases


def _improve_note(path: str, content: str, index: _CanonicalIndex) -> tuple[str, list[AgentQuestion]]:
    frontmatter = _parse_frontmatter(content)
    body = _strip_frontmatter(content)
    questions: list[AgentQuestion] = []

    updated_frontmatter = _normalize_frontmatter(frontmatter, path, index, questions)
    updated_body = _normalize_body(path, body, frontmatter, index)
    _collect_ambiguity_questions(path, body, index, questions)

    rebuilt = _frontmatter(**updated_frontmatter)
    if updated_body and not updated_body.startswith("\n"):
        candidate = f"{rebuilt}\n{updated_body}"
    else:
        candidate = f"{rebuilt}{updated_body}"

    if candidate == content:
        return content, questions
    return candidate, questions


def _normalize_frontmatter(
    frontmatter: dict,
    path: str,
    index: _CanonicalIndex,
    questions: list[AgentQuestion],
) -> dict:
    updated = dict(frontmatter)

    for key in _REFERENCE_SCALAR_KEYS:
        value = updated.get(key)
        if not isinstance(value, str) or not value.strip():
            continue
        resolved = _resolve_reference(value, index)
        if resolved is None:
            if _strip_wikilink(value) in index.ambiguous_terms:
                questions.append(_ambiguity_question(path, _strip_wikilink(value)))
            continue
        updated[key] = resolved

    for key in _REFERENCE_LIST_KEYS:
        value = updated.get(key)
        if not isinstance(value, list):
            continue
        rewritten: list[str] = []
        for item in value:
            if not isinstance(item, str) or not item.strip():
                continue
            resolved = _resolve_reference(item, index)
            if resolved is None:
                if _strip_wikilink(item) in index.ambiguous_terms:
                    questions.append(_ambiguity_question(path, _strip_wikilink(item)))
                rewritten.append(item)
            else:
                rewritten.append(resolved)
        updated[key] = rewritten

    return updated


def _resolve_reference(value: str, index: _CanonicalIndex) -> str | None:
    raw = _strip_wikilink(value).strip()
    if raw in index.link_map:
        return _strip_wikilink(index.link_map[raw])
    return None


def _link_body(body: str, index: _CanonicalIndex) -> str:
    if not body.strip():
        return body

    linked_lines: list[str] = []
    for line in body.splitlines():
        if line.startswith("#"):
            linked_lines.append(line)
            continue
        normalized = _repair_mixed_name_links(line, index)
        normalized = _normalize_existing_links(normalized, index)
        linked_lines.append(_link_text(normalized, index.link_map))
    suffix = "\n" if body.endswith("\n") else ""
    return "\n".join(linked_lines) + suffix


def _normalize_body(
    path: str,
    body: str,
    frontmatter: dict,
    index: _CanonicalIndex,
) -> str:
    lines = body.splitlines()
    if path.startswith("Sessions/") and lines:
        lines[0] = _normalize_session_heading(lines[0], frontmatter)
    normalized = "\n".join(lines)
    if body.endswith("\n"):
        normalized += "\n"
    return _link_body(normalized, index)


def _normalize_existing_links(text: str, index: _CanonicalIndex) -> str:
    if not text:
        return text

    def _replace(match: re.Match[str]) -> str:
        target = match.group(1).strip()
        alias = match.group(2)
        canonical = index.term_to_canonical.get(target) or index.term_to_canonical.get(
            _normalize_quote_style(target)
        )
        if canonical:
            if alias:
                return f"[[{canonical}|{alias}]]"
            return f"[[{canonical}]]"
        return match.group(0)

    return re.sub(r"\[\[([^\]|]+)(?:\|([^\]]+))?\]\]", _replace, text)


def _repair_mixed_name_links(text: str, index: _CanonicalIndex) -> str:
    if not text:
        return text

    def _repair_alias_plus_suffix(match: re.Match[str]) -> str:
        target = match.group(1).strip()
        alias = match.group(2).strip()
        suffix = match.group(3).strip()
        canonical = index.term_to_canonical.get(_normalize_quote_style(target))
        if not canonical:
            return match.group(0)
        candidate = f"{alias} {suffix}".strip()
        if _matches_canonical_display(candidate, canonical):
            return f"[[{canonical}|{candidate}]]"
        return match.group(0)

    repaired = re.sub(
        r"\[\[([^\]|]+)\|([^\]]+)\]\]\s+([A-Z][\w'’\-]+)",
        _repair_alias_plus_suffix,
        text,
    )

    def _repair_embedded_nickname(match: re.Match[str]) -> str:
        prefix = match.group(1).strip()
        quote = match.group(2)
        target = match.group(3).strip()
        alias = match.group(4).strip()
        suffix = match.group(5).strip()
        canonical = index.term_to_canonical.get(_normalize_quote_style(target))
        if not canonical:
            return match.group(0)
        candidate = f"{prefix} {quote}{alias}{quote} {suffix}".strip()
        if _matches_canonical_display(candidate, canonical):
            return f"[[{canonical}|{candidate}]]"
        if _matches_nickname_surname(alias, suffix, canonical):
            return f"[[{canonical}]]"
        return match.group(0)

    return re.sub(
        r"([A-Z][\w'’\-]+)\s+([\"'])\[\[([^\]|]+)\|([^\]]+)\]\]\2\s+([A-Z][\w'’\-]+)",
        _repair_embedded_nickname,
        repaired,
    )


def _normalize_quote_style(value: str) -> str:
    return (
        value.replace("“", '"')
        .replace("”", '"')
        .replace("‘", "'")
        .replace("’", "'")
    )


def _matches_canonical_display(candidate: str, canonical: str) -> bool:
    normalized_candidate = _normalize_quote_style(candidate).strip()
    variants = {
        _normalize_quote_style(canonical).strip(),
        *(_normalize_quote_style(variant).strip() for variant in _name_variants(canonical)),
    }
    return normalized_candidate in variants


def _matches_nickname_surname(alias: str, suffix: str, canonical: str) -> bool:
    nickname_match = re.search(r'["\']([^"\']+)["\']', _normalize_quote_style(canonical))
    surname = _normalize_quote_style(canonical).split()[-1]
    if not nickname_match:
        return False
    return (
        _normalize_quote_style(alias).strip() == nickname_match.group(1).strip()
        and _normalize_quote_style(suffix).strip() == surname.strip()
    )


def _canonicalize_party_timeline(note: str, index: _CanonicalIndex) -> str:
    return _canonicalize_managed_section(
        note=note,
        heading="Timeline",
        placeholder="_No timeline entries yet._",
        normalize_entry=lambda entry: _normalize_timeline_entry(entry, index),
    )


def _canonicalize_party_relationships(
    note: str,
    index: _CanonicalIndex,
    self_canonical: str,
) -> str:
    normalized_self = _normalize_quote_style(self_canonical)
    return _canonicalize_managed_section(
        note=note,
        heading="Relationships",
        placeholder="_No relationships recorded yet._",
        normalize_entry=lambda entry: _normalize_relationship_entry(
            entry, index, normalized_self
        ),
    )


def _canonicalize_managed_section(
    note: str,
    heading: str,
    placeholder: str,
    normalize_entry,
) -> str:
    lines = note.splitlines()
    result: list[str] = []
    target_heading = f"## {heading}"
    in_section = False
    seen: set[str] = set()
    wrote_entries = False

    for line in lines:
        if line == target_heading:
            in_section = True
            seen.clear()
            wrote_entries = False
            result.append(line)
            continue

        if in_section and line.startswith("## ") and line != target_heading:
            if not wrote_entries:
                result.append("")
                result.append(placeholder)
            in_section = False
            result.append(line)
            continue

        if not in_section:
            result.append(line)
            continue

        if not line.strip():
            if wrote_entries:
                result.append(line)
            continue

        if line.strip().startswith("_No "):
            continue

        normalized = normalize_entry(line.strip())
        if normalized is None or normalized in seen:
            continue
        if not wrote_entries:
            result.append("")
        result.append(normalized)
        seen.add(normalized)
        wrote_entries = True

    if in_section and not wrote_entries:
        result.append("")
        result.append(placeholder)

    suffix = "\n" if note.endswith("\n") else ""
    return "\n".join(result) + suffix


def _normalize_timeline_entry(entry: str, index: _CanonicalIndex) -> str | None:
    if not entry.startswith("- [[Session-"):
        return None
    prefix, sep, detail = entry.partition(": ")
    if not sep:
        return None
    normalized_detail = _repair_mixed_name_links(detail, index)
    normalized_detail = _normalize_existing_links(normalized_detail, index)
    normalized_detail = _link_text(normalized_detail, index.link_map)
    return f"{prefix}: {normalized_detail}"


def _normalize_relationship_entry(
    entry: str,
    index: _CanonicalIndex,
    normalized_self: str,
) -> str | None:
    match = re.match(r"^-\s+\[\[([^\]|]+)(?:\|[^\]]+)?\]\]\s*$", entry)
    if not match:
        return None
    original_target = match.group(1).strip()
    canonical = index.term_to_canonical.get(_normalize_quote_style(original_target))
    target = canonical or original_target
    if _normalize_quote_style(target) == normalized_self:
        return None
    return f"- [[{target}]]"


def _normalize_session_heading(line: str, frontmatter: dict) -> str:
    if not line.startswith("# "):
        return line
    title = frontmatter.get("title")
    if not isinstance(title, str) or not title.strip():
        return line
    heading = line[2:].strip()
    if heading == title:
        return line
    if heading.startswith(f"{title}:"):
        return f"# {title}"
    duplicate = re.match(r"^(Session\s+\d+:\s+)(.+)$", heading)
    if duplicate and duplicate.group(2).strip() == title.strip():
        return f"# {title}"
    if heading == f"{title}: {title}":
        return f"# {title}"
    return line


def _collect_ambiguity_questions(
    path: str,
    body: str,
    index: _CanonicalIndex,
    questions: list[AgentQuestion],
) -> None:
    prose_lines = [line for line in body.splitlines() if not line.startswith("#")]
    protected = re.sub(r"\[\[[^\]]+\]\]", "", "\n".join(prose_lines))
    seen: set[str] = set()
    for term in sorted(index.ambiguous_terms, key=len, reverse=True):
        if term in seen:
            continue
        pattern = re.compile(rf"(?<![\w]){re.escape(term)}(?![\w])")
        if pattern.search(protected):
            questions.append(_ambiguity_question(path, term))
            seen.add(term)


def _ambiguity_question(path: str, term: str) -> AgentQuestion:
    return AgentQuestion(
        question=f"Which note should '{term}' link to?",
        context=(
            "issue_type: ambiguous_entity_reference\n"
            f"note: {path}\n"
            f"term: {term}\n"
            "The improver found multiple possible canonical targets and did not auto-link it."
        ),
        priority=QuestionPriority.MEDIUM,
    )


def _question_path(note_path: str, question_text: str) -> str:
    stem = Path(note_path).stem.lower()
    slug = re.sub(r"[^a-z0-9]+", "-", question_text.lower()).strip("-")
    return f"_Agent/Questions/{stem}-{slug[:48]}.md"


def _render_question(question: AgentQuestion, source_path: str) -> str:
    lines = [
        "---",
        "type: agent-question",
        f"priority: {question.priority.value}",
        "---",
        "",
        f"# {question.question}",
        "",
        f"**Source Note:** {source_path}",
        "",
        f"**Context:** {question.context}",
        "",
    ]
    return "\n".join(lines)


def _canonical_name(path: str, frontmatter: dict) -> str:
    return Path(path).stem


def _parse_frontmatter(content: str) -> dict:
    if not content.startswith("---"):
        return {}
    parts = content.split("---", 2)
    if len(parts) < 3:
        return {}
    data = yaml.safe_load(parts[1])
    return data if isinstance(data, dict) else {}


def _strip_frontmatter(content: str) -> str:
    if not content.startswith("---"):
        return content
    parts = content.split("---", 2)
    if len(parts) < 3:
        return content
    return parts[2].lstrip("\n")


def _strip_wikilink(value: str) -> str:
    match = re.fullmatch(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]", value.strip())
    if match:
        return match.group(1)
    return value


def _is_supported_note(path: str) -> bool:
    return path.endswith(".md") and (
        path.startswith(_SUPPORTED_FOLDERS) or path in _SUPPORTED_ROOT_NOTES
    )
