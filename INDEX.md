# D&D Session Scribe Index

Quick-reference for finding content in this directory. For conventions, see `context/conventions.md`.

## Project Files

| File/Folder | Purpose | When to Use |
|-------------|---------|-------------|
| `prd.md` | Original product requirements document | Historical reference only — design spec supersedes this |
| `docs/interview-notes.md` | Discovery interview capturing all design decisions and context | Understanding project rationale, constraints, and Scott's preferences |
| `docs/superpowers/specs/2026-04-02-session-scribe-design.md` | Full design specification — architecture, modules, milestones, testing | **Primary reference for implementation.** Read before any coding work. |
| `docs/superpowers/plans/2026-04-02-milestone-1-foundation.md` | Step-by-step implementation plan for Milestone 1 (Foundation) | Complete. Reference for patterns used in scaffolding. |

## Source Code

| Module | Status | Purpose |
|--------|--------|---------|
| `src/session_scribe/models/` | Complete | All Pydantic data models (entities, sessions, extraction, context, memory) |
| `src/session_scribe/config/` | Complete | Settings via pydantic-settings with SCRIBE_ env prefix |
| `src/session_scribe/gateway/` | Complete | LLM Gateway — nano-gpt.com integration, retries, structured output |
| `src/session_scribe/cli/` | Stubbed | typer CLI with all commands defined, wired to config, others pending |
| `src/session_scribe/ingestion/` | Not started | Milestone 2 — PLAUD PDF + transcript parsing |
| `src/session_scribe/extraction/` | Not started | Milestone 2 — LLM entity extraction |

## context/

| File | Purpose |
|------|---------|
| `conventions.md` | Code patterns, module boundaries, testing conventions, git conventions |
| `lessons.md` | Running log of lessons learned — read at session start |
