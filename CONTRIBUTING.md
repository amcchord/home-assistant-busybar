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
deno check custom_components/busybar_playground/www/busybar-playground-card.js
deno test --allow-read tests/test_card.js
```

CI also loads both this integration and the actual `pickerin/hass-busybar` integration, pinned to v0.6.10 commit `91a74bc9cace3c05bc64026c1074ce44c2e40862`, in one Home Assistant instance with mocked device APIs. To reproduce:

```bash
git clone --no-checkout https://github.com/pickerin/hass-busybar.git .compat/pickerin
git -C .compat/pickerin checkout 91a74bc9cace3c05bc64026c1074ce44c2e40862
PYTHONPATH="$PWD/.compat/pickerin:$PWD" pytest tests/compatibility/check_catalog_coexistence.py
```

This verifies software loading, entity registration, service routing, separate card URLs, and independent unloading. It does not exercise physical hardware or simultaneous display commands.

## Pull requests

Describe the user impact, tests performed, firmware/API version used, and whether the change writes device state. Add or update tests for behavior changes. Screenshots or a short video are especially helpful for visual effects.

By contributing, you agree that your work is licensed under this repository's MIT license.
