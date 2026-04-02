# D&D Session Scribe

## Purpose

AI agent that ingests PLAUD session recordings (PDF summaries + raw transcripts), extracts structured D&D campaign data via LLM, populates an Obsidian vault, and provides an interactive CLI for querying campaign knowledge. Built for Scott's active campaign (22+ sessions, 7-8 players). Also a portfolio piece.

## Tree

```
dnd_notes_organizaer/
  CLAUDE.md
  INDEX.md
  prd.md
  pyproject.toml
  .env.example
  src/
    session_scribe/
      __init__.py
      py.typed
      cli/
        main.py          — typer CLI entry point (ingest, chat, review, ask, config, reindex, stats)
      models/
        __init__.py      — public exports for all 15+ Pydantic models
        entities.py      — NPC, Location, Faction, LootItem, PlotThread
        session.py       — NormalizedSession, TranscriptSegment, SessionRecap, KeyEvent
        extraction.py    — ExtractionResult, AgentQuestion, QualityScore
        context.py       — ContextBundle, EntitySummary, AgentMemory, PlayerCharacter
      gateway/
        __init__.py
        llm_gateway.py   — LLMGateway (nano-gpt.com, retries, structured output)
        types.py         — LLMRequest, LLMResponse, LLMUsage
      config/
        settings.py      — Settings via pydantic-settings (SCRIBE_ env prefix)
      ingestion/
        __init__.py
        pdf_parser.py    — parse_plaud_pdf, ParsedPDF, PDFSection, PLAUDParseError
      vault/
        __init__.py
        obsidian_cli.py  — ObsidianCLI, ObsidianCLIError (low-level CLI wrapper)
  tests/
    conftest.py          — shared fixtures (settings, tmp_vault)
    cli/
    models/
    gateway/
    config/
    ingestion/
      test_pdf_parser.py
    vault/
      __init__.py
      test_obsidian_cli.py
  docs/
    interview-notes.md
    superpowers/
      specs/
        2026-04-02-session-scribe-design.md
      plans/
        2026-04-02-milestone-1-foundation.md
  context/
    conventions.md
    lessons.md
```

## Rules

1. On session start within `dnd_notes_organizaer/`, read this file, then `INDEX.md`.
2. The **design spec** (`docs/superpowers/specs/2026-04-02-session-scribe-design.md`) is the primary reference for architecture, modules, and scope. The original PRD is historical only.
3. Read the relevant **milestone plan** before starting implementation work.
4. Do not deviate from the vault structure or module boundaries in the spec without discussing with Scott.
5. When creating, renaming, or deleting files, update the Tree section above.
6. Follow the Note-Taking protocol below after completing tasks.

## Core Principles

These are non-negotiable. See the design spec Section 2 for full details.

- **Clean Architecture:** Dependencies point inward. Domain logic never depends on infrastructure.
- **Testability First:** TDD. Golden fixtures. User-style testing after every milestone.
- **Explicit Over Clever:** Type hints everywhere. Pydantic models for all data. No raw dicts. No magic.
- **Small Files, Clear Boundaries:** No file over ~300 lines. One job per module.
- **Fail Loudly, Recover Gracefully:** Never swallow errors. Validate LLM outputs.
- **Vault is Source of Truth:** Agent memory, campaign state, everything lives in the Obsidian vault.

## Stack

| Component | Choice |
|-----------|--------|
| Language | Python 3.12+ |
| LLM API | nano-gpt.com (via LLM Gateway) |
| Embeddings | LM Studio serving nomic-embed-text-v1.5 locally |
| Vector store | ChromaDB |
| PDF parsing | pdfplumber |
| Vault integration | Obsidian CLI + direct filesystem |
| CLI | typer (commands) + textual (chat TUI) |
| Testing | pytest, golden fixtures, user-style QA |
| Package mgmt | uv |

## Note-Taking

After completing any task — feature work, bug fix, discovery, or debugging session — append a dated one-liner to `context/lessons.md`.

**Format:**
```
- YYYY-MM-DD (scope): One-sentence lesson or discovery.
```

**When to write a lesson:**
- You learned something non-obvious about the LLM Gateway, Obsidian CLI, PLAUD parsing, or extraction quality.
- A timing assumption, deduplication approach, or prompt strategy surprised you.
- You made a mistake that future work should avoid.
- A design decision was validated or invalidated by testing.

Write lessons to either:
1. A context file in `context/` (if topic-specific)
2. `context/lessons.md` (if general)

If 3+ related lessons accumulate, extract into a dedicated context file and update the Tree.

## Lessons Learned

Running log lives in `context/lessons.md`. Read it at session start to catch non-obvious pitfalls before writing new code.

Escalated topic files (created when 3+ related lessons accumulate):
- *(none yet — add pointers here as topic files are created)*
