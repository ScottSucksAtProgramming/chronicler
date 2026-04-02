# D&D Session Scribe — Design Specification

**Date:** 2026-04-02  
**Status:** Draft  
**Author:** Claude (with Scott)

---

## 1. Overview

A Python-based agent that ingests PLAUD session recordings (PDF summaries + raw transcripts), extracts structured D&D campaign data via LLM, populates and maintains an Obsidian vault, and provides an interactive CLI for querying campaign knowledge. The agent learns and improves over time through persistent memory stored in the vault.

### What This Is

- A reliable tool for Scott's active D&D campaign (22 sessions and counting, 7-8 players, 3-4 hour sessions)
- A portfolio piece demonstrating well-built AI agent architecture
- A zero-manual-effort note-taking system: export from PLAUD, run the agent, open Obsidian

### What This Is Not (V1)

- Not a live transcription system (no whisper.cpp, no streaming audio)
- Not a real-time session monitor (no sidebar, no during-game updates)
- Not a web application (CLI only)

---

## 2. Core Principles

These govern every implementation decision. Written for AI agent coders who will build this.

### Clean Architecture

- Strict separation of concerns. Each module has one job.
- Dependencies point inward — domain logic never depends on infrastructure. The extraction logic doesn't know about Obsidian. The vault manager doesn't know about nano-gpt.com.
- All external services (LLM API, Obsidian CLI, filesystem, vector store) are accessed through interfaces/abstractions. Swap implementations without touching business logic.

### Testability First

- Every module is independently testable with no external dependencies in unit tests.
- TDD: write the test, watch it fail, make it pass.
- Golden fixtures from real session data are the foundation of extraction evals.
- Integration tests hit real services but are isolated from unit tests.
- User-style testing after every milestone — manual QA from a real user's perspective.

### Explicit Over Clever

- No magic. No metaprogramming. No dynamic imports. AI coders (and humans) should be able to read any file and understand what it does without tracing through abstractions.
- Flat is better than nested. A function that does one thing clearly is better than a class hierarchy.
- Type hints everywhere. Pydantic models for all data structures. No passing raw dicts between modules.

### Small Files, Clear Boundaries

- No file over ~300 lines. If it's growing, it's doing too much — split it.
- Each module exposes a clear public interface. Internal implementation details stay internal.
- Module communication happens through defined data structures, never by reaching into another module's internals.

### Fail Loudly, Recover Gracefully

- Never swallow errors silently. Log what happened and why.
- Extraction failures on one entity shouldn't kill the whole session processing. Process what you can, flag what you can't.
- Every LLM call can fail or return garbage. Validate outputs against expected schemas.

### Vault is Source of Truth

- The Obsidian vault is the single source of truth for all campaign state.
- Agent memory lives in the vault, not in a separate database.
- If it's not in the vault, it doesn't exist. No hidden state.

---

## 3. Architecture

### Module Overview

```
┌─────────────────────────────────────────────────┐
│                  CLI Interface                    │
│      (typer commands + textual chat TUI)          │
└──────────┬──────────────┬──────────────┬─────────┘
           │              │              │
    ┌──────▼──────┐ ┌─────▼─────┐ ┌─────▼─────┐
    │  Ingestion  │ │   Chat    │ │  Reviewer  │
    │   Module    │ │  Module   │ │   Module   │
    └──────┬──────┘ └─────┬─────┘ └─────┬──────┘
           │              │              │
    ┌──────▼──────┐ ┌─────▼─────┐       │
    │ Extraction  │ │ Retrieval │       │
    │   Module    │ │   Layer   │       │
    └──────┬──────┘ └─────┬─────┘       │
           │              │              │
    ┌──────▼──────────────▼──────────────▼─────────┐
    │              Vault Manager                    │
    │   (read/write/search/link/memory)             │
    └──────────────────┬───────────────────────────┘
                       │
              ┌────────▼────────┐
              │  Obsidian Vault │
              │   (filesystem   │
              │    + CLI)       │
              └─────────────────┘

              ┌─────────────────┐
              │   LLM Gateway   │  ← shared by Ingestion, Extraction,
              │  (nano-gpt.com) │     Chat, and Reviewer
              └─────────────────┘
```

### Module Responsibilities

**CLI Interface**
- Entry point for all user interaction.
- `typer` handles non-interactive commands: `scribe ingest`, `scribe review`, `scribe reindex`, `scribe ask` (review and answer the agent's pending questions — shows the queue, accepts answers one at a time), `scribe stats` (show LLM usage and cost tracking).
- `textual` handles `scribe chat` — drops into a rich interactive TUI for campaign Q&A.
- Thin delegation layer — no business logic lives here.

**Ingestion Module**
- Accepts PLAUD PDF summaries and raw transcript .txt files.
- Parses PDFs into structured text with layout awareness. Validates expected PLAUD structure — fails loudly if format has changed.
- Normalizes transcript timestamps.
- Filters out-of-game banter from in-game content (LLM-assisted via LLM Gateway).
- Outputs a normalized session document that the extraction module consumes.
- Does NOT know about Obsidian or the vault.

**Extraction Module**
- Takes a normalized session document plus a context bundle (from Vault Manager) containing known entities, active threads, and recent events.
- Uses LLM (via LLM Gateway) to extract structured entities: NPCs, locations, factions, plot hooks, loot, key events.
- PLAUD summary is the primary extraction source (high-signal, pre-structured). Raw transcript is the ground truth and is used for supplementary enrichment — filling gaps, verifying details, and capturing nuance the summary missed. When the two conflict, the transcript wins.
- Generates a session recap and identifies open/closed threads.
- Flags low-confidence extractions as questions for Scott.
- Outputs Pydantic models, NOT markdown. Does not write to the vault.
- Never calls Vault Manager directly — receives context bundle as a parameter.

**LLM Gateway**
- Single integration point for all LLM calls across the system.
- Handles nano-gpt.com API communication, model selection, request/response serialization.
- Prompt versioning — each module's prompts are stored as Jinja2 or string templates in a `prompts/` directory, organized by module (e.g., `prompts/extraction/extract_entities.py`). Each prompt has a version comment. Changes to prompts are tracked in git.
- Error handling: max 3 retries with exponential backoff (1s, 2s, 4s). 30-second timeout per request. On exhaustion, raise with clear error message.
- Rate limiting and cost tracking: log every LLM call (model, token count, latency) to a local log file. Surface cumulative cost per session via `scribe stats`.
- Validates LLM outputs against expected Pydantic schemas before returning. On validation failure, retry with a corrective prompt (once), then flag as failed extraction.

**Vault Manager**
- The ONLY module that touches Obsidian. All vault reads and writes go through here.
- Note CRUD: create, read, update, append, delete.
- Wikilink generation and management.
- Deduplication checks (fuzzy matching on entity names + aliases from agent memory).
- Frontmatter management (type, status, tags, affiliations, aliases).
- Agent memory read/write (extraction rules, user preferences, entity aliases, etc.).
- Context bundle generation: `get_context_bundle(session_number)` returns a `ContextBundle` Pydantic model containing:
  - `known_npcs`: list of NPC names, aliases, and status (alive/dead/unknown)
  - `known_locations`: list of location names and aliases
  - `known_factions`: list of faction names and key members
  - `active_threads`: list of currently open plot threads with summaries
  - `recent_events`: recap of the previous 2-3 sessions for continuity
  - `entity_aliases`: full alias mapping from agent memory
  - `player_characters`: player-to-character mapping and known abilities
- Uses Obsidian CLI for search, create, append operations. Direct filesystem for bulk reads and writing normalized transcripts.
- Fallback strategy: on CLI call failure (timeout, connection refused, unexpected error), log the error and fall back to direct filesystem operations. CLI-only operations (search) degrade to grep over markdown files. Detect CLI availability at startup via a health check command.
- Exposes clean interface: `get_npc()`, `create_location()`, `append_to_session()`, `search()`, etc.

**Retrieval Layer**
- Manages local vector store (ChromaDB) with embeddings of vault contents.
- Embeddings generated via LM Studio serving `nomic-embed-text-v1.5` locally on M3 Pro MacBook.
- Re-indexes when vault changes (triggered by Vault Manager, not polling).
- Provides semantic search: query → relevant note chunks with source attribution.
- Used by Chat Module and Reviewer Module.

**Chat Module**
- Interactive CLI conversation about the campaign via Textual TUI.
- Uses Retrieval Layer to find relevant vault context, sends to LLM (via LLM Gateway) with the question.
- Conversation history within a chat session, not persisted between sessions.
- Answers grounded in vault content — cites source notes.

**Reviewer Module**
- Runs quality passes over the vault. Triggered manually (`scribe review`) or automatically after ingestion.
- Checks: broken wikilinks, duplicate entities, notes missing key fields, inconsistencies across notes, timeline gaps, orphaned notes.
- Can propose improvements: new links, merged notes, updated descriptions.
- Writes findings to Review-Log. Applies high-confidence fixes directly, flags low-confidence findings as agent questions.

### Data Flow: Ingest a Session

```
PLAUD PDF + transcript
       │
       ▼
  [Ingestion] → Normalized session document
       │
       ▼
  [Vault Manager] → get_context_bundle(session_number)
       │
       ▼
  [Extraction] (normalized doc + context bundle)
       │
       ▼
  Structured entities + recap + questions
       │
       ▼
  [Vault Manager] → creates/updates notes in Obsidian
       │
       ▼
  [Retrieval Layer] → re-indexes new content
       │
       ▼
  [Reviewer] → quality check on new/updated notes
```

---

## 4. Vault Structure

### Top-Level Organization

```
Campaign/
├── _Dashboard.md
├── Sessions/
│   ├── Session-001.md
│   ├── Session-002.md
│   └── ...
├── NPCs/
│   └── [auto-generated]
├── Locations/
│   └── [auto-generated]
├── Factions/
│   └── [auto-generated]
├── Loot/
│   └── [auto-generated]
├── Plot-Threads/
│   ├── _Open-Threads.md
│   ├── _Closed-Threads.md
│   └── [individual thread notes]
├── Timeline.md
├── _Agent/
│   ├── Memory/
│   │   ├── extraction-rules.md
│   │   ├── user-preferences.md
│   │   ├── entity-aliases.md
│   │   ├── player-characters.md
│   │   └── campaign-patterns.md
│   ├── Questions/
│   │   └── [pending questions for Scott]
│   └── Review-Log.md
└── Transcripts/
    ├── raw/
    └── normalized/
```

### Design Choices

- **`_` prefix** on agent-managed files/folders separates "for Scott" from "agent internals."
- **Dashboard** is the single landing page — links to latest recap, open threads, recent changes. Updated after every ingestion.
- **Open Threads** is the most important living document — updated every session, threads move to Closed when resolved.
- **Entity aliases** in agent memory solve the "the tavern" → `[[Smoked Eel Tavern]]` problem. Built over time from context and user corrections.
- **Transcripts stored in vault** so the retrieval layer can search them.
- Dense **wikilinks** throughout — every entity mention is a link. Critical for Obsidian's graph view.

### Note Format Example (NPC)

```markdown
---
type: npc
status: alive
first_appeared: Session-022
affiliations:
  - "[[Sylvie's Cult]]"
aliases:
  - "the friendly face"
tags:
  - cult
  - informant
---

# The Friendly Face

**First Appeared:** [[Session-022]]
**Status:** Alive (assassinated by clone — original status unknown)
**Affiliation:** [[Sylvie's Cult]] (paid operative)

## Description
A man previously hired by the cult to confront the party. Known for his
distinctive friendly demeanor. Operates from a booby-trapped safe house.

## Key Interactions
- **[[Session-022]]:** Party tracked him to his safe house. Found it ransacked
  and booby-trapped (powder traps, poison darts). Discovered underground tunnel
  network beneath. Located him in a second safe house, interrogated him. Revealed
  details about [[Sylvie]]'s smuggling operation, [[The Black Spire]], and
  cloning activities. Assassinated by his own clone via crossbow bolt before
  session ended.

## Intel Provided
- Works for [[Sylvie]], smuggling chemicals and soil to [[The Farm]]
- ~20 townsfolk involved, including [[Bill Tidewater]]
- [[The Black Spire]] is in the swamp
- Magical glyphs bypassed by knocking three times
- Clones are a known cult tactic
```

---

## 5. Technology Stack

| Component | Choice | Rationale |
|-----------|--------|-----------|
| Language | Python 3.12+ | LLM ecosystem, PDF parsing, embeddings. Matches EMScribe patterns. |
| LLM API | nano-gpt.com | Multiple model options, powerful models available. Single integration via LLM Gateway. |
| Local embeddings | LM Studio serving `nomic-embed-text-v1.5` | Already installed on M3 Pro MacBook. 8192 token context, strong narrative text performance. |
| Vector store | ChromaDB | Lightweight, local, file-based, no server. Good Python API. |
| PDF parsing | `pdfplumber` | Layout-aware text extraction for PLAUD's structured PDFs. |
| Data models | Pydantic v2 | Type-safe structures, validation, serialization. Natural LLM output parsing. |
| Vault integration | Obsidian CLI + direct filesystem | CLI for search/create/append. Filesystem for bulk reads and transcript storage. |
| Testing | `pytest` | Standard. Fixtures, parametrize, clean assertions. |
| Evals | Custom eval harness + golden fixtures | Hand-labeled expected output from real sessions. Precision/recall per entity type. |
| CLI commands | `typer` | Type-hint-driven CLI for non-interactive commands. |
| Interactive chat | `textual` | Rich TUI for campaign Q&A. Claude Code-style interactive experience. |
| Output formatting | `rich` (bundled with textual) | Beautiful terminal output — tables, markdown rendering, panels. |
| Package management | `uv` | Fast, modern, handles venvs and dependencies. |

### Not Using

| Skipped | Why |
|---------|-----|
| LangChain / CrewAI | Unnecessary orchestration overhead for a predictable pipeline. |
| SQLite / Postgres | Vault is the database. ChromaDB handles vectors. No relational needs. |
| FastAPI / Flask | No web server in V1. CLI only. |
| whisper.cpp | Not needed for V1. PLAUD handles transcription. |
| Docker | Runs locally on Mac. No deployment complexity needed. |

---

## 6. Testing Strategy

### Unit Tests (per module)

- **Ingestion:** Given this PDF/transcript input, produces this normalized output.
- **Extraction:** Given this normalized doc + context bundle, produces these entities.
- **LLM Gateway:** Request/response serialization, error handling, retries, schema validation.
- **Vault Manager:** Given these entities, creates/updates correct files with correct wikilinks and frontmatter.
- **Retrieval:** Given this query, returns relevant chunks.
- **Chat:** Given retrieval results + question, produces grounded answer.
- **Reviewer:** Given this vault state, detects these issues.

### Golden Fixture Tests

Hand-label Session 22 (the sample we have) as the first golden fixture:

- **Expected NPCs:** The Friendly Face, Sylvie, Bill Tidewater, Pavo, Yisela Tideborn, Santiago, Quattro, Lisa/Lyssa
- **Expected Locations:** The safe house, underground tunnel network (6 tunnels), The Black Spire, The Farm, city docks, wine cellar, Smoked Eel Tavern, the Mayweather (ship), the party's ship
- **Expected Factions:** Sylvie's Cult
- **Expected Plot Threads:** Smuggling operation, cloning activities, The Black Spire in the swamp, the Mayweather's cargo, ~20 townsfolk involvement
- **Expected Session Recap:** Key beats from reconnaissance through interrogation to assassination

Extraction module runs against this fixture. Measure precision (did we extract garbage?) and recall (did we miss real entities?). Add a new golden fixture every few sessions to catch regression.

### Integration Tests

- End-to-end: ingest real files → extraction → vault population → verify vault contents.
- Obsidian CLI operations: create, read, search, append — verify each works. Catches CLI breaking changes early.
- LM Studio embedding endpoint: verify connectivity and output shape.
- nano-gpt.com: verify API connectivity and response parsing.

### Eval Framework

- After each ingestion run, compare extracted entities against the PLAUD summary as a baseline.
- Track extraction quality metrics over time as agent memory improves.
- Reviewer module findings are themselves an eval — count of broken links, duplicates, gaps per session.

### Output Quality Validation

The agent must validate the quality of its own output, not just functional correctness. This goes beyond "did the code run without errors" to "is the output actually good."

**LLM-as-Judge:** After extraction, a separate LLM call evaluates the output against a quality rubric:
- **Completeness:** Did we capture all entities that appear in the source material?
- **Accuracy:** Are entity names, descriptions, and relationships correct? No hallucinated details?
- **Coherence:** Does the session recap read as a clear narrative? Would someone who wasn't there understand what happened?
- **Relevance:** Did we filter out real-life banter and only capture in-game content?
- **Linking quality:** Are wikilinks pointing to the right entities? Are aliases resolved correctly?

Each dimension is scored 1-5. Scores below 3 on any dimension trigger a re-extraction or flag for human review. Scores are logged per session for trend tracking.

**Structural Validation:** Programmatic checks on generated markdown:
- Frontmatter parses correctly (valid YAML)
- All wikilinks resolve to existing notes (or are flagged as new entities to create)
- Required fields are present per entity type (NPC must have status, first_appeared, etc.)
- No empty sections in generated notes
- Timestamps and session references are internally consistent

**Regression Detection:** Compare current extraction quality scores against historical averages. Alert if quality drops significantly on a new session (may indicate PLAUD format change, model degradation, or unusual session content).

### User-Style Testing

After every milestone, conduct manual QA from the user's perspective. This is NOT automated testing — this is using the software the way Scott would and looking for bugs, bad experiences, confusing output, and quality issues.

**Process:**
1. Define user stories specific to the milestone.
2. Execute each story manually, acting as Scott would.
3. Document every issue found: bugs, UX friction, output quality problems, confusing behavior.
4. Fix all issues before declaring the milestone complete.
5. Re-test after fixes to verify resolution.

**User stories are defined per-milestone below in Section 7.**

The system must feel polished and reliable before Scott touches it. No "it works if you do it exactly right" — it needs to handle real-world messiness gracefully.

---

## 7. Milestones

### Milestone 1: Foundation

**Scope:**
- Project scaffolding: package structure, `uv` setup, `pytest` configuration
- Pydantic data models for all entity types (NPC, Location, Faction, PlotThread, Loot, SessionRecap, Question, AgentMemory)
- LLM Gateway with nano-gpt.com integration
- Basic config system (vault path, API keys, model selection, LM Studio endpoint)
- Tests: data model validation, LLM Gateway mocked round-trip

**User-Style Testing — Stories:**
- "I clone the repo and run `uv sync` — does everything install cleanly?"
- "I run `scribe --help` — do I see clear, understandable commands?"
- "I run `scribe config` — can I set my vault path, API key, and model without confusion?"
- "I misconfigure something — does it tell me what's wrong clearly?"

---

### Milestone 2: Ingestion + Extraction

**Scope:**
- PDF parser for PLAUD summaries with structure validation
- Transcript parser with timestamp normalization
- Banter filtering (LLM-assisted via LLM Gateway)
- Entity extraction from normalized session documents
- Golden fixture for Session 22, extraction eval passing
- Tests: ingestion parsing, extraction precision/recall against golden fixture

**User-Style Testing — Stories:**
- "I run `scribe ingest session-22-summary.pdf session-22-transcript.txt` — does it process without errors?"
- "I give it just a PDF with no transcript — does it handle that gracefully?"
- "I give it just a transcript with no PDF — does it handle that gracefully?"
- "I give it a corrupted or differently-formatted PDF — does it fail with a clear message?"
- "I look at the extracted entities — are they accurate? Are the NPCs real NPCs and not players? Are the locations real locations and not real-world references? Did it filter out the food delivery conversation and the Passover discussion?"
- "I look at the flagged questions — are they reasonable things to be uncertain about, or is it flagging obvious stuff?"
- "I look at the session recap — does it capture the key beats? Would I know what happened last session from reading this?"

---

### Milestone 3: Vault Management

**Scope:**
- Vault Manager with Obsidian CLI + filesystem operations
- Note creation with templates, frontmatter, wikilinks
- Deduplication logic (fuzzy matching on entity names + aliases)
- Context bundle generation for extraction
- Agent memory read/write
- Tests: note CRUD, dedup logic, wikilink generation, integration tests against real vault

**User-Style Testing — Stories:**
- "I open the vault in Obsidian — does the folder structure make sense at a glance?"
- "I open an NPC note — is it well-formatted, does the frontmatter render correctly, are the wikilinks clickable?"
- "I click on a wikilink — does it go to the right note?"
- "I open the graph view — are entities connected in ways that make sense?"
- "I search for 'Sylvie' in Obsidian — do I find all relevant notes?"
- "I run ingestion twice on the same session — does it update existing notes rather than creating duplicates?"
- "I look at the agent memory files — do they contain reasonable learned information?"

---

### Milestone 4: End-to-End Pipeline

**Scope:**
- Wire ingestion → extraction → vault manager together as complete pipeline
- Process Session 22 end-to-end, verify vault output
- Question queue for low-confidence extractions
- Reviewer module: link checking, duplicate detection, gap analysis
- Dashboard and Open Threads generation
- Tests: full pipeline integration test, reviewer finding detection

**User-Style Testing — Stories:**
- "I run `scribe ingest` on Session 22 from scratch — does the vault populate correctly in one command?"
- "I open _Dashboard.md — does it show me useful information? Can I navigate to the session recap and open threads from here?"
- "I open _Open-Threads.md — are these real unresolved plot threads from the session?"
- "I run `scribe review` — does it find real issues? Are its fixes correct?"
- "I run `scribe ask` — can I see the agent's pending questions? Can I answer them? Does the agent incorporate my answers?"
- "I process a second session — does the vault grow correctly? Do existing NPC notes get updated rather than duplicated? Do open threads update?"
- "The agent made a mistake (wrong NPC name, bad link) — can I fix it manually in Obsidian and the agent respects my change next time?"

---

### Milestone 5: Retrieval + Chat

**Scope:**
- LM Studio embedding integration via OpenAI-compatible API
- ChromaDB vector store, indexing vault contents
- Retrieval layer with semantic search
- Chat module with Textual TUI
- Tests: embedding generation, retrieval relevance, chat response grounding

**User-Style Testing — Stories:**
- "I run `scribe chat` — does the TUI launch cleanly? Is it intuitive?"
- "I ask 'What do we know about Sylvie?' — does it give me a comprehensive answer citing the right notes?"
- "I ask 'When did we first encounter the cult?' — does it find the right session?"
- "I ask 'What are our open plot threads?' — does it match what's in _Open-Threads.md?"
- "I ask a vague question like 'What happened with the boat?' — does it figure out I mean the Mayweather?"
- "I ask about something that doesn't exist in the vault — does it say it doesn't know rather than hallucinating?"
- "I have a multi-turn conversation — does it maintain context? 'Tell me about the tunnels' then 'How many were there?' — does it know I mean the tunnels?"
- "Is the TUI responsive? Does output render cleanly? Is it pleasant to use?"
- "LM Studio is not running — does `scribe chat` give me a clear error instead of crashing?"
- "I ask a question and the nano-gpt.com API is slow/down — does it handle the timeout gracefully?"
- "I run `scribe reindex` after manually editing notes in Obsidian — does the vector store update correctly?"

---

### Milestone 6: Backlog Processing

**Quality Gates:**
- Extraction precision above 85% by session 10 (measured against golden fixtures and spot checks)
- Reviewer findings (broken links, duplicates) trending downward across sessions
- Agent memory contains accurate player-character mappings and at least 10 entity aliases by session 15
- Chat can answer basic questions about events from any processed session

**Scope:**
- Process sessions 1-22 chronologically in batches
- Human review loops between batches
- Agent memory accumulation
- Vault quality stabilization
- Evals: extraction quality trend across sessions, reviewer findings decreasing over time

**User-Style Testing — Stories:**
- "I process sessions 1-5 — does the vault build up coherently?"
- "I answer the agent's questions from sessions 1-5 — does it use those answers when processing sessions 6-10?"
- "I look at the agent memory after 10 sessions — has it learned useful patterns? Player-character mappings? Entity aliases? DM naming conventions?"
- "I open the graph view after all 22 sessions — does it show a meaningful web of campaign relationships?"
- "I open _Open-Threads.md after all 22 sessions — does it reflect the current state of the campaign, not just the latest session?"
- "I ask the chat 'Give me a full recap of our campaign so far' — does it produce something coherent and accurate?"
- "I compare the vault to my memory of the campaign — are there major events, NPCs, or locations missing? Are there fabricated ones that never happened?"
- "Would I confidently use this vault to prep for our next session?"
- "I process sessions out of order (e.g., skip session 8) — does it handle the gap or warn me?"
- "A transcript is unusually short or low-quality — does the agent flag this rather than producing garbage?"
- "I delete a note manually in Obsidian and re-run ingestion — does it recreate it correctly?"

---

## 8. Open Questions

To be resolved during implementation:

- **nano-gpt.com model selection:** Which specific models are available and what works best for structured D&D entity extraction? Test during Milestone 2.
- **Obsidian CLI version:** Verify Scott has GA version (v1.12.4+) installed. Test during Milestone 3.
- **Banter filtering approach:** What prompt strategy best separates in-game from out-of-game content? Evaluate during Milestone 2 with real transcripts.
- **Deduplication threshold:** How fuzzy should entity matching be? Too strict = duplicates. Too loose = false merges. Tune during Milestone 3.
- **Embedding chunk size:** How should vault notes be chunked for embedding? By section? By paragraph? Whole note? Test during Milestone 5.
