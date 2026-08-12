"""Playful, dependency-free display compositions for BUSY Bar."""

from __future__ import annotations

import colorsys
import math
import random
import re
from collections.abc import Iterator
from typing import Any

from .const import APPLICATION_NAME

FRONT_WIDTH = 72
FRONT_HEIGHT = 16
_COLOR_RE = re.compile(r"^#?([0-9a-fA-F]{6})([0-9a-fA-F]{2})?$")

SCENE_STYLES: dict[str, tuple[str, str, str, str | None]] = {
    "available": ("AVAILABLE", "#052E16FF", "#4ADE80FF", "#22C55EFF"),
    "busy": ("BUSY", "#450A0AFF", "#FF4D4DFF", "#EF4444FF"),
    "do_not_disturb": ("DO NOT DISTURB", "#2E1065FF", "#C084FCFF", "#A855F7FF"),
    "on_air": ("ON AIR", "#4C0519FF", "#FB7185FF", "#F43F5EFF"),
    "meeting": ("IN A MEETING", "#082F49FF", "#38BDF8FF", "#0EA5E9FF"),
    "focus": ("FOCUS MODE", "#431407FF", "#FDBA74FF", "#F97316FF"),
    "away": ("BACK SOON", "#083344FF", "#67E8F9FF", "#06B6D4FF"),
    "celebrate": ("YAY!", "#3B0764FF", "#FDE047FF", "#F472B6FF"),
}


ColorValue = str | list[int] | tuple[int, ...]


def normalize_color(value: ColorValue, default: str = "#FFFFFFFF") -> str:
    """Return a BUSY Bar #RRGGBBAA color."""
    if isinstance(value, (list, tuple)):
        if len(value) not in (3, 4) or any(
            not isinstance(channel, int) or not 0 <= channel <= 255 for channel in value
        ):
            return default
        channels = tuple(value) if len(value) == 4 else (*value, 255)
        return "#" + "".join(f"{channel:02X}" for channel in channels)
    match = _COLOR_RE.fullmatch(value.strip())
    if not match:
        return default
    return f"#{match.group(1).upper()}{(match.group(2) or 'FF').upper()}"


def scale_color(value: ColorValue, factor: float) -> str:
    """Scale RGB channels while preserving alpha."""
    color = normalize_color(value)
    factor = max(0.0, min(1.0, factor))
    channels = [int(color[index : index + 2], 16) for index in (1, 3, 5)]
    return (
        "#"
        + "".join(f"{round(channel * factor):02X}" for channel in channels)
        + color[7:9]
    )


def _base(
    priority: int, elements: list[dict[str, Any]], led_color: str | None = None
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "application_name": APPLICATION_NAME,
        "priority": priority,
        "elements": elements,
    }
    if led_color:
        payload["led_notification_color"] = normalize_color(led_color)
    return payload


def _background(color: str) -> dict[str, Any]:
    return {
        "id": "background",
        "type": "rectangle",
        "x": 0,
        "y": 0,
        "width": FRONT_WIDTH,
        "height": FRONT_HEIGHT,
        "fill": "solid",
        "fill_colors": [normalize_color(color)],
        "border_width": 0,
        "border_color": "#00000000",
        "display": "front",
    }


def _text(
    message: str,
    color: str,
    *,
    element_id: str = "message",
    timeout: int | None = None,
    scroll: bool = True,
) -> dict[str, Any]:
    is_long = len(message) > 11
    element: dict[str, Any] = {
        "id": element_id,
        "type": "text",
        "text": message,
        "font": "normal",
        "color": normalize_color(color),
        "align": "mid_left" if is_long else "center",
        "x": 0 if is_long else FRONT_WIDTH // 2,
        "y": 3,
        "display": "front",
    }
    if timeout is not None:
        element["timeout"] = timeout
    if is_long:
        element["width"] = FRONT_WIDTH
    if scroll and is_long:
        element.update(
            {
                "scroll_rate": 45,
                "scroll_start_delay": 700,
                "scroll_repeat_delay": 1200,
            }
        )
    return element


def message_payload(
    message: str,
    *,
    color: str = "#FFFFFFFF",
    background: str = "#000000FF",
    priority: int = 50,
    duration: int = 10,
    led_color: str | None = None,
    scroll: bool = True,
) -> dict[str, Any]:
    """Compose a readable text notification."""
    background_element = _background(background)
    background_element["timeout"] = duration
    return _base(
        priority,
        [
            background_element,
            _text(message, color, timeout=duration, scroll=scroll),
        ],
        led_color,
    )


def progress_payload(
    value: float,
    *,
    label: str = "",
    color: str = "#22C55EFF",
    background: str = "#111827FF",
    priority: int = 50,
    duration: int = 10,
) -> dict[str, Any]:
    """Compose a progress bar with an optional centered label."""
    percent = max(0.0, min(100.0, float(value)))
    width = max(1, round(FRONT_WIDTH * percent / 100))
    background_element = _background(background)
    background_element["timeout"] = duration
    elements = [
        background_element,
        {
            "id": "progress",
            "type": "rectangle",
            "x": 0,
            "y": 11,
            "width": width,
            "height": 5,
            "fill": "solid",
            "fill_colors": [normalize_color(color)],
            "border_width": 0,
            "border_color": "#00000000",
            "display": "front",
            "timeout": duration,
        },
    ]
    caption = label or f"{round(percent)}%"
    elements.append(_text(caption, "#FFFFFFFF", timeout=duration, scroll=True))
    return _base(priority, elements)


def scene_payload(
    scene: str, *, priority: int = 50, duration: int = 0
) -> dict[str, Any]:
    """Compose one of the opinionated status scenes."""
    message, background, foreground, led_color = SCENE_STYLES[scene]
    if scene != "celebrate":
        return message_payload(
            message,
            color=foreground,
            background=background,
            priority=priority,
            duration=duration,
            led_color=led_color,
        )

    colors = (
        "#F43F5EFF",
        "#F59E0BFF",
        "#FDE047FF",
        "#22C55EFF",
        "#38BDF8FF",
        "#A855F7FF",
    )
    elements = [
        {
            "id": f"stripe-{index}",
            "type": "rectangle",
            "x": index * 12,
            "y": 0,
            "width": 12,
            "height": FRONT_HEIGHT,
            "fill": "solid",
            "fill_colors": [color],
            "border_width": 0,
            "border_color": "#00000000",
            "display": "front",
        }
        for index, color in enumerate(colors)
    ]
    elements.append(_text(message, "#FFFFFFFF", timeout=duration, scroll=False))
    return _base(priority, elements, led_color)


def effect_frames(
    effect: str,
    *,
    color: str = "#22D3EEFF",
    message: str = "",
    priority: int = 50,
    fps: int = 8,
    duration: float = 5.0,
) -> Iterator[dict[str, Any]]:
    """Yield deterministic animation frames suitable for repeated draw calls."""
    count = max(1, round(max(0.5, min(30.0, duration)) * max(2, min(12, fps))))
    rng = random.Random(0xB05B4A)
    base_color = normalize_color(color)

    for frame in range(count):
        elements: list[dict[str, Any]] = [_background("#000000FF")]
        if effect == "rainbow":
            for stripe in range(9):
                hue = ((stripe + frame * 0.35) / 9) % 1.0
                red, green, blue = colorsys.hsv_to_rgb(hue, 0.9, 1.0)
                stripe_color = (
                    f"#{round(red * 255):02X}{round(green * 255):02X}"
                    f"{round(blue * 255):02X}FF"
                )
                elements.append(
                    {
                        "id": f"stripe-{stripe}",
                        "type": "rectangle",
                        "x": stripe * 8,
                        "y": 0,
                        "width": 8,
                        "height": FRONT_HEIGHT,
                        "fill": "solid",
                        "fill_colors": [stripe_color],
                        "border_width": 0,
                        "border_color": "#00000000",
                        "display": "front",
                    }
                )
        elif effect == "scanner":
            position = (
                round(
                    (FRONT_WIDTH + 8)
                    * (frame % max(2, count // 2))
                    / max(1, count // 2 - 1)
                )
                - 4
            )
            for offset, strength in (
                (-4, 0.2),
                (-2, 0.5),
                (0, 1.0),
                (2, 0.5),
                (4, 0.2),
            ):
                x = position + offset
                if 0 <= x < FRONT_WIDTH:
                    elements.append(
                        {
                            "id": f"beam-{offset}",
                            "type": "rectangle",
                            "x": x,
                            "y": 0,
                            "width": 2,
                            "height": FRONT_HEIGHT,
                            "fill": "solid",
                            "fill_colors": [scale_color(base_color, strength)],
                            "border_width": 0,
                            "border_color": "#00000000",
                            "display": "front",
                        }
                    )
        elif effect == "confetti":
            palette = (base_color, "#F43F5EFF", "#FDE047FF", "#4ADE80FF", "#A78BFAFF")
            for dot in range(18):
                elements.append(
                    {
                        "id": f"confetti-{dot}",
                        "type": "rectangle",
                        "x": rng.randrange(0, FRONT_WIDTH - 1),
                        "y": rng.randrange(0, FRONT_HEIGHT - 1),
                        "width": 2,
                        "height": 2,
                        "fill": "solid",
                        "fill_colors": [rng.choice(palette)],
                        "border_width": 0,
                        "border_color": "#00000000",
                        "display": "front",
                    }
                )
        elif effect == "breathe":
            strength = 0.12 + 0.88 * (
                (math.sin(frame / max(1, count - 1) * math.tau - math.pi / 2) + 1) / 2
            )
            elements = [_background(scale_color(base_color, strength))]
        else:
            raise ValueError(f"Unknown effect: {effect}")

        if message:
            elements.append(_text(message, "#FFFFFFFF", scroll=False))
        yield _base(priority, elements, base_color)
