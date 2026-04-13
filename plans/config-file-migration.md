# Plan: Config File Migration

> Source PRD: `prd-config-file-migration.md`

## Architectural Decisions

- **Config file format:** TOML. Read via stdlib `tomllib` (Python 3.12+, no extra dep). Write via `tomli-w`.
- **Config file location:** OS-appropriate via `platformdirs.user_config_dir("chronicler")`.
  - macOS: `~/Library/Application Support/chronicler/config.toml`
  - Linux: `${XDG_CONFIG_HOME:-~/.config}/chronicler/config.toml`
  - Windows: `%APPDATA%\chronicler\config.toml`
- **Settings priority:** constructor kwargs > `CHRONICLER_` env vars > TOML config file > field defaults. Implemented via `settings_customise_sources` classmethod with `TomlConfigSettingsSource`. `dotenv_settings` is dropped from the chain entirely.
- **Config path seam:** A `config/paths.py` module exposes `get_config_path()` and `set_config_path()`. All code calls `get_config_path()`; tests call `set_config_path(tmp_path / "config.toml")` and reset to `None` on teardown. No monkeypatching of `platformdirs`.
- **TOML shape:** Flat — no nested sections. All keys match `Settings` field names directly.
- **Env var annotation:** A `get_field_sources()` utility reads env vars and TOML independently, returning a per-field `"env" | "file" | "default"` mapping used by `config show`.
- **Typer subcommand pattern:** `config_app = typer.Typer()` added to `main.py`, following the existing `party_app` pattern. `app.add_typer(config_app, name="config")`. A `invoke_without_command=True` callback ensures bare `chronicler config` continues to invoke `config show`.
- **New runtime dependencies:** `platformdirs>=4.0`, `tomli-w>=1.0`.
- **Dropped:** `env_file` and `env_file_encoding` from `SettingsConfigDict`. `.env` file support removed entirely.

---

## Phase 1: Config Path Resolution & TOML Loading Foundation

**User stories:** 14, 15, 16, 17, 18, 19

### What to build

Add `platformdirs` and `tomli-w` to runtime dependencies. Build a `config/paths.py` module with two public functions: one that returns the OS-appropriate config file path using `platformdirs`, and one that overrides it (for test injection). Update `Settings` to use `settings_customise_sources`, wiring in `TomlConfigSettingsSource` pointed at the resolved config path. Remove `env_file` from the settings config entirely. `TomlConfigSettingsSource` silently no-ops when the file does not exist, so no file-existence guard is needed.

The rest of the application is unaffected — `Settings()` is still the single interface everywhere.

### Acceptance criteria

- [ ] `platformdirs` and `tomli-w` added to `[project.dependencies]` in `pyproject.toml`
- [ ] `config/paths.py` module exists with `get_config_path() -> Path` and `set_config_path(path: Path | None) -> None`
- [ ] `get_config_path()` returns the correct platform-specific path on macOS, Linux (with and without `$XDG_CONFIG_HOME`), and Windows
- [ ] `Settings` uses `settings_customise_sources`; source order is: init kwargs → env vars → TOML file
- [ ] `env_file` and `env_file_encoding` are removed from `SettingsConfigDict`
- [ ] `Settings()` loads values from a TOML file placed at the path returned by `get_config_path()`
- [ ] An env var (`CHRONICLER_LOG_LEVEL=DEBUG`) overrides the same field in the TOML file
- [ ] `Settings()` raises a validation error when `vault_path` is absent from both env vars and the config file
- [ ] Unit tests cover: correct path per OS (via `set_config_path`), TOML loading, env var override, missing required field error
- [ ] `uv run pytest` passes

---

## Phase 2: Config Show Subcommand

**User stories:** 10, 11, 20, 21

### What to build

Convert the existing `config` command to a Typer subcommand group following the `party_app` pattern already in `main.py`. The existing `config()` function body moves to a `config show` subcommand. A `invoke_without_command=True` callback ensures `chronicler config` (bare) continues to invoke `show`, preserving backward compatibility.

Add a `get_field_sources()` utility that reads the TOML file and env vars independently and returns a per-field source label. Use this in `config show` to annotate each line with `(from env)` when an env var is active, or `(default)` when neither file nor env is set.

Update every error message in the CLI that currently references `cp .env.example .env` to reference `chronicler config init` instead.

### Acceptance criteria

- [ ] `chronicler config` (bare) shows configuration — same behavior as before
- [ ] `chronicler config show` is an explicit subcommand that produces the same output
- [ ] Fields whose values come from a `CHRONICLER_` env var show `(from env)` in `config show` output
- [ ] Fields falling back to defaults show `(default)` in `config show` output
- [ ] API key is still masked (last 4 characters shown)
- [ ] Vault path existence check still present (green / yellow warning)
- [ ] All CLI error messages that previously said "Copy .env.example to .env" now say "Run: chronicler config init"
- [ ] CLI tests for `config show` cover: values from file, env override annotation, default annotation
- [ ] `uv run pytest` passes

---

## Phase 3: Config Init Wizard

**User stories:** 1, 2, 3, 4, 5, 6, 7, 8, 9, 12, 13, 22

### What to build

Implement `chronicler config init` as an interactive wizard registered under `config_app`. The wizard uses `typer.prompt` for input and `rich` for display (consistent with the rest of the CLI).

Wizard flow:
1. If a config file already exists at the resolved path, display a warning and ask for confirmation before continuing. Abort if the user declines.
2. Prompt for `vault_path`. Validate that the entered path exists on disk. Re-prompt on failure with a clear error.
3. Prompt for `vault_name`, defaulting to the basename of the entered vault path.
4. Prompt for `llm_provider` as a choice between `kimi` and `nanogpt`.
5. If `nanogpt`: prompt for `nanogpt_api_key` (required, no default) and `nanogpt_model` (default shown).
6. If `kimi`: check whether `kimi` is available on `PATH`. Display a warning if not found, but do not abort.
7. Prompt for `lm_studio_base_url` with the default shown — user presses Enter to accept.
8. Prompt for `embedding_model` with the default shown.
9. Prompt for `log_level` with the default shown.
10. Display a formatted summary of all collected values.
11. Ask for confirmation. Abort cleanly if the user declines.
12. Create the config directory if it does not exist, then write `config.toml` via `tomli-w`.
13. Print the path where the file was saved.

### Acceptance criteria

- [ ] `chronicler config init` runs the wizard end-to-end
- [ ] Entering a non-existent vault path re-prompts with a clear error
- [ ] Vault name defaults to the basename of the vault path
- [ ] LLM provider prompt accepts only `kimi` or `nanogpt`
- [ ] `nanogpt_api_key` prompt appears only when `nanogpt` is selected
- [ ] Kimi PATH check emits a warning but does not abort when `kimi` is not found
- [ ] All optional prompts show their default value and accept Enter to skip
- [ ] A summary is shown before writing; declining aborts without writing
- [ ] Running `config init` when a config file already exists warns and asks for confirmation before overwriting
- [ ] The config directory is created automatically if it does not exist
- [ ] The written `config.toml` is valid TOML and loads correctly via `Settings()`
- [ ] The path of the written file is printed on success
- [ ] CLI tests using `CliRunner` cover: happy path, invalid vault path re-prompt, existing file overwrite confirmation, user abort at summary
- [ ] `uv run pytest` passes

---

## Phase 4: Cleanup & Documentation

**User stories:** (supports all prior stories)

### What to build

Update all remaining documentation and in-repo references so nothing still points users toward the `.env` workflow.

- Update the header comment in `.env.example` to clarify it is a reference document only and that `chronicler config init` is the recommended setup path.
- Update `CONTRIBUTING.md` dev setup section: replace `cp .env.example .env` with `chronicler config init` (or `Settings(vault_path=...)` direct constructor for unit tests).
- Verify no remaining CLI output, README section, or doc file still references the `.env` setup flow for end users.
- Update `uv.lock` to reflect the new dependencies.

### Acceptance criteria

- [ ] `.env.example` header comment states it is for reference only and directs users to `chronicler config init`
- [ ] `CONTRIBUTING.md` dev setup section references `chronicler config init` instead of `cp .env.example .env`
- [ ] `grep` for `cp .env.example` across the repo returns no results outside of `.env.example` itself
- [ ] `grep` for `CHRONICLER_VAULT_PATH` in user-facing docs/error messages is replaced with config file references where appropriate
- [ ] `uv.lock` updated to include `platformdirs` and `tomli-w`
- [ ] `uv run pytest` passes
- [ ] `uv run ruff check src/ tests/` passes
- [ ] `uv run black --check src/ tests/` passes
