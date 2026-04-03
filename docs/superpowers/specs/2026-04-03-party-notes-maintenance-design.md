# Party Notes Maintenance Design

**Date:** 2026-04-03
**Status:** Approved for implementation

## Goal

Make `Party/` notes first-class maintained records that accumulate explicit character information and session-linked changes over time.

## Problem

Party notes currently act as thin stubs. They are authoritative for reading player-character identity, but they are not enriched by `ingest` or `improve`, so they remain mostly empty and do not show how a character changed across sessions.

This leaves a major gap in the vault:

- party members are under-linked in session notes
- `Party/` lacks meaningful character state
- there is no maintained timeline of character evolution

## Approach

Treat `Party/` notes like maintained entity notes with app-managed sections.

Each party note should have stable sections:

- `## Overview`
- `## Aliases`
- `## Known Facts`
- `## Timeline`
- `## Relationships`
- `## Notable Items`
- `## Open Questions`

The app should update only those managed sections and preserve other user-authored content.

## Update Model

### Ingest

When a new session is ingested:

- detect explicit mentions of player characters in the extracted recap and entity lists
- append session-linked timeline bullets for explicit character activity
- add explicit aliases, relationships, and notable items when clearly stated

### Improve

When `chronicler improve` runs:

- backfill missing links for party members in supported notes
- scan existing session notes for explicit party-member facts
- append missing timeline and structured facts into party notes
- route ambiguous candidate facts into `_Agent/Questions/`

## Safety Rules

Only auto-apply facts that are explicit in the vault.

Allowed:

- exact or alias-backed character references
- session-linked timeline bullets derived from explicit note text
- directly stated relationships and held items
- deterministic link enrichment

Not allowed in v1:

- inferred personality summaries
- speculative motivations
- rewriting user-authored prose outside managed sections
- choosing between conflicting interpretations silently

## Managed Section Behavior

### Overview

A short current-state summary. In v1 this can remain minimal or be derived only from explicit note content. Do not allow broad LLM rewriting here.

### Aliases

Canonical aliases for the character, from party frontmatter and explicit vault memory.

### Known Facts

Stable bullet facts such as class, titles, or recurring explicit descriptors.

### Timeline

Session-linked bullets showing what changed or what the character explicitly did.

Example:

- `[[Session-003]]: Helped fight Zalzigarath aboard the Sloop Dogg`

### Relationships

Explicit ties to NPCs, factions, and party members when stated in the vault.

### Notable Items

Explicit possessions or recurring character-linked items.

### Open Questions

Character-specific unresolved issues gathered from ambiguity handling.

## Implementation Shape

Use a dedicated party-note updater rather than embedding this logic in the CLI.

Suggested responsibilities:

- parse party notes into managed sections
- extract explicit character facts from session notes
- merge new facts idempotently into the right sections
- preserve unmanaged user content
- expose helpers used by both `ingest` and `improve`

## Verification

- renderer tests for new party note structure
- updater tests for section merge and idempotency
- ingest tests for party-note updates after extraction
- improve tests for backfilling from existing session notes
- full test suite run
