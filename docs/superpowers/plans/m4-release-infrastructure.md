# Plan: M4 — Release Infrastructure

> Source PRD: https://github.com/ScottSucksAtProgramming/chronicler/issues/8

## Architectural Decisions

Durable decisions that apply across all phases:

- **PyPI distribution name**: `chronicler-ttrpg` (the name `chronicler` is claimed by a dormant Django app)
- **CLI entry point**: `chronicler` — independent of the distribution name; unchanged throughout
- **Python module**: `src/chronicler/` — unchanged; no internal imports are affected
- **Version**: `0.1.0` (down from `1.0.0`; macOS-only limitation warrants pre-1.0 signal)
- **Dev Status classifier**: `Development Status :: 4 - Beta` — kept as-is
- **OIDC trusted publisher fields** (used on both TestPyPI and PyPI):
  - Owner: `ScottSucksAtProgramming`
  - Repository: `chronicler`
  - Workflow: `ci.yml`
  - Environment: `pypi`
- **TestPyPI pre-release tag**: `v0.1.0b1`
- **Production release tag**: `v0.1.0`

---

## Phase 1: Metadata & Docs

**User stories**: 1, 3, 4, 5, 6, 7, 12, 13, 14

### What to build

Update `pyproject.toml` to rename the distribution from `chronicler` to `chronicler-ttrpg` and set the version to `0.1.0`. The `[project.scripts]` entry point (`chronicler = "chronicler.cli.main:app"`) stays unchanged. Regenerate `uv.lock` with `uv sync --dev` to keep the lock file consistent.

Update all user-facing install documentation to reference the new package name:
- `README.md`: replace `pip install chronicler` with `pip install chronicler-ttrpg`; update the PyPI badge URLs from `/pypi/v/chronicler` to `/pypi/v/chronicler-ttrpg` and the badge link from `pypi.org/project/chronicler/` to `pypi.org/project/chronicler-ttrpg/`
- `docs/installation.md`: replace `pip install chronicler` with `pip install chronicler-ttrpg`
- `docs/quick-start.md`: replace any install references if present

All references to the CLI commands themselves (`chronicler ingest`, `chronicler chat`, etc.) are unchanged.

Commit everything to `main` with a message like `chore: rename package to chronicler-ttrpg, bump version to 0.1.0`.

### Acceptance criteria

- [ ] `pyproject.toml` has `name = "chronicler-ttrpg"` and `version = "0.1.0"`
- [ ] `[project.scripts]` still reads `chronicler = "chronicler.cli.main:app"`
- [ ] `uv build` succeeds and the generated wheel filename contains `chronicler_ttrpg-0.1.0`
- [ ] Inspecting the wheel metadata (`unzip -p dist/*.whl '*/METADATA' | head -5`) shows `Name: chronicler-ttrpg` and `Version: 0.1.0`
- [ ] `README.md` contains no remaining `pip install chronicler` (without `-ttrpg`)
- [ ] `README.md` badge URLs reference `chronicler-ttrpg`
- [ ] `docs/installation.md` install command reads `pip install chronicler-ttrpg`
- [ ] `uv run pytest` passes (no regressions from metadata-only changes)

---

## Phase 2: TestPyPI Dry Run

**User stories**: 2, 8, 9, 10, 11

### What to build

This phase is a two-part manual + automated sequence.

**Part A — Manual: Configure OIDC trusted publisher on TestPyPI**

1. Log in to https://test.pypi.org
2. Go to Account Settings → Publishing → Add a new pending publisher
3. Fill in:
   - PyPI Project Name: `chronicler-ttrpg`
   - Owner: `ScottSucksAtProgramming`
   - Repository name: `chronicler`
   - Workflow name: `ci.yml`
   - Environment name: `pypi`
4. Save. No package needs to exist yet — this is a "pending" publisher.

**Part B — Code: Temporarily redirect CI to TestPyPI**

Add `repository-url: https://test.pypi.org/legacy/` to the `pypa/gh-action-pypi-publish` step in `.github/workflows/ci.yml`:

```yaml
- name: Publish package distributions to PyPI
  uses: pypa/gh-action-pypi-publish@release/v1
  with:
    repository-url: https://test.pypi.org/legacy/
```

Commit this change (e.g. `chore: temporarily redirect publish to TestPyPI`) and push tag `v0.1.0b1`:

```bash
git tag v0.1.0b1
git push origin v0.1.0b1
```

Watch the GitHub Actions run. The `publish` job requires the `test` job to pass first, then publishes to TestPyPI via OIDC.

**Part C — Verify**

```bash
pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ chronicler-ttrpg==0.1.0b1
chronicler --help
```

`--extra-index-url` is needed because TestPyPI does not mirror all dependencies.

### Acceptance criteria

- [ ] OIDC pending publisher for `chronicler-ttrpg` exists on test.pypi.org before pushing the tag
- [ ] Pushing `v0.1.0b1` triggers the CI `publish` job (not just `test`)
- [ ] The `publish` job completes green — no OIDC or permissions errors
- [ ] `https://test.pypi.org/project/chronicler-ttrpg/` shows version `0.1.0b1`
- [ ] `pip install --index-url https://test.pypi.org/simple/ ... chronicler-ttrpg==0.1.0b1` installs without errors
- [ ] `chronicler --help` exits 0 and lists expected commands after install

---

## Phase 3: Production Release

**User stories**: 1, 2, 3, 4, 8

### What to build

**Part A — Manual: Configure OIDC trusted publisher on production PyPI**

1. Log in to https://pypi.org
2. Go to Account Settings → Publishing → Add a new pending publisher
3. Fill in the same fields as TestPyPI:
   - PyPI Project Name: `chronicler-ttrpg`
   - Owner: `ScottSucksAtProgramming`
   - Repository name: `chronicler`
   - Workflow name: `ci.yml`
   - Environment name: `pypi`
4. Save.

**Part B — Code: Restore CI to production PyPI**

Remove the `repository-url: https://test.pypi.org/legacy/` line added in Phase 2, leaving the `pypa/gh-action-pypi-publish` step with no `with:` block (which defaults to production PyPI).

Commit: `chore: restore CI publish target to production PyPI`

Push to `main`, then push the release tag:

```bash
git push origin main
git tag v0.1.0
git push origin v0.1.0
```

**Part C — Verify**

```bash
pip install chronicler-ttrpg
chronicler --help
```

Also visually confirm:
- `https://pypi.org/project/chronicler-ttrpg/` shows version `0.1.0`
- The README PyPI badge in the GitHub repo resolves and displays `0.1.0`

### Acceptance criteria

- [ ] OIDC pending publisher for `chronicler-ttrpg` exists on pypi.org before pushing `v0.1.0`
- [ ] `ci.yml` has no `repository-url` line (targets production PyPI)
- [ ] Pushing `v0.1.0` triggers the CI `publish` job and it completes green
- [ ] `https://pypi.org/project/chronicler-ttrpg/` shows version `0.1.0`
- [ ] `pip install chronicler-ttrpg` installs cleanly from production PyPI
- [ ] `chronicler --help` exits 0 after production install
- [ ] README PyPI badge displays `0.1.0` and links to the correct PyPI page
- [ ] Mark M4 tasks as `@done` in `todo.taskpaper`
