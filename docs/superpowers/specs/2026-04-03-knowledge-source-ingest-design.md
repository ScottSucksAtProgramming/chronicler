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
- Location relationships use two explicit link types: containment (`parent_location`) and adjacency (`adjacent_to`).
- Chronicler only writes location relationships it is confident about; unclear geography becomes agent questions.

## Parsing And Routing

- `.md` and `.txt` files are parsed as text sources.
- `.pdf` files first try PLAUD parsing, then fall back to generic `pdfplumber` text extraction.
- Smart routing is based on classified intent, not just file suffix.
- Ambiguous inputs prompt the user for direction instead of silently guessing.
- After model extraction, explicit containment phrases in location descriptions (for example, "a district in Laguna Nera") can be promoted into `parent_location` as a deterministic fallback when the model omits the hierarchy field.

## Vault Behavior

- Source artifacts are archived in `_Agent/Sources/<timestamp-slug>/`.
- Archived metadata records classification, session anchor, and source attribution.
- Filesystem-backed vault operations must honor `CHRONICLER_VAULT_PATH` consistently; `vault_name` is not assumed to resolve to the same filesystem location.
- Knowledge-first imports update existing notes additively when a matching entity already exists.
- Location notes expose navigable geography in both frontmatter and body:
  - `Contained In` from `parent_location`
  - `Adjacent To` from `adjacent_to`
  - `Contains` derived by scanning known locations whose `parent_location` points at the current note
- For legacy curated notes that do not yet carry relationship frontmatter, `Contains` derivation also scans managed location-relationship sections so repeated imports keep accumulating child links.

## Remaining Deferred Scope

- image inputs
- `.docx`, `.pages`, `.csv`, `.xlsx`
- richer interactive ambiguity routing beyond the current prompt override
