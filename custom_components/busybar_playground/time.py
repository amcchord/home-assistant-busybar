"""Automatic update window controls for BUSY Bar."""

from __future__ import annotations

from datetime import time

from homeassistant.components.time import TimeEntity
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
    """Set up automatic update window entities."""
    async_add_entities(
        (
            BusyBarUpdateTime(entry.runtime_data, "start"),
            BusyBarUpdateTime(entry.runtime_data, "end"),
        )
    )


class BusyBarUpdateTime(BusyBarEntity, TimeEntity):
    """Start or end of the device's automatic update window."""

    _attr_entity_category = EntityCategory.CONFIG
    _attr_icon = "mdi:clock-outline"

    def __init__(self, coordinator: BusyBarCoordinator, boundary: str) -> None:
        super().__init__(coordinator, f"update_window_{boundary}")
        self._boundary = boundary
        self._attr_translation_key = f"update_window_{boundary}"

    @property
    def native_value(self) -> time | None:
        """Return the configured boundary."""
        settings = self.coordinator.data.autoupdate
        if settings is None:
            return None
        value = (
            settings.interval_start
            if self._boundary == "start"
            else settings.interval_end
        )
        if not value:
            return None
        try:
            return time.fromisoformat(value)
        except ValueError:
            return None

    async def async_set_value(self, value: time) -> None:
        """Set this automatic update boundary."""
        field = f"interval_{self._boundary}"
        await self.coordinator._async_command(
            self.coordinator.api.update_autoupdate_set(
                {field: value.strftime("%H:%M")}
            ),
            f"set automatic update window {self._boundary}",
        )
        await self.coordinator.async_request_refresh()
