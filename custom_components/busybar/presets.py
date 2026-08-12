"""Opinionated, playful household shortcuts for BUSY Bar."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class BusyBarPreset:
    """A ready-to-play display moment."""

    effect: str
    message: str
    color: str
    duration: float = 8
    priority: int = 60


PRESET_SPECS: dict[str, BusyBarPreset] = {
    "someone_is_here": BusyBarPreset(
        "red_alert", "SOMEONE'S HERE", "#F43F5EFF", 10, 90
    ),
    "package_delivered": BusyBarPreset("package_drop", "PACKAGE!", "#F59E0BFF", 9, 65),
    "laundry_done": BusyBarPreset("laundry_party", "LAUNDRY DONE", "#22D3EEFF", 10, 65),
    "dinner_ready": BusyBarPreset("sparkle", "DINNER!", "#FDE047FF", 10, 70),
    "meeting_soon": BusyBarPreset("scanner", "MEETING SOON", "#38BDF8FF", 8, 60),
    "weather_warning": BusyBarPreset(
        "thunderstorm", "WEATHER ALERT", "#A78BFAFF", 12, 90
    ),
    "air_quality_warning": BusyBarPreset("breathe", "AIR QUALITY", "#FB7185FF", 12, 80),
    "alarm": BusyBarPreset("red_alert", "ALARM", "#EF4444FF", 15, 100),
    "welcome_home": BusyBarPreset("aurora", "WELCOME HOME", "#4ADE80FF", 10, 55),
    "bedtime": BusyBarPreset("starfield", "GOOD NIGHT", "#818CF8FF", 12, 45),
    "chore_complete": BusyBarPreset("confetti", "NICE WORK!", "#F472B6FF", 8, 55),
    "focus_break": BusyBarPreset("ocean_waves", "TAKE A BREAK", "#22D3EEFF", 10, 50),
    "goal_scored": BusyBarPreset("goal", "GOAL!", "#4ADE80FF", 10, 80),
    "print_complete": BusyBarPreset("fireworks", "PRINT DONE", "#C084FCFF", 10, 60),
    "celebration": BusyBarPreset("fireworks", "HOORAY!", "#FDE047FF", 10, 60),
}

PRESETS = tuple(PRESET_SPECS)


def preset_spec(name: str, *, message: str = "") -> BusyBarPreset:
    """Return a preset, optionally replacing its friendly default message."""
    try:
        preset = PRESET_SPECS[name]
    except KeyError as err:
        raise ValueError(f"Unknown preset: {name}") from err
    if not message:
        return preset
    return BusyBarPreset(
        effect=preset.effect,
        message=message,
        color=preset.color,
        duration=preset.duration,
        priority=preset.priority,
    )
