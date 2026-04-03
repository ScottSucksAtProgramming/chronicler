---
type: agent-memory
---
# Extraction Rules

## New Entity Detection
When processing transcripts or notes, create new vault entries for:
1. **Named NPCs** - Any character with a name mentioned by DM or players
2. **Named Locations** - Places, buildings, vessels, landmarks
3. **Items** - Named magical items, quest items, valuables worth noting
4. **Factions** - Organizations, guilds, groups with distinct identity

## Alias Capture
- Note ALL name variations heard in transcripts
- Mark transcription errors separately from canonical aliases
- Update entity-aliases.md when new patterns are discovered

## Session Note Structure
```yaml
---
type: session
session_number: N
title: "Session N: Descriptive Title"
npcs:
  - NPC Name (new or appearing)
locations:
  - Location Name (new or visited)
---
```

## Key Events to Capture
- Combat encounters and outcomes
- New loot acquired and who holds it
- NPC deaths or status changes
- Quest decisions and moral dilemmas
- New information about ongoing plots
- Party member actions that reveal character

## Link Creation Rules
1. Use wikilinks `[[Note Name]]` for all vault references
2. Use aliases for readability: `[[Full Name|Display Name]]`
3. Link first occurrence in each section, not every occurrence
4. Always link to canonical note names, not aliases

## Loot Documentation
For each notable item found:
- Item name and type
- Found in which session
- Currently held by which character
- Estimated value if known
- Magical properties if identified

## NPC Status Tracking
- Mark status: alive, dead, unknown
- Note affiliations (factions, groups)
- Capture key interactions with party
- Update if status changes
