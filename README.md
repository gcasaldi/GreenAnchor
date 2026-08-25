# GreenAnchor

GreenAnchor is an independent platform that helps people discover and support real environmental campaigns without creating duplicates.

The idea is simple: do not start another petition, help complete an existing one.

## What it does

- Aggregates public campaign data from trusted sources.
- Highlights urgent and high-impact actions.
- Shows progress when reliable numeric targets are available.
- Links users directly to the original campaign pages.

## Tech at a glance

- Frontend: static site (`index.html`) deployed on GitHub Pages.
- Data: versioned `campagne.json` in this repository.
- Data updater: `scripts/update_campaigns.py`.
- Search and filtering: client-side, no backend required.

## Quick start

```bash
python -m pip install -r scripts/requirements.txt
python scripts/update_campaigns.py
```

Then open `index.html` in your browser.

## Automation

- Nightly data refresh runs via GitHub Actions.
- GitHub Pages deploy runs automatically on pushes to `main`.
- Validation checks run on push and pull requests.

## Contributing

Contributions are welcome. For a fast guide, see `CONTRIBUTING.md`.

## License

MIT (see `LICENSE`).
