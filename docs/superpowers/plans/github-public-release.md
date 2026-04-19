# Plan: GitHub Public Release Preparation

> Source PRD: `prd-github-release.md`

## Architectural Decisions

Durable decisions that apply across all phases:

- **License:** AGPL v3 (replaces MIT). Author retains commercial rights as copyright holder. Compatible with `thefuzz` GPLv2 dependency.
- **Package distribution:** PyPI via `hatchling` build backend and `uv build`. Entry point: `chronicler` CLI command.
- **CI runner:** `ubuntu-latest` with `astral-sh/setup-uv@v2` and Python 3.12.
- **Test scope in CI:** Unit tests only (`-m "not integration"` already set as default in `pyproject.toml`). Integration tests require live services and run locally only.
- **PyPI publishing:** OIDC trusted publisher (no stored API tokens). Publish job triggers only on `v*.*.*` tags. Must be verified against `test.pypi.org` before first production push.
- **Linting/formatting stack:** `ruff` (lint) + `black` (format). Both added to `[dependency-groups] dev`. No per-project pre-commit config — enforced by CI only (workspace-level hooks exist separately).
- **Version:** `1.0.0` for initial public release (tag: `v1.0.0`).
- **Changelog format:** Keep a Changelog (`https://keepachangelog.com`), organized by milestone rather than individual commits.

---

## Phase 1: Legal & Security Foundation

**User stories:** 1, 2, 3

### What to build

Replace the existing MIT `LICENSE` file with the full AGPL v3 license text. Update the `license` field in `pyproject.toml` to `AGPL-3.0-or-later`. Then commit the 6 currently-modified source files and decide whether `docs/article-brainstorm.md` is included or added to `.gitignore`.

This is the foundation — it must land before any public-facing metadata or community docs reference a license.

### Acceptance criteria

- [ ] `LICENSE` file contains the full AGPL v3 text with copyright year and author name
- [ ] `pyproject.toml` `license` field reads `AGPL-3.0-or-later`
- [ ] All 6 pending modified files are committed with a clear commit message
- [ ] `docs/article-brainstorm.md` is either committed or listed in `.gitignore`
- [ ] `git status` is clean after the commit

---

## Phase 2: Package Metadata

**User stories:** 14, 15, 16, 17

### What to build

Expand `pyproject.toml` with the metadata fields that PyPI and package discovery tools expect. This covers author, description, keywords, classifiers, and project URLs. Also bump the version to `1.0.0`.

No application code changes. This phase is purely metadata configuration.

### Acceptance criteria

- [ ] `[project]` includes `authors` (name + email), `readme = "README.md"`, and `keywords` relevant to DnD, Obsidian, and AI tooling
- [ ] `[project]` includes `classifiers` for: development status (Beta), license (AGPL v3), Python 3.12, and topic (Games/Entertainment :: Role-Playing)
- [ ] `[project.urls]` section added with `Homepage`, `Repository`, and `Issues` keys
- [ ] `version` bumped to `1.0.0`
- [ ] `uv build` completes successfully and the generated wheel metadata reflects the new fields
- [ ] `ruff` and `black` added to `[dependency-groups] dev`

---

## Phase 3: Community Documentation

**User stories:** 4, 5, 6, 20, 21

### What to build

Create `CONTRIBUTING.md` at the repo root and GitHub issue/PR templates under `.github/`. These files set expectations for contributors and provide structure for bug reports and feature requests.

`CONTRIBUTING.md` must cover: development environment setup (uv, Python 3.12, local LLM services), code style standards (Black formatting, ruff linting, type hints required, 300-line file limit), testing requirements (TDD, all new behavior unit-tested, integration tests marked), PR process (open issue first for significant changes, branch conventions, PR description expectations), and commit message style.

GitHub templates must cover: bug reports (Python version, OS, steps to reproduce, expected vs actual), feature requests (motivation, proposed solution, alternatives), and a PR checklist (description, related issue, tests, type of change).

### Acceptance criteria

- [ ] `CONTRIBUTING.md` exists at repo root and covers: dev setup, code style, testing requirements, PR process, commit conventions
- [ ] `CONTRIBUTING.md` documents how to run unit tests (`uv run pytest`) and how to run lint/format checks (`uv run ruff check`, `uv run black --check`)
- [ ] `.github/ISSUE_TEMPLATE/bug_report.md` exists with required fields
- [ ] `.github/ISSUE_TEMPLATE/feature_request.md` exists with required fields
- [ ] `.github/pull_request_template.md` exists with a PR checklist
- [ ] All templates use front matter with `name`, `about`, and `labels` fields

---

## Phase 4: Release History

**User stories:** 7, 8, 25

### What to build

Create `CHANGELOG.md` at the repo root using Keep a Changelog format. Organize entries by the project's development milestones (Foundation through Milestone 6+) rather than individual commits. Include an `[Unreleased]` section at the top. The initial release is tagged `v1.0.0`.

Tag `v1.0.0` in git after the changelog is committed. This tag will later trigger the CI publish job.

### Acceptance criteria

- [ ] `CHANGELOG.md` exists at repo root, following Keep a Changelog format
- [ ] File includes an `[Unreleased]` section at the top
- [ ] File includes a `[1.0.0]` section with milestone-organized entries covering the project's full development history
- [ ] Each milestone section uses Keep a Changelog categories (Added, Changed, Fixed, Removed) as appropriate
- [ ] Git tag `v1.0.0` exists pointing to the changelog commit

---

## Phase 5: CI/CD Pipeline

**User stories:** 11, 12, 13, 22, 23, 24

### What to build

Create `.github/workflows/ci.yml` with two jobs:

**`test` job** — runs on every push to `main` and every pull request targeting `main`:
- Checks out the repo
- Installs uv via `astral-sh/setup-uv@v2` with Python 3.12
- Caches `~/.cache/uv` keyed on `uv.lock`
- Runs `uv sync` to install all deps including dev group
- Runs `uv run ruff check src/ tests/`
- Runs `uv run black --check src/ tests/`
- Runs `uv run pytest` (integration tests already excluded by `pyproject.toml` default)

**`publish` job** — runs only on `v*.*.*` tag pushes, depends on `test` passing:
- Same uv setup
- Runs `uv build`
- Publishes via `pypa/gh-action-pypi-publish` using OIDC (no stored secrets)
- Requires `id-token: write` permission

Also add CI status badge and PyPI version badge to the top of `README.md`.

Before the first real production push: test the publish job against `test.pypi.org` by setting `repository-url: https://test.pypi.org/legacy/` and pushing a pre-release tag. Configure PyPI trusted publisher (OIDC) for the GitHub repo/workflow on both `test.pypi.org` and `pypi.org` before running the workflow.

### Acceptance criteria

- [ ] `.github/workflows/ci.yml` exists with `test` and `publish` jobs
- [ ] `test` job triggers on push to `main` and on pull requests targeting `main`
- [ ] `test` job runs ruff, black, and pytest in sequence; all must pass
- [ ] `publish` job only runs on `v*.*.*` tag pushes and requires `test` to pass first
- [ ] `publish` job uses OIDC (no `password:` or `token:` secrets in the workflow file)
- [ ] uv dependency cache is configured using `uv.lock` as the cache key
- [ ] CI status badge added to `README.md` (GitHub Actions badge format)
- [ ] PyPI version badge added to `README.md`
- [ ] Workflow verified passing on a push to `main` before tagging `v1.0.0`
- [ ] Test publish to `test.pypi.org` succeeds before publishing to production PyPI

---

## Phase 6: Architecture Documentation

**User stories:** 19

### What to build

Create `docs/ARCHITECTURE.md` as a public-facing, concise overview of how Chronicler works internally. This is for developers who want to understand the codebase — not a full spec, but a clear map.

Cover: the end-to-end data flow (PDF/text in → LLM extraction → Obsidian vault out → ChromaDB index → TUI query), the 8 core modules and their single responsibilities, the dependency direction (Clean Architecture: outer layers depend on inner, never the reverse), and a note pointing to the detailed design specs in `docs/superpowers/specs/` for readers who want to go deeper.

### Acceptance criteria

- [ ] `docs/ARCHITECTURE.md` exists and is reachable from `README.md` (add a link in the README's "Documentation" or "Contributing" section)
- [ ] Document covers end-to-end data flow with enough detail to orient a new contributor
- [ ] All 8 modules (`config`, `models`, `gateway`, `ingestion`, `extraction`, `vault`, `retrieval`, `cli`) are described with their responsibility and key inputs/outputs
- [ ] Dependency direction (Clean Architecture) is explained and illustrated (ASCII or prose)
- [ ] External service boundaries (LM Studio, Kimi CLI, nano-gpt.com, Obsidian filesystem) are identified
- [ ] Link to detailed specs in `docs/superpowers/specs/` for deeper reading
