"""Base entity for BUSY Bar."""

from __future__ import annotations

from homeassistant.const import CONF_HOST
from homeassistant.helpers.device_registry import CONNECTION_NETWORK_MAC, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER
from .coordinator import BusyBarCoordinator


class BusyBarEntity(CoordinatorEntity[BusyBarCoordinator]):
    """Common BUSY Bar entity behavior."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: BusyBarCoordinator, key: str) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        snapshot = coordinator.data.snapshot
        status = snapshot.status
        device = status.device if status else None
        firmware = status.firmware if status else None
        serial = (
            device.serial_number
            if device and device.serial_number
            else coordinator.config_entry.unique_id or coordinator.config_entry.entry_id
        )
        self._attr_unique_id = f"{serial}-{key}"

        connections: set[tuple[str, str]] = set()
        if device and device.wifi_mac:
            connections.add((CONNECTION_NETWORK_MAC, device.wifi_mac))
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, serial)},
            connections=connections,
            manufacturer=MANUFACTURER,
            model="BUSY Bar",
            model_id=device.otp_model if device else None,
            name=snapshot.name or "BUSY Bar",
            serial_number=device.serial_number if device else None,
            sw_version=firmware.version if firmware else None,
            configuration_url=f"http://{coordinator.config_entry.data[CONF_HOST]}",
        )
