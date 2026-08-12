"""Configuration switches for BUSY Bar."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import BusyBarConfigEntry, BusyBarCoordinator
from .entity import BusyBarEntity


@dataclass(frozen=True, kw_only=True)
class BusyBarSwitchDescription(SwitchEntityDescription):
    """Describe a BUSY Bar setting switch."""

    value_fn: Callable[[BusyBarCoordinator], bool | None]
    turn_on_fn: Callable[[BusyBarCoordinator], Awaitable[object]]
    turn_off_fn: Callable[[BusyBarCoordinator], Awaitable[object]]


SWITCHES = (
    BusyBarSwitchDescription(
        key="automatic_brightness",
        translation_key="automatic_brightness",
        icon="mdi:brightness-auto",
        entity_category=EntityCategory.CONFIG,
        value_fn=lambda coordinator: bool(
            coordinator.data.snapshot.brightness
            and coordinator.data.snapshot.brightness.value == "auto"
        ),
        turn_on_fn=lambda coordinator: coordinator.api.display_brightness_set("auto"),
        turn_off_fn=lambda coordinator: coordinator.api.display_brightness_set(50),
    ),
    BusyBarSwitchDescription(
        key="automatic_updates",
        translation_key="automatic_updates",
        icon="mdi:update",
        entity_category=EntityCategory.CONFIG,
        value_fn=lambda coordinator: (
            coordinator.data.autoupdate.is_enabled
            if coordinator.data.autoupdate
            else None
        ),
        turn_on_fn=lambda coordinator: coordinator.api.update_autoupdate_set(
            {"is_enabled": True}
        ),
        turn_off_fn=lambda coordinator: coordinator.api.update_autoupdate_set(
            {"is_enabled": False}
        ),
    ),
    BusyBarSwitchDescription(
        key="bluetooth",
        translation_key="bluetooth",
        icon="mdi:bluetooth",
        entity_category=EntityCategory.CONFIG,
        value_fn=lambda coordinator: (
            coordinator.data.snapshot.ble.status == "enabled"
            if coordinator.data.snapshot.ble
            else None
        ),
        turn_on_fn=lambda coordinator: coordinator.api.ble_enable(),
        turn_off_fn=lambda coordinator: coordinator.api.ble_disable(),
    ),
    BusyBarSwitchDescription(
        key="smart_home",
        translation_key="smart_home",
        icon="mdi:home-automation",
        entity_category=EntityCategory.CONFIG,
        value_fn=lambda coordinator: (
            coordinator.data.smart_home.state if coordinator.data.smart_home else None
        ),
        turn_on_fn=lambda coordinator: coordinator.api.smart_home_switch_set(True),
        turn_off_fn=lambda coordinator: coordinator.api.smart_home_switch_set(False),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: BusyBarConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up BUSY Bar switches."""
    async_add_entities(
        BusyBarSwitch(entry.runtime_data, description) for description in SWITCHES
    )


class BusyBarSwitch(BusyBarEntity, SwitchEntity):
    """A writable BUSY Bar setting."""

    entity_description: BusyBarSwitchDescription

    def __init__(
        self,
        coordinator: BusyBarCoordinator,
        description: BusyBarSwitchDescription,
    ) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def is_on(self) -> bool | None:
        """Return the current setting."""
        return self.entity_description.value_fn(self.coordinator)

    async def async_turn_on(self, **kwargs: object) -> None:
        """Enable the setting."""
        await self.coordinator._async_command(
            self.entity_description.turn_on_fn(self.coordinator),
            f"enable {self.entity_description.key}",
        )
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: object) -> None:
        """Disable the setting."""
        await self.coordinator._async_command(
            self.entity_description.turn_off_fn(self.coordinator),
            f"disable {self.entity_description.key}",
        )
        await self.coordinator.async_request_refresh()
