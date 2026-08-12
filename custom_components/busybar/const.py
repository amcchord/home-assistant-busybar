"""Constants for the BUSY Bar integration."""

import logging
from datetime import timedelta
from typing import Final

from homeassistant.const import Platform

DOMAIN: Final = "busybar"
NAME: Final = "BUSY Bar"
MANUFACTURER: Final = "BUSY"
APPLICATION_NAME: Final = "home_assistant"

CONF_TOKEN: Final = "token"
CONF_SCAN_INTERVAL: Final = "scan_interval"
CONF_DEFAULT_PRIORITY: Final = "default_priority"

DEFAULT_SCAN_INTERVAL: Final = 15
DEFAULT_PRIORITY: Final = 50
MIN_SCAN_INTERVAL: Final = 5
MAX_SCAN_INTERVAL: Final = 300

UPDATE_INTERVAL: Final = timedelta(seconds=DEFAULT_SCAN_INTERVAL)

PLATFORMS: Final = (
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.SENSOR,
    Platform.TEXT,
)

LOGGER = logging.getLogger(__package__)

SERVICE_SHOW_MESSAGE: Final = "show_message"
SERVICE_SHOW_PROGRESS: Final = "show_progress"
SERVICE_PLAY_EFFECT: Final = "play_effect"
SERVICE_CLEAR_DISPLAY: Final = "clear_display"
SERVICE_START_FOCUS: Final = "start_focus"
SERVICE_SEND_KEY: Final = "send_key"
SERVICE_DRAW: Final = "draw"

EFFECTS: Final = ("rainbow", "scanner", "confetti", "breathe")
SCENES: Final = (
    "available",
    "busy",
    "do_not_disturb",
    "on_air",
    "meeting",
    "focus",
    "away",
    "celebrate",
)
