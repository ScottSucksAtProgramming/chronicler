# Chronicler Index

Quick reference for the repository.

## Start Here

| File | Purpose |
|------|---------|
| `README.md` | Main getting-started guide, setup instructions, command reference, and operational workflow |
| `.env.example` | Example configuration for local setup |
| `pyproject.toml` | Package metadata, dependencies, and CLI entrypoint |
| `INDEX.md` | This file |

## Active Documentation

| File | Purpose |
|------|---------|
| `docs/interview-notes.md` | Original discovery notes and project context |
| `docs/superpowers/specs/2026-04-02-session-scribe-design.md` | Historical primary architecture spec created before the rename |
| `docs/superpowers/specs/2026-04-02-chronicler-rename-and-docs-design.md` | Rename and documentation design for the Chronicler transition |
| `docs/superpowers/plans/2026-04-02-chronicler-rename-and-docs.md` | Implementation plan for the rename and documentation pass |

## Source Layout

| Path | Purpose |
|------|---------|
| `src/chronicler/cli/` | Typer CLI commands and entrypoint |
| `src/chronicler/config/` | Environment-driven settings |
| `src/chronicler/gateway/` | LLM provider integration |
| `src/chronicler/ingestion/` | PLAUD PDF and transcript parsing plus normalization |
| `src/chronicler/extraction/` | Structured entity extraction prompts and orchestration |
| `src/chronicler/vault/` | Obsidian integration, note rendering, deduplication, metrics |
| `src/chronicler/retrieval/` | Embeddings, indexing, and retrieval |
| `src/chronicler/chat/` | Textual chat interface |
| `src/chronicler/reviewer/` | Vault review checks and reporting |
| `src/chronicler/models/` | Shared Pydantic domain models |

## Tests And Fixtures

| Path | Purpose |
|------|---------|
| `tests/cli/` | CLI behavior tests |
| `tests/config/` | Settings and configuration tests |
| `tests/extraction/` | Extraction and prompt tests |
| `tests/gateway/` | LLM gateway tests |
| `tests/ingestion/` | Transcript, PDF, and normalization tests |
| `tests/models/` | Domain model tests |
| `tests/retrieval/` | Embeddings and retrieval tests |
| `tests/reviewer/` | Vault review tests |
| `tests/vault/` | Obsidian and vault manager tests |
| `tests/fixtures/` | Sample transcript, PDF, and golden extraction data |

## Historical Context

| File | Purpose |
|------|---------|
| `prd.md` | Original project requirements draft |
| `docs/superpowers/plans/` | Milestone implementation plans from earlier development phases |
| `context/conventions.md` | Coding and repo conventions used during development |
| `context/lessons.md` | Development notes and lessons learned |
