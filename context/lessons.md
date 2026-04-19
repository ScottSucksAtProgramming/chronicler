---
title: "Chronicler Lessons Learned"
summary: "Running log of corrections, preferences, and discoveries for the Chronicler project"
created: 2026-04-02
updated: 2026-04-03
---

# Chronicler Lessons Learned

<!-- Append dated one-liners below. When 3+ related lessons accumulate, extract into a dedicated context file. -->

- 2026-04-02 (config): pydantic-settings `SettingsConfigDict` supports `_env_file=None` at construction time to suppress `.env` file loading in tests, which is essential for reliable env-var isolation with `monkeypatch`.
- 2026-04-02 (gateway): LLM responses commonly wrap JSON in markdown code fences (```json ... ```). The gateway must strip these before parsing. Extract this into a dedicated method rather than inline string manipulation — edge cases around missing language tags and malformed fences are real.
- 2026-04-02 (testing): Subagent-built code needs a manual read-through after implementation. Subagents report "DONE" but may not catch subtle issues (fragile string parsing, missing edge case tests). Trust but verify.
- 2026-04-02 (cli): Raw Pydantic ValidationError messages are terrible UX. The `config` command should catch these and translate field names to their `SCRIBE_`-prefixed env var names for the user.
- 2026-04-02 (gitignore): `.env.*` glob pattern in gitignore will also match `.env.example`. Use explicit entries (`.env.local`, `.env.production`) plus `!.env.example` to allow the example file.
- 2026-04-02 (pdf-parsing): PLAUD PDFs have a cover page (title + narrative summary) followed by named section pages. Skipping page 1 for section detection and using a title-case ratio heuristic (>=60% capitalized words, <80 chars, no trailing punctuation) reliably detects section headers against the real fixture on first attempt.
- 2026-04-02 (gateway): nano-gpt.com response format doesn't always include a `usage` field — parse it tolerantly with `.get()` defaults. Also hits 429 rate limits quickly with batch calls.
- 2026-04-02 (gateway): Kimi Code CLI (`kimi --quiet -p`) works as an LLM provider but is much slower than API calls. Default timeout needs to be 120s+ for full session extraction. The `--quiet` flag gives clean text output suitable for JSON parsing.
- 2026-04-02 (extraction): PDF-only extraction (no transcript) produces good results — 6 NPCs, 11 locations from a single session. The PLAUD summary is high enough signal that transcript is truly supplementary, not required.
- 2026-04-02 (testing): async fixtures in pytest-asyncio STRICT mode cause collection errors even when marked as integration. Use sync `asyncio.run()` with module-level cache instead of async fixtures for integration tests.
- 2026-04-02 (vault): The Obsidian CLI binary uses `key=value` positional args that require `shell=True` in subprocess — quoting the binary path and passing args as a single string is the only reliable way to call it from Python.
- 2026-04-02 (vault): Obsidian CLI calls spawn full Electron processes. If subprocess timeout fires, child processes may not be killed and accumulate as zombies. Multiple zombie processes cause Obsidian to restart constantly. Prefer filesystem operations for bulk reads/writes and minimize CLI calls. Use CLI only for search, property management, and operations that need Obsidian's index.
- 2026-04-02 (vault): The reviewer was refactored to use `read_all_notes()` (filesystem bulk read) instead of per-file CLI calls. This pattern should be used wherever possible — CLI subprocess overhead is ~300ms per call.
- 2026-04-02 (retrieval): LM Studio's OpenAI-compatible `/embeddings` endpoint works cleanly with `httpx.AsyncClient`; `patch.object(client, "_client")` in tests is the right mock strategy since the client is an instance attribute, not a module-level import.
- 2026-04-02 (milestone-6): Player characters work better as first-class `Party/` notes, but keeping a fallback read path from `_Agent/Memory/player-characters.md` avoids regressing older context-bundle and memory tests during the transition.
- 2026-04-02 (repo): A package rename is not finished when imports compile. Repo polish also needs aligned ignore rules, maintenance docs, and generic top-level documentation so the remote repository reflects the supported public surface.
- 2026-04-03 (vault-links): Obsidian link targets must canonicalize to actual note path stems, not display-style frontmatter names; quote-style and accent variants should normalize onto the filename so wiki links resolve to the real notes.
- 2026-04-03 (workflow): For live-vault features, code-level tests are not sufficient; the completion bar is focused regressions, broader suite coverage, and one installed-CLI validation against the real vault before reporting success.
- 2026-04-03 (ingest): Unanchored source imports need separate `source_attribution` provenance instead of fake `Session-NNN` values; missing provenance should become a question, not a guess.
- 2026-04-03 (ingest): Source PDF parsing cannot assume PLAUD structure; a generic pdfplumber text fallback is required so older PDFs can still enter the knowledge-ingest path.
- 2026-04-03 (ingest): Knowledge-first source ingest needs its own result model and vault write path; reusing the session-only extraction result forces bad assumptions about recaps and session anchoring.
- 2026-04-03 (ingest): Source-material ingest should archive provenance in the vault while keeping raw artifacts out of retrieval so answers stay grounded in curated notes instead of attachment dumps.
- 2026-04-03 (vault): `vault_name` and `CHRONICLER_VAULT_PATH` can point at different vault locations in real usage; filesystem-backed operations must consistently honor the configured path or live writes will split across two vaults.
- 2026-04-03 (ingest): Dedup-by-skip is wrong for knowledge imports into existing notes; source-driven updates need an additive managed section so imported lore enriches notes instead of being silently dropped.
- 2026-04-03 (ingest): `source_attribution` inference must only trust explicit attribution-style lines near the top of a source; scraping arbitrary prose for words like "from" produces bad provenance.
- 2026-04-03 (locations): Location hierarchy needs two passes: prompt for `parent_location`, then a deterministic fallback that promotes explicit phrases like "district in Laguna Nera" when the model only returns a generic connection.
- 2026-04-03 (locations): Parent `Contains` links cannot rely on frontmatter alone once curated notes already exist; relationship discovery must also scan managed body sections so repeated imports accumulate children instead of replacing them.
- 2026-04-03 (improve): `chronicler improve` needs a location-relationship backfill pass for pre-feature notes; otherwise older district notes never gain `parent_location` and parent city notes stay incomplete even after successful ingest.
- 2026-04-03 (formatting): Visible agent scaffolding in location notes ages poorly; `improve` should normalize old notes into the same user-facing format as fresh renders by removing source-update sections, collapsing stale labels, and surfacing navigation fields in the top metadata block.
- 2026-04-03 (questions): Deterministic maintenance can still ask useful relationship questions if triggers are high-signal and deduped against existing question files; otherwise repeated `improve` runs become noisy quickly.
- 2026-04-13 (config): A dedicated `set_config_path()` seam keeps config-file tests deterministic across CLI and settings layers without monkeypatching `platformdirs`, and writing only non-default prompt values preserves meaningful `(default)` annotations in `config show`.
- 2026-04-19 (repo): After a directory rename, `.venv` shebang lines still point to the old path and silently fall back to the system Python, causing all imports to fail. Fix by deleting `.venv` and running `uv sync --dev` to regenerate it with correct paths.
- 2026-04-19 (docs): When prompting Codex to update PLAUD-only framing throughout a README, it will correctly find all occurrences but may produce awkward multi-sentence bullet points and redundant intro prose. Always review Phase 3-style "find and update" changes for prose quality, not just criteria coverage.
