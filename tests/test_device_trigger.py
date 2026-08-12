"""Tests for BUSY Bar device automation trigger mappings."""

import pytest

from custom_components.busybar.device_trigger import TRIGGER_TYPES, _event_match


def test_all_physical_and_timer_triggers_are_advertised() -> None:
    """The visual editor gets the complete local input surface."""
    assert len(TRIGGER_TYPES) == 19
    assert {
        "ok_press",
        "back_release",
        "encoder_clockwise",
        "switch_custom",
        "timer_finished",
    } <= TRIGGER_TYPES


@pytest.mark.parametrize(
    ("trigger_type", "expected"),
    [
        (
            "ok_press",
            {"category": "button", "source": "ok", "type": "press"},
        ),
        (
            "encoder_counterclockwise",
            {
                "category": "encoder",
                "source": "encoder",
                "type": "counterclockwise",
            },
        ),
        (
            "switch_settings",
            {"category": "switch", "source": "mode_switch", "type": "settings"},
        ),
        (
            "timer_phase_changed",
            {"category": "timer", "source": "timer", "type": "phase_changed"},
        ),
    ],
)
def test_trigger_type_maps_to_stable_event_data(
    trigger_type: str, expected: dict[str, str]
) -> None:
    """Device automations match the normalized event-bus contract."""
    assert _event_match(trigger_type) == expected
