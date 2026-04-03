"""Fuzzy entity name matching for deduplication."""

from thefuzz import fuzz


def find_match(
    name: str,
    existing_names: list[str],
    alias_map: dict[str, list[str]] | None = None,
    threshold: int = 80,
) -> str | None:
    """Find the best match for a name among existing entities.

    Checks in order: exact (case-insensitive), alias, fuzzy.
    Returns the matched existing name, or None.
    """
    name_lower = name.lower().strip()

    for existing in existing_names:
        if existing.lower().strip() == name_lower:
            return existing

    if alias_map:
        for entity_name, aliases in alias_map.items():
            for alias in aliases:
                if alias.lower().strip() == name_lower:
                    return entity_name

    best_score = 0
    best_match = None
    for existing in existing_names:
        score = max(
            fuzz.token_sort_ratio(name_lower, existing.lower()),
            fuzz.partial_ratio(name_lower, existing.lower()),
        )
        if score > best_score and score >= threshold:
            best_score = score
            best_match = existing

    return best_match


def is_duplicate(
    name: str,
    existing_names: list[str],
    alias_map: dict[str, list[str]] | None = None,
    threshold: int = 80,
) -> bool:
    return find_match(name, existing_names, alias_map, threshold) is not None
