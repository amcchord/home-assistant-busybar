"""Physical control and timer events for BUSY Bar."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.event import (
    ButtonEventType,
    EventDeviceClass,
    EventEntity,
    EventEntityDescription,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import BusyBarConfigEntry, BusyBarCoordinator
from .entity import BusyBarEntity
from .stream import BusyBarStreamEvent


@dataclass(frozen=True, kw_only=True)
class BusyBarEventDescription(EventEntityDescription):
    """Describe one BUSY Bar event source."""

    category: str
    source: str


EVENTS = (
    BusyBarEventDescription(
        key="ok_button",
        translation_key="ok_button",
        device_class=EventDeviceClass.BUTTON,
        event_types=[ButtonEventType.PRESS_START, ButtonEventType.PRESS_END],
        category="button",
        source="ok",
    ),
    BusyBarEventDescription(
        key="back_button",
        translation_key="back_button",
        device_class=EventDeviceClass.BUTTON,
        event_types=[ButtonEventType.PRESS_START, ButtonEventType.PRESS_END],
        category="button",
        source="back",
    ),
    BusyBarEventDescription(
        key="start_button",
        translation_key="start_button",
        device_class=EventDeviceClass.BUTTON,
        event_types=[ButtonEventType.PRESS_START, ButtonEventType.PRESS_END],
        category="button",
        source="start",
    ),
    BusyBarEventDescription(
        key="encoder",
        translation_key="encoder",
        event_types=["clockwise", "counterclockwise"],
        category="encoder",
        source="encoder",
    ),
    BusyBarEventDescription(
        key="mode_switch",
        translation_key="mode_switch",
        event_types=["busy", "custom", "off", "apps", "settings"],
        category="switch",
        source="mode_switch",
    ),
    BusyBarEventDescription(
        key="timer_event",
        translation_key="timer_event",
        event_types=[
            "started",
            "paused",
            "resumed",
            "phase_changed",
            "finished",
            "stopped",
        ],
        category="timer",
        source="timer",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: BusyBarConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up BUSY Bar event entities."""
    async_add_entities(
        BusyBarEventEntity(entry.runtime_data, description) for description in EVENTS
    )


class BusyBarEventEntity(BusyBarEntity, EventEntity):
    """Expose one source from the BUSY Bar input stream."""

    entity_description: BusyBarEventDescription

    def __init__(
        self,
        coordinator: BusyBarCoordinator,
        description: BusyBarEventDescription,
    ) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    async def async_added_to_hass(self) -> None:
        """Subscribe after the entity has an entity ID."""
        await super().async_added_to_hass()
        self.async_on_remove(
            self.coordinator.async_add_stream_listener(self._handle_stream_event)
        )

    @callback
    def _handle_stream_event(self, event: BusyBarStreamEvent) -> None:
        if (
            event.category != self.entity_description.category
            or event.source != self.entity_description.source
        ):
            return
        event_type = event.event_type
        if event.category == "button":
            event_type = (
                ButtonEventType.PRESS_START
                if event_type == "press"
                else ButtonEventType.PRESS_END
            )
        self._trigger_event(event_type, event.data)
        self.async_write_ha_state()
