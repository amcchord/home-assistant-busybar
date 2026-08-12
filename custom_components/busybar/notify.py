"""Notification service support for BUSY Bar."""

from __future__ import annotations

from typing import Any

from homeassistant.components.notify import (
    ATTR_DATA,
    ATTR_TITLE,
    BaseNotificationService,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

from .coordinator import BusyBarConfigEntry, BusyBarCoordinator


async def async_get_service(
    hass: HomeAssistant,
    config: ConfigType,
    discovery_info: DiscoveryInfoType | None = None,
) -> BusyBarNotificationService | None:
    """Create a per-device notify service."""
    if discovery_info is None:
        return None
    entry: BusyBarConfigEntry | None = hass.config_entries.async_get_entry(
        discovery_info["entry_id"]
    )
    if entry is None:
        return None
    return BusyBarNotificationService(entry.runtime_data)


class BusyBarNotificationService(BaseNotificationService):
    """Display Home Assistant notifications on a BUSY Bar."""

    def __init__(self, coordinator: BusyBarCoordinator) -> None:
        self.coordinator = coordinator

    async def async_send_message(self, message: str = "", **kwargs: Any) -> None:
        """Send a notification."""
        data = dict(kwargs.get(ATTR_DATA) or {})
        title = kwargs.get(ATTR_TITLE)
        if title:
            message = f"{title}: {message}"
        allowed = {
            key: data[key]
            for key in (
                "color",
                "background",
                "priority",
                "duration",
                "led_color",
                "scroll",
            )
            if key in data
        }
        await self.coordinator.async_show_message(message, **allowed)
