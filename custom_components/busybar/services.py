"""Home Assistant services for BUSY Bar."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.const import CONF_DEVICE_ID
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import device_registry as dr

from .const import (
    DOMAIN,
    EFFECTS,
    SERVICE_CLEAR_DISPLAY,
    SERVICE_DRAW,
    SERVICE_PLAY_EFFECT,
    SERVICE_SEND_KEY,
    SERVICE_SHOW_MESSAGE,
    SERVICE_SHOW_PROGRESS,
    SERVICE_START_FOCUS,
)
from .coordinator import BusyBarCoordinator

RGB_COLOR = vol.All(
    [vol.All(vol.Coerce(int), vol.Range(min=0, max=255))],
    vol.Length(min=3, max=4),
)
COLOR = vol.Any(vol.Match(r"^#?[0-9a-fA-F]{6}([0-9a-fA-F]{2})?$"), RGB_COLOR)
PRIORITY = vol.All(vol.Coerce(int), vol.Range(min=1, max=100))

BASE_SCHEMA = vol.Schema({vol.Required(CONF_DEVICE_ID): cv.string})
MESSAGE_SCHEMA = BASE_SCHEMA.extend(
    {
        vol.Required("message"): cv.string,
        vol.Optional("color", default="#FFFFFFFF"): COLOR,
        vol.Optional("background", default="#000000FF"): COLOR,
        vol.Optional("priority"): PRIORITY,
        vol.Optional("duration", default=10): vol.All(
            vol.Coerce(int), vol.Range(min=0, max=3600)
        ),
        vol.Optional("led_color"): COLOR,
        vol.Optional("scroll", default=True): cv.boolean,
    }
)
PROGRESS_SCHEMA = BASE_SCHEMA.extend(
    {
        vol.Required("value"): vol.All(vol.Coerce(float), vol.Range(min=0, max=100)),
        vol.Optional("label", default=""): cv.string,
        vol.Optional("color", default="#22C55EFF"): COLOR,
        vol.Optional("background", default="#111827FF"): COLOR,
        vol.Optional("priority"): PRIORITY,
        vol.Optional("duration", default=10): vol.All(
            vol.Coerce(int), vol.Range(min=0, max=3600)
        ),
    }
)
EFFECT_SCHEMA = BASE_SCHEMA.extend(
    {
        vol.Required("effect"): vol.In(EFFECTS),
        vol.Optional("color", default="#22D3EEFF"): COLOR,
        vol.Optional("message", default=""): cv.string,
        vol.Optional("priority"): PRIORITY,
        vol.Optional("fps", default=8): vol.All(
            vol.Coerce(int), vol.Range(min=2, max=12)
        ),
        vol.Optional("duration", default=5): vol.All(
            vol.Coerce(float), vol.Range(min=0.5, max=30)
        ),
    }
)
FOCUS_SCHEMA = BASE_SCHEMA.extend(
    {
        vol.Required("minutes", default=25): vol.All(
            vol.Coerce(int), vol.Range(min=1, max=1440)
        ),
        vol.Optional("theme", default="on_air"): cv.string,
        vol.Optional("trigger_smart_home", default=True): cv.boolean,
    }
)
KEY_SCHEMA = BASE_SCHEMA.extend(
    {
        vol.Required("key"): vol.In(
            (
                "up",
                "down",
                "ok",
                "back",
                "start",
                "busy",
                "custom",
                "off",
                "apps",
                "settings",
            )
        )
    }
)
DRAW_SCHEMA = BASE_SCHEMA.extend(
    {
        vol.Required("payload"): dict,
        vol.Optional("clear_before_draw", default=False): cv.boolean,
    }
)


def _coordinator_for_device(hass: HomeAssistant, device_id: str) -> BusyBarCoordinator:
    """Resolve a BUSY Bar coordinator from a device target."""
    device = dr.async_get(hass).async_get(device_id)
    if device is None:
        raise ServiceValidationError("The selected BUSY Bar device no longer exists")
    for entry_id in device.config_entries:
        entry = hass.config_entries.async_get_entry(entry_id)
        if entry is not None and entry.domain == DOMAIN:
            return entry.runtime_data
    raise ServiceValidationError("The selected device is not a BUSY Bar")


def _kwargs(data: dict[str, Any], *names: str) -> dict[str, Any]:
    return {name: data[name] for name in names if name in data}


@callback
def async_setup_services(hass: HomeAssistant) -> None:
    """Register the integration's expressive display services once."""
    if hass.services.has_service(DOMAIN, SERVICE_SHOW_MESSAGE):
        return

    async def show_message(call: ServiceCall) -> None:
        coordinator = _coordinator_for_device(hass, call.data[CONF_DEVICE_ID])
        await coordinator.async_show_message(
            call.data["message"],
            **_kwargs(
                call.data,
                "color",
                "background",
                "priority",
                "duration",
                "led_color",
                "scroll",
            ),
        )

    async def show_progress(call: ServiceCall) -> None:
        coordinator = _coordinator_for_device(hass, call.data[CONF_DEVICE_ID])
        await coordinator.async_show_progress(
            call.data["value"],
            **_kwargs(
                call.data, "label", "color", "background", "priority", "duration"
            ),
        )

    async def play_effect(call: ServiceCall) -> None:
        coordinator = _coordinator_for_device(hass, call.data[CONF_DEVICE_ID])
        await coordinator.async_start_effect(
            call.data["effect"],
            **_kwargs(call.data, "color", "message", "priority", "fps", "duration"),
        )

    async def clear_display(call: ServiceCall) -> None:
        await _coordinator_for_device(hass, call.data[CONF_DEVICE_ID]).async_clear()

    async def start_focus(call: ServiceCall) -> None:
        coordinator = _coordinator_for_device(hass, call.data[CONF_DEVICE_ID])
        await coordinator.async_start_focus(
            call.data["minutes"],
            **_kwargs(call.data, "theme", "trigger_smart_home"),
        )

    async def send_key(call: ServiceCall) -> None:
        await _coordinator_for_device(hass, call.data[CONF_DEVICE_ID]).async_send_key(
            call.data["key"]
        )

    async def draw(call: ServiceCall) -> None:
        await _coordinator_for_device(hass, call.data[CONF_DEVICE_ID]).async_draw(
            call.data["payload"], clear_before_draw=call.data["clear_before_draw"]
        )

    registrations = (
        (SERVICE_SHOW_MESSAGE, show_message, MESSAGE_SCHEMA),
        (SERVICE_SHOW_PROGRESS, show_progress, PROGRESS_SCHEMA),
        (SERVICE_PLAY_EFFECT, play_effect, EFFECT_SCHEMA),
        (SERVICE_CLEAR_DISPLAY, clear_display, BASE_SCHEMA),
        (SERVICE_START_FOCUS, start_focus, FOCUS_SCHEMA),
        (SERVICE_SEND_KEY, send_key, KEY_SCHEMA),
        (SERVICE_DRAW, draw, DRAW_SCHEMA),
    )
    for service, handler, schema in registrations:
        hass.services.async_register(DOMAIN, service, handler, schema=schema)
