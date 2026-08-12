"""Constants for the BUSY Bar integration."""

import logging
from datetime import timedelta
from typing import Final

from homeassistant.const import Platform

DOMAIN: Final = "busybar"
NAME: Final = "BUSY Bar"
VERSION: Final = "0.2.0"
MANUFACTURER: Final = "BUSY"
APPLICATION_NAME: Final = "home_assistant"
EVENT_BUSYBAR: Final = "busybar_event"

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
    Platform.EVENT,
    Platform.IMAGE,
    Platform.MEDIA_PLAYER,
    Platform.NOTIFY,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.SENSOR,
    Platform.SWITCH,
    Platform.TEXT,
    Platform.TIME,
    Platform.UPDATE,
)

LOGGER = logging.getLogger(__package__)

SERVICE_SHOW_MESSAGE: Final = "show_message"
SERVICE_SHOW_PROGRESS: Final = "show_progress"
SERVICE_PLAY_EFFECT: Final = "play_effect"
SERVICE_PLAY_PRESET: Final = "play_preset"
SERVICE_CLEAR_DISPLAY: Final = "clear_display"
SERVICE_START_FOCUS: Final = "start_focus"
SERVICE_SEND_KEY: Final = "send_key"
SERVICE_DRAW: Final = "draw"
SERVICE_SHOW_WIDGET: Final = "show_widget"
SERVICE_PLAY_SOUND: Final = "play_sound"
SERVICE_STOP_SOUND: Final = "stop_sound"
SERVICE_SET_PROFILE: Final = "set_profile"
SERVICE_CHECK_UPDATE: Final = "check_update"
SERVICE_ABORT_UPDATE: Final = "abort_update"
SERVICE_PLAY_GAME: Final = "play_game"
SERVICE_STOP_GAME: Final = "stop_game"
SERVICE_SHOW_MEDIA: Final = "show_media"
SERVICE_PLAY_MEDIA: Final = "play_media"
SERVICE_SHOW_QR: Final = "show_qr"
SERVICE_DELETE_ASSETS: Final = "delete_assets"

EFFECTS: Final = (
    "rainbow",
    "scanner",
    "confetti",
    "breathe",
    "aurora",
    "fireplace",
    "lava_lamp",
    "ocean_waves",
    "starfield",
    "matrix_rain",
    "snowfall",
    "sunrise",
    "equalizer",
    "fireworks",
    "jackpot",
    "thunderstorm",
    "red_alert",
    "heartbeat",
    "sparkle",
    "package_drop",
    "laundry_party",
    "goal",
)
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
