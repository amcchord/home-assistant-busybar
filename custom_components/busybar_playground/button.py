"""Action buttons for BUSY Bar."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import BusyBarConfigEntry, BusyBarCoordinator
from .entity import BusyBarEntity


@dataclass(frozen=True, kw_only=True)
class BusyBarButtonDescription(ButtonEntityDescription):
    """Describe a BUSY Bar button."""

    press_fn: Callable[[BusyBarCoordinator], Awaitable[None]]


BUTTONS = (
    BusyBarButtonDescription(
        key="start_busy",
        translation_key="start_busy",
        icon="mdi:briefcase-play",
        press_fn=lambda coordinator: coordinator.async_send_key("busy"),
    ),
    BusyBarButtonDescription(
        key="start_custom",
        translation_key="start_custom",
        icon="mdi:timer-play-outline",
        press_fn=lambda coordinator: coordinator.async_send_key("custom"),
    ),
    BusyBarButtonDescription(
        key="pause_resume",
        translation_key="pause_resume",
        icon="mdi:play-pause",
        press_fn=lambda coordinator: coordinator.async_send_key("start"),
    ),
    BusyBarButtonDescription(
        key="stop",
        translation_key="stop",
        icon="mdi:stop-circle-outline",
        press_fn=lambda coordinator: coordinator.async_send_key("off"),
    ),
    BusyBarButtonDescription(
        key="celebrate",
        translation_key="celebrate",
        icon="mdi:party-popper",
        press_fn=lambda coordinator: coordinator.async_start_effect(
            "confetti", message="YAY!", duration=5
        ),
    ),
    BusyBarButtonDescription(
        key="clear_display",
        translation_key="clear_display",
        icon="mdi:monitor-off",
        entity_category=EntityCategory.CONFIG,
        press_fn=lambda coordinator: coordinator.async_clear(),
    ),
    BusyBarButtonDescription(
        key="check_update",
        translation_key="check_update",
        icon="mdi:update",
        entity_category=EntityCategory.CONFIG,
        press_fn=lambda coordinator: coordinator.async_check_update(),
    ),
    BusyBarButtonDescription(
        key="abort_update",
        translation_key="abort_update",
        icon="mdi:download-off",
        entity_category=EntityCategory.CONFIG,
        entity_registry_enabled_default=False,
        press_fn=lambda coordinator: coordinator.async_abort_update(),
    ),
    BusyBarButtonDescription(
        key="start_smart_home_pairing",
        translation_key="start_smart_home_pairing",
        icon="mdi:qrcode-scan",
        entity_category=EntityCategory.CONFIG,
        press_fn=lambda coordinator: coordinator.async_start_smart_home_pairing(),
    ),
    BusyBarButtonDescription(
        key="stop_smart_home_pairing",
        translation_key="stop_smart_home_pairing",
        icon="mdi:link-off",
        entity_category=EntityCategory.CONFIG,
        entity_registry_enabled_default=False,
        press_fn=lambda coordinator: coordinator.async_stop_smart_home_pairing(),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: BusyBarConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up BUSY Bar buttons."""
    async_add_entities(
        BusyBarButton(entry.runtime_data, description) for description in BUTTONS
    )


class BusyBarButton(BusyBarEntity, ButtonEntity):
    """Representation of a BUSY Bar button."""

    entity_description: BusyBarButtonDescription

    def __init__(
        self, coordinator: BusyBarCoordinator, description: BusyBarButtonDescription
    ) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    async def async_press(self) -> None:
        """Run the action."""
        await self.entity_description.press_fn(self.coordinator)
