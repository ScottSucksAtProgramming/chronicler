---
title: "D&D Session Scribe Lessons Learned"
summary: "Running log of corrections, preferences, and discoveries for the Session Scribe project"
created: 2026-04-02
updated: 2026-04-02
---

# D&D Session Scribe Lessons Learned

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
