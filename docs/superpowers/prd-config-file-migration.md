# PRD: Config File Migration

## Problem Statement

Chronicler currently requires users to create a `.env` file by hand, copying `.env.example` and filling in values. This is a developer convention that non-developer users — tabletop RPG players who just want to manage campaign notes — will find confusing and unwelcoming. There is no guided setup, no standard file location, and no clear indication of where the configuration should live relative to where the user runs the CLI. As Chronicler moves toward public distribution via PyPI, this is the most significant onboarding friction point.

## Solution

Replace `.env`-based configuration with a persistent TOML config file at an OS-appropriate location (`~/.config/chronicler/config.toml` on Linux, `~/Library/Application Support/chronicler/config.toml` on macOS, `%APPDATA%\chronicler\config.toml` on Windows). Introduce `chronicler config init` as an interactive wizard that walks the user through every required and optional setting, then writes the config file. Retain `chronicler config show` to display the active configuration. Environment variables continue to override config file values for power users and CI environments. Drop `.env` file support entirely for a clean break.

## User Stories

1. As a new user, I want to run a single setup command after installing Chronicler, so that I can get configured without reading documentation first.
2. As a new user, I want the setup wizard to ask me for my vault path, so that I don't have to guess the correct environment variable name.
3. As a new user, I want the setup wizard to validate that my vault path exists before accepting it, so that I catch typos immediately instead of later during ingest.
4. As a new user, I want to choose my LLM provider from a menu during setup, so that I understand my options without consulting external docs.
5. As a new user choosing nano-gpt, I want to be prompted for my API key during setup, so that I'm told exactly what value is needed and where to put it.
6. As a new user choosing Kimi CLI, I want setup to confirm Kimi is available on my PATH, so that I find out about missing dependencies at configuration time rather than first ingest.
7. As a new user, I want optional settings (LM Studio URL, embedding model, log level) to show their defaults during setup so I can accept them quickly, so that I'm not overwhelmed by fields I don't need to change.
8. As a new user, I want the wizard to confirm what it is about to write before saving, so that I can review my choices before committing them.
9. As a new user, I want to be told where the config file was saved after setup completes, so that I know where to find it if I need to edit it later.
10. As a returning user, I want `chronicler config show` to display all active configuration values, so that I can quickly verify my setup is correct.
11. As a returning user, I want `chronicler config show` to tell me when a value is coming from an environment variable override rather than the config file, so that I understand the precedence in effect.
12. As a returning user, I want `chronicler config init` to warn me if a config file already exists and ask for confirmation before overwriting it, so that I don't accidentally lose my existing setup.
13. As a returning user, I want to re-run `chronicler config init` to change my setup, so that I have a guided way to update configuration without manually editing TOML.
14. As a power user, I want environment variables prefixed with `CHRONICLER_` to override any config file value, so that I can control settings in CI or scripts without modifying the file.
15. As a power user, I want to run Chronicler in an environment without a config file by setting all required values via environment variables, so that containerized and ephemeral workflows are still supported.
16. As a developer contributing to Chronicler, I want to understand where the config file lives on each OS, so that I can write tests that work cross-platform.
17. As a user on macOS, I want the config file to live in `~/Library/Application Support/chronicler/`, so that it follows macOS conventions.
18. As a user on Linux, I want the config file to live in `~/.config/chronicler/` by default, respecting `$XDG_CONFIG_HOME` if set, so that my setup follows XDG conventions.
19. As a user on Windows, I want the config file to live in `%APPDATA%\chronicler\`, so that it is stored in the standard user application data directory.
20. As a user, I want Chronicler to give a clear, friendly error message when the config file is missing and no environment variables are set, so that I know exactly what to do to fix the problem.
21. As a user, I want the error message for missing configuration to reference `chronicler config init` rather than `.env.example`, so that I'm directed to the right solution.
22. As a user, I want `chronicler config init` to create the config directory if it does not already exist, so that I don't have to create parent directories manually.

## Implementation Decisions

### Config Path Resolution Module
A dedicated, deeply encapsulated module handles determining the OS-appropriate config directory and file path. It takes the application name as input and returns the correct `Path` for the current OS, using the `platformdirs` library (a well-maintained cross-platform utility used by pip, black, and others). This module has a simple, stable interface and is independently testable with no side effects.

- `platformdirs` is added as a runtime dependency
- The module exposes a single function: given an app name, return the config file path
- On macOS: `~/Library/Application Support/chronicler/config.toml`
- On Linux: `${XDG_CONFIG_HOME:-~/.config}/chronicler/config.toml`
- On Windows: `%APPDATA%\chronicler\config.toml`

### TOML Config File Source
`pydantic-settings` (already a dependency) supports custom settings sources including TOML via `TomlConfigSettingsSource`. The `Settings` class is updated to:
- Add a `TomlConfigSettingsSource` pointed at the OS-appropriate config path
- Remove the `env_file=".env"` entry from `SettingsConfigDict`
- Preserve `env_prefix="CHRONICLER_"` so environment variables continue to work
- Priority order: environment variables > config file > field defaults

The `Settings` class itself stays as the single interface for the rest of the application. No callers outside `config/` need to change.

### Config Write Helper
A thin helper in the config module handles writing a validated `Settings` instance to disk as TOML. It:
- Creates the parent directory if it does not exist
- Writes only the fields the user explicitly provided (not defaults for fields they skipped)
- Uses the `tomllib`/`tomli-w` approach: read with stdlib `tomllib` (Python 3.11+), write with `tomli-w`
- `tomli-w` is added as a runtime dependency

### `config init` Wizard (CLI layer)
The wizard lives in the CLI layer and uses `typer.prompt` for interactive input. It is not a deep module — it is a thin orchestration of prompts that collects values and delegates writing to the config module.

Wizard flow:
1. Check if a config file already exists — if so, warn and ask for confirmation before continuing
2. Prompt for `vault_path` — validate that the path exists before accepting
3. Prompt for `vault_name` — default to the basename of the vault path
4. Prompt for `llm_provider` — present "kimi" and "nanogpt" as choices
5. If `nanogpt`: prompt for `nanogpt_api_key` (required) and `nanogpt_model` (default shown)
6. If `kimi`: check that `kimi` is on PATH; warn but do not block if not found
7. Prompt for `lm_studio_base_url` with default shown — user can press Enter to accept
8. Prompt for `embedding_model` with default shown
9. Prompt for `log_level` with default shown
10. Display a summary of all collected values
11. Ask for confirmation before writing
12. Write config file, print the path where it was saved

### `config show` Command (CLI layer)
The existing `config` command is converted to a subcommand group. The `show` subcommand:
- Loads settings via the normal `Settings()` path
- Displays each field with its value
- For fields overridden by an environment variable, appends `(from env)` to the displayed value
- Masks API keys (shows last 4 characters)
- Validates vault path existence and reports green/yellow accordingly

### Removing `.env` Support
- `env_file=".env"` removed from `SettingsConfigDict`
- `.env.example` kept in the repo as documentation reference only (update its header comment to note it is for reference, not for direct use)
- Error messages that currently reference `cp .env.example .env` updated to reference `chronicler config init`
- `CONTRIBUTING.md` updated to document the config file approach for local dev

### New Dependencies
- `platformdirs` — runtime dependency, for OS-appropriate config dir resolution
- `tomli-w` — runtime dependency, for writing TOML config files

## Testing Decisions

**Philosophy:** Tests should verify observable external behavior, not implementation details. A good test calls a public function or CLI command with a known environment and asserts on outputs — the config file written, the settings loaded, or the CLI output produced — without testing private internals.

**Config path resolution module:**
- Unit tests cover all three OS cases by mocking `platformdirs.user_config_dir`
- Tests assert that the returned path uses the correct base directory and file name for each platform
- This is the highest-value test target: pure function, no side effects, complex platform logic

**Settings loading:**
- Unit tests verify the priority order: env var overrides config file value, config file value overrides default
- Tests use a temporary TOML file as the config source, injected via a test-only settings constructor or monkeypatching the config path resolver
- Tests verify that missing required fields produce a clear `ValidationError`
- Prior art: existing `tests/config/` test files for the settings module

**Config write helper:**
- Unit tests write a settings object to a temp directory and assert the resulting TOML file contains the expected keys and values
- Tests verify that the parent directory is created if it does not exist

**`config init` wizard:**
- Integration-style CLI tests using `typer.testing.CliRunner` to simulate user input
- Tests assert the written config file matches the wizard inputs
- Tests assert that attempting to overwrite an existing config without confirmation does not write
- Prior art: existing CLI tests in `tests/cli/`

**`config show` command:**
- CLI tests using `CliRunner` assert that output contains expected field values
- Tests verify that `(from env)` annotation appears when an env var overrides a config file value

## Out of Scope

- `chronicler config set` and `chronicler config get` subcommands for individual field manipulation — users edit the TOML file directly
- Config file encryption or secrets management — API keys are stored in plaintext in the config file, consistent with how `.env` worked
- Config file validation on every command invocation — settings are validated at load time by pydantic-settings as they are today
- Migration tooling to convert an existing `.env` to `config.toml` — users re-run `chronicler config init`
- Multiple config profiles or per-project config files — single global config only
- GUI or web-based configuration interface

## Further Notes

- `platformdirs` is already used by many tools in the Python ecosystem (pip, black, pytest-cache) and is a safe, well-maintained dependency. It avoids the need to hand-roll OS detection.
- `tomllib` is part of the Python standard library since 3.11. Since Chronicler requires Python 3.12+, no read-side TOML dependency is needed. Only `tomli-w` is needed for writing.
- The `CONTRIBUTING.md` local dev setup section should be updated to instruct contributors to run `chronicler config init` after cloning, instead of copying `.env.example`.
- The `.env.example` file should be retained in the repository as a reference for what each variable does, but its header comment should be updated to clarify it is for documentation purposes and that `chronicler config init` is the recommended setup path.
- After this change, `chronicler config` becomes a subcommand group. Any documentation, README sections, or error messages that reference `chronicler config` as a standalone command need to be updated to reference `chronicler config show`.
