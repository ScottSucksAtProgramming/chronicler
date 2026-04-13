# Chronicler Architecture

Chronicler is a local-first Python CLI that turns tabletop RPG source material into a structured Obsidian knowledge base, then layers retrieval and chat on top of that vault.

## End-To-End Data Flow

```text
PDF / transcript / markdown / text
        |
        v
ingestion
  - parse source files
  - classify source intent
  - normalize session inputs when needed
        |
        v
extraction
  - build prompts
  - call gateway-backed LLMs
  - validate structured results into models
        |
        v
vault
  - write or update Obsidian notes
  - archive source artifacts
  - track questions, memory, and metrics
        |
        +----------------------+
        |                      |
        v                      v
retrieval                 reviewer / improve flows
  - chunk notes             - inspect vault state
  - embed via LM Studio     - queue deterministic fixes/questions
  - index in ChromaDB
        |
        v
cli + chat
  - query the vault and index
  - present answers in the terminal / TUI
```

In practice, the main user loop looks like this:

1. Source files come in as PLAUD PDFs, transcript text, or general campaign notes.
2. Chronicler parses and classifies them through `ingestion`.
3. `extraction` sends curated prompts through the LLM `gateway` and receives structured entities, recap data, and quality signals.
4. `vault` writes those results into the Obsidian vault as linked markdown notes and keeps agent-managed state under `_Agent/`.
5. `retrieval` can then embed the vault and store searchable vectors in ChromaDB.
6. `chronicler chat` combines retrieval results with direct vault reads so the user can ask campaign questions against current vault state.

## Core Modules

### `config`

Loads runtime settings from environment variables and turns them into validated application configuration.

- Key inputs: `.env`, process environment
- Key outputs: `Settings` used across CLI, gateway, vault, and retrieval code

### `models`

Defines the shared Pydantic domain models that move through the system.

- Key inputs: raw parsed data and LLM responses
- Key outputs: typed entities, session records, extraction results, source classifications, context bundles, and memory records

### `gateway`

Provides the boundary between Chronicler and LLM providers.

- Key inputs: prompt messages and structured-output schemas
- Key outputs: validated text or JSON-shaped model responses
- External boundaries: Kimi CLI subprocesses and nano-gpt.com HTTP API

### `ingestion`

Owns file parsing, source classification, transcript filtering, and session normalization.

- Key inputs: PDFs, transcripts, markdown notes, plain-text notes, explicit session anchors
- Key outputs: parsed source documents, normalized sessions, and routing decisions for extraction

### `extraction`

Turns parsed sources plus campaign context into structured campaign knowledge.

- Key inputs: normalized sessions or knowledge-source documents, context bundles, gateway access
- Key outputs: NPCs, locations, factions, loot, plot threads, recaps, and quality metadata

### `vault`

Owns Obsidian-facing persistence and deterministic note maintenance.

- Key inputs: extraction results, source documents, questions, and memory updates
- Key outputs: markdown notes, archived source files, review artifacts, metrics, and managed agent state
- External boundaries: Obsidian filesystem and Obsidian CLI integration

### `retrieval`

Builds and queries the semantic index over vault content.

- Key inputs: vault note content
- Key outputs: embedded chunks, ChromaDB index state, ranked retrieval results
- External boundaries: LM Studio embeddings endpoint and local ChromaDB storage

### `cli`

Acts as the application entrypoint and orchestration layer for commands like `init`, `ingest`, `review`, `ask`, `reindex`, `chat`, and `party`.

- Key inputs: user commands and command-line options
- Key outputs: orchestrated workflows and terminal-facing responses

## Dependency Direction

Chronicler follows a clean-architecture style dependency rule: outer layers depend on inner layers, never the reverse.

```text
cli
  -> vault / retrieval / extraction / ingestion / gateway / config
vault / retrieval / extraction / ingestion / gateway
  -> models / config
models
  -> no application-layer dependencies
```

What that means in practice:

- `models` stays at the center as the shared domain language.
- `gateway`, `ingestion`, `extraction`, `vault`, and `retrieval` all consume models, but domain models do not import those outer modules.
- `cli` is the thinnest outer layer and is allowed to compose the lower-level modules together.
- External systems stay behind boundaries in `gateway`, `vault`, and `retrieval` instead of leaking throughout the codebase.

## External Service Boundaries

- **Kimi CLI:** subprocess-backed LLM provider used for extraction and chat-oriented generation.
- **nano-gpt.com:** HTTP-backed LLM provider supported through the same gateway abstraction.
- **LM Studio:** local embeddings provider used by retrieval and reindex flows.
- **Obsidian filesystem:** source of truth for campaign notes and agent-managed files.
- **Obsidian CLI:** helper boundary for vault discovery and selected read/write operations.
- **ChromaDB:** local vector index used for semantic retrieval over vault content.

## Where To Read Next

For deeper design history and feature-level details, see the specs in `docs/superpowers/specs/`:

- `2026-04-02-session-scribe-design.md`
- `2026-04-02-chronicler-rename-and-docs-design.md`
- `2026-04-03-hybrid-chat-vault-reads-design.md`
- `2026-04-03-knowledge-source-ingest-design.md`
- `2026-04-03-party-notes-maintenance-design.md`
- `2026-04-03-vault-improve-design.md`
