"""Quick-message text entity for BUSY Bar."""

from __future__ import annotations

from homeassistant.components.text import TextEntity, TextMode
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import BusyBarConfigEntry, BusyBarCoordinator
from .entity import BusyBarEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: BusyBarConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the quick-message entity."""
    async_add_entities([BusyBarMessageText(entry.runtime_data)])


class BusyBarMessageText(BusyBarEntity, TextEntity):
    """Send an instant display message by setting text."""

    _attr_translation_key = "message"
    _attr_icon = "mdi:message-badge"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_mode = TextMode.TEXT
    _attr_native_min = 1
    _attr_native_max = 128

    def __init__(self, coordinator: BusyBarCoordinator) -> None:
        super().__init__(coordinator, "message")

    @property
    def native_value(self) -> str | None:
        """Return the most recently sent message."""
        return self.coordinator.last_message or None

    async def async_set_value(self, value: str) -> None:
        """Show the message."""
        await self.coordinator.async_show_message(value)
        self.async_write_ha_state()
