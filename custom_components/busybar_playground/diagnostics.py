"""Diagnostics for BUSY Bar."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.core import HomeAssistant

from .coordinator import BusyBarConfigEntry

TO_REDACT = {
    "host",
    "token",
    "serial_number",
    "usb_mac",
    "wifi_mac",
    "ble_mac",
    "ssid",
    "bssid",
    "address",
}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: BusyBarConfigEntry
) -> dict[str, Any]:
    """Return redacted config and last snapshot."""
    coordinator = entry.runtime_data
    return async_redact_data(
        {
            "config_entry": {
                "data": dict(entry.data),
                "options": dict(entry.options),
            },
            "snapshot": coordinator.data.snapshot.model_dump(mode="json"),
            "timer": coordinator.data.timer.model_dump(mode="json")
            if coordinator.data.timer
            else None,
            "profiles": {
                slot: profile.model_dump(mode="json")
                for slot, profile in coordinator.data.profiles.items()
            },
            "update_status": coordinator.data.update_status.model_dump(mode="json")
            if coordinator.data.update_status
            else None,
            "automatic_updates": coordinator.data.autoupdate.model_dump(mode="json")
            if coordinator.data.autoupdate
            else None,
            "smart_home": coordinator.data.smart_home.model_dump(mode="json")
            if coordinator.data.smart_home
            else None,
            "display_manager": {
                "active_layer_id": coordinator.display_manager.active_layer_id,
                "layer_count": coordinator.display_manager.layer_count,
            },
            "last_update_success": coordinator.last_update_success,
        },
        TO_REDACT,
    )
