"""Number controls for BUSY Bar."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.number import (
    NumberEntity,
    NumberEntityDescription,
    NumberMode,
)
from homeassistant.const import PERCENTAGE, EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import BusyBarConfigEntry, BusyBarCoordinator
from .entity import BusyBarEntity


def _brightness(coordinator: BusyBarCoordinator) -> float | None:
    info = coordinator.data.snapshot.brightness
    if info is None:
        return None
    for candidate in (info.value, info.front):
        if candidate is not None and str(candidate).isdigit():
            return float(candidate)
    return None


@dataclass(frozen=True, kw_only=True)
class BusyBarNumberDescription(NumberEntityDescription):
    """Describe a BUSY Bar number."""

    value_fn: Callable[[BusyBarCoordinator], float | None]
    set_fn: Callable[[BusyBarCoordinator, float], Awaitable[Any]]


NUMBERS = (
    BusyBarNumberDescription(
        key="brightness",
        translation_key="brightness",
        icon="mdi:brightness-6",
        entity_category=EntityCategory.CONFIG,
        native_min_value=0,
        native_max_value=100,
        native_step=1,
        native_unit_of_measurement=PERCENTAGE,
        mode=NumberMode.SLIDER,
        value_fn=_brightness,
        set_fn=lambda coordinator, value: coordinator.api.display_brightness_set(
            round(value)
        ),
    ),
    BusyBarNumberDescription(
        key="volume",
        translation_key="volume",
        icon="mdi:volume-high",
        entity_category=EntityCategory.CONFIG,
        native_min_value=0,
        native_max_value=100,
        native_step=1,
        native_unit_of_measurement=PERCENTAGE,
        mode=NumberMode.SLIDER,
        value_fn=lambda coordinator: (
            coordinator.data.snapshot.volume.volume
            if coordinator.data.snapshot.volume
            else None
        ),
        set_fn=lambda coordinator, value: coordinator.api.audio_volume_set(value),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: BusyBarConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up BUSY Bar number controls."""
    async_add_entities(
        BusyBarNumber(entry.runtime_data, description) for description in NUMBERS
    )


class BusyBarNumber(BusyBarEntity, NumberEntity):
    """Representation of a BUSY Bar number control."""

    entity_description: BusyBarNumberDescription

    def __init__(
        self, coordinator: BusyBarCoordinator, description: BusyBarNumberDescription
    ) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> float | None:
        """Return the current value."""
        return self.entity_description.value_fn(self.coordinator)

    async def async_set_native_value(self, value: float) -> None:
        """Set the value."""
        await self.coordinator._async_command(
            self.entity_description.set_fn(self.coordinator, value),
            f"set {self.entity_description.key}",
        )
        await self.coordinator.async_request_refresh()
