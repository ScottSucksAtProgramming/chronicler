# Knowledge Source Ingest Implementation Plan

> **For agentic workers:** Use TDD and verify with both focused suites and a live vault run before claiming completion.

**Goal:** Extend `chronicler ingest` so non-transcript source materials can be archived, classified, and extracted into the vault without breaking the session pipeline.

**Delivered Scope:**

- source-document models and tests
- source parser for markdown, text, and PDF with generic PDF fallback
- conservative source classifier and smart ingest routing
- knowledge-first extraction flow with `source_attribution`
- source archive writer and retrieval exclusion
- additive updates for existing entity notes via managed source-update sections
- path-aware vault operations that honor `CHRONICLER_VAULT_PATH`
- explicit location graph support for `parent_location` and `adjacent_to`
- map-style note rendering with derived `Contains` links and question generation for uncertain geography

**Verification:**

- automated suite: `uv run pytest -q`
- live vault validation: unanchored import of `Laguna Nera.md`

**Follow-up Work:**

- multimodal image support
- office/table adapters
- better user-guided ambiguity routing
