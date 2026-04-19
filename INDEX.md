# Chronicler Index

Quick reference for the repository.

## Start Here

| File | Purpose |
|------|---------|
| `README.md` | Main getting-started guide, setup instructions, command reference, and operational workflow |
| `.env.example` | Example configuration for local setup |
| `pyproject.toml` | Package metadata, dependencies, and CLI entrypoint |
| `INDEX.md` | This file |
| `CLAUDE.md` | Project-specific operating rules, note-taking requirements, and repo tree |

## Active Documentation

| File | Purpose |
|------|---------|
| `docs/interview-notes.md` | Original discovery notes and project context |
| `docs/ARCHITECTURE.md` | Public-facing high-level architecture overview for contributors |
| `docs/superpowers/specs/2026-04-02-session-scribe-design.md` | Historical primary architecture spec created before the rename |
| `docs/superpowers/specs/2026-04-02-chronicler-rename-and-docs-design.md` | Rename and documentation design for the Chronicler transition |
| `docs/superpowers/specs/2026-04-03-hybrid-chat-vault-reads-design.md` | Hybrid chat design that combines direct vault reads with retrieval |
| `docs/superpowers/specs/2026-04-03-vault-improve-design.md` | Design for deterministic full-vault maintenance and ambiguity routing |
| `docs/superpowers/specs/2026-04-03-party-notes-maintenance-design.md` | Design for evolving party notes as maintained entity records |
| `docs/superpowers/specs/2026-04-03-knowledge-source-ingest-design.md` | Design for smart ingest of general source materials with provenance and optional session anchoring |
| `docs/superpowers/plans/2026-04-02-chronicler-rename-and-docs.md` | Implementation plan for the rename and documentation pass |
| `docs/superpowers/plans/2026-04-03-hybrid-chat-vault-reads.md` | Implementation plan for hybrid vault-aware chat |
| `docs/superpowers/plans/2026-04-03-vault-improve.md` | Implementation plan for `chronicler improve` |
| `docs/superpowers/plans/2026-04-03-party-notes-maintenance.md` | Implementation plan for maintained party-note updates |
| `docs/superpowers/plans/2026-04-03-knowledge-source-ingest.md` | Implementation plan for smart source-material ingest |

## Source Layout

| Path | Purpose |
|------|---------|
| `src/chronicler/cli/` | Typer CLI commands and entrypoint |
| `src/chronicler/config/` | Environment-driven settings |
| `src/chronicler/gateway/` | LLM provider integration |
| `src/chronicler/ingestion/` | PLAUD parsing plus general source parsing and conservative ingest classification |
| `src/chronicler/extraction/` | Session and knowledge-source extraction prompts and orchestration |
| `src/chronicler/vault/` | Obsidian integration, source archiving, additive note updates, deterministic normalization, deduplication, metrics |
| `src/chronicler/retrieval/` | Embeddings, indexing, and retrieval |
| `src/chronicler/chat/` | Textual chat interface |
| `src/chronicler/reviewer/` | Vault review checks and reporting |
| `src/chronicler/models/` | Shared Pydantic domain models |

## Repo-Only State

| Path | Purpose |
|------|---------|
| `context/conventions.md` | Working conventions, testing expectations, and repo norms |
| `context/lessons.md` | Running development lessons and non-obvious discoveries |
| `LICENSE` | GNU AGPL v3-or-later license |

## Tests And Fixtures

| Path | Purpose |
|------|---------|
| `tests/cli/` | CLI behavior tests |
| `tests/config/` | Settings and configuration tests |
| `tests/extraction/` | Extraction and prompt tests |
| `tests/gateway/` | LLM gateway tests |
| `tests/ingestion/` | Transcript, PDF, source classification, and normalization tests |
| `tests/models/` | Domain model tests |
| `tests/retrieval/` | Embeddings and retrieval tests |
| `tests/reviewer/` | Vault review tests |
| `tests/vault/` | Obsidian, improver, source archive, and vault manager tests |
| `tests/fixtures/` | Sample transcript, PDF, and golden extraction data |

## Historical Context

| File | Purpose |
|------|---------|
| `prd.md` | Original project requirements draft |
| `plans/` | Active implementation plans (feature milestones linked to GitHub issues) |
| `docs/superpowers/plans/` | Milestone implementation plans from earlier development phases |
| `docs/superpowers/plans/2026-04-02-milestone-1-foundation.md` | Early milestone implementation record |
| `docs/superpowers/plans/2026-04-02-milestone-2-ingestion-extraction.md` | Early ingestion/extraction implementation record |
| `docs/superpowers/plans/2026-04-02-milestone-3-vault-management.md` | Early vault-management implementation record |
| `docs/superpowers/plans/2026-04-02-milestone-4-reviewer-and-ask.md` | Early reviewer/ask implementation record |
| `docs/superpowers/plans/2026-04-03-milestone-5-retrieval-chat.md` | Early retrieval/chat implementation record |
| `docs/superpowers/plans/2026-04-03-milestone-6-backlog-ready.md` | Early backlog-ready planning record |
