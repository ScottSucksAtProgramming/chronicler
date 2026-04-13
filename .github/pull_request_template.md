---
name: Pull request
about: Checklist for submitting changes to Chronicler
labels: ""
---

## Summary

Describe the change and the reason for it.

## Related Issue

Link the issue this PR addresses, if applicable.

## Type of Change

- [ ] Feature
- [ ] Bug fix
- [ ] Documentation
- [ ] Refactor
- [ ] Tooling or maintenance

## Verification

- [ ] I ran the relevant local tests
- [ ] I ran `uv run ruff check src/ tests/`
- [ ] I ran `uv run black --check src/ tests/`

## Checklist

- [ ] My PR includes a clear description of the change
- [ ] I linked the related issue, or documented why there is no issue
- [ ] I updated tests for behavior changes
- [ ] I updated documentation where needed
