# Troubleshooting

## Pre-flight Checklist

Before debugging output quality or error messages, verify these basics:

- [ ] **Obsidian is installed and running** — the vault integration requires
      the Obsidian desktop app to be open.
- [ ] **Vault name matches** — `vault_name` in `config.toml` must match the
      name shown in Obsidian's title bar, not the filesystem folder name. Run
      `chronicler config show` and compare.
- [ ] **Vault path exists** — `vault_path` must be the absolute path to the
      vault folder on disk. Run `chronicler config show` to validate.
- [ ] **LLM provider is configured** — if using `nanogpt`, confirm
      `CHRONICLER_NANOGPT_API_KEY` is set. If using `kimi`, confirm `kimi` is
      on your PATH (`which kimi`).
- [ ] **LM Studio is running** (only for `reindex` and `chat`) — LM Studio
      must be open with an embedding model loaded. Check that the model name in
      `config.toml` matches the one loaded in LM Studio.
- [ ] **No config validation errors** — run `chronicler config show` and check
      for any warnings or errors.

---

## Obsidian CLI Errors

### `Obsidian binary not found`

**Symptom:** Chronicler exits immediately with an error about the Obsidian
binary or macOS app.

**Cause:** The Obsidian app is not installed at the expected path
(`/Applications/Obsidian.app`) or is not running.

**Fix:**
1. Confirm Obsidian is installed in `/Applications/`.
2. Open the Obsidian app before running Chronicler commands.
3. If Obsidian is installed elsewhere, this is a known limitation — the binary
   path is not yet configurable.

---

### `Vault not found` or `Vault name not recognized`

**Symptom:** Chronicler reports that it cannot find the vault or that the vault
name is unrecognized.

**Cause:** The `vault_name` in `config.toml` does not match the name Obsidian
uses internally. The vault display name in Obsidian may differ from the folder
name on disk.

**Fix:**
1. Open Obsidian and note the exact vault name shown in the title bar or
   vault switcher.
2. Update `vault_name` in `config.toml` to match exactly.
3. Run `chronicler config show` to confirm the value.

---

### Slow or hanging CLI operations

**Symptom:** Commands that use Obsidian CLI (like `init` or note writes)
take a very long time or appear to hang.

**Cause:** Each Obsidian CLI call spawns an Electron process. Multiple
simultaneous or rapid calls can cause slowdowns.

**Fix:**
1. Ensure only one Chronicler command is running at a time.
2. If Obsidian is restarting repeatedly, quit it completely, wait a moment,
   and reopen it before retrying.

---

## LLM Provider Errors

### `nanogpt: API key missing` or `401 Unauthorized`

**Symptom:** `chronicler ingest` fails with an authentication error when using
the nanogpt provider.

**Cause:** `nanogpt_api_key` is not set or is invalid.

**Fix:**
1. Run `chronicler config init` and enter your nano-gpt.com API key.
2. Alternatively, set `CHRONICLER_NANOGPT_API_KEY=your-key` in your
   environment.
3. Verify your key at [nano-gpt.com](https://nano-gpt.com).

---

### `429 Too Many Requests` (nanogpt)

**Symptom:** Extraction fails or retries repeatedly when ingesting a session.

**Cause:** nano-gpt.com rate limits batch LLM calls.

**Fix:** Wait a minute and retry. If it happens consistently, reduce the
frequency of ingest calls or check your nano-gpt.com account tier.

---

### `kimi: command not found`

**Symptom:** Chronicler exits with a message about Kimi not being found.

**Cause:** The `kimi` CLI is not installed or not on your PATH.

**Fix:**
1. Install the Kimi CLI following its official documentation.
2. Confirm it's available: `which kimi`
3. If it's installed but not on PATH, add its location to your shell's PATH.

---

### LLM response timeout

**Symptom:** Ingest hangs for a long time and then fails with a timeout error.

**Cause:** The LLM call took longer than `llm_timeout_seconds` (default: 120).

**Fix:**
1. Increase the timeout in `config.toml`: `llm_timeout_seconds = 240`
2. If using the Kimi CLI, longer timeouts are normal — Kimi can take 90+ seconds
   for complex extraction.

---

## LM Studio / Embeddings Errors

### `Connection refused` on reindex or chat

**Symptom:** `chronicler reindex` or `chronicler chat` fails with a connection
error to `localhost:1234`.

**Cause:** LM Studio is not running, or is running on a different port.

**Fix:**
1. Open LM Studio and start the local server.
2. Load an embedding model (the model name must match `embedding_model` in
   `config.toml`).
3. If LM Studio is on a different port, update `lm_studio_base_url` in
   `config.toml`.

---

### `Model not loaded` or empty embeddings

**Symptom:** Reindex completes but chat gives poor or empty results, or LM
Studio returns an error about the model.

**Cause:** The embedding model name in `config.toml` doesn't match the model
currently loaded in LM Studio.

**Fix:**
1. In LM Studio, check the name of the loaded embedding model exactly.
2. Update `embedding_model` in `config.toml` to match.
3. Run `chronicler reindex` again.

---

## Config Errors

### `CHRONICLER_VAULT_PATH is not set` or `vault_path is required`

**Symptom:** Any Chronicler command exits immediately with a message about
`vault_path`.

**Cause:** The config file doesn't exist yet or `vault_path` wasn't set during
`config init`.

**Fix:**
1. Run `chronicler config init` to create the config file.
2. Enter your vault path when prompted.

---

### Config file not found

**Symptom:** Chronicler uses default values even though you've set up config.

**Cause:** The config file is in an unexpected location, or `config init` was
not completed.

**Fix:**
1. Run `chronicler config show` — it will report where it's looking for the
   config file.
2. If the file is missing, run `chronicler config init`.

---

## Vault Errors

### Duplicate notes appearing

**Symptom:** After ingest, you see two notes for what appears to be the same
NPC or location.

**Cause:** The entity names were spelled differently across sessions, so the
deduplication check didn't match them.

**Fix:**
1. Manually merge or rename one of the notes in Obsidian.
2. Run `chronicler improve` — it will backfill relationships and may catch
   remaining duplicates.
3. Use `chronicler ask` to answer any questions the agent raised about the
   entity.

---

### Note write failures

**Symptom:** Ingest reports errors writing specific notes to the vault.

**Cause:** File permissions, a locked file in Obsidian, or a path conflict.

**Fix:**
1. Confirm Obsidian is running and the vault is open.
2. Check that the vault path in `config.toml` is correct and writable.
3. Close any other programs that might have the vault folder locked.
4. Retry the ingest — it is safe to re-run; already-written notes will be
   updated rather than duplicated.
