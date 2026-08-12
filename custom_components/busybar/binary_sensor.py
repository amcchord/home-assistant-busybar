"""Binary sensors for BUSY Bar."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import BusyBarConfigEntry, BusyBarCoordinator, BusyBarData
from .entity import BusyBarEntity


def _timer(data: BusyBarData):
    return data.timer.snapshot if data.timer else None


@dataclass(frozen=True, kw_only=True)
class BusyBarBinarySensorDescription(BinarySensorEntityDescription):
    """Describe a BUSY Bar binary sensor."""

    value_fn: Callable[[BusyBarData], bool | None]


BINARY_SENSORS = (
    BusyBarBinarySensorDescription(
        key="busy",
        translation_key="busy",
        icon="mdi:briefcase-clock",
        value_fn=lambda data: (
            _timer(data) is not None and _timer(data).type != "NOT_STARTED"
        ),
    ),
    BusyBarBinarySensorDescription(
        key="paused",
        translation_key="paused",
        icon="mdi:pause-circle",
        value_fn=lambda data: bool(getattr(_timer(data), "is_paused", False)),
    ),
    BusyBarBinarySensorDescription(
        key="charging",
        translation_key="charging",
        device_class=BinarySensorDeviceClass.BATTERY_CHARGING,
        value_fn=lambda data: (
            data.snapshot.power.state.value == "charging"
            if data.snapshot.power and data.snapshot.power.state
            else None
        ),
    ),
    BusyBarBinarySensorDescription(
        key="update_available",
        translation_key="update_available",
        device_class=BinarySensorDeviceClass.UPDATE,
        value_fn=lambda data: bool(data.snapshot.update_available_version),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: BusyBarConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up BUSY Bar binary sensors."""
    async_add_entities(
        BusyBarBinarySensor(entry.runtime_data, description)
        for description in BINARY_SENSORS
    )


class BusyBarBinarySensor(BusyBarEntity, BinarySensorEntity):
    """Representation of a BUSY Bar binary sensor."""

    entity_description: BusyBarBinarySensorDescription

    def __init__(
        self,
        coordinator: BusyBarCoordinator,
        description: BusyBarBinarySensorDescription,
    ) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def is_on(self) -> bool | None:
        """Return the binary state."""
        return self.entity_description.value_fn(self.coordinator.data)
