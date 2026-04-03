# Chronicler Rename And Docs Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fully rename the project runtime and public documentation from Session Scribe to Chronicler and make the repository ready for remote publication and first-time setup.

**Architecture:** Apply one coherent rename across the package, CLI, configuration, and local storage paths, then rewrite the top-level documentation around the current shipped workflow. Historical planning documents remain archival; active code and docs define the supported interface.

**Tech Stack:** Python 3.12, Typer, Rich, Textual, Pydantic Settings, pytest, uv

---

## Chunk 1: Runtime Rename

### Task 1: Add tests that lock the new public interface

**Files:**
- Modify: `tests/config/test_settings.py`
- Modify: `tests/cli/test_main.py`
- Modify: `tests/cli/test_init.py`

- [ ] **Step 1: Write failing tests for `CHRONICLER_*` configuration**

Add assertions that `Settings` reads `CHRONICLER_VAULT_PATH` and no longer refers to `SCRIBE_*` in expected output.

- [ ] **Step 2: Run focused config tests to verify they fail**

Run: `uv run pytest tests/config/test_settings.py -q`
Expected: FAIL because the current env prefix is still `SCRIBE_`

- [ ] **Step 3: Write failing CLI assertions for `chronicler` branding**

Update CLI tests to expect `chronicler` in help/version/output strings.

- [ ] **Step 4: Run focused CLI tests to verify they fail**

Run: `uv run pytest tests/cli/test_main.py tests/cli/test_init.py -q`
Expected: FAIL because the CLI is still branded as `scribe`

- [ ] **Step 5: Commit**

```bash
git add tests/config/test_settings.py tests/cli/test_main.py tests/cli/test_init.py
git commit -m "test: lock Chronicler public interface"
```

### Task 2: Rename the runtime package and command surface

**Files:**
- Modify: `pyproject.toml`
- Modify: `.env.example`
- Modify: `src/chronicler/**`
- Modify: `tests/**`

- [ ] **Step 1: Rename `src/session_scribe` to `src/chronicler` and update imports**
- [ ] **Step 2: Update package metadata and script entrypoint to `chronicler`**
- [ ] **Step 3: Switch config prefix to `CHRONICLER_` and local storage path to `.chronicler`**
- [ ] **Step 4: Update user-facing strings, help text, version output, and command guidance**
- [ ] **Step 5: Run focused tests**

Run: `uv run pytest tests/config/test_settings.py tests/cli/test_main.py tests/cli/test_init.py -q`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml .env.example src tests
git commit -m "refactor: rename runtime to Chronicler"
```

## Chunk 2: Documentation Rewrite

### Task 3: Replace top-level docs with GitHub-ready onboarding

**Files:**
- Modify: `README.md`
- Modify: `INDEX.md`

- [ ] **Step 1: Draft README sections from the current shipped behavior**
- [ ] **Step 2: Add installation, configuration, and first-run workflow**
- [ ] **Step 3: Add command reference and troubleshooting**
- [ ] **Step 4: Refresh `INDEX.md` to match the current repository**
- [ ] **Step 5: Sanity-check commands against the CLI**

Run: `uv run chronicler --help`
Expected: shows the renamed command and documented subcommands

- [ ] **Step 6: Commit**

```bash
git add README.md INDEX.md
git commit -m "docs: add Chronicler README and repo guide"
```

## Chunk 3: Final Verification

### Task 4: Verify repo readiness

**Files:**
- Modify: none unless fixes are needed

- [ ] **Step 1: Run the full test suite**

Run: `uv run pytest -q`
Expected: PASS

- [ ] **Step 2: Verify the CLI directly**

Run: `uv run chronicler --version`
Expected: prints `chronicler v0.1.0`

- [ ] **Step 3: Review the working tree for accidental churn**

Run: `git status --short`
Expected: only intended rename/doc updates remain
