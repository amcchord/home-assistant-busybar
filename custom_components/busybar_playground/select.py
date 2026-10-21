"""Scene selector for BUSY Bar."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import SCENES
from .coordinator import BusyBarConfigEntry, BusyBarCoordinator
from .entity import BusyBarEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: BusyBarConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the status scene selector."""
    async_add_entities([BusyBarSceneSelect(entry.runtime_data)])


class BusyBarSceneSelect(BusyBarEntity, SelectEntity):
    """Apply delightful status scenes."""

    _attr_translation_key = "scene"
    _attr_icon = "mdi:palette"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_options = list(SCENES)

    def __init__(self, coordinator: BusyBarCoordinator) -> None:
        super().__init__(coordinator, "scene")

    @property
    def current_option(self) -> str:
        """Return the most recently selected scene."""
        return self.coordinator.active_scene

    async def async_select_option(self, option: str) -> None:
        """Apply a scene."""
        await self.coordinator.async_show_scene(option)
        self.async_write_ha_state()
