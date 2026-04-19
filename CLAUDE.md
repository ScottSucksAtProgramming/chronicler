# Chronicler

## Purpose

AI agent that ingests session recordings and general source materials, extracts structured tabletop campaign data via LLM, populates an Obsidian vault, and provides an interactive CLI for querying campaign knowledge.

## Tree

```
chronicler/
  CLAUDE.md
  INDEX.md
  pyproject.toml
  .env.example
  todo.taskpaper
  src/
    chronicler/
      __init__.py
      py.typed
      cli/
        main.py          — typer CLI entry point (ingest, chat, review, improve, ask, config, reindex, stats, party)
      models/
        __init__.py      — public exports for all 15+ Pydantic models
        entities.py      — NPC, Location, Faction, LootItem, PlotThread
        session.py       — NormalizedSession, TranscriptSegment, SessionRecap, KeyEvent
        extraction.py    — ExtractionResult, KnowledgeIngestResult, AgentQuestion, QualityScore
        source_document.py — SourceDocument, SourceClassification, DocumentType
        context.py       — ContextBundle, EntitySummary, AgentMemory, PlayerCharacter
      gateway/
        __init__.py
        llm_gateway.py   — LLMGateway (nano-gpt.com, retries, structured output)
        types.py         — LLMRequest, LLMResponse, LLMUsage
      config/
        settings.py      — Settings via pydantic-settings (CHRONICLER_ env prefix)
      ingestion/
        __init__.py
        source_classifier.py — conservative source-type classifier for smart ingest routing
        source_parser.py    — parser registry for text/markdown/pdf source documents
        pdf_parser.py    — parse_plaud_pdf, ParsedPDF, PDFSection, PLAUDParseError
      extraction/
        source_extractor.py — knowledge-first source extraction flow
      vault/
        __init__.py
        obsidian_cli.py  — ObsidianCLI, ObsidianCLIError (low-level CLI wrapper)
        improver.py      — deterministic vault normalization and high-signal ambiguity/question generation
        source_archive.py — archives imported source artifacts under _Agent/Sources/
      retrieval/
        __init__.py
        embeddings.py    — EmbeddingClient, EmbeddingError (LM Studio httpx client)
  tests/
    conftest.py          — shared fixtures (settings, tmp_vault)
    cli/
    models/
    gateway/
    config/
    ingestion/
      test_pdf_parser.py
      test_source_classifier.py
      test_source_parser.py
    extraction/
      test_extractor.py
    vault/
      __init__.py
      test_improver.py
      test_obsidian_cli.py
      test_source_archive.py
    retrieval/
      __init__.py
      test_embeddings.py
  docs/
    installation.md          — prerequisites, install options, initial config walkthrough
    quick-start.md           — first session end-to-end walkthrough
    commands.md              — every command, flag, and usage example
    configuration.md         — all settings and environment variable reference
    workflows.md             — backlog processing, active campaign, knowledge import
    troubleshooting.md       — pre-flight checklist and common error fixes
    development.md           — dev environment, tests, linting, contributing
    ARCHITECTURE.md          — high-level architecture overview for contributors
    superpowers/
      specs/
        2026-04-02-session-scribe-design.md
        2026-04-02-chronicler-rename-and-docs-design.md
        2026-04-03-knowledge-source-ingest-design.md
        2026-04-19-cli-help-text-m3.md
      plans/
        2026-04-02-milestone-1-foundation.md
        2026-04-02-chronicler-rename-and-docs.md
        2026-04-03-knowledge-source-ingest.md
        m1-documentation-polish.md
        m2-documentation-restructure.md
        m3-cli-help-text.md
  context/
    conventions.md
    lessons.md
```

## Rules

1. On session start within `dnd_notes_organizaer/`, read this file, then `INDEX.md`.
2. The **design spec** (`docs/superpowers/specs/2026-04-02-session-scribe-design.md`) is the primary reference for architecture, modules, and scope. The rename/design doc (`docs/superpowers/specs/2026-04-02-chronicler-rename-and-docs-design.md`) covers the public-facing rename and repo documentation pass. Generalized source-material ingest work is scoped in `docs/superpowers/specs/2026-04-03-knowledge-source-ingest-design.md`. The original PRD is historical only.
3. Read the relevant **milestone plan** before starting implementation work.
4. Do not deviate from the vault structure or module boundaries in the spec without discussion.
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
- **Configured Vault Path Wins:** When `CHRONICLER_VAULT_PATH` is set, filesystem-backed vault reads/writes must honor it consistently instead of assuming the Obsidian CLI resolves `vault_name` to the same path.
- **Knowledge Imports Are Additive:** Source-material ingest must enrich existing entity notes through managed additive sections instead of skipping duplicates or overwriting curated content.
- **Location Notes Use One Navigation Format:** User-facing location notes should surface `Belongs To`, `Contains`, and `Nearby Locations` in the top metadata block. Legacy relationship labels and visible ingest scaffolding should be normalized away.
- **Improve Stays Deterministic:** `chronicler improve` is allowed to repair structure, backfill high-confidence relationships, and queue high-signal questions with dedupe, but it should not silently do LLM prose rewrites.

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
