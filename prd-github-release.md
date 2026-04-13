# PRD: Chronicler Public GitHub Release Preparation

## Problem Statement

Chronicler is a mature, well-architected Python CLI tool for managing tabletop RPG campaign notes. It has 70 commits, comprehensive tests, and thorough documentation — but it is not ready for public GitHub visibility. Key blockers include a license that doesn't reflect the author's intent (MIT does not prevent commercial exploitation by others, and conflicts with a GPLv2 dependency), a configuration template that may expose a real API key, missing community-facing files (CONTRIBUTING.md, CHANGELOG.md), no automated CI/CD pipeline, and under-specified package metadata. Publishing the repository in its current state would result in a confusing, legally ambiguous, and professionally incomplete public presence.

## Solution

Prepare the Chronicler repository for public GitHub release by resolving all legal, security, documentation, and automation gaps. This includes relicensing to AGPL v3 (which prevents commercial exploitation by third parties while preserving the author's own rights, and is compatible with the thefuzz GPLv2 dependency), sanitizing the .env.example file, adding CONTRIBUTING.md and CHANGELOG.md, creating a GitHub Actions CI/CD pipeline that runs tests and linting on every push and publishes to PyPI on version tags, and polishing pyproject.toml package metadata for PyPI discoverability.

## User Stories

1. As a developer visiting the repository, I want to see a clear license, so that I know under what terms I can use or contribute to the project.
2. As a developer, I want to know that any derivative work I publish must remain open-source, so that I understand the copyleft requirements of AGPL v3.
3. As the project author, I want to retain the right to build a commercial product from Chronicler, so that my own future business options are not restricted by the public license.
4. As a potential contributor, I want to read a CONTRIBUTING.md, so that I know how to submit issues and pull requests effectively.
5. As a potential contributor, I want to know the project's code style and testing requirements, so that my contributions meet the project's standards.
6. As a potential contributor, I want to know what tools and commands to use for local development, so that I can set up the project quickly.
7. As a new user, I want a CHANGELOG.md, so that I can understand what changed between versions and how the project has evolved.
8. As a new user, I want to see a clear version history tied to milestones, so that I can understand the project's maturity and trajectory.
9. As a security-conscious developer, I want the .env.example file to use generic placeholders for API keys, so that I am not exposed to a real credential accidentally committed to the repository.
10. As a developer cloning the repository, I want .env.example to show every required environment variable, so that I can configure my environment correctly without guessing.
11. As a contributor submitting a pull request, I want a GitHub Actions workflow to run automatically, so that I get immediate feedback on whether my changes pass tests and lint checks.
12. As the project maintainer, I want tests and linting to run on every push to main and every pull request, so that regressions are caught before merging.
13. As the project maintainer, I want to publish a new release to PyPI by pushing a version tag, so that the release process is automated and repeatable.
14. As a PyPI user browsing for DnD tools, I want Chronicler to appear in search results with accurate metadata, so that I can discover and evaluate the tool.
15. As a PyPI user, I want to see the project description, keywords, author, and homepage URL on the PyPI listing, so that I can quickly assess the project.
16. As a PyPI user, I want to install Chronicler with a single `pip install` or `uv add` command, so that setup is straightforward.
17. As a developer exploring the project, I want pyproject.toml to declare the correct Python version classifiers, so that I know which Python versions are supported.
18. As a developer, I want the repository's git history to reflect a clean, committed state at the time of public release, so that the commit history is meaningful and not full of uncommitted noise.
19. As a developer, I want docs/ARCHITECTURE.md to give a high-level overview of the system's modules and data flow, so that I can orient myself in the codebase quickly.
20. As a contributor, I want issue templates on GitHub, so that bug reports and feature requests include the information needed to act on them.
21. As a maintainer, I want a pull request template, so that contributors provide context, testing evidence, and a checklist before requesting review.
22. As a developer, I want the GitHub Actions workflow to use caching for Python dependencies, so that CI runs are fast.
23. As the project maintainer, I want the PyPI publish step to only trigger on version tags (e.g., v1.0.0), so that accidental pushes do not trigger a release.
24. As a developer evaluating the project, I want the README to include a PyPI install badge and CI status badge, so that I can see the project's health at a glance.
25. As a maintainer, I want CHANGELOG.md to follow the Keep a Changelog format, so that entries are consistent and machine-readable.

## Implementation Decisions

### License Change (MIT → AGPL v3)
- Replace the existing MIT LICENSE file with the full AGPL v3 license text
- Update the license field in pyproject.toml from MIT to AGPL-3.0-or-later
- Add an SPDX license identifier comment to the top of the main entry point if appropriate
- AGPL v3 is compatible with the thefuzz GPLv2 dependency, resolving the existing license conflict
- The author retains full rights to commercialize the project under separate terms (dual licensing is implicit as copyright holder)

### .env.example Sanitization
- Replace the example nano-gpt API key value with a generic placeholder string (e.g., `sk-nano-your-api-key-here`)
- Review all other values in .env.example and replace any user-specific paths with descriptive placeholders (e.g., `/path/to/your/obsidian/vault`)
- Add inline comments to .env.example explaining each variable's purpose and where to obtain values

### Commit Pending Changes
- Review all 6 modified source files and 1 new untracked file before committing
- Decide whether docs/article-brainstorm.md should be committed or added to .gitignore
- Commit all intended changes with a clear message before tagging for release

### CONTRIBUTING.md
- State that the project is open to external contributions
- Document the development environment setup (uv, Python 3.12+, local LLM requirements)
- Document the code style standards: Black formatting, ruff linting, type hints required, no files over 300 lines
- Document the testing requirements: TDD, all new behavior must have unit tests, integration tests must be marked with `@pytest.mark.integration`
- Document the PR process: open an issue first for significant changes, branch naming conventions, PR description expectations
- Document commit message conventions (matching existing project style)
- Link to the issue tracker for bug reports and feature requests

### CHANGELOG.md
- Use the Keep a Changelog format (https://keepachangelog.com)
- Organize by milestone rather than individual commits (Milestone 1 through Milestone 6+)
- Include an [Unreleased] section at the top for ongoing work
- Summarize each milestone's major features, changes, and fixes
- Tag the initial public release as v1.0.0

### GitHub Actions CI/CD Workflow
- Create a single workflow file with two jobs: `test` and `publish`
- The `test` job runs on every push and pull request to main
  - Set up Python 3.12
  - Install dependencies via uv
  - Run ruff for linting
  - Run black for formatting checks
  - Run pytest, excluding integration tests (using `-m "not integration"`)
  - Cache uv/pip dependencies to speed up runs
- The `publish` job runs only on version tag pushes (pattern: `v*.*.*`)
  - Depends on the `test` job passing
  - Builds the package using `uv build` or `python -m build`
  - Publishes to PyPI using the official PyPA publish action with a trusted publisher (OIDC, no stored secrets)
  - Requires setting up a PyPI trusted publisher configuration

### pyproject.toml Metadata Polish
- Add `[project]` fields: `authors`, `description`, `readme`, `keywords`, `classifiers`
- Add `[project.urls]` section with Homepage, Repository, and Issue Tracker links
- Add Python version classifiers matching supported versions (3.12+)
- Add topic classifiers (e.g., "Topic :: Games/Entertainment :: Role-Playing", "Topic :: Utilities")
- Verify the `license` field matches the new AGPL v3 license
- Confirm the package `name`, `version`, and `entry_points` are correct

### docs/ARCHITECTURE.md
- Write a concise public-facing architecture overview (not a full spec)
- Cover: high-level data flow from PDF ingestion to Obsidian vault population to ChromaDB indexing
- Document the 8 core modules (config, models, gateway, ingestion, extraction, vault, retrieval, chat/cli) and their responsibilities
- Explain the dependency direction (Clean Architecture: outer layers depend on inner layers)
- Reference the detailed design specs in docs/superpowers/specs/ for readers who want to go deeper

### GitHub Issue and PR Templates
- Create `.github/ISSUE_TEMPLATE/bug_report.md` with fields for Python version, OS, steps to reproduce, expected vs actual behavior
- Create `.github/ISSUE_TEMPLATE/feature_request.md` with fields for motivation, proposed solution, alternatives considered
- Create `.github/pull_request_template.md` with a checklist: description of changes, related issue, testing done, type of change

### README Badges
- Add a CI status badge (GitHub Actions) at the top of README.md
- Add a PyPI version badge once the package is published

## Testing Decisions

**Philosophy:** Tests should verify observable external behavior, not implementation details. A good test calls a public function or CLI command with known inputs and asserts on outputs, without knowledge of internal data structures or intermediate steps.

**Modules to test for this PRD's changes:**

- **CI/CD workflow (manual verification):** The GitHub Actions workflow itself is not unit-tested, but must be verified by triggering a push and confirming all steps pass. The publish step must be verified against PyPI test (test.pypi.org) before a real release.
- **pyproject.toml metadata:** Verified by running `uv build` and inspecting the generated wheel/sdist metadata, and by checking the PyPI listing after publish.
- **No new application logic is introduced by this PRD**, so no new unit or integration tests are required in the test suite beyond what already exists.

**Prior art:** Existing tests in `tests/` follow pytest conventions with `@pytest.mark.integration` markers. CI should mirror this pattern by excluding integration tests in the automated workflow.

## Out of Scope

- Replacing `thefuzz` with `rapidfuzz` — not needed since the license is changing to AGPL v3, which is compatible with GPLv2
- Creating a docs/INSTALLATION.md — the README's installation section is sufficient for now
- Creating docs/EXAMPLES.md — out of scope for this release
- Adding pre-commit hooks to the repository — the developer's environment already has these configured at the workspace level
- Setting up a GitHub Discussions forum or Discord
- Internationalization or localization
- Any new application features or bug fixes — this PRD is strictly about public release readiness
- Automated dependency updates (Dependabot) — can be added later
- Code coverage reporting in CI — can be added later

## Further Notes

- The AGPL v3 license means that any person or company who distributes a modified version of Chronicler, or offers it as a network service, must release their modifications under AGPL v3. The original author is not bound by this restriction and may commercialize the project separately.
- PyPI trusted publishing (OIDC) is the recommended approach for the publish step — it avoids storing long-lived PyPI API tokens as GitHub secrets.
- The initial PyPI release should be tested against test.pypi.org before publishing to the real index.
- The article-brainstorm.md file found in docs/ should be reviewed before commit — if it contains notes intended for a future blog post or article about the project, it may be worth keeping. If it's too raw, add it to .gitignore instead.
- Version tagging convention: use semantic versioning (v1.0.0 for initial public release, incrementing as features are added).
