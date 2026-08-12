"""Tests for full config-entry setup."""

from unittest.mock import AsyncMock, MagicMock, patch

from busylib import types
from busylib.features import DeviceSnapshot
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.busybar.const import CONF_TOKEN, DOMAIN


async def test_setup_and_unload_entry(hass: HomeAssistant) -> None:
    """A snapshot produces the expected Home Assistant device entities."""
    status = types.Status(
        device=types.StatusDevice(
            serial_number="203638485431500400123456",
            wifi_mac="0c:fa:22:aa:bb:cc",
            otp_model="BB.1",
        ),
        firmware=types.StatusFirmware(version="1.1.1"),
        system=types.StatusSystem(api_semver="25.0.0", uptime="01d 01h 01m 01s"),
        power=types.StatusPower(
            state=types.PowerState.CHARGING,
            battery_charge=77,
        ),
    )
    snapshot = DeviceSnapshot(
        name="Office Bar",
        status=status,
        system=status.system,
        power=status.power,
        wifi=types.StatusResponse(state="connected", rssi=-42),
        brightness=types.DisplayBrightnessInfo(value="auto", front="60"),
        volume=types.AudioVolumeInfo(volume=35),
        storage=types.StorageStatus(
            total_bytes=8_000_000_000,
            used_bytes=1_000_000_000,
            free_bytes=7_000_000_000,
        ),
    )
    timer = types.BusySnapshot.model_validate(
        {
            "snapshot": {"type": "NOT_STARTED"},
            "snapshot_timestamp_ms": 1,
        }
    )

    api = MagicMock()
    api.status = AsyncMock(return_value=status)
    api.busy_snapshot = AsyncMock(return_value=timer)
    api.aclose = AsyncMock()

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Office Bar",
        data={CONF_HOST: "192.168.1.50", CONF_TOKEN: ""},
        unique_id="203638485431500400123456",
    )
    entry.add_to_hass(hass)

    with (
        patch("custom_components.busybar.coordinator.AsyncBusyBar", return_value=api),
        patch(
            "custom_components.busybar.coordinator.collect_device_snapshot",
            AsyncMock(return_value=snapshot),
        ),
        patch(
            "custom_components.busybar.coordinator.BusyBarCoordinator.async_start_stream"
        ),
        patch(
            "custom_components.busybar.discovery.async_load_platform",
            AsyncMock(return_value=None),
        ),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        assert hass.states.get("sensor.office_bar_battery").state == "77"
        assert hass.states.get("binary_sensor.office_bar_charging").state == "on"
        assert hass.states.get("number.office_bar_volume").state == "35.0"
        assert hass.states.get("select.office_bar_status_scene").state == "available"

        with patch(
            "custom_components.busybar.hass_notify.async_reload",
            AsyncMock(return_value=None),
        ):
            assert await hass.config_entries.async_unload(entry.entry_id)

    api.aclose.assert_awaited_once()
