# Vault Improve Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a safe `chronicler improve` command that automatically applies deterministic vault maintenance fixes and writes questions for ambiguous cases.

**Architecture:** Introduce a focused vault-maintenance module that scans supported note folders, builds canonical entity targets from the existing vault, rewrites notes with deterministic link/frontmatter fixes, and emits question notes instead of guessing. Keep the CLI thin and make the maintenance pass idempotent.

**Tech Stack:** Python 3.12, Typer, Obsidian CLI wrapper, pytest

---

## Chunk 1: Maintenance Model Tests

### Task 1: Lock the maintenance behavior with failing tests

**Files:**
- Create: `tests/vault/test_improver.py`
- Modify: `tests/cli/test_main.py`

- [ ] **Step 1: Write a failing test for scanning canonical vault targets**
- [ ] **Step 2: Write a failing test for deterministic session/body link enrichment**
- [ ] **Step 3: Write a failing test for frontmatter reference normalization**
- [ ] **Step 4: Write a failing test for ambiguity question creation**
- [ ] **Step 5: Write a failing CLI smoke test for `improve --help` or `improve`**
- [ ] **Step 6: Run the focused tests to verify they fail**

Run: `uv run pytest tests/vault/test_improver.py tests/cli/test_main.py -q`
Expected: FAIL because the improver module and CLI command do not exist yet

## Chunk 2: Maintenance Engine

### Task 2: Implement canonical scanning and deterministic fixers

**Files:**
- Create: `src/chronicler/vault/improver.py`
- Modify: `src/chronicler/vault/note_renderer.py` if shared helpers are worth reusing
- Test: `tests/vault/test_improver.py`

- [ ] **Step 1: Implement canonical note target discovery for supported folders**
- [ ] **Step 2: Implement deterministic body link enrichment for supported notes**
- [ ] **Step 3: Implement deterministic frontmatter reference normalization**
- [ ] **Step 4: Add ambiguity detection for unresolved or multi-match references**
- [ ] **Step 5: Run focused tests**

Run: `uv run pytest tests/vault/test_improver.py -q`
Expected: PASS

### Task 3: Add question-note writing

**Files:**
- Modify: `src/chronicler/vault/improver.py`
- Modify: `src/chronicler/vault/vault_manager.py` only if shared path helpers are useful
- Test: `tests/vault/test_improver.py`

- [ ] **Step 1: Implement `_Agent/Questions/` note writing for ambiguous cases**
- [ ] **Step 2: Make question output stable and idempotent enough for repeated runs**
- [ ] **Step 3: Run focused tests**

Run: `uv run pytest tests/vault/test_improver.py -q`
Expected: PASS

## Chunk 3: CLI Integration

### Task 4: Add the `improve` command

**Files:**
- Modify: `src/chronicler/cli/main.py`
- Modify: `tests/cli/test_main.py`
- Create or Modify: `tests/cli/test_improve.py`

- [ ] **Step 1: Write a failing CLI test for `chronicler improve` output**
- [ ] **Step 2: Run the CLI test to verify it fails**

Run: `uv run pytest tests/cli/test_improve.py -q`
Expected: FAIL because the command is not wired yet

- [ ] **Step 3: Add the Typer command and summary reporting**
- [ ] **Step 4: Run focused CLI and maintenance tests**

Run: `uv run pytest tests/cli/test_improve.py tests/vault/test_improver.py -q`
Expected: PASS

## Chunk 4: Verification

### Task 5: Verify the full feature

**Files:**
- Modify: none unless fixes are needed

- [ ] **Step 1: Run focused vault and CLI tests**

Run: `uv run pytest tests/vault/ tests/cli/test_improve.py tests/cli/test_main.py -q`
Expected: PASS

- [ ] **Step 2: Run the full test suite**

Run: `uv run pytest -q`
Expected: PASS

- [ ] **Step 3: Review the working tree**

Run: `git status --short`
Expected: only intended `improve` feature changes remain
