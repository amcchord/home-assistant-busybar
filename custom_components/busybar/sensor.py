"""Sensors for BUSY Bar."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from busylib import types
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    PERCENTAGE,
    SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
    EntityCategory,
    UnitOfInformation,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import BusyBarConfigEntry, BusyBarData
from .entity import BusyBarEntity


def _timer_variant(data: BusyBarData) -> Any | None:
    return data.timer.snapshot if data.timer else None


def _timer_remaining(data: BusyBarData) -> int | None:
    timer = _timer_variant(data)
    if timer is None:
        return None
    milliseconds = getattr(timer, "time_left_ms", None)
    if milliseconds is None:
        milliseconds = getattr(timer, "current_interval_time_left_ms", None)
    return round(milliseconds / 1000) if isinstance(milliseconds, int) else None


@dataclass(frozen=True, kw_only=True)
class BusyBarSensorDescription(SensorEntityDescription):
    """Describe a BUSY Bar sensor."""

    value_fn: Callable[[BusyBarData], Any]
    attributes_fn: Callable[[BusyBarData], dict[str, Any] | None] | None = None


def _profile_attributes(data: BusyBarData, slot: str) -> dict[str, Any] | None:
    profile = data.profiles.get(slot)
    if profile is None:
        return None
    timer = profile.timer_settings
    attributes: dict[str, Any] = {
        "timer_type": timer.type.lower(),
        "theme": profile.busy_bar_settings.theme,
        "show_work_only": profile.busy_bar_settings.show_work_phase_only,
        "trigger_smart_home": profile.busy_bar_settings.trigger_smart_home,
    }
    if isinstance(timer, types.BusyTimerSimpleSettings):
        attributes["minutes"] = round(timer.total_time_ms / 60_000)
    elif isinstance(timer, types.BusySnapshotIntervalSettings):
        attributes.update(
            {
                "work_minutes": round(timer.interval_work_ms / 60_000),
                "rest_minutes": round(timer.interval_rest_ms / 60_000),
                "cycles": timer.interval_work_cycles_count,
                "autostart": timer.is_autostart_enabled,
            }
        )
    return attributes


SENSORS: tuple[BusyBarSensorDescription, ...] = (
    BusyBarSensorDescription(
        key="battery",
        translation_key="battery",
        device_class=SensorDeviceClass.BATTERY,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: (
            data.snapshot.power.battery_charge if data.snapshot.power else None
        ),
    ),
    BusyBarSensorDescription(
        key="wifi_signal",
        translation_key="wifi_signal",
        device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.snapshot.wifi.rssi if data.snapshot.wifi else None,
    ),
    BusyBarSensorDescription(
        key="power_state",
        translation_key="power_state",
        device_class=SensorDeviceClass.ENUM,
        options=("discharging", "charging", "charged"),
        value_fn=lambda data: (
            data.snapshot.power.state.value
            if data.snapshot.power and data.snapshot.power.state
            else None
        ),
    ),
    BusyBarSensorDescription(
        key="timer_state",
        translation_key="timer_state",
        device_class=SensorDeviceClass.ENUM,
        options=("not_started", "infinite", "simple", "interval"),
        value_fn=lambda data: (
            _timer_variant(data).type.lower() if _timer_variant(data) else None
        ),
    ),
    BusyBarSensorDescription(
        key="time_remaining",
        translation_key="time_remaining",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        value_fn=_timer_remaining,
    ),
    BusyBarSensorDescription(
        key="current_interval",
        translation_key="current_interval",
        icon="mdi:counter",
        value_fn=lambda data: getattr(_timer_variant(data), "current_interval", None),
    ),
    BusyBarSensorDescription(
        key="firmware_version",
        translation_key="firmware_version",
        icon="mdi:chip",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: (
            data.snapshot.status.firmware.version
            if data.snapshot.status and data.snapshot.status.firmware
            else None
        ),
    ),
    BusyBarSensorDescription(
        key="api_version",
        translation_key="api_version",
        icon="mdi:api",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: (
            data.snapshot.system.api_semver if data.snapshot.system else None
        ),
    ),
    BusyBarSensorDescription(
        key="uptime",
        translation_key="uptime",
        icon="mdi:timer-outline",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: (
            data.snapshot.system.uptime if data.snapshot.system else None
        ),
    ),
    BusyBarSensorDescription(
        key="storage_free",
        translation_key="storage_free",
        device_class=SensorDeviceClass.DATA_SIZE,
        native_unit_of_measurement=UnitOfInformation.BYTES,
        suggested_display_precision=1,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: (
            data.snapshot.storage.free if data.snapshot.storage else None
        ),
    ),
    BusyBarSensorDescription(
        key="busy_profile",
        translation_key="busy_profile",
        icon="mdi:briefcase-clock",
        value_fn=lambda data: (
            data.profiles["busy"].title if "busy" in data.profiles else None
        ),
        attributes_fn=lambda data: _profile_attributes(data, "busy"),
    ),
    BusyBarSensorDescription(
        key="custom_profile",
        translation_key="custom_profile",
        icon="mdi:timer-cog-outline",
        value_fn=lambda data: (
            data.profiles["custom"].title if "custom" in data.profiles else None
        ),
        attributes_fn=lambda data: _profile_attributes(data, "custom"),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: BusyBarConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up BUSY Bar sensors."""
    async_add_entities(
        BusyBarSensor(entry.runtime_data, description) for description in SENSORS
    )


class BusyBarSensor(BusyBarEntity, SensorEntity):
    """Representation of a BUSY Bar sensor."""

    entity_description: BusyBarSensorDescription

    def __init__(self, coordinator: Any, description: BusyBarSensorDescription) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> Any:
        """Return the sensor value."""
        return self.entity_description.value_fn(self.coordinator.data)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return compact profile details when applicable."""
        if self.entity_description.attributes_fn is None:
            return None
        return self.entity_description.attributes_fn(self.coordinator.data)
