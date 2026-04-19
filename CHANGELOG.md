# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
with release history organized by project milestone.

## [Unreleased]

### Changed

- Documented the public release process for `1.0.0` while intentionally leaving the `v1.0.0` git tag and PyPI publish step unexecuted in this local preparation pass.

## [1.0.0] - 2026-04-13

### Milestone 1: Foundation

#### Added

- Project scaffolding with `uv`, pytest, a package layout under `src/chronicler/`, and a Typer-based CLI entry point.
- Core Pydantic models for campaign entities, sessions, extraction results, context bundles, and agent memory.
- Environment-driven configuration and an LLM gateway for structured extraction workflows.
- A documented `.env.example` for local setup.

#### Fixed

- User-facing validation errors for missing configuration.
- Markdown code-fence handling in the LLM gateway response parsing.

### Milestone 2: Ingestion And Extraction

#### Added

- Session PDF and transcript parsers for source material.
- LLM-assisted banter filtering and session normalization.
- Extraction prompts, orchestration, and golden-fixture evaluation coverage.
- CLI ingest wiring for end-to-end extraction from session files.
- Kimi CLI provider support alongside nano-gpt.com.

#### Changed

- Default pytest behavior to skip integration tests during routine runs.

#### Fixed

- LLM timeout defaults for better Kimi CLI compatibility.

### Milestone 3: Vault Management

#### Added

- Obsidian CLI wrapper and note rendering for campaign entities.
- Fuzzy deduplication with alias support.
- Vault manager support for note CRUD, context bundles, and agent memory.
- `chronicler init` wiring to bootstrap a vault and persist ingest output.
- Integration coverage for vault behavior against a real Obsidian setup.

#### Changed

- Added explicit `vault_name` configuration for Obsidian CLI targeting.

#### Fixed

- Obsidian CLI stdout parsing for noisy or empty responses.

### Milestone 4: Reviewer And Question Queue

#### Added

- Vault quality checks for broken links, missing fields, duplicates, orphans, timeline gaps, and inconsistencies.
- Reviewer orchestration with isolated error handling and reporting.
- Review and question-queue CLI commands for human-in-the-loop correction workflows.
- Multi-session pipeline integration coverage.

#### Fixed

- Reviewer performance and stability by switching to snapshot-style bulk reads.
- Repository cleanup after accidentally committed PLAUD source artifacts and related CLI noise.

### Milestone 5: Retrieval And Chat

#### Added

- LM Studio embedding client, ChromaDB-backed indexing, and semantic retrieval.
- Retrieval-grounded chat prompts and a Textual TUI for campaign Q&A.
- CLI commands for chat and reindex workflows.

#### Fixed

- Reindex filesystem reads and close behavior.
- Chat TUI event-loop handling and sync-method usage.
- Additional Obsidian CLI noise cleanup during retrieval-era work.

### Milestone 6: Backlog-Ready Workflow

#### Added

- Player character note management and `chronicler party` commands.
- Auto-reindex after ingest and quality metrics tracking.
- Chat-based correction flows to support backlog processing.

### Milestone 6+: Knowledge Maintenance And Public-Facing Polish

#### Added

- Knowledge-source ingest pipeline for non-transcript source material.
- Deterministic location relationship maintenance and review-question generation.
- Contributor guidance, issue templates, and pull request template for open-source collaboration.

#### Changed

- Project rename from Session Scribe to Chronicler across runtime and documentation.
- Package metadata polished for public distribution with version `1.0.0`, AGPL licensing, and PyPI-ready metadata fields.
- Repository legal foundation updated to AGPL v3 and public-release planning docs captured in-repo.

#### Fixed

- Legacy-note session anchoring behavior in source classification and CLI routing.
- Kimi subprocess execution so it runs from the configured vault directory instead of the repository root.
