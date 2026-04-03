"""Helpers for loading authoritative chat context directly from the vault."""

from __future__ import annotations

from dataclasses import dataclass
import re

from chronicler.retrieval.retrieval import SearchResult

_CORE_FILE_PATHS = [
    "_Agent/Memory/vault-guide.md",
    "_Dashboard.md",
    "Timeline.md",
    "Plot-Threads/_Open-Threads.md",
]

_CORE_FOLDERS = [
    "_Agent/Memory/",
    "Party/",
]


@dataclass
class DirectVaultNote:
    """A note read directly from the vault filesystem or CLI."""

    path: str
    content: str


@dataclass
class ChatContextBundle:
    """All note layers used to answer a chat question."""

    core_notes: list[DirectVaultNote]
    supporting_notes: list[DirectVaultNote]
    retrieval_hits: list[SearchResult]


def _normalize(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def _extract_search_phrases(query: str) -> list[str]:
    cleaned = query.strip().rstrip("?.!")
    phrases: list[str] = []

    match = re.match(r"(?i)what is (?:the )?(.+)$", cleaned)
    if match:
        phrases.append(match.group(1).strip())

    if not phrases:
        phrases.append(cleaned)

    return [phrase for phrase in phrases if phrase]


def _safe_read(cli, path: str) -> str | None:
    try:
        return cli.read(path)
    except Exception:
        return None


def _is_meta_question(query: str) -> bool:
    lowered = query.lower()
    markers = [
        "what questions do you have",
        "what are you unsure about",
        "what information is missing",
        "what should i clarify",
    ]
    return any(marker in lowered for marker in markers)


def _extract_alias_terms(memory_notes: list[DirectVaultNote]) -> list[str]:
    aliases: list[str] = []
    for note in memory_notes:
        if not note.path.endswith("entity-aliases.md"):
            continue
        for line in note.content.splitlines():
            if ":" not in line or line.startswith("---"):
                continue
            _, alias = line.split(":", 1)
            alias = alias.strip()
            if alias:
                aliases.append(alias)
    return aliases


def _discover_fallback_paths(
    cli,
    query: str,
    core_notes: list[DirectVaultNote],
    retrieval_results: list[SearchResult],
) -> list[str]:
    try:
        all_files = cli.list_files()
    except Exception:
        all_files = []

    seen = {note.path for note in core_notes}
    seen.update(result.path for result in retrieval_results if result.path)

    fallback_paths: list[str] = []
    normalized_query = _normalize(query)
    alias_terms = [_normalize(term) for term in _extract_alias_terms(core_notes) if term]

    if _is_meta_question(query):
        session_paths = [path for path in all_files if path.startswith("Sessions/")]
        if not session_paths:
            try:
                session_paths = cli.find_notes_in_folder("Sessions/")
            except Exception:
                session_paths = []
        for path in session_paths:
            if path.startswith("Sessions/") and path not in seen:
                fallback_paths.append(path)
        return fallback_paths

    for path in all_files:
        if path in seen:
            continue
        normalized_path = _normalize(path.rsplit("/", 1)[-1].replace(".md", ""))
        if normalized_query and normalized_query in normalized_path:
            fallback_paths.append(path)
            continue
        if any(alias and alias in normalized_query for alias in alias_terms):
            if path.startswith(("Sessions/", "Locations/", "NPCs/", "Factions/", "Loot/")):
                fallback_paths.append(path)

    if normalized_query:
        content_matches: list[str] = []
        for phrase in _extract_search_phrases(query):
            try:
                phrase_matches = cli.search(phrase)
            except Exception:
                phrase_matches = []
            for path in phrase_matches:
                if path in seen or path in fallback_paths or path in content_matches:
                    continue
                content_matches.append(path)

        for path in content_matches:
            if path.startswith(("Sessions/", "Locations/", "NPCs/", "Factions/", "Loot/")):
                fallback_paths.append(path)

    return fallback_paths

def load_chat_context(cli, query: str, retrieval_results: list[SearchResult]) -> ChatContextBundle:
    """Load core vault notes plus direct reads for retrieval source files."""
    core_notes: list[DirectVaultNote] = []
    seen_core_paths: set[str] = set()

    for path in _CORE_FILE_PATHS:
        if path in seen_core_paths:
            continue
        try:
            exists = cli.note_exists(path)
        except Exception:
            exists = False
        if not exists:
            continue
        content = _safe_read(cli, path)
        if content is None:
            continue
        core_notes.append(DirectVaultNote(path=path, content=content))
        seen_core_paths.add(path)

    for folder in _CORE_FOLDERS:
        try:
            paths = cli.find_notes_in_folder(folder)
        except Exception:
            paths = []
        for path in paths:
            if path in seen_core_paths:
                continue
            content = _safe_read(cli, path)
            if content is None:
                continue
            core_notes.append(DirectVaultNote(path=path, content=content))
            seen_core_paths.add(path)

    supporting_notes: list[DirectVaultNote] = []
    seen_supporting_paths: set[str] = set()
    for result in retrieval_results:
        path = result.path
        if not path or path in seen_core_paths or path in seen_supporting_paths:
            continue
        content = _safe_read(cli, path)
        if content is None:
            continue
        supporting_notes.append(DirectVaultNote(path=path, content=content))
        seen_supporting_paths.add(path)

    for path in _discover_fallback_paths(cli, query, core_notes, retrieval_results):
        if path in seen_core_paths or path in seen_supporting_paths:
            continue
        content = _safe_read(cli, path)
        if content is None:
            continue
        supporting_notes.append(DirectVaultNote(path=path, content=content))
        seen_supporting_paths.add(path)

    return ChatContextBundle(
        core_notes=core_notes,
        supporting_notes=supporting_notes,
        retrieval_hits=retrieval_results,
    )
