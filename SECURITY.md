# Security Policy

## Reporting a Vulnerability

To report a security vulnerability in Chronicler, please use GitHub's private
vulnerability reporting rather than opening a public issue:

1. Go to the [Security tab](https://github.com/ScottSucksAtProgramming/chronicler/security) of this repository.
2. Click **Report a vulnerability**.
3. Fill in the details and submit.

We will acknowledge the report within 72 hours and aim to provide a fix or
mitigation within 30 days for confirmed vulnerabilities.

## Scope

This policy covers the `chronicler` Python package itself. Vulnerabilities in
upstream services — nano-gpt.com, Kimi CLI, Obsidian, or LM Studio — should
be reported to those projects directly.

API keys and tokens stored in your local `config.toml` are your responsibility
to keep private. Do not commit `config.toml` to version control.
