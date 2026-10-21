"""Load the actual catalog integration alongside Playground with mocked devices.

Run explicitly with the pinned pickerin/hass-busybar checkout on PYTHONPATH;
see the Tests workflow. No commands are sent to physical hardware.
"""

from unittest.mock import AsyncMock, patch

from custom_components.busybar.api import BusyBarApi
from homeassistant.components.frontend import DATA_EXTRA_MODULE_URL
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from tests.test_init import test_setup_and_unload_entry as _check_playground


async def test_actual_catalog_integrations_coexist(hass: HomeAssistant) -> None:
    """Both integrations load entities/services and unload independently."""
    entry = MockConfigEntry(
        domain="busybar",
        title="Catalog Bar",
        unique_id="203638485431500400123456",
        data={"host": "192.168.1.50"},
    )
    entry.add_to_hass(hass)
    api = AsyncMock(spec=BusyBarApi)
    api.busy_snapshot.return_value = {"snapshot": {"type": "NOT_STARTED"}}
    api.brightness.return_value = {"value": 50}
    api.volume.return_value = {"volume": 35}
    api.busy_profile.return_value = {
        "timer_settings": {"type": "INFINITE"},
        "busy_bar_settings": {"theme": "busy"},
    }
    api.themes.return_value = ["busy"]
    with (
        patch("custom_components.busybar.BusyBarApi", return_value=api),
        patch("custom_components.busybar.BusyBarWsListener.run", new=AsyncMock()),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        assert entry.state is ConfigEntryState.LOADED
        assert hass.services.has_service("busybar", "clear_display")
        registry = er.async_get(hass)
        catalog_entities = {
            entity.entity_id
            for entity in er.async_entries_for_config_entry(registry, entry.entry_id)
        }
        assert catalog_entities

        # The normal regression test loads every Playground platform, exercises
        # its services, checks entity state and unloads it, with busybar loaded.
        await _check_playground(hass)
        assert entry.state is ConfigEntryState.LOADED
        assert all(hass.states.get(entity_id) for entity_id in catalog_entities)
        urls = hass.data[DATA_EXTRA_MODULE_URL].urls
        assert any(url.startswith("/busybar-static/busybar-card.js?v=") for url in urls)
        assert any(
            url.startswith("/busybar_playground/busybar-playground-card.js?v=")
            for url in urls
        )
        await hass.services.async_call("busybar", "clear_display", {}, blocking=True)
        api.display_clear.assert_awaited_once()
        assert await hass.config_entries.async_unload(entry.entry_id)
