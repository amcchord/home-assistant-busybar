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


def _rect(
    element_id: str,
    x: int,
    y: int,
    width: int,
    height: int,
    color: str,
) -> dict[str, Any]:
    """Create a borderless front-display rectangle."""
    x = max(0, min(FRONT_WIDTH - 1, x))
    y = max(0, min(FRONT_HEIGHT - 1, y))
    width = max(1, min(width, FRONT_WIDTH - x))
    height = max(1, min(height, FRONT_HEIGHT - y))
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
        elif effect == "aurora":
            elements = [_background("#020617FF")]
            for stripe in range(12):
                wave = math.sin(frame * 0.25 + stripe * 0.7)
                hue = (0.42 + stripe * 0.025 + wave * 0.04) % 1
                red, green, blue = colorsys.hsv_to_rgb(hue, 0.8, 0.85)
                elements.append(
                    _rect(
                        f"aurora-{stripe}",
                        stripe * 6,
                        max(0, round(5 + wave * 4)),
                        6,
                        8,
                        f"#{round(red * 255):02X}{round(green * 255):02X}"
                        f"{round(blue * 255):02X}FF",
                    )
                )
        elif effect == "fireplace":
            palette = ("#7F1D1DFF", "#DC2626FF", "#F97316FF", "#FDE047FF")
            for flame in range(18):
                height = rng.randrange(3, 15)
                elements.append(
                    _rect(
                        f"flame-{flame}",
                        flame * 4,
                        FRONT_HEIGHT - height,
                        4,
                        height,
                        rng.choice(palette),
                    )
                )
        elif effect == "lava_lamp":
            for blob in range(7):
                x = round((blob * 13 + frame * (1 + blob % 3)) % (FRONT_WIDTH + 12)) - 6
                y = round(7 + math.sin(frame * 0.2 + blob) * 6)
                elements.append(
                    _rect(
                        f"lava-{blob}",
                        x,
                        max(0, y - 3),
                        8,
                        6,
                        scale_color(base_color, 0.45 + blob * 0.08),
                    )
                )
        elif effect == "ocean_waves":
            elements = [_background("#082F49FF")]
            for column in range(18):
                height = round(5 + 4 * math.sin(column * 0.7 + frame * 0.35))
                elements.append(
                    _rect(
                        f"wave-{column}",
                        column * 4,
                        FRONT_HEIGHT - height,
                        4,
                        height,
                        "#38BDF8FF" if column % 2 else "#0EA5E9FF",
                    )
                )
        elif effect in {"starfield", "sparkle", "snowfall"}:
            palette = {
                "starfield": ("#FFFFFFFF", "#93C5FDFF", "#C4B5FDFF"),
                "sparkle": (base_color, "#FFFFFFFF", "#FDE047FF"),
                "snowfall": ("#FFFFFFFF", "#BAE6FDFF", "#E0F2FEFF"),
            }[effect]
            for dot in range(22):
                speed = 1 + dot % 3
                x = (dot * 17 + (frame * speed if effect == "starfield" else dot)) % 72
                y = (
                    (dot * 7 + frame * speed) % 16
                    if effect == "snowfall"
                    else (dot * 11 + frame // speed) % 16
                )
                size = 2 if dot % 7 == 0 else 1
                elements.append(
                    _rect(f"particle-{dot}", x, y, size, size, palette[dot % 3])
                )
        elif effect == "matrix_rain":
            for column in range(12):
                head = (frame * (1 + column % 3) + column * 5) % 22 - 6
                for tail in range(4):
                    y = head - tail * 3
                    if 0 <= y < FRONT_HEIGHT:
                        elements.append(
                            _rect(
                                f"matrix-{column}-{tail}",
                                column * 6,
                                y,
                                3,
                                2,
                                scale_color("#4ADE80FF", 1 - tail * 0.22),
                            )
                        )
        elif effect == "sunrise":
            strength = min(1.0, frame / max(1, count - 1))
            elements = [_background(scale_color("#F97316FF", 0.12 + strength * 0.5))]
            sun_y = round(14 - strength * 12)
            elements.append(_rect("sun", 30, sun_y, 12, 12, "#FDE047FF"))
            elements.append(_rect("horizon", 0, 13, 72, 3, "#7C2D12FF"))
        elif effect == "equalizer":
            for bar in range(18):
                height = 2 + round(12 * (math.sin(frame * 0.55 + bar * 1.7) + 1) / 2)
                elements.append(
                    _rect(
                        f"eq-{bar}",
                        bar * 4,
                        FRONT_HEIGHT - height,
                        3,
                        height,
                        base_color,
                    )
                )
        elif effect == "fireworks":
            palette = (base_color, "#F43F5EFF", "#FDE047FF", "#4ADE80FF")
            center_x = 12 + (frame // 8 * 23) % 48
            center_y = 8
            radius = 1 + frame % 8
            for spark in range(16):
                angle = spark / 16 * math.tau
                x = round(center_x + math.cos(angle) * radius)
                y = round(center_y + math.sin(angle) * radius)
                if 0 <= x < 72 and 0 <= y < 16:
                    elements.append(
                        _rect(f"spark-{spark}", x, y, 2, 2, palette[spark % 4])
                    )
        elif effect in {"jackpot", "red_alert", "heartbeat", "thunderstorm"}:
            if effect == "jackpot":
                elements = [_background("#7F1D1DFF" if frame % 2 else "#F59E0BFF")]
                message = message or "7 7 7"
            elif effect == "red_alert":
                elements = [_background("#DC2626FF" if frame % 2 else "#450A0AFF")]
                message = message or "ALERT"
            elif effect == "heartbeat":
                phase = frame % max(4, fps)
                pulse = 1.0 if phase in (0, 2) else 0.18
                elements = [_background(scale_color("#F43F5EFF", pulse))]
                message = message or "♥"
            else:
                flash = frame % max(3, fps) == 0
                elements = [_background("#FFFFFFFF" if flash else "#1E1B4BFF")]
                for bolt in range(5):
                    elements.append(
                        _rect(
                            f"bolt-{bolt}",
                            28 + bolt * 3,
                            bolt * 3,
                            5,
                            4,
                            "#FDE047FF",
                        )
                    )
        elif effect in {"package_drop", "laundry_party", "goal"}:
            if effect == "package_drop":
                y = max(2, 14 - frame % 16)
                elements.append(_rect("box", 30, y, 12, 9, "#D97706FF"))
                elements.append(_rect("tape", 35, y, 2, 9, "#FDE68AFF"))
                message = message or "PACKAGE"
            elif effect == "laundry_party":
                palette = ("#BAE6FDFF", "#67E8F9FF", "#FFFFFFFF")
                for bubble in range(18):
                    x = (bubble * 13 + frame * (bubble % 3 + 1)) % 72
                    y = (bubble * 9 - frame * 2) % 16
                    elements.append(
                        _rect(f"bubble-{bubble}", x, y, 2, 2, palette[bubble % 3])
                    )
                message = message or "DONE!"
            else:
                palette = ("#22C55EFF", "#FDE047FF", "#FFFFFFFF")
                for dot in range(20):
                    elements.append(
                        _rect(
                            f"goal-{dot}",
                            (dot * 19 + frame * 3) % 72,
                            (dot * 7 + frame) % 16,
                            2,
                            2,
                            palette[dot % 3],
                        )
                    )
                message = message or "GOAL!"
        else:
            raise ValueError(f"Unknown effect: {effect}")

        if message:
            elements.append(_text(message, "#FFFFFFFF", scroll=False))
        yield _base(priority, elements, base_color)
