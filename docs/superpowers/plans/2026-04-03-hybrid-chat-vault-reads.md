# Hybrid Chat Vault Reads Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make chat use direct vault reads plus retrieval so the vault remains the authoritative source of truth during campaign Q&A.

**Architecture:** Introduce a chat-specific context loader that always reads core vault notes directly, then supplements them with semantic retrieval and direct reads of retrieved source notes. Seed a user-editable `_Agent/Memory/vault-guide.md` note during vault initialization and update the chat prompt to reflect note authority rules.

**Tech Stack:** Python 3.12, Typer, Textual, ChromaDB, pytest

---

## Chunk 1: Chat Context Loading

### Task 1: Lock the new chat behavior with failing tests

**Files:**
- Create: `tests/chat/test_context_loader.py`
- Modify: `tests/chat/test_prompts.py`

- [ ] **Step 1: Write failing tests for always-read core context**
- [ ] **Step 2: Write failing tests for direct reading of retrieval source files**
- [ ] **Step 3: Write failing tests for prompt authority rules**
- [ ] **Step 4: Run focused tests to verify they fail**

Run: `uv run pytest tests/chat/test_context_loader.py tests/chat/test_prompts.py -q`
Expected: FAIL because the hybrid context loader does not exist yet

## Chunk 2: Hybrid Chat Implementation

### Task 2: Add chat context loader and prompt layers

**Files:**
- Create: `src/chronicler/chat/context_loader.py`
- Modify: `src/chronicler/chat/prompts.py`
- Modify: `src/chronicler/chat/app.py`

- [ ] **Step 1: Implement a loader for core direct-read notes**
- [ ] **Step 2: Implement direct reading of files referenced by retrieval results**
- [ ] **Step 3: Update the prompt builder to separate core notes, supporting notes, and retrieval hits**
- [ ] **Step 4: Update chat to use the hybrid loader before calling the LLM**
- [ ] **Step 5: Run focused tests**

Run: `uv run pytest tests/chat/test_context_loader.py tests/chat/test_prompts.py tests/chat/test_app_commands.py -q`
Expected: PASS

### Task 3: Seed the vault guide note

**Files:**
- Modify: `src/chronicler/vault/vault_manager.py`
- Modify: `tests/vault/test_vault_manager.py`

- [ ] **Step 1: Write a failing test for seeding `_Agent/Memory/vault-guide.md`**
- [ ] **Step 2: Run the focused vault test to verify it fails**

Run: `uv run pytest tests/vault/test_vault_manager.py -q`
Expected: FAIL because the guide note is not seeded yet

- [ ] **Step 3: Implement guide-note seeding without overwriting existing content**
- [ ] **Step 4: Run the focused vault test to verify it passes**

Run: `uv run pytest tests/vault/test_vault_manager.py -q`
Expected: PASS

## Chunk 3: Verification

### Task 4: Verify end-to-end behavior

**Files:**
- Modify: none unless fixes are needed

- [ ] **Step 1: Run focused chat and vault tests**

Run: `uv run pytest tests/chat/ tests/vault/test_vault_manager.py tests/cli/test_chat_launch.py -q`
Expected: PASS

- [ ] **Step 2: Run the full test suite**

Run: `uv run pytest -q`
Expected: PASS

- [ ] **Step 3: Manually review the working tree**

Run: `git status --short`
Expected: only intended hybrid-chat changes remain
