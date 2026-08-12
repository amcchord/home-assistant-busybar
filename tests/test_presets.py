"""Tests for opinionated household shortcuts."""

import pytest

from custom_components.busybar.const import EFFECTS
from custom_components.busybar.presets import PRESETS, preset_spec


@pytest.mark.parametrize("preset", PRESETS)
def test_every_preset_uses_a_real_bounded_effect(preset: str) -> None:
    """Every shortcut maps to a supported, safe animation."""
    spec = preset_spec(preset)
    assert spec.effect in EFFECTS
    assert spec.message
    assert 0.5 <= spec.duration <= 30
    assert 1 <= spec.priority <= 100


def test_preset_message_can_be_personalized() -> None:
    """Automations can retain a preset's personality with custom words."""
    original = preset_spec("welcome_home")
    custom = preset_spec("welcome_home", message="HI ALEX")
    assert custom.message == "HI ALEX"
    assert custom.effect == original.effect


def test_unknown_preset_is_rejected() -> None:
    """Typos fail before any device request."""
    with pytest.raises(ValueError, match="Unknown preset"):
        preset_spec("warp_drive")
