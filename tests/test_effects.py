"""Tests for generated display compositions."""

import pytest
from busylib import types

from custom_components.busybar.const import EFFECTS, SCENES
from custom_components.busybar.effects import (
    effect_frames,
    message_payload,
    normalize_color,
    progress_payload,
    scene_payload,
)


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("#abcdef", "#ABCDEFFF"),
        ("11223344", "#11223344"),
        ([1, 2, 3], "#010203FF"),
        ((255, 128, 0, 64), "#FF800040"),
        ("nope", "#FFFFFFFF"),
    ],
)
def test_normalize_color(source, expected: str) -> None:
    """Colors from YAML and the UI normalize to the firmware format."""
    assert normalize_color(source) == expected


def test_message_payload_is_owned_and_bounded() -> None:
    """Messages use the integration application and front display bounds."""
    payload = message_payload(
        "A deliberately long Home Assistant message",
        color=[74, 222, 128],
        background=[5, 46, 22],
        priority=42,
        duration=8,
    )
    assert payload["application_name"] == "home_assistant"
    assert payload["priority"] == 42
    assert payload["elements"][0]["width"] == 72
    assert payload["elements"][0]["height"] == 16
    assert payload["elements"][1]["scroll_rate"] == 45
    assert payload["elements"][1]["timeout"] == 8


@pytest.mark.parametrize("value", [-10, 0, 50, 100, 150])
def test_progress_is_clamped(value: float) -> None:
    """Progress never draws outside the panel."""
    payload = progress_payload(value)
    bar = payload["elements"][1]
    assert 1 <= bar["width"] <= 72


@pytest.mark.parametrize("scene", SCENES)
def test_all_scenes_render(scene: str) -> None:
    """Every advertised status scene produces valid elements."""
    payload = scene_payload(scene)
    assert payload["elements"]
    assert all(element["display"] == "front" for element in payload["elements"])


@pytest.mark.parametrize("effect", EFFECTS)
def test_all_effects_are_bounded(effect: str) -> None:
    """Every effect yields the requested bounded number of frames."""
    frames = list(effect_frames(effect, fps=4, duration=1.0, message="HI"))
    assert len(frames) == 4
    assert all(frame["priority"] == 50 for frame in frames)
    assert all(frame["application_name"] == "home_assistant" for frame in frames)
    for frame in frames:
        model = types.DisplayElements.model_validate(frame)
        assert all(
            element.x + element.width <= 72 and element.y + element.height <= 16
            for element in model.elements
            if getattr(element, "width", None) is not None
            and getattr(element, "height", None) is not None
        )


def test_unknown_effect_is_rejected() -> None:
    """Unknown effect names fail before network traffic."""
    with pytest.raises(ValueError, match="Unknown effect"):
        list(effect_frames("warp_drive", duration=0.5))
