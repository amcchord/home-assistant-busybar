"""Tests for decoded BUSY Bar stream events."""

import base64
import gzip
import json

from busylib import types

from custom_components.busybar.stream import (
    parse_input_events,
    parse_timer_snapshot,
    timer_transition_events,
)


def test_parse_every_input_shape_including_proto_defaults() -> None:
    """Default-valued protobuf enums still map to OK, press, and Busy."""
    message = {
        "updates": [
            {"input": {"button_event": {}}},
            {"input": {"button_event": {"button": "BACK", "action": "RELEASE"}}},
            {"input": {"switch_event": {}}},
            {"input": {"encoder_event": {"delta": -2}}},
        ]
    }
    events = parse_input_events(message)
    assert [(event.category, event.source, event.event_type) for event in events] == [
        ("button", "ok", "press"),
        ("button", "back", "release"),
        ("switch", "mode_switch", "busy"),
        ("encoder", "encoder", "counterclockwise"),
    ]
    assert events[-1].data["delta"] == -2


def test_parse_gzip_timer_and_transitions() -> None:
    """Timer JSON envelopes become snapshots and stable lifecycle events."""
    payload = {
        "snapshot": {
            "type": "SIMPLE",
            "card_id": "00000000-0000-0000-0000-000000000001",
            "time_left_ms": 60_000,
            "is_paused": False,
        },
        "snapshot_timestamp_ms": 123,
    }
    encoded = base64.b64encode(gzip.compress(json.dumps(payload).encode())).decode()
    current = parse_timer_snapshot(
        {"updates": [{"timer": {"json": {"compression": "GZIP", "data": encoded}}}]}
    )
    assert current is not None
    assert current.snapshot.type == "SIMPLE"
    assert [event.event_type for event in timer_transition_events(None, current)] == [
        "started"
    ]

    paused = current.model_copy(deep=True)
    paused.snapshot.is_paused = True
    assert [event.event_type for event in timer_transition_events(current, paused)] == [
        "paused"
    ]


def test_finished_timer_transition() -> None:
    """A near-zero timer ending is distinguished from a manual stop."""
    previous = types.BusySnapshot.model_validate(
        {
            "snapshot": {
                "type": "SIMPLE",
                "card_id": "00000000-0000-0000-0000-000000000001",
                "time_left_ms": 500,
                "is_paused": False,
            },
            "snapshot_timestamp_ms": 1,
        }
    )
    current = types.BusySnapshot.model_validate(
        {
            "snapshot": {"type": "NOT_STARTED"},
            "snapshot_timestamp_ms": 2,
        }
    )
    assert [
        event.event_type for event in timer_transition_events(previous, current)
    ] == ["finished"]


def test_malformed_compressed_timer_is_ignored() -> None:
    """A corrupt WebSocket envelope cannot break the live stream."""
    encoded = base64.b64encode(b"not gzip").decode()
    message = {
        "updates": [{"timer": {"json": {"compression": "GZIP", "data": encoded}}}]
    }
    assert parse_timer_snapshot(message) is None
