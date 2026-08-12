"""Reusable, display-aware BUSY Bar widgets."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from busylib import display as busy_display

from .const import APPLICATION_NAME
from .effects import normalize_color

WIDGETS = (
    "message",
    "entity",
    "weather",
    "calendar",
    "countdown",
    "clock",
    "progress",
    "chart",
    "alert",
    "streak",
    "scoreboard",
)


def widget_payload(
    widget: str,
    *,
    title: str = "",
    value: str = "",
    unit: str = "",
    timestamp: str | datetime | None = None,
    values: list[float] | None = None,
    progress: float = 0,
    color: str = "#22D3EEFF",
    background: str = "#000000FF",
    display: str = "front",
    priority: int = 50,
    duration: int = 10,
    led_color: str | None = None,
) -> dict[str, Any]:
    """Compose one friendly widget using native display elements."""
    if widget not in WIDGETS:
        raise ValueError(f"Unsupported widget: {widget}")
    spec = busy_display.get_display_spec(display)
    foreground = normalize_color(color)
    background_color = normalize_color(background)
    elements: list[dict[str, Any]] = [
        _rectangle(
            "background",
            0,
            0,
            spec.width,
            spec.height,
            background_color,
            display,
            duration,
        )
    ]

    if widget == "message":
        elements.append(
            _text(
                "message",
                value or title,
                foreground,
                display,
                spec.width // 2,
                _center_y(display),
                "center",
                duration,
                width=spec.width,
            )
        )
    elif widget in {"entity", "weather", "calendar", "clock"}:
        caption = value + (f" {unit}" if unit else "")
        if display == "front":
            if title:
                elements.append(
                    _text(
                        "title",
                        title.upper(),
                        foreground,
                        display,
                        0,
                        0,
                        "top_left",
                        duration,
                        font="tiny",
                        width=spec.width,
                    )
                )
            elements.append(
                _text(
                    "value",
                    caption,
                    "#FFFFFFFF",
                    display,
                    spec.width // 2,
                    6 if title else 3,
                    "center",
                    duration,
                    width=spec.width,
                )
            )
        else:
            elements.extend(
                (
                    _text(
                        "title",
                        title,
                        foreground,
                        display,
                        spec.width // 2,
                        12,
                        "top_mid",
                        duration,
                        width=spec.width,
                    ),
                    _text(
                        "value",
                        caption,
                        "#FFFFFFFF",
                        display,
                        spec.width // 2,
                        42,
                        "center",
                        duration,
                        font="large",
                        width=spec.width,
                    ),
                )
            )
    elif widget == "countdown":
        if timestamp is None:
            raise ValueError("Countdown widget requires timestamp")
        timestamp_value = (
            timestamp.isoformat() if isinstance(timestamp, datetime) else timestamp
        )
        elements.append(
            {
                "id": "countdown",
                "type": "countdown",
                "timestamp": timestamp_value,
                "direction": "time_left",
                "show_hours": "when_non_zero",
                "color": foreground,
                "x": spec.width // 2,
                "y": _center_y(display),
                "align": "center",
                "display": display,
                "timeout": duration,
            }
        )
        if title:
            elements.append(
                _text(
                    "title",
                    title,
                    "#FFFFFFFF",
                    display,
                    0,
                    0,
                    "top_left",
                    duration,
                    font="tiny" if display == "front" else "normal",
                    width=spec.width,
                )
            )
    elif widget == "progress":
        percent = max(0.0, min(100.0, progress))
        bar_height = 5 if display == "front" else 16
        elements.append(
            _rectangle(
                "progress",
                0,
                spec.height - bar_height,
                max(1, round(spec.width * percent / 100)),
                bar_height,
                foreground,
                display,
                duration,
            )
        )
        elements.append(
            _text(
                "value",
                value or f"{round(percent)}%",
                "#FFFFFFFF",
                display,
                spec.width // 2,
                _center_y(display, offset=-2),
                "center",
                duration,
                width=spec.width,
            )
        )
    elif widget == "chart":
        points = values or []
        if not points:
            raise ValueError("Chart widget requires values")
        low, high = min(points), max(points)
        span = high - low or 1
        width = max(1, spec.width // len(points))
        usable_height = spec.height - (5 if title and display == "front" else 0)
        for index, point in enumerate(points[-spec.width :]):
            height = max(1, round((point - low) / span * (usable_height - 1)) + 1)
            elements.append(
                _rectangle(
                    f"bar-{index}",
                    index * width,
                    spec.height - height,
                    width,
                    height,
                    foreground,
                    display,
                    duration,
                )
            )
        if title:
            elements.append(
                _text(
                    "title",
                    title,
                    "#FFFFFFFF",
                    display,
                    0,
                    0,
                    "top_left",
                    duration,
                    font="tiny",
                    width=spec.width,
                )
            )
    elif widget == "alert":
        elements.append(
            {
                **_rectangle(
                    "border",
                    0,
                    0,
                    spec.width,
                    spec.height,
                    "#00000000",
                    display,
                    duration,
                ),
                "fill": "none",
                "border_width": 2,
                "border_color": foreground,
            }
        )
        elements.append(
            _text(
                "alert",
                value or title,
                foreground,
                display,
                spec.width // 2,
                _center_y(display),
                "center",
                duration,
                width=spec.width - 4,
            )
        )
    elif widget == "streak":
        streak_value = value + (f" {unit}" if unit else "")
        elements.append(
            _rectangle(
                "streak-accent",
                0,
                spec.height - (3 if display == "front" else 10),
                spec.width,
                3 if display == "front" else 10,
                foreground,
                display,
                duration,
            )
        )
        elements.append(
            _text(
                "streak-value",
                streak_value or "1 DAY",
                "#FFFFFFFF",
                display,
                spec.width // 2,
                _center_y(display, offset=3 if display == "front" else -8),
                "center",
                duration,
                font="normal" if display == "front" else "large",
                width=spec.width,
            )
        )
        if title:
            elements.append(
                _text(
                    "streak-title",
                    title,
                    foreground,
                    display,
                    0,
                    0,
                    "top_left",
                    duration,
                    font="tiny" if display == "front" else "normal",
                    width=spec.width,
                )
            )
    elif widget == "scoreboard":
        elements.append(
            _text(
                "score-title",
                title or "SCOREBOARD",
                foreground,
                display,
                0,
                0,
                "top_left",
                duration,
                font="tiny" if display == "front" else "normal",
                width=spec.width,
            )
        )
        elements.append(
            _text(
                "scores",
                value,
                "#FFFFFFFF",
                display,
                0 if display == "front" else spec.width // 2,
                7 if display == "front" else 42,
                "mid_left" if display == "front" else "center",
                duration,
                font="tiny" if display == "front" else "large",
                width=spec.width,
            )
        )

    payload: dict[str, Any] = {
        "application_name": APPLICATION_NAME,
        "priority": priority,
        "elements": elements,
    }
    if led_color:
        payload["led_notification_color"] = normalize_color(led_color)
    return payload


def _center_y(display: str, *, offset: int = 0) -> int:
    return (3 if display == "front" else 34) + offset


def _rectangle(
    element_id: str,
    x: int,
    y: int,
    width: int,
    height: int,
    color: str,
    display: str,
    timeout: int,
) -> dict[str, Any]:
    return {
        "id": element_id,
        "type": "rectangle",
        "x": x,
        "y": y,
        "width": width,
        "height": height,
        "fill": "solid",
        "fill_colors": [normalize_color(color)],
        "border_width": 0,
        "border_color": "#00000000",
        "display": display,
        "timeout": timeout,
    }


def _text(
    element_id: str,
    text: str,
    color: str,
    display: str,
    x: int,
    y: int,
    align: str,
    timeout: int,
    *,
    font: str = "normal",
    width: int | None = None,
) -> dict[str, Any]:
    spec = busy_display.get_display_spec(display)
    is_long = len(text) > (11 if display == "front" else 25)
    if is_long and align in {"center", "top_mid"}:
        x = 0
        align = "mid_left" if align == "center" else "top_left"
        width = spec.width
    element: dict[str, Any] = {
        "id": element_id,
        "type": "text",
        "text": text,
        "font": font,
        "color": normalize_color(color),
        "x": x,
        "y": y,
        "align": align,
        "display": display,
        "timeout": timeout,
    }
    if width and x + width <= spec.width:
        element["width"] = width
    if is_long:
        element.update(
            {
                "scroll_rate": 45,
                "scroll_start_delay": 700,
                "scroll_repeat_delay": 1200,
            }
        )
    return element
