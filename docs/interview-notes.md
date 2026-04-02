# D&D Session Scribe — Discovery Interview

**Date:** 2026-04-02
**Participants:** Scott (user), Claude (interviewer)

---

## Project Context

- **Purpose:** Real tool for Scott's active D&D campaign, also a portfolio piece to write about and show off. Must work reliably — not a throwaway demo.
- **Campaign:** 22 sessions so far, 7-8 players, 3-4 hour sessions.
- **Current pain:** Manual note-taking is tedious and disruptive. Post-session organization is worse. Goal is zero manual effort.

---

## Existing Data & Backlog

- **~22 sessions** of transcripts to process as backlog.
- **Transcripts are the primary source of truth**, existing notes are supplementary.
- **PLAUD NotePin** is the recording device. Exports two files per session:
  - **PDF summary** — well-structured with sections, key intel, action items, tactical diagrams. High signal.
  - **Raw transcript (.txt)** — continuous text with timestamps every ~30-60 seconds. No speaker labels. Heavy mix of in-game content and real-life banter (food orders, personal stories, off-topic conversation).
- **Existing vaults:** One game-specific vault (difficult to use), some notes in personal vault, other random files. Starting fresh with a new vault.

### Transcript Characteristics (from Session 22 sample)

- Timestamps present but no speaker identification.
- Significant real-life crosstalk that needs filtering (estimated 30-50% of transcript is off-topic).
- In-game content is freeform — DM doesn't always clearly introduce NPCs/locations. Names and details emerge organically from conversation.
- PLAUD summary already does solid extraction — agent should use it as primary source, transcript for gap-filling and nuance.

---

## V1 Scope (Agreed)

### In Scope

1. **Transcript ingestion** — PLAUD summary PDFs + raw transcripts, processed chronologically session by session.
2. **Entity extraction** — NPCs, locations, factions, plot hooks, loot, key events via powerful model on nano-gpt.com.
3. **Vault population** — Obsidian vault with densely wikilinked notes. Top-level categories defined by Scott, agent owns everything below that.
4. **Session recaps + open threads** — per-session summary and a living "open threads/unanswered questions" document.
5. **Vector store** — local embeddings over vault contents for retrieval.
6. **Interactive CLI chat** — natural language questions about the campaign, grounded in vault contents.
7. **Async question queue** — agent flags low-confidence extractions for Scott to answer between sessions. Feedback loop to improve over time.
8. **Vault review & improvement** — agent can re-read existing notes, identify inconsistencies, fill gaps, improve linking, merge duplicates, refine quality.
9. **Agent memory** — dedicated area in the vault for the agent's learned rules, patterns, preferences, corrections. Persists across sessions. Scott can inspect but doesn't interact with it often.
10. **Backlog processing** — process ~22 existing sessions through the pipeline, a few at a time with human review between batches.

### Out of V1 Scope (Future)

- Live audio streaming / whisper.cpp integration
- Real-time monitoring sidebar
- Live session updates
- Asking Scott questions during gameplay

---

## Key Design Decisions

### Inference
- **nano-gpt.com** for LLM extraction and chat (multiple model options, use the most powerful available).
- **Local model** for vector embeddings only.
- Original PRD specified LM Studio/Qwen — superseded by this decision.

### Vault Integration
- **Obsidian CLI** (official, released Feb 2026, GA in v1.12.4) is the preferred interface. Supports CRUD, search, templates, frontmatter, tags, links.
  - Requires Obsidian desktop app to be running (acts as remote control).
  - Fallback to direct filesystem writes if needed.
- Agent designs its own vault organization below the top-level categories.
- Heavy use of `[[wikilinks]]` — critical for graph view usability.

### User Interaction Patterns
- **Primary use case:** Review open threads and session recap before each game.
- **Graph view and natural language queries** are the most important interaction modes.
- **Browsing file tree** is secondary.
- **CLI chat** for asking questions — no web server needed for V1.

### Backlog Strategy
- Chronological processing, a few sessions at a time.
- Scott reviews vault output and answers agent's questions between batches.
- Allows catching extraction mistakes early before they compound.

### Quality & Testing
- **TDD-style development** with tests covering common user stories.
- **Evals** to measure agent extraction quality over time.
- **Golden test fixtures** from real data — hand-labeled expected output from the sample session transcript/summary.
- Build it right from the foundation rather than rushing.
- AI agents will be coding it, so milestones and clear module boundaries are important.

---

## Technical Notes

### PLAUD Summary Content (from sample)
- Session title and timestamp
- Structured sections: Interrogation Findings, Underground Smuggling Grid, Tactical Execution, Critical Next Steps
- Key intel extracted: cult operations, key locations, personnel counts, tactical details
- Action items per player (mix of player/character names — mostly not useful for the agent)

### PLAUD Transcript Content (from sample)
- Timestamps every ~30-60 seconds (format: HH:MM:SS)
- No speaker labels
- Massive amount of off-topic banter mixed with game content
- Game content includes: DM narration, player decisions, dice rolls, spell descriptions, tactical planning, character dialogue
- Real-life content includes: food delivery logistics, personal stories, name discussions, holiday conversations

### Player/Character Note
- Speaker labels available in PLAUD but unreliable — uses player names not character names.
- Decision: skip speaker labels for now, agent can infer from context.
- Action items from PLAUD summaries: skip, they're artifacts not real campaign data.

---

## Open Questions for Design Phase

- Specific vault categories Scott wants at the top level
- nano-gpt.com model selection (which models are available, pricing considerations)
- Obsidian CLI availability on Scott's machine (Catalyst license or GA version?)
- Vector store technology choice (ChromaDB, FAISS, etc.)
- Agent memory schema design
