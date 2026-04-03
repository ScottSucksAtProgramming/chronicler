---
type: agent-memory
title: Vault Guide
---
# Vault Guide
This vault is the source of truth for campaign knowledge. Chat should prefer direct vault notes over
retrieval summaries when they disagree.

## Authority Order
1. Directly read vault notes
2. Session notes and structured campaign notes
3. Retrieval hits from the vector index
4. Conversation history alone

If retrieval suggests something but the directly read note says otherwise, trust the note.

## Folder Map
- `Party/`
  Authoritative source for player characters, player-to-character mapping, and character class/role
  details.
- `Sessions/`
  Authoritative source for what happened in each session. Use these for recap details, key events,
  discoveries, and when specific items or NPCs first appeared.
- `NPCs/`
  Canonical notes for NPC identity, aliases, affiliations, status, and known interactions.
- `Locations/`
  Canonical notes for places, landmarks, vessels, settlements, and connected locations.
- `Factions/`
  Canonical notes for organizations, memberships, goals, and relationships.
- `Loot/`
  Canonical notes for items, where they were found, who holds them, and why they matter.
- `Plot-Threads/`
  Campaign objective tracking.
  - `_Open-Threads.md` is the current source for active unresolved threads.
  - `_Closed-Threads.md` is historical reference for resolved threads.
  - `_Dashboard.md`
  High-level current-state summary.
  - `Timeline.md`
  High-level chronological summary across sessions.
- `_Agent/Memory/`
  Persistent agent memory, extraction rules, aliases, campaign patterns, and operating guidance.
- `_Agent/Questions/`
  Open questions or ambiguities that still need confirmation.

## Chat Rules
For every question:
- Always read `Party/`
- Always read `_Agent/Memory/`
- Always read `_Dashboard.md`
- Always read `Timeline.md`
- Always read `Plot-Threads/_Open-Threads.md`
- Use vector retrieval to discover additional relevant notes
- Directly read the source files returned by retrieval before answering

## Interpretation Rules
- Missing retrieval results do not mean the vault lacks the information.
- If notes conflict, say so explicitly instead of choosing silently.
- If a fact appears only in one weak source, say it is uncertain.
- Prefer session notes for "what happened" questions.
- Prefer entity notes for "who/what is this" questions.
- Prefer `Party/` over incidental mentions in session notes for player character identity.

## Common Lookups
- "Who are the player characters?"
  Check `Party/` first.
- "What happened in Session N?"
  Check `Sessions/Session-NNN.md`.
- "What are the current objectives?"
  Check `Plot-Threads/_Open-Threads.md`, then recent session notes.
- "Who/what is X?"
  Check the relevant entity folder first, then session notes for context.
- "Why does this item matter?"
  Check `Loot/`, then the session where it was found, then open threads.

## Behavior Expectations
Do not say "it is not in the vault" unless:
- core files were read
- relevant retrieved source notes were read
- and the information is still absent

When possible, cite notes with wikilinks.
