"""Local-first Home Assistant integration for BUSY Bar."""

from pathlib import Path

from homeassistant.components import notify as hass_notify
from homeassistant.components.frontend import DATA_EXTRA_MODULE_URL, add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.const import CONF_NAME, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import discovery
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN, PLATFORMS, VERSION
from .coordinator import BusyBarConfigEntry, BusyBarCoordinator
from .services import async_setup_services

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up global BUSY Bar services."""
    async_setup_services(hass)
    if hass.http is not None:
        await hass.http.async_register_static_paths(
            [
                StaticPathConfig(
                    "/busybar/busybar-card.js",
                    str(Path(__file__).parent / "www" / "busybar-card.js"),
                    cache_headers=True,
                )
            ]
        )
    hass.data.setdefault(DATA_EXTRA_MODULE_URL, set())
    add_extra_js_url(hass, f"/busybar/busybar-card.js?v={VERSION}")
    return True


async def async_setup_entry(hass: HomeAssistant, entry: BusyBarConfigEntry) -> bool:
    """Set up a BUSY Bar config entry."""
    coordinator = BusyBarCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    entry.async_on_unload(entry.add_update_listener(_async_reload_entry))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    coordinator.async_start_stream()

    hass.async_create_task(
        discovery.async_load_platform(
            hass,
            Platform.NOTIFY,
            DOMAIN,
            {
                CONF_NAME: coordinator.data.snapshot.name or "BUSY Bar",
                "entry_id": entry.entry_id,
            },
            {},
        )
    )
    return True


async def async_unload_entry(hass: HomeAssistant, entry: BusyBarConfigEntry) -> bool:
    """Unload a BUSY Bar config entry."""
    if not await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        return False
    await entry.runtime_data.async_shutdown()
    await hass_notify.async_reload(hass, DOMAIN)
    return True


async def _async_reload_entry(hass: HomeAssistant, entry: BusyBarConfigEntry) -> None:
    """Reload after options change."""
    await hass.config_entries.async_reload(entry.entry_id)
