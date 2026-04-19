# Configuration

Chronicler is configured through a `config.toml` file created by
`chronicler config init`. All settings can also be overridden with environment
variables prefixed with `CHRONICLER_` — useful for CI, scripts, or temporary
overrides without touching the config file.

**Precedence (highest to lowest):** environment variable → config file → default

## Config file location

| Platform | Path |
|---|---|
| macOS | `~/Library/Application Support/chronicler/config.toml` |
| Linux | `~/.config/chronicler/config.toml` |
| Windows | `%APPDATA%\chronicler\config.toml` |

---

## Vault Settings

| Config key | Env var | Required | Default | Description |
|---|---|---|---|---|
| `vault_path` | `CHRONICLER_VAULT_PATH` | **Yes** | — | Absolute path to your Obsidian vault folder on disk |
| `vault_name` | `CHRONICLER_VAULT_NAME` | **Yes** | — | Vault name as it appears in Obsidian (used for CLI operations) |

`vault_path` and `vault_name` must point to the same vault. `vault_name` is the
display name Obsidian uses, which may differ from the folder name.

---

## LLM Provider Settings

| Config key | Env var | Required | Default | Description |
|---|---|---|---|---|
| `llm_provider` | `CHRONICLER_LLM_PROVIDER` | No | `"kimi"` | Which LLM provider to use: `"kimi"` or `"nanogpt"` |

### nano-gpt.com settings

Only relevant when `llm_provider = "nanogpt"`.

| Config key | Env var | Required | Default | Description |
|---|---|---|---|---|
| `nanogpt_api_key` | `CHRONICLER_NANOGPT_API_KEY` | **Yes** (if nanogpt) | — | Your nano-gpt.com API key |
| `nanogpt_base_url` | `CHRONICLER_NANOGPT_BASE_URL` | No | `"https://nano-gpt.com/api/v1"` | nano-gpt.com API base URL |
| `nanogpt_model` | `CHRONICLER_NANOGPT_MODEL` | No | `"chatgpt-4o-latest"` | Model to use for extraction and chat |

### Kimi CLI settings

Only relevant when `llm_provider = "kimi"`.

| Config key | Env var | Required | Default | Description |
|---|---|---|---|---|
| `kimi_model` | `CHRONICLER_KIMI_MODEL` | No | `""` | Model override passed to the Kimi CLI. Empty string uses Kimi's default. |

---

## Embeddings / LM Studio Settings

Used by `chronicler reindex` and `chronicler chat`. If you don't use those
commands, you can leave these at their defaults.

| Config key | Env var | Required | Default | Description |
|---|---|---|---|---|
| `lm_studio_base_url` | `CHRONICLER_LM_STUDIO_BASE_URL` | No | `"http://localhost:1234/v1"` | Base URL of your running LM Studio instance |
| `embedding_model` | `CHRONICLER_EMBEDDING_MODEL` | No | `"text-embedding-nomic-embed-text-v1.5"` | Embedding model name as loaded in LM Studio |

---

## Operational Settings

| Config key | Env var | Required | Default | Description |
|---|---|---|---|---|
| `log_level` | `CHRONICLER_LOG_LEVEL` | No | `"INFO"` | Logging verbosity: `"DEBUG"`, `"INFO"`, `"WARNING"`, `"ERROR"` |
| `llm_timeout_seconds` | `CHRONICLER_LLM_TIMEOUT_SECONDS` | No | `120` | Seconds before an LLM call is considered timed out |
| `llm_max_retries` | `CHRONICLER_LLM_MAX_RETRIES` | No | `3` | Number of times to retry a failed LLM call before raising an error |

---

## Example config.toml

```toml
# Vault
vault_path = "/Users/you/Documents/CampaignVault"
vault_name = "CampaignVault"

# LLM provider — choose "kimi" or "nanogpt"
llm_provider = "nanogpt"
nanogpt_api_key = "ngp-xxxxxxxxxxxxxxxxxxxx"
# nanogpt_base_url = "https://nano-gpt.com/api/v1"  # default
# nanogpt_model = "chatgpt-4o-latest"               # default

# LM Studio (optional — needed for reindex and chat)
# lm_studio_base_url = "http://localhost:1234/v1"   # default
# embedding_model = "text-embedding-nomic-embed-text-v1.5"  # default

# Operational
# log_level = "INFO"              # default
# llm_timeout_seconds = 120       # default
# llm_max_retries = 3             # default
```

---

## Using environment variables

Environment variables override the config file without modifying it — useful
for CI pipelines or temporary changes:

```bash
CHRONICLER_LLM_PROVIDER=nanogpt \
CHRONICLER_NANOGPT_API_KEY=ngp-xxxx \
chronicler ingest --session 5 session-05.pdf
```

The `.env.example` file in the repository root lists all available variable
names as a reference.
