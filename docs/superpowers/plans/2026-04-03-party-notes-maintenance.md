# Party Notes Maintenance Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn `Party/` notes into maintained records with structured sections and session-linked character history.

**Architecture:** Add a focused party-note updater that owns the managed section format and merges explicit character facts into those sections idempotently. Reuse it from both `ingest` and `improve`, while keeping edits bounded to safe, deterministic sections.

**Tech Stack:** Python 3.12, Typer, Obsidian CLI wrapper, pytest

---

## Chunk 1: Party Note Structure

### Task 1: Lock the new party note format with failing tests

**Files:**
- Modify: `tests/vault/test_pc_management.py`
- Modify: `tests/vault/test_note_renderer.py`

- [ ] **Step 1: Write a failing test for rendered party notes containing managed sections**
- [ ] **Step 2: Write a failing test for alias support in party note frontmatter**
- [ ] **Step 3: Run focused tests to verify they fail**

Run: `uv run pytest tests/vault/test_pc_management.py tests/vault/test_note_renderer.py -q`
Expected: FAIL because party notes are still minimal stubs

## Chunk 2: Party Note Updater

### Task 2: Add deterministic party-note maintenance

**Files:**
- Create: `src/chronicler/vault/party_updater.py`
- Modify: `src/chronicler/vault/note_renderer.py`
- Test: `tests/vault/test_party_updater.py`

- [ ] **Step 1: Write failing tests for parsing and updating managed party-note sections**
- [ ] **Step 2: Write failing tests for idempotent timeline merges**
- [ ] **Step 3: Write failing tests for explicit relationships and notable items**
- [ ] **Step 4: Run focused tests to verify they fail**

Run: `uv run pytest tests/vault/test_party_updater.py -q`
Expected: FAIL because the updater does not exist yet

- [ ] **Step 5: Implement party note parsing and managed-section rewriting**
- [ ] **Step 6: Implement explicit fact extraction and merge helpers**
- [ ] **Step 7: Run focused tests**

Run: `uv run pytest tests/vault/test_party_updater.py tests/vault/test_pc_management.py tests/vault/test_note_renderer.py -q`
Expected: PASS

## Chunk 3: Integrate With Ingest And Improve

### Task 3: Update party notes during session ingest

**Files:**
- Modify: `src/chronicler/vault/vault_manager.py`
- Modify: `tests/vault/test_vault_manager.py`

- [ ] **Step 1: Write a failing test for `write_extraction_result` updating party notes**
- [ ] **Step 2: Run the focused test to verify it fails**

Run: `uv run pytest tests/vault/test_vault_manager.py -q`
Expected: FAIL because extraction writes do not enrich party notes yet

- [ ] **Step 3: Integrate the party updater into the extraction write flow**
- [ ] **Step 4: Run focused vault tests**

Run: `uv run pytest tests/vault/test_vault_manager.py tests/vault/test_party_updater.py -q`
Expected: PASS

### Task 4: Backfill party notes during `improve`

**Files:**
- Modify: `src/chronicler/vault/improver.py`
- Modify: `tests/vault/test_improver.py`

- [ ] **Step 1: Write a failing test for `improve` backfilling party-note timeline facts from sessions**
- [ ] **Step 2: Write a failing test for safer party alias linking in session notes**
- [ ] **Step 3: Run focused tests to verify they fail**

Run: `uv run pytest tests/vault/test_improver.py -q`
Expected: FAIL because `improve` does not maintain party notes yet

- [ ] **Step 4: Integrate party-note backfill into the improver**
- [ ] **Step 5: Tighten party alias linking to avoid bad substitutions**
- [ ] **Step 6: Run focused tests**

Run: `uv run pytest tests/vault/test_improver.py tests/vault/test_party_updater.py -q`
Expected: PASS

## Chunk 4: Verification

### Task 5: Verify the full feature

**Files:**
- Modify: none unless fixes are needed

- [ ] **Step 1: Run focused vault and CLI tests**

Run: `uv run pytest tests/vault/ tests/cli/test_improve.py tests/cli/test_ingest.py -q`
Expected: PASS

- [ ] **Step 2: Run the full test suite**

Run: `uv run pytest -q`
Expected: PASS

- [ ] **Step 3: Review the working tree**

Run: `git status --short`
Expected: only intended party-note maintenance changes remain
