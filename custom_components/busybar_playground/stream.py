"""Normalize BUSY Bar WebSocket messages into stable integration events."""

from __future__ import annotations

import base64
import gzip
import json
import zlib
from dataclasses import dataclass
from typing import Any

from busylib import types


@dataclass(frozen=True, slots=True)
class BusyBarStreamEvent:
    """A stable event emitted by a BUSY Bar."""

    category: str
    event_type: str
    source: str
    data: dict[str, Any]


def parse_input_events(message: dict[str, Any]) -> list[BusyBarStreamEvent]:
    """Extract physical input events from one decoded state message."""
    events: list[BusyBarStreamEvent] = []
    for update in _updates(message):
        input_event = update.get("input")
        if not isinstance(input_event, dict):
            continue

        button = input_event.get("button_event")
        if isinstance(button, dict):
            # OK and PRESS are protobuf enum zero-values and are omitted by
            # MessageToDict even when explicitly emitted by the device.
            name = str(button.get("button", "ok")).lower()
            action = str(button.get("action", "press")).lower()
            if name in {"ok", "back", "start"} and action in {"press", "release"}:
                events.append(
                    BusyBarStreamEvent(
                        category="button",
                        event_type=action,
                        source=name,
                        data={"button": name, "action": action},
                    )
                )

        switch = input_event.get("switch_event")
        if isinstance(switch, dict):
            # BUSY is likewise the enum zero-value.
            position = str(switch.get("position", "busy")).lower()
            if position in {"busy", "custom", "off", "apps", "settings"}:
                events.append(
                    BusyBarStreamEvent(
                        category="switch",
                        event_type=position,
                        source="mode_switch",
                        data={"position": position},
                    )
                )

        encoder = input_event.get("encoder_event")
        if isinstance(encoder, dict):
            try:
                delta = int(encoder.get("delta", 0))
            except (TypeError, ValueError):
                delta = 0
            if delta:
                direction = "clockwise" if delta > 0 else "counterclockwise"
                events.append(
                    BusyBarStreamEvent(
                        category="encoder",
                        event_type=direction,
                        source="encoder",
                        data={"direction": direction, "delta": delta},
                    )
                )
    return events


def parse_timer_snapshot(message: dict[str, Any]) -> types.BusySnapshot | None:
    """Decode a timer snapshot carried inside a state-stream JSON envelope."""
    for update in _updates(message):
        timer = update.get("timer")
        if not isinstance(timer, dict):
            continue
        payload = _decode_json_envelope(timer.get("json"))
        if not isinstance(payload, dict):
            continue
        try:
            return types.BusySnapshot.model_validate(payload)
        except ValueError:
            continue
    return None


def timer_transition_events(
    previous: types.BusySnapshot | None,
    current: types.BusySnapshot,
) -> list[BusyBarStreamEvent]:
    """Describe meaningful state transitions between timer snapshots."""
    old = previous.snapshot if previous else None
    new = current.snapshot
    old_type = getattr(old, "type", "NOT_STARTED")
    new_type = getattr(new, "type", "NOT_STARTED")
    old_active = old_type != "NOT_STARTED"
    new_active = new_type != "NOT_STARTED"
    events: list[BusyBarStreamEvent] = []

    if not old_active and new_active:
        events.append(_timer_event("started", new))
    elif old_active and not new_active:
        remaining = _remaining_ms(old)
        event_type = (
            "finished" if remaining is not None and remaining <= 1000 else "stopped"
        )
        events.append(_timer_event(event_type, new))

    if old_active and new_active:
        old_paused = bool(getattr(old, "is_paused", False))
        new_paused = bool(getattr(new, "is_paused", False))
        if old_paused != new_paused:
            events.append(_timer_event("paused" if new_paused else "resumed", new))

        old_interval = getattr(old, "current_interval", None)
        new_interval = getattr(new, "current_interval", None)
        if (
            old_interval is not None
            and new_interval is not None
            and old_interval != new_interval
        ):
            events.append(_timer_event("phase_changed", new))
    return events


def _timer_event(event_type: str, snapshot: Any) -> BusyBarStreamEvent:
    data: dict[str, Any] = {
        "timer_type": str(getattr(snapshot, "type", "NOT_STARTED")).lower(),
        "paused": bool(getattr(snapshot, "is_paused", False)),
    }
    if (remaining := _remaining_ms(snapshot)) is not None:
        data["remaining_seconds"] = max(0, round(remaining / 1000))
    if (interval := getattr(snapshot, "current_interval", None)) is not None:
        data["current_interval"] = interval
    return BusyBarStreamEvent(
        category="timer",
        event_type=event_type,
        source="timer",
        data=data,
    )


def _remaining_ms(snapshot: Any) -> int | None:
    value = getattr(snapshot, "time_left_ms", None)
    if value is None:
        value = getattr(snapshot, "current_interval_time_left_ms", None)
    return value if isinstance(value, int) else None


def _updates(message: dict[str, Any]) -> list[dict[str, Any]]:
    updates = message.get("updates")
    if not isinstance(updates, list):
        return []
    return [update for update in updates if isinstance(update, dict)]


def _decode_json_envelope(value: Any) -> Any:
    if not isinstance(value, dict):
        return None
    encoded = value.get("data")
    if not isinstance(encoded, str):
        return None
    try:
        data = base64.b64decode(encoded, validate=True)
        if value.get("compression") == "GZIP":
            data = gzip.decompress(data)
        return json.loads(data)
    except (
        ValueError,
        TypeError,
        EOFError,
        gzip.BadGzipFile,
        json.JSONDecodeError,
        zlib.error,
    ):
        return None
