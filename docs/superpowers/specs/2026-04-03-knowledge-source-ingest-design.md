# Knowledge Source Ingest Design

**Date:** 2026-04-03  
**Status:** Implemented  
**Author:** Codex (with Scott)

---

## Overview

Chronicler supports knowledge-first ingest for non-transcript source materials. `chronicler ingest` can now parse `.md`, `.txt`, and `.pdf` inputs, classify them conservatively, archive the raw source under `_Agent/Sources/`, and extract campaign knowledge without forcing every import into a session flow.

## Implemented Rules

- `--session` anchors an import to a session when the user intends session enrichment.
- Without `--session`, imports are knowledge-first and should not invent session provenance.
- Unanchored imports use `source_attribution` instead of fake `Session-NNN` values.
- If useful provenance is missing, Chronicler writes an agent question rather than guessing.
- Existing entity notes are updated additively through a managed `## Source Updates` section rather than being overwritten.
- Raw archived sources are excluded from retrieval indexing.

## Parsing And Routing

- `.md` and `.txt` files are parsed as text sources.
- `.pdf` files first try PLAUD parsing, then fall back to generic `pdfplumber` text extraction.
- Smart routing is based on classified intent, not just file suffix.
- Ambiguous inputs prompt the user for direction instead of silently guessing.

## Vault Behavior

- Source artifacts are archived in `_Agent/Sources/<timestamp-slug>/`.
- Archived metadata records classification, session anchor, and source attribution.
- Filesystem-backed vault operations must honor `CHRONICLER_VAULT_PATH` consistently; `vault_name` is not assumed to resolve to the same filesystem location.
- Knowledge-first imports update existing notes additively when a matching entity already exists.

## Remaining Deferred Scope

- image inputs
- `.docx`, `.pages`, `.csv`, `.xlsx`
- richer interactive ambiguity routing beyond the current prompt override
