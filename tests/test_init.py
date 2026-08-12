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
        ble=types.BleStatus(status="disabled"),
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
    busy_profile = types.BusyProfile.model_validate(
        {
            "sort_order": -1,
            "title": "BUSY",
            "id": "00000000-0000-0000-0000-000000000000",
            "timer_settings": {"type": "INFINITE"},
            "busy_bar_settings": {
                "theme": "busy",
                "show_work_phase_only": True,
                "trigger_smart_home": True,
            },
            "profile_timestamp_ms": 1,
        }
    )
    custom_profile = busy_profile.model_copy(
        update={
            "title": "ZEN",
            "id": "00000000-0000-0000-0000-000000000001",
        }
    )

    api = MagicMock()
    api.status = AsyncMock(return_value=status)
    api.busy_snapshot = AsyncMock(return_value=timer)
    api.busy_profile = AsyncMock(side_effect=[busy_profile, custom_profile])
    api.update_status = AsyncMock(
        return_value=types.UpdateStatus(
            check=types.UpdateCheckStatus(available_version="1.2.0", status="available")
        )
    )
    api.update_autoupdate = AsyncMock(
        return_value=types.AutoupdateSettings(
            is_enabled=True,
            interval_start="02:00",
            interval_end="05:00",
        )
    )
    api.smart_home_switch = AsyncMock(
        return_value=types.SmartHomeSwitchState(state=False)
    )
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
        assert hass.states.get("sensor.office_bar_busy_profile").state == "BUSY"
        assert hass.states.get("sensor.office_bar_custom_profile").state == "ZEN"
        assert hass.states.get("event.office_bar_ok_button") is not None
        assert hass.states.get("image.office_bar_front_screen") is not None
        assert hass.states.get("image.office_bar_rear_screen") is not None
        assert hass.states.get("media_player.office_bar_audio").state == "idle"
        assert hass.states.get("notify.office_bar_display") is not None
        assert hass.states.get("switch.office_bar_automatic_brightness").state == "on"
        assert hass.states.get("switch.office_bar_automatic_updates").state == "on"
        assert hass.states.get("switch.office_bar_bluetooth").state == "off"
        assert hass.states.get("switch.office_bar_smart_home_switch").state == "off"
        assert (
            hass.states.get("time.office_bar_update_window_start").state == "02:00:00"
        )
        assert hass.states.get("update.office_bar_firmware").state == "on"
        assert hass.states.get("button.office_bar_start_smart_home_pairing") is not None

        coordinator = entry.runtime_data
        coordinator.async_play_preset = AsyncMock()
        device_id = next(
            device.id
            for device in hass.data["device_registry"].devices.values()
            if entry.entry_id in device.config_entries
        )
        await hass.services.async_call(
            DOMAIN,
            "play_preset",
            {
                "device_id": [device_id],
                "preset": "welcome_home",
                "message": "HI!",
            },
            blocking=True,
        )
        coordinator.async_play_preset.assert_awaited_once_with(
            "welcome_home", message="HI!"
        )

        coordinator.default_priority = 37
        coordinator.async_draw = AsyncMock()
        await hass.services.async_call(
            DOMAIN,
            "show_widget",
            {
                "device_id": [device_id],
                "widget": "scoreboard",
                "title": "CHORES",
                "value": "ALEX 12 • SAM 9",
            },
            blocking=True,
        )
        payload = coordinator.async_draw.await_args.args[0]
        assert payload["priority"] == 37

        with patch(
            "custom_components.busybar.hass_notify.async_reload",
            AsyncMock(return_value=None),
        ):
            assert await hass.config_entries.async_unload(entry.entry_id)

    api.aclose.assert_awaited_once()
