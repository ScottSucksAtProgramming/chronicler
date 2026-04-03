"""Prompt templates for entity extraction, recap generation, and quality evaluation.

All prompts are versioned. Changes are tracked in git.
"""

from chronicler.models.context import ContextBundle


def _format_context(context: ContextBundle) -> str:
    """Format a ContextBundle into a string for inclusion in prompts."""
    parts = []

    if context.known_npcs:
        npc_list = ", ".join(
            f"{n.name} ({'/'.join(n.aliases)})" if n.aliases else n.name
            for n in context.known_npcs
        )
        parts.append(f"Known NPCs: {npc_list}")

    if context.known_locations:
        loc_list = ", ".join(n.name for n in context.known_locations)
        parts.append(f"Known Locations: {loc_list}")

    if context.known_factions:
        fac_list = ", ".join(n.name for n in context.known_factions)
        parts.append(f"Known Factions: {fac_list}")

    if context.active_threads:
        thread_list = "\n".join(f"  - {t.title}: {t.summary}" for t in context.active_threads)
        parts.append(f"Active Plot Threads:\n{thread_list}")

    if context.entity_aliases:
        alias_list = "\n".join(f'  - "{k}" → {v}' for k, v in context.entity_aliases.items())
        parts.append(f"Entity Aliases (use these to resolve ambiguous references):\n{alias_list}")

    if context.player_characters:
        pc_list = ", ".join(
            f"{pc.character_name} (played by {pc.player_name})"
            for pc in context.player_characters
        )
        parts.append(f"Player Characters (do NOT extract these as NPCs): {pc_list}")

    if context.recent_events:
        events = "\n".join(f"  - {e}" for e in context.recent_events)
        parts.append(f"Recent Events (for continuity):\n{events}")

    return "\n\n".join(parts) if parts else "No prior campaign context available."


# v1 — 2026-04-02
def build_extraction_prompt(
    summary_text: str | None,
    transcript_text: str | None,
    context: ContextBundle,
) -> str:
    """Build the entity extraction prompt."""

    context_str = _format_context(context)
    session_number = context.session_number

    source_parts = []
    if summary_text:
        source_parts.append(
            f"## PLAUD Session Summary (primary source — high signal)\n\n{summary_text}"
        )
    if transcript_text:
        source_parts.append(
            f"## Raw Transcript (supplementary — use to fill gaps and verify details)\n\n{transcript_text}"
        )

    source_text = "\n\n---\n\n".join(source_parts) if source_parts else "No source text provided."

    return f"""You are extracting structured D&D campaign data from a session recording.

## Campaign Context

{context_str}

## Source Material

{source_text}

## Instructions

Extract ALL of the following from the session material. Be thorough — missing an NPC or location is worse than including a minor one.

**IMPORTANT RULES:**
- Do NOT extract player characters as NPCs. Player characters are listed in the context above.
- Do NOT extract real-world people, places, or events. Only extract in-game D&D content.
- If a name appears in the context as an existing entity, use the EXACT name from context (not a variation).
- If you're uncertain whether something is an NPC or a player character, flag it as a question.
- For the `first_appeared` field, use "Session-{session_number:03d}" format.

Return a JSON object with this exact structure:
```json
{{
  "npcs": [
    {{
      "name": "string",
      "first_appeared": "Session-NNN",
      "status": "alive|dead|unknown",
      "description": "string",
      "aliases": ["string"],
      "affiliations": ["string"],
      "tags": ["string"],
      "key_interactions": ["string — brief summary of what this NPC did this session"]
    }}
  ],
  "locations": [
    {{
      "name": "string",
      "first_appeared": "Session-NNN",
      "description": "string",
      "aliases": ["string"],
      "connected_to": ["string"],
      "tags": ["string"]
    }}
  ],
  "factions": [
    {{
      "name": "string",
      "first_appeared": "Session-NNN",
      "description": "string",
      "known_members": ["string"],
      "aliases": ["string"],
      "tags": ["string"]
    }}
  ],
  "loot": [
    {{
      "name": "string",
      "found_in": "Session-NNN",
      "description": "string",
      "held_by": "string or null — who currently has this item",
      "tags": ["string"]
    }}
  ],
  "plot_threads": [
    {{
      "title": "string",
      "status": "open|closed",
      "introduced_in": "Session-NNN",
      "summary": "string"
    }}
  ],
  "questions": [
    {{
      "question": "string",
      "context": "string",
      "priority": "low|medium|high"
    }}
  ]
}}
```

Return ONLY the JSON object. No markdown formatting, no explanation."""


def build_source_extraction_prompt(
    source_text: str,
    context: ContextBundle,
    source_label: str,
    session_anchor: int | None,
    source_attribution: str | None,
) -> str:
    """Build an extraction prompt for general imported source material."""
    context_str = _format_context(context)
    session_rule = (
        f'- This import is anchored to Session {session_anchor}. Use "Session-{session_anchor:03d}" for session provenance fields when justified.'
        if session_anchor is not None
        else (
            "- This import is not anchored to a session. Leave session provenance fields as null unless the material explicitly establishes a session.\n"
            "- Use `source_attribution` for extracted entities when the material indicates who authored or supplied the information."
        )
    )
    known_attribution = (
        f"Known source attribution: {source_attribution}"
        if source_attribution
        else "Known source attribution: none"
    )

    return f"""You are extracting structured D&D campaign data from imported campaign source material.

## Campaign Context

{context_str}

## Source Metadata

- Source label: {source_label}
- {known_attribution}

## Source Material

{source_text}

## Instructions

Extract campaign knowledge from this material.

**IMPORTANT RULES:**
- Do NOT extract player characters as NPCs.
- Do NOT invent session provenance for unanchored material.
- If a source attribution is apparent from the document, preserve it in `source_attribution`.
- If the material lacks enough provenance to safely ground important extracted facts, add a question asking the user for source attribution.
- For locations, use `parent_location` for containment (district in city, city in region) and `adjacent_to` for neighbor-style map links.
- Only include location relationships when the source is explicit enough to be reliable. If the document leaves unclear geography, add a question instead of guessing.
- Use null for session provenance fields when the source is unanchored and the document does not establish a session.
- {session_rule}

Return a JSON object with this exact structure:
```json
{{
  "npcs": [
    {{
      "name": "string",
      "first_appeared": "Session-NNN or null",
      "source_attribution": "string or null",
      "status": "alive|dead|unknown",
      "description": "string",
      "aliases": ["string"],
      "affiliations": ["string"],
      "tags": ["string"],
      "key_interactions": ["string"]
    }}
  ],
  "locations": [
    {{
      "name": "string",
      "first_appeared": "Session-NNN or null",
      "source_attribution": "string or null",
      "description": "string",
      "aliases": ["string"],
      "parent_location": "string or null",
      "adjacent_to": ["string"],
      "connected_to": ["string"],
      "tags": ["string"]
    }}
  ],
  "factions": [
    {{
      "name": "string",
      "first_appeared": "Session-NNN or null",
      "source_attribution": "string or null",
      "description": "string",
      "known_members": ["string"],
      "aliases": ["string"],
      "tags": ["string"]
    }}
  ],
  "loot": [
    {{
      "name": "string",
      "found_in": "Session-NNN or null",
      "source_attribution": "string or null",
      "description": "string",
      "held_by": "string or null",
      "tags": ["string"]
    }}
  ],
  "plot_threads": [
    {{
      "title": "string",
      "status": "open|closed",
      "introduced_in": "Session-NNN or null",
      "source_attribution": "string or null",
      "summary": "string"
    }}
  ],
  "questions": [
    {{
      "question": "string",
      "context": "string",
      "priority": "low|medium|high"
    }}
  ]
}}
```

Return ONLY the JSON object. No markdown formatting, no explanation."""


# v1 — 2026-04-02
def build_recap_prompt(summary_text: str, session_number: int) -> str:
    """Build the session recap generation prompt."""
    return f"""You are writing a session recap for D&D Session {session_number}.

Based on the following session summary, write a concise but complete recap that captures:
1. The main narrative arc of the session
2. Key decisions the party made
3. Important revelations or discoveries
4. How the session ended

Also identify the key events with approximate timestamps if available.

## Source Material

{summary_text}

Return a JSON object:
```json
{{
  "title": "Short session title",
  "summary": "2-4 paragraph narrative recap",
  "key_events": [
    {{"description": "What happened", "timestamp": "HH:MM:SS or null"}}
  ]
}}
```

Return ONLY the JSON object."""


# v1 — 2026-04-02
def build_quality_judge_prompt(source_text: str, extraction_json: str) -> str:
    """Build the LLM-as-judge quality evaluation prompt."""
    return f"""You are evaluating the quality of a D&D session entity extraction.

## Original Source Material

{source_text}

## Extraction Result

{extraction_json}

## Evaluation Criteria

Score each dimension from 1 (poor) to 5 (excellent):

1. **Completeness**: Did the extraction capture all NPCs, locations, factions, plot threads, and loot mentioned in the source?
2. **Accuracy**: Are the extracted names, descriptions, and relationships correct? No hallucinated details?
3. **Coherence**: Does the session recap read as a clear narrative? Would someone who wasn't there understand what happened?
4. **Relevance**: Was real-life banter correctly excluded? Only in-game D&D content extracted?
5. **Linking Quality**: Are entity names consistent? Would aliases resolve correctly? Are affiliations and connections accurate?

Return a JSON object:
```json
{{
  "completeness": 1-5,
  "accuracy": 1-5,
  "coherence": 1-5,
  "relevance": 1-5,
  "linking_quality": 1-5,
  "notes": "Brief explanation of any low scores"
}}
```

Return ONLY the JSON object."""
