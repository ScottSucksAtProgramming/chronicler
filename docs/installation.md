# Installation

> **macOS only:** Chronicler's vault integration relies on the Obsidian desktop
> app binary. Linux and Windows are not currently supported.

## Prerequisites

Install each of the following before proceeding:

| Dependency | Why you need it |
|---|---|
| Python 3.12+ | Chronicler's runtime |
| [uv](https://docs.astral.sh/uv/) | Package and environment manager used to install Chronicler |
| Obsidian desktop (macOS) | Vault integration — Chronicler reads and writes your campaign vault through Obsidian's CLI |
| An LLM provider (one of the two below) | Powers session extraction and chat |
| LM Studio *(optional)* | Local embeddings for `reindex` and `chat`; skip if you don't plan to use those commands |

**LLM provider options — choose one:**

- **nano-gpt.com** — Create an account at [nano-gpt.com](https://nano-gpt.com) and generate an API key.
- **Kimi CLI** — Install the Kimi CLI and ensure the `kimi` command is on your `PATH`.

## Install Chronicler

```bash
pip install chronicler-ttrpg
```

Verify the CLI is available:

```bash
chronicler --help
```

## Global Tool Install (alternative)

If you use `uv` and want `chronicler` available system-wide without activating
a virtual environment:

```bash
uv tool install chronicler-ttrpg
```

To update later:

```bash
uv tool upgrade chronicler-ttrpg
```

## Configure

Run the interactive wizard to create your config file:

```bash
chronicler config init
```

The wizard will prompt you for each required setting. Example session:

```
Vault path [/Users/you/Documents/CampaignVault]:
Vault name [CampaignVault]:
LLM provider (kimi/nanogpt) [kimi]:
nano-gpt API key []:
LM Studio base URL [http://localhost:1234/v1]:
Embedding model [text-embedding-nomic-embed-text-v1.5]:
Log level [INFO]:
```

Config is saved to the standard user config directory for your OS:

- **macOS:** `~/Library/Application Support/chronicler/config.toml`
- **Linux:** `~/.config/chronicler/config.toml`
- **Windows:** `%APPDATA%\chronicler\config.toml`

Review the saved configuration at any time:

```bash
chronicler config show
```

## Next Steps

Follow the [Quick Start guide](quick-start.md) for your first vault session.
