"""Firmware update support for BUSY Bar."""

from __future__ import annotations

from homeassistant.components.update import (
    UpdateDeviceClass,
    UpdateEntity,
    UpdateEntityFeature,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import BusyBarConfigEntry, BusyBarCoordinator
from .entity import BusyBarEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: BusyBarConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the firmware update entity."""
    async_add_entities([BusyBarFirmwareUpdate(entry.runtime_data)])


class BusyBarFirmwareUpdate(BusyBarEntity, UpdateEntity):
    """Install firmware offered by the BUSY Bar updater."""

    _attr_translation_key = "firmware"
    _attr_device_class = UpdateDeviceClass.FIRMWARE
    _attr_title = "BUSY Bar firmware"
    _attr_supported_features = (
        UpdateEntityFeature.INSTALL
        | UpdateEntityFeature.PROGRESS
        | UpdateEntityFeature.RELEASE_NOTES
    )

    def __init__(self, coordinator: BusyBarCoordinator) -> None:
        super().__init__(coordinator, "firmware_update")
        self._release_summary: str | None = None

    @property
    def installed_version(self) -> str | None:
        """Return the installed firmware version."""
        status = self.coordinator.data.snapshot.status
        return status.firmware.version if status and status.firmware else None

    @property
    def latest_version(self) -> str | None:
        """Return the offered version, or installed version when current."""
        return (
            self.coordinator.data.snapshot.update_available_version
            or self.installed_version
        )

    @property
    def auto_update(self) -> bool:
        """Return whether automatic firmware updates are enabled."""
        settings = self.coordinator.data.autoupdate
        return bool(settings and settings.is_enabled)

    @property
    def in_progress(self) -> bool:
        """Return whether an installation is running."""
        status = self.coordinator.data.update_status
        install = status.install if status else None
        return bool(
            install
            and (
                install.action not in (None, "none")
                or install.event
                in {
                    "session_start",
                    "action_begin",
                    "action_progress",
                    "detail_change",
                }
            )
        )

    @property
    def update_percentage(self) -> float | None:
        """Return firmware download progress."""
        status = self.coordinator.data.update_status
        install = status.install if status else None
        download = install.download if install else None
        if not download or not download.total_bytes:
            return None
        return min(100.0, 100 * (download.received_bytes or 0) / download.total_bytes)

    @property
    def release_summary(self) -> str | None:
        """Return a cached short firmware changelog."""
        return self._release_summary

    async def async_install(
        self, version: str | None, backup: bool, **kwargs: object
    ) -> None:
        """Start the device's verified remote update process."""
        target = version or self.latest_version
        if target is None or target == self.installed_version:
            raise HomeAssistantError("No BUSY Bar firmware update is available")
        status = self.coordinator.data.update_status
        if status and status.install and status.install.is_allowed is False:
            raise HomeAssistantError(
                "BUSY Bar cannot update while its battery is too low"
            )
        await self.coordinator._async_command(
            self.coordinator.api.update_install(target),
            f"install firmware {target}",
        )
        await self.coordinator.async_request_refresh()

    async def async_release_notes(self) -> str | None:
        """Fetch the full changelog for the offered firmware."""
        target = self.latest_version
        if target is None or target == self.installed_version:
            return None
        response = await self.coordinator._async_command(
            self.coordinator.api.update_changelog(target),
            f"fetch the {target} firmware changelog",
        )
        changelog = response.changelog
        self._release_summary = changelog[:255] if changelog else None
        return changelog
