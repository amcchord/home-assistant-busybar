"""Regression tests for coexistence with the catalog's busybar domain."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import device_registry as dr
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.busybar_playground.const import DOMAIN, EVENT_BUSYBAR
from custom_components.busybar_playground.coordinator import BusyBarCoordinator
from custom_components.busybar_playground.device_trigger import (
    async_attach_trigger,
    async_get_triggers,
)
from custom_components.busybar_playground.services import async_setup_services
from custom_components.busybar_playground.stream import BusyBarStreamEvent


async def test_services_route_only_to_playground(hass: HomeAssistant) -> None:
    """Equal hardware serials in different domains resolve the right entry."""
    registry = dr.async_get(hass)
    entries = []
    devices = []
    for domain in ("busybar", DOMAIN):
        entry = MockConfigEntry(domain=domain, unique_id="same-serial")
        entry.runtime_data = SimpleNamespace(async_clear=AsyncMock())
        entry.add_to_hass(hass)
        entries.append(entry)
        devices.append(
            registry.async_get_or_create(
                config_entry_id=entry.entry_id,
                identifiers={(domain, "same-serial")},
            )
        )
    assert devices[0].id != devices[1].id

    old_handler = AsyncMock()
    hass.services.async_register("busybar", "clear_display", old_handler)
    async_setup_services(hass)
    assert not hass.services.has_service("busybar", "show_widget")

    await hass.services.async_call(
        DOMAIN, "clear_display", {"device_id": [devices[1].id]}, blocking=True
    )
    entries[1].runtime_data.async_clear.assert_awaited_once()
    entries[0].runtime_data.async_clear.assert_not_awaited()
    old_handler.assert_not_awaited()

    with pytest.raises(ServiceValidationError, match="not a BUSY Bar"):
        await hass.services.async_call(
            DOMAIN, "clear_display", {"device_id": [devices[0].id]}, blocking=True
        )

    await hass.services.async_call("busybar", "clear_display", {}, blocking=True)
    old_handler.assert_awaited_once()


async def test_device_triggers_ignore_other_integrations_events(
    hass: HomeAssistant,
) -> None:
    """A picker-style event must not activate a Playground device trigger."""
    entry = MockConfigEntry(domain=DOMAIN, unique_id="serial")
    entry.add_to_hass(hass)
    device = dr.async_get(hass).async_get_or_create(
        config_entry_id=entry.entry_id, identifiers={(DOMAIN, "serial")}
    )
    triggers = await async_get_triggers(hass, device.id)
    assert {trigger["domain"] for trigger in triggers} == {DOMAIN}
    trigger = next(item for item in triggers if item["type"] == "ok_press")
    action = AsyncMock()
    unsubscribe = await async_attach_trigger(
        hass,
        trigger,
        action,
        {"trigger_data": {"id": "test", "idx": "0"}, "variables": {}},
    )

    coordinator = BusyBarCoordinator.__new__(BusyBarCoordinator)
    coordinator.hass = hass
    coordinator.config_entry = entry
    coordinator._game_task = None
    coordinator._stream_listeners = []
    old_listener = MagicMock()
    unsubscribe_old = hass.bus.async_listen("busybar_event", old_listener)
    event = BusyBarStreamEvent("button", "press", "ok", {})

    hass.bus.async_fire(
        "busybar_event",
        {
            "entry_id": entry.entry_id,
            "category": "button",
            "source": "ok",
            "type": "press",
        },
    )
    await hass.async_block_till_done()
    action.assert_not_awaited()
    old_listener.reset_mock()

    assert EVENT_BUSYBAR == "busybar_playground_event"
    coordinator._emit_stream_event(event)
    await hass.async_block_till_done()
    action.assert_awaited_once()
    old_listener.assert_not_called()
    unsubscribe()
    unsubscribe_old()
