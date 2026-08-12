"""Tests for BUSY Bar setup flows."""

from unittest.mock import AsyncMock, MagicMock, patch

from busylib import types
from homeassistant import config_entries
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers.service_info.dhcp import DhcpServiceInfo

from custom_components.busybar.config_flow import (
    BusyBarApiDisabled,
    DiscoveredDevice,
    _normalize_host,
)
from custom_components.busybar.const import CONF_TOKEN, DOMAIN


def test_normalize_host() -> None:
    """URLs pasted from a browser become client-compatible hosts."""
    assert _normalize_host(" http://192.168.1.50/ ") == "192.168.1.50"
    assert _normalize_host("busybar.local:8080/settings") == "busybar.local:8080"


async def test_user_flow_success(hass: HomeAssistant) -> None:
    """A validated device creates a config entry without cloud credentials."""
    with (
        patch(
            "custom_components.busybar.config_flow.async_validate_input",
            AsyncMock(
                return_value=DiscoveredDevice(
                    title="Office Bar",
                    unique_id="serial-123",
                    host="192.168.1.50",
                    token="",
                )
            ),
        ),
        patch(
            "custom_components.busybar.async_setup_entry",
            AsyncMock(return_value=True),
        ),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_USER},
            data={CONF_HOST: "192.168.1.50", CONF_TOKEN: ""},
        )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Office Bar"
    assert result["data"] == {CONF_HOST: "192.168.1.50", CONF_TOKEN: ""}


async def test_user_flow_api_disabled(hass: HomeAssistant) -> None:
    """Setup gives a specific remediation when Wi-Fi API access is off."""
    with patch(
        "custom_components.busybar.config_flow.async_validate_input",
        AsyncMock(side_effect=BusyBarApiDisabled),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_USER},
            data={CONF_HOST: "192.168.1.50", CONF_TOKEN: ""},
        )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "api_disabled"}


async def test_dhcp_discovery_shows_confirmation_form(hass: HomeAssistant) -> None:
    """DHCP discoveries route through a real, submit-capable flow step."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_DHCP},
        data=DhcpServiceInfo(
            ip="192.168.1.50",
            hostname="busybar",
            macaddress="0cfa22aabbcc",
        ),
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "discovery_confirm"


async def test_validate_input_uses_serial_and_name(hass: HomeAssistant) -> None:
    """Hardware identity—not a changing DHCP address—is used as unique ID."""
    from custom_components.busybar.config_flow import async_validate_input

    api = MagicMock()
    api.access = AsyncMock(return_value=types.HttpAccessInfo(mode="enabled"))
    api.status = AsyncMock(
        return_value=types.Status(
            device=types.StatusDevice(
                serial_number="203638485431500400123456",
                wifi_mac="0c:fa:22:aa:bb:cc",
            )
        )
    )
    api.name = AsyncMock(return_value=types.DeviceNameResponse(name="Office Bar"))
    api.aclose = AsyncMock()

    with patch("custom_components.busybar.config_flow.AsyncBusyBar", return_value=api):
        info = await async_validate_input(hass, "http://192.168.1.50/", "")

    assert info.unique_id == "203638485431500400123456"
    assert info.title == "Office Bar"
    assert info.host == "192.168.1.50"
    api.aclose.assert_awaited_once()
