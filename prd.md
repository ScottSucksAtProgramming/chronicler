# D&D Live Session Scribe — Project Spec

## Overview

A real-time AI agent that listens to an active D&D session, transcribes it live, extracts structured campaign data, and automatically populates an Obsidian vault — so you can focus entirely on playing.

---

## Problem Statement

Manual session note-taking is tedious, disruptive, and easy to fall behind on. Post-session organization is even worse. The goal is zero manual effort: hit record, play your session, open Obsidian to find a fully organized set of notes already waiting.

---

## Core Workflow
```
PLAUD Device (audio capture)
        ↓
whisper.cpp (live streaming transcription on MacBook Pro)
        ↓
Session Scribe Agent (Python service — local)
        ↓
Obsidian Vault (auto-populated via Local REST API plugin)
```

---

## Stack

| Component | Tool |
|---|---|
| Audio capture | PLAUD NotePin |
| Live transcription | whisper.cpp (streaming mode) |
| Agent runtime | Python (FastAPI or async service) |
| LLM for extraction | LM Studio (Qwen) — local, no API needed |
| Vault integration | Obsidian Local REST API plugin |
| Orchestration | Claude Code (for building and iteration) |

---

## Agent Responsibilities

### Real-Time Extraction (during session)
- Detect and create NPC entries (name, description, first mention timestamp)
- Log locations as they're introduced or revisited
- Flag plot hooks and unresolved threads
- Note major player decisions with context
- Track loot and items mentioned
- Timestamp key moments in the session

### Deduplication & Linking
- Recognize when an existing vault entity is mentioned (e.g. "the tavern" → links to existing `Locations/The-Prancing-Pony.md`)
- Append new information to existing notes rather than creating duplicates
- Build wikilinks between related notes automatically

### Post-Session Synthesis (after recording ends)
- Generate a session summary note
- Update the campaign timeline
- Create a "loose threads" note of unresolved plot hooks
- Flag any new relationships between NPCs or factions

---

## Obsidian Vault Structure
```
Campaign/
├── Sessions/
│   ├── Session-001.md
│   ├── Session-002.md
│   └── ...
├── NPCs/
│   ├── _NPC-Template.md
│   └── [auto-generated NPC notes]
├── Locations/
│   ├── _Location-Template.md
│   └── [auto-generated location notes]
├── Factions/
├── Loot/
├── Timeline.md
└── Loose-Threads.md
```

---

## NPC Note Template (auto-generated)
```markdown
# {{NPC Name}}

**First Appeared:** Session {{number}} — {{timestamp}}
**Affiliation:** 
**Status:** Alive / Dead / Unknown

## Description
{{extracted description}}

## Key Interactions
- Session {{number}}: {{summary}}

## Notes
```

---

## Optional: Live Sidebar Feed

A lightweight terminal or simple web UI (Flask) running on the Mac that shows:
- "🧙 New NPC detected: Theron the Ranger"
- "📍 New location: The Sunken Vault"
- "⚠️ Plot hook flagged: The missing merchant"

Gives you ambient awareness without pulling you out of the game.

---

## Build Phases

### Phase 1 — Transcription Pipeline
- Get whisper.cpp running in streaming/live mode on MacBook
- Confirm it outputs a rolling transcript to stdout or a file

### Phase 2 — Extraction Agent
- Python service watches the transcript stream
- LM Studio (Qwen) extracts structured entities per chunk
- Outputs JSON: `{ type: "npc", name: "Theron", description: "...", timestamp: "00:14:32" }`

### Phase 3 — Vault Integration
- Install Obsidian Local REST API plugin
- Agent pushes new/updated notes to vault via HTTP
- Deduplication logic: check if note exists before creating

### Phase 4 — Post-Session Synthesis
- On session end signal, run a full-session pass
- Generate summary note, update timeline, compile loose threads

### Phase 5 — Live Sidebar (optional)
- Simple Flask web UI or terminal feed
- Shows real-time entity detection events

---

## Key Technical Considerations

- **whisper.cpp streaming**: Use `--step` and `--length` flags for chunked live output
- **Chunk size**: Process transcript in ~30-60 second rolling windows to balance latency vs. context
- **LM Studio model**: Qwen is already set up — use a structured prompt that returns JSON
- **Obsidian REST API**: Requires the community plugin enabled and an API key set
- **No PHI concerns**: Pure creative/personal use, no HIPAA considerations

---

## Success Criteria

- Session ends → vault is populated with zero manual effort
- NPCs, locations, and plot hooks are findable by next session
- No duplicate notes created
- Runs headlessly on MacBook without needing attention during play

---

## Related Projects / Reusable Components

- EMScribe (Python transcript processing patterns)
- Existing Obsidian vault PARA structure + HOME.md dashboard
- PLAUD → whisper.cpp → LM Studio pipeline already in use for EMS docs
- Claude Code skills for autonomous building and testing