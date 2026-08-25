# Contributing to GreenAnchor

Thanks for your interest in improving GreenAnchor.

## How to contribute

1. Fork the repository.
2. Create a branch: `feat/short-description`.
3. Keep changes focused and small.
4. Open a pull request with a clear summary.

## Good contribution examples

- Improve campaign source quality.
- Fix UI bugs or accessibility issues.
- Improve docs and onboarding.
- Add tests or validation checks.

## Local checks before PR

```bash
python -m py_compile scripts/update_campaigns.py
python -m json.tool campagne.json > /dev/null
```

## Style notes

- Prefer simple, readable code.
- Do not break existing data structure in `campagne.json`.
- If you change data logic, explain why in the PR.

Thank you for helping make environmental action easier to find and complete.
