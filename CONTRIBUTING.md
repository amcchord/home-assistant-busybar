# Contributing

Thanks for helping make BUSY Bar more useful—and more fun.

## Before opening a change

- Search existing issues and pull requests.
- Keep routine operation local-first; new cloud dependencies need a compelling, opt-in reason.
- Never log API keys or unredacted device/network identifiers.
- Preserve display priority semantics and Home Assistant application ownership.

## Development setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements_test.txt
pytest
ruff check .
ruff format --check .
deno check custom_components/busybar/www/busybar-card.js
```

## Pull requests

Describe the user impact, tests performed, firmware/API version used, and whether the change writes device state. Add or update tests for behavior changes. Screenshots or a short video are especially helpful for visual effects.

By contributing, you agree that your work is licensed under this repository's MIT license.
