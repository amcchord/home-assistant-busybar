"""Home Assistant actions for BUSY Bar."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
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
    SERVICE_ABORT_UPDATE,
    SERVICE_CHECK_UPDATE,
    SERVICE_CLEAR_DISPLAY,
    SERVICE_DELETE_ASSETS,
    SERVICE_DRAW,
    SERVICE_PLAY_EFFECT,
    SERVICE_PLAY_GAME,
    SERVICE_PLAY_MEDIA,
    SERVICE_PLAY_PRESET,
    SERVICE_PLAY_SOUND,
    SERVICE_SEND_KEY,
    SERVICE_SET_PROFILE,
    SERVICE_SHOW_MEDIA,
    SERVICE_SHOW_MESSAGE,
    SERVICE_SHOW_PROGRESS,
    SERVICE_SHOW_QR,
    SERVICE_SHOW_WIDGET,
    SERVICE_START_FOCUS,
    SERVICE_STOP_GAME,
    SERVICE_STOP_SOUND,
)
from .coordinator import BusyBarCoordinator
from .games import GAMES
from .media import async_convert_asset, async_qr_png, async_read_media_source
from .presets import PRESETS
from .widgets import WIDGETS, widget_payload

RGB_COLOR = vol.All(
    [vol.All(vol.Coerce(int), vol.Range(min=0, max=255))],
    vol.Length(min=3, max=4),
)
COLOR = vol.Any(vol.Match(r"^#?[0-9a-fA-F]{6}([0-9a-fA-F]{2})?$"), RGB_COLOR)
PRIORITY = vol.All(vol.Coerce(int), vol.Range(min=1, max=100))
DURATION = vol.All(vol.Coerce(int), vol.Range(min=0, max=3600))
DEVICE_IDS = vol.All(cv.ensure_list, [cv.string], vol.Length(min=1))

BASE_SCHEMA = vol.Schema({vol.Required(CONF_DEVICE_ID): DEVICE_IDS})
MESSAGE_SCHEMA = BASE_SCHEMA.extend(
    {
        vol.Required("message"): cv.string,
        vol.Optional("color", default="#FFFFFFFF"): COLOR,
        vol.Optional("background", default="#000000FF"): COLOR,
        vol.Optional("priority"): PRIORITY,
        vol.Optional("duration", default=10): DURATION,
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
        vol.Optional("duration", default=10): DURATION,
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
PRESET_SCHEMA = BASE_SCHEMA.extend(
    {
        vol.Required("preset"): vol.In(PRESETS),
        vol.Optional("message", default=""): cv.string,
        vol.Optional("priority"): PRIORITY,
        vol.Optional("duration"): vol.All(
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
WIDGET_SCHEMA = BASE_SCHEMA.extend(
    {
        vol.Required("widget"): vol.In(WIDGETS),
        vol.Optional("title", default=""): cv.string,
        vol.Optional("value", default=""): cv.string,
        vol.Optional("unit", default=""): cv.string,
        vol.Optional("timestamp"): cv.string,
        vol.Optional("values"): [vol.Coerce(float)],
        vol.Optional("progress", default=0): vol.All(
            vol.Coerce(float), vol.Range(min=0, max=100)
        ),
        vol.Optional("color", default="#22D3EEFF"): COLOR,
        vol.Optional("background", default="#000000FF"): COLOR,
        vol.Optional("display", default="front"): vol.In(("front", "back")),
        vol.Optional("priority"): PRIORITY,
        vol.Optional("duration", default=10): DURATION,
        vol.Optional("led_color"): COLOR,
        vol.Optional("restore", default=True): cv.boolean,
        vol.Optional("layer_id"): cv.string,
    }
)
SOUND_SCHEMA = vol.Any(
    BASE_SCHEMA.extend({vol.Required("path"): cv.string}),
    BASE_SCHEMA.extend({vol.Required("stock_path"): cv.string}),
)
PROFILE_SCHEMA = BASE_SCHEMA.extend(
    {
        vol.Required("slot"): vol.In(("busy", "custom")),
        vol.Required("title"): vol.All(cv.string, vol.Length(min=1, max=32)),
        vol.Required("timer_type"): vol.In(("infinite", "simple", "interval")),
        vol.Optional("minutes", default=25): vol.All(
            vol.Coerce(int), vol.Range(min=1, max=1440)
        ),
        vol.Optional("work_minutes", default=25): vol.All(
            vol.Coerce(int), vol.Range(min=1, max=1440)
        ),
        vol.Optional("rest_minutes", default=5): vol.All(
            vol.Coerce(int), vol.Range(min=1, max=1440)
        ),
        vol.Optional("cycles", default=4): vol.All(
            vol.Coerce(int), vol.Range(min=1, max=99)
        ),
        vol.Optional("autostart", default=False): cv.boolean,
        vol.Optional("theme", default="busy"): cv.string,
        vol.Optional("show_work_only", default=True): cv.boolean,
        vol.Optional("trigger_smart_home", default=True): cv.boolean,
    }
)
GAME_SCHEMA = BASE_SCHEMA.extend(
    {
        vol.Required("game"): vol.In(GAMES),
        vol.Optional("duration", default=30): vol.All(
            vol.Coerce(float), vol.Range(min=2, max=600)
        ),
        vol.Optional("fps", default=8): vol.All(
            vol.Coerce(int), vol.Range(min=2, max=12)
        ),
        vol.Optional("mood", default="happy"): vol.In(
            ("happy", "sleepy", "excited", "sad", "busy", "cool")
        ),
        vol.Optional("priority"): PRIORITY,
    }
)
SHOW_MEDIA_SCHEMA = BASE_SCHEMA.extend(
    {
        vol.Required("media_content_id"): cv.string,
        vol.Optional("display", default="front"): vol.In(("front", "back")),
        vol.Optional("duration", default=10): DURATION,
        vol.Optional("priority"): PRIORITY,
        vol.Optional("loop", default=True): cv.boolean,
        vol.Optional("opacity", default=100): vol.All(
            vol.Coerce(int), vol.Range(min=0, max=100)
        ),
    }
)
PLAY_MEDIA_SCHEMA = BASE_SCHEMA.extend({vol.Required("media_content_id"): cv.string})
QR_SCHEMA = BASE_SCHEMA.extend(
    {
        vol.Required("value"): vol.All(cv.string, vol.Length(min=1, max=256)),
        vol.Optional("duration", default=30): DURATION,
        vol.Optional("priority"): PRIORITY,
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


def _coordinators_for_call(
    hass: HomeAssistant, call: ServiceCall
) -> list[BusyBarCoordinator]:
    return [
        _coordinator_for_device(hass, device_id)
        for device_id in call.data[CONF_DEVICE_ID]
    ]


async def _for_each(
    hass: HomeAssistant,
    call: ServiceCall,
    action: Callable[[BusyBarCoordinator], Awaitable[Any]],
) -> None:
    """Run one action concurrently on every targeted Bar."""
    await asyncio.gather(
        *(action(coordinator) for coordinator in _coordinators_for_call(hass, call))
    )


def _kwargs(data: dict[str, Any], *names: str) -> dict[str, Any]:
    return {name: data[name] for name in names if name in data}


@callback
def async_setup_services(hass: HomeAssistant) -> None:
    """Register the integration's expressive actions once."""
    if hass.services.has_service(DOMAIN, SERVICE_SHOW_MESSAGE):
        return

    async def show_message(call: ServiceCall) -> None:
        await _for_each(
            hass,
            call,
            lambda coordinator: coordinator.async_show_message(
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
            ),
        )

    async def show_progress(call: ServiceCall) -> None:
        await _for_each(
            hass,
            call,
            lambda coordinator: coordinator.async_show_progress(
                call.data["value"],
                **_kwargs(
                    call.data,
                    "label",
                    "color",
                    "background",
                    "priority",
                    "duration",
                ),
            ),
        )

    async def play_effect(call: ServiceCall) -> None:
        await _for_each(
            hass,
            call,
            lambda coordinator: coordinator.async_start_effect(
                call.data["effect"],
                **_kwargs(call.data, "color", "message", "priority", "fps", "duration"),
            ),
        )

    async def play_preset(call: ServiceCall) -> None:
        await _for_each(
            hass,
            call,
            lambda coordinator: coordinator.async_play_preset(
                call.data["preset"],
                **_kwargs(call.data, "message", "priority", "duration"),
            ),
        )

    async def clear_display(call: ServiceCall) -> None:
        await _for_each(hass, call, lambda coordinator: coordinator.async_clear())

    async def start_focus(call: ServiceCall) -> None:
        await _for_each(
            hass,
            call,
            lambda coordinator: coordinator.async_start_focus(
                call.data["minutes"],
                **_kwargs(call.data, "theme", "trigger_smart_home"),
            ),
        )

    async def send_key(call: ServiceCall) -> None:
        await _for_each(
            hass,
            call,
            lambda coordinator: coordinator.async_send_key(call.data["key"]),
        )

    async def draw(call: ServiceCall) -> None:
        await _for_each(
            hass,
            call,
            lambda coordinator: coordinator.async_draw(
                call.data["payload"],
                clear_before_draw=call.data["clear_before_draw"],
            ),
        )

    async def show_widget(call: ServiceCall) -> None:
        async def draw_widget(coordinator: BusyBarCoordinator) -> None:
            payload = widget_payload(
                call.data["widget"],
                **_kwargs(
                    call.data,
                    "title",
                    "value",
                    "unit",
                    "timestamp",
                    "values",
                    "progress",
                    "color",
                    "background",
                    "display",
                    "duration",
                    "led_color",
                ),
                priority=call.data.get("priority", coordinator.default_priority),
            )
            await coordinator.async_draw(
                payload,
                duration=call.data["duration"],
                restore=call.data["restore"],
                layer_id=call.data.get("layer_id"),
            )

        await _for_each(hass, call, draw_widget)

    async def play_sound(call: ServiceCall) -> None:
        await _for_each(
            hass,
            call,
            lambda coordinator: coordinator.async_play_sound(
                path=call.data.get("path"),
                stock_path=call.data.get("stock_path"),
            ),
        )

    async def stop_sound(call: ServiceCall) -> None:
        await _for_each(hass, call, lambda coordinator: coordinator.async_stop_sound())

    async def set_profile(call: ServiceCall) -> None:
        await _for_each(
            hass,
            call,
            lambda coordinator: coordinator.async_set_profile(
                call.data["slot"],
                **_kwargs(
                    call.data,
                    "title",
                    "timer_type",
                    "minutes",
                    "work_minutes",
                    "rest_minutes",
                    "cycles",
                    "autostart",
                    "theme",
                    "show_work_only",
                    "trigger_smart_home",
                ),
            ),
        )

    async def check_update(call: ServiceCall) -> None:
        await _for_each(
            hass, call, lambda coordinator: coordinator.async_check_update()
        )

    async def abort_update(call: ServiceCall) -> None:
        await _for_each(
            hass, call, lambda coordinator: coordinator.async_abort_update()
        )

    async def play_game(call: ServiceCall) -> None:
        await _for_each(
            hass,
            call,
            lambda coordinator: coordinator.async_start_game(
                call.data["game"],
                **_kwargs(call.data, "duration", "fps", "mood", "priority"),
            ),
        )

    async def stop_game(call: ServiceCall) -> None:
        await _for_each(hass, call, lambda coordinator: coordinator.async_cancel_game())

    async def show_media(call: ServiceCall) -> None:
        filename, mime_type, data = await async_read_media_source(
            hass, call.data["media_content_id"]
        )
        if not mime_type.startswith(("image/", "video/")):
            raise ServiceValidationError("Select an image, GIF, or video")
        converted_name, converted_data = await async_convert_asset(
            hass,
            filename,
            data,
            display=call.data["display"],
        )
        media_type = (
            "animation"
            if mime_type.startswith("video/") or mime_type == "image/gif"
            else "image"
        )

        async def upload_and_show(coordinator: BusyBarCoordinator) -> None:
            await coordinator.async_upload_asset(converted_name, converted_data)
            await coordinator.async_show_asset(
                converted_name,
                media_type=media_type,
                **_kwargs(
                    call.data,
                    "display",
                    "duration",
                    "priority",
                    "loop",
                    "opacity",
                ),
            )

        await _for_each(hass, call, upload_and_show)

    async def play_media(call: ServiceCall) -> None:
        filename, mime_type, data = await async_read_media_source(
            hass, call.data["media_content_id"]
        )
        if not mime_type.startswith("audio/"):
            raise ServiceValidationError("Select an audio file")
        converted_name, converted_data = await async_convert_asset(hass, filename, data)

        async def upload_and_play(coordinator: BusyBarCoordinator) -> None:
            await coordinator.async_upload_asset(converted_name, converted_data)
            await coordinator.async_play_sound(path=converted_name)

        await _for_each(hass, call, upload_and_play)

    async def show_qr(call: ServiceCall) -> None:
        filename, data = await async_qr_png(hass, call.data["value"])

        async def upload_and_show(coordinator: BusyBarCoordinator) -> None:
            await coordinator.async_upload_asset(filename, data)
            await coordinator.async_show_asset(
                filename,
                display="back",
                duration=call.data["duration"],
                priority=call.data.get("priority"),
            )

        await _for_each(hass, call, upload_and_show)

    async def delete_assets(call: ServiceCall) -> None:
        await _for_each(
            hass, call, lambda coordinator: coordinator.async_delete_assets()
        )

    registrations = (
        (SERVICE_SHOW_MESSAGE, show_message, MESSAGE_SCHEMA),
        (SERVICE_SHOW_PROGRESS, show_progress, PROGRESS_SCHEMA),
        (SERVICE_PLAY_EFFECT, play_effect, EFFECT_SCHEMA),
        (SERVICE_PLAY_PRESET, play_preset, PRESET_SCHEMA),
        (SERVICE_CLEAR_DISPLAY, clear_display, BASE_SCHEMA),
        (SERVICE_START_FOCUS, start_focus, FOCUS_SCHEMA),
        (SERVICE_SEND_KEY, send_key, KEY_SCHEMA),
        (SERVICE_DRAW, draw, DRAW_SCHEMA),
        (SERVICE_SHOW_WIDGET, show_widget, WIDGET_SCHEMA),
        (SERVICE_PLAY_SOUND, play_sound, SOUND_SCHEMA),
        (SERVICE_STOP_SOUND, stop_sound, BASE_SCHEMA),
        (SERVICE_SET_PROFILE, set_profile, PROFILE_SCHEMA),
        (SERVICE_CHECK_UPDATE, check_update, BASE_SCHEMA),
        (SERVICE_ABORT_UPDATE, abort_update, BASE_SCHEMA),
        (SERVICE_PLAY_GAME, play_game, GAME_SCHEMA),
        (SERVICE_STOP_GAME, stop_game, BASE_SCHEMA),
        (SERVICE_SHOW_MEDIA, show_media, SHOW_MEDIA_SCHEMA),
        (SERVICE_PLAY_MEDIA, play_media, PLAY_MEDIA_SCHEMA),
        (SERVICE_SHOW_QR, show_qr, QR_SCHEMA),
        (SERVICE_DELETE_ASSETS, delete_assets, BASE_SCHEMA),
    )
    for service, handler, schema in registrations:
        hass.services.async_register(DOMAIN, service, handler, schema=schema)
