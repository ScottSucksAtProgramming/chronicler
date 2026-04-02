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
