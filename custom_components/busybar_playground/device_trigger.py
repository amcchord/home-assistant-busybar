"""Device automation triggers for BUSY Bar controls and timer events."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.components.device_automation import DEVICE_TRIGGER_BASE_SCHEMA
from homeassistant.components.homeassistant.triggers import event as event_trigger
from homeassistant.const import CONF_DEVICE_ID, CONF_DOMAIN, CONF_PLATFORM, CONF_TYPE
from homeassistant.core import CALLBACK_TYPE, HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.trigger import TriggerActionType, TriggerInfo
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN, EVENT_BUSYBAR

BUTTON_TRIGGERS = {
    f"{button}_{action}"
    for button in ("ok", "back", "start")
    for action in ("press", "release")
}
ENCODER_TRIGGERS = {"encoder_clockwise", "encoder_counterclockwise"}
SWITCH_TRIGGERS = {
    f"switch_{position}" for position in ("busy", "custom", "off", "apps", "settings")
}
TIMER_TRIGGERS = {
    f"timer_{event}"
    for event in (
        "started",
        "paused",
        "resumed",
        "phase_changed",
        "finished",
        "stopped",
    )
}
TRIGGER_TYPES = BUTTON_TRIGGERS | ENCODER_TRIGGERS | SWITCH_TRIGGERS | TIMER_TRIGGERS

TRIGGER_SCHEMA = DEVICE_TRIGGER_BASE_SCHEMA.extend(
    {vol.Required(CONF_TYPE): vol.In(TRIGGER_TYPES)}
)


async def async_get_triggers(
    hass: HomeAssistant, device_id: str
) -> list[dict[str, str]]:
    """List every physical and timer trigger for a configured Bar."""
    device = dr.async_get(hass).async_get(device_id)
    if device is None or not any(
        (entry := hass.config_entries.async_get_entry(entry_id))
        and entry.domain == DOMAIN
        for entry_id in device.config_entries
    ):
        return []
    return [
        {
            CONF_PLATFORM: "device",
            CONF_DOMAIN: DOMAIN,
            CONF_DEVICE_ID: device_id,
            CONF_TYPE: trigger_type,
        }
        for trigger_type in sorted(TRIGGER_TYPES)
    ]


async def async_attach_trigger(
    hass: HomeAssistant,
    config: ConfigType,
    action: TriggerActionType,
    trigger_info: TriggerInfo,
) -> CALLBACK_TYPE:
    """Attach one BUSY Bar event-bus trigger."""
    device = dr.async_get(hass).async_get(config[CONF_DEVICE_ID])
    if device is None:
        raise ValueError("BUSY Bar device no longer exists")
    entry_id = next(
        (
            entry_id
            for entry_id in device.config_entries
            if (entry := hass.config_entries.async_get_entry(entry_id))
            and entry.domain == DOMAIN
        ),
        None,
    )
    if entry_id is None:
        raise ValueError("Device is not associated with a BUSY Bar config entry")

    event_data = {"entry_id": entry_id, **_event_match(config[CONF_TYPE])}
    event_config = event_trigger.TRIGGER_SCHEMA(
        {
            event_trigger.CONF_PLATFORM: "event",
            event_trigger.CONF_EVENT_TYPE: EVENT_BUSYBAR,
            event_trigger.CONF_EVENT_DATA: event_data,
        }
    )
    return await event_trigger.async_attach_trigger(
        hass,
        event_config,
        action,
        trigger_info,
        platform_type="device",
    )


def _event_match(trigger_type: str) -> dict[str, Any]:
    if trigger_type in BUTTON_TRIGGERS:
        source, action = trigger_type.rsplit("_", 1)
        return {"category": "button", "source": source, "type": action}
    if trigger_type in ENCODER_TRIGGERS:
        return {
            "category": "encoder",
            "source": "encoder",
            "type": trigger_type.removeprefix("encoder_"),
        }
    if trigger_type in SWITCH_TRIGGERS:
        return {
            "category": "switch",
            "source": "mode_switch",
            "type": trigger_type.removeprefix("switch_"),
        }
    return {
        "category": "timer",
        "source": "timer",
        "type": trigger_type.removeprefix("timer_"),
    }
