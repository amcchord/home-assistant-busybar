"""Tests for friendly front and rear display widgets."""

from datetime import UTC, datetime, timedelta

import pytest
from busylib import types

from custom_components.busybar.widgets import WIDGETS, widget_payload


@pytest.mark.parametrize("widget", WIDGETS)
@pytest.mark.parametrize("display", ["front", "back"])
def test_widget_payloads_validate(widget: str, display: str) -> None:
    """Every advertised widget produces a busylib-valid display request."""
    kwargs = {
        "title": "TEST",
        "value": "42",
        "display": display,
        "timestamp": (datetime.now(UTC) + timedelta(minutes=5)).isoformat(),
        "values": [1, 4, 2, 8, 5],
        "progress": 42,
    }
    payload = widget_payload(widget, **kwargs)
    model = types.DisplayElements.model_validate(payload)
    assert model.priority == 50
    assert all(element.display.value == display for element in model.elements)
    width = 72 if display == "front" else 160
    assert all(
        element.x + element.width <= width
        for element in model.elements
        if getattr(element, "width", None) is not None
    )


def test_widget_rejects_missing_specialized_data() -> None:
    """Countdowns and charts fail before malformed network traffic."""
    with pytest.raises(ValueError, match="timestamp"):
        widget_payload("countdown")
    with pytest.raises(ValueError, match="values"):
        widget_payload("chart")
