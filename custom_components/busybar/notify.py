"""Notification service support for BUSY Bar."""

from __future__ import annotations

from typing import Any

from homeassistant.components.notify import (
    ATTR_DATA,
    ATTR_TITLE,
    BaseNotificationService,
    NotifyEntity,
    NotifyEntityFeature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

from .coordinator import BusyBarConfigEntry, BusyBarCoordinator
from .entity import BusyBarEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: BusyBarConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the modern notify entity."""
    async_add_entities([BusyBarNotifyEntity(entry.runtime_data)])


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


class BusyBarNotifyEntity(BusyBarEntity, NotifyEntity):
    """Send standard Home Assistant notifications to the display."""

    _attr_translation_key = "display"
    _attr_icon = "mdi:message-text-fast"
    _attr_supported_features = NotifyEntityFeature.TITLE

    def __init__(self, coordinator: BusyBarCoordinator) -> None:
        BusyBarEntity.__init__(self, coordinator, "notify")

    async def async_send_message(self, message: str, title: str | None = None) -> None:
        """Display a standard notification."""
        if title:
            message = f"{title}: {message}"
        await self.coordinator.async_show_message(message)
