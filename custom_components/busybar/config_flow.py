"""Config and options flows for BUSY Bar."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import voluptuous as vol
from busylib import AsyncBusyBar
from busylib.exceptions import BusyBarAPIError, BusyBarError
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import CONF_HOST
from homeassistant.core import callback
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)
from homeassistant.helpers.service_info.dhcp import DhcpServiceInfo
from homeassistant.helpers.service_info.zeroconf import ZeroconfServiceInfo

from .const import (
    CONF_DEFAULT_PRIORITY,
    CONF_SCAN_INTERVAL,
    CONF_TOKEN,
    DEFAULT_PRIORITY,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MAX_SCAN_INTERVAL,
    MIN_SCAN_INTERVAL,
)


class BusyBarCannotConnect(Exception):
    """Raised when a BUSY Bar cannot be reached."""


class BusyBarInvalidAuth(Exception):
    """Raised when an access key is rejected."""


class BusyBarApiDisabled(Exception):
    """Raised when Wi-Fi API access is disabled on the bar."""


@dataclass(slots=True)
class DiscoveredDevice:
    """Validated setup details."""

    title: str
    unique_id: str
    host: str
    token: str


def _normalize_host(host: str) -> str:
    """Keep a hostname/IP (and optional port) without URL decoration."""
    value = host.strip().rstrip("/")
    for prefix in ("http://", "https://"):
        if value.startswith(prefix):
            value = value[len(prefix) :]
    return value.split("/", 1)[0]


async def async_validate_input(host: str, token: str = "") -> DiscoveredDevice:
    """Validate local access and collect stable identity."""
    host = _normalize_host(host)
    api = AsyncBusyBar(host, token=token or None)
    try:
        try:
            access = await api.access()
        except BusyBarError:
            # Very old firmware may not expose access(), so let status decide.
            access = None
        if access is not None and access.mode == "disabled":
            raise BusyBarApiDisabled

        status = await api.status()
        name = await api.name()
    except BusyBarApiDisabled:
        raise
    except BusyBarAPIError as err:
        if err.status_code == 403:
            raise BusyBarInvalidAuth from err
        raise BusyBarCannotConnect from err
    except BusyBarError as err:
        raise BusyBarCannotConnect from err
    finally:
        await api.aclose()

    device = status.device
    unique_id = None
    if device:
        unique_id = device.serial_number or device.wifi_mac
    if not unique_id:
        unique_id = host
    title = name.name or name.device or name.value or "BUSY Bar"
    return DiscoveredDevice(title=title, unique_id=unique_id, host=host, token=token)


def _user_schema(defaults: dict[str, Any] | None = None) -> vol.Schema:
    defaults = defaults or {}
    return vol.Schema(
        {
            vol.Required(
                CONF_HOST, default=defaults.get(CONF_HOST, "")
            ): TextSelector(),
            vol.Optional(
                CONF_TOKEN, default=defaults.get(CONF_TOKEN, "")
            ): TextSelector(TextSelectorConfig(type=TextSelectorType.PASSWORD)),
        }
    )


class BusyBarConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a BUSY Bar config flow."""

    VERSION = 1
    _discovered_host: str | None = None

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Return the options flow."""
        return BusyBarOptionsFlow()

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle manual setup."""
        return await self._async_step_setup("user", user_input)

    async def _async_step_setup(
        self, step_id: str, user_input: dict[str, Any] | None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        defaults: dict[str, Any] = {}
        if self._discovered_host:
            defaults[CONF_HOST] = self._discovered_host

        if user_input is not None:
            try:
                info = await async_validate_input(
                    user_input[CONF_HOST], user_input.get(CONF_TOKEN, "")
                )
            except BusyBarApiDisabled:
                errors["base"] = "api_disabled"
            except BusyBarInvalidAuth:
                errors["base"] = "invalid_auth"
            except BusyBarCannotConnect:
                errors["base"] = "cannot_connect"
            except Exception:
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(info.unique_id)
                self._abort_if_unique_id_configured(updates={CONF_HOST: info.host})
                return self.async_create_entry(
                    title=info.title,
                    data={CONF_HOST: info.host, CONF_TOKEN: info.token},
                )
            defaults.update(user_input)

        return self.async_show_form(
            step_id=step_id,
            data_schema=_user_schema(defaults),
            errors=errors,
            description_placeholders={"host": self._discovered_host or ""},
        )

    async def async_step_dhcp(
        self, discovery_info: DhcpServiceInfo
    ) -> ConfigFlowResult:
        """Handle DHCP discovery."""
        self._discovered_host = discovery_info.ip
        self.context["title_placeholders"] = {"name": "BUSY Bar"}
        return await self._async_step_setup("discovery_confirm", None)

    async def async_step_zeroconf(
        self, discovery_info: ZeroconfServiceInfo
    ) -> ConfigFlowResult:
        """Handle future BUSY Bar mDNS advertisements."""
        self._discovered_host = discovery_info.host
        self.context["title_placeholders"] = {
            "name": discovery_info.properties.get("name", "BUSY Bar")
        }
        return await self._async_step_setup("discovery_confirm", None)

    async def async_step_reauth(self, entry_data: dict[str, Any]) -> ConfigFlowResult:
        """Handle reauthentication."""
        self._discovered_host = entry_data[CONF_HOST]
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Confirm new local credentials."""
        errors: dict[str, str] = {}
        entry = self._get_reauth_entry()
        if user_input is not None:
            try:
                info = await async_validate_input(
                    entry.data[CONF_HOST], user_input.get(CONF_TOKEN, "")
                )
            except BusyBarApiDisabled:
                errors["base"] = "api_disabled"
            except BusyBarInvalidAuth:
                errors["base"] = "invalid_auth"
            except BusyBarCannotConnect:
                errors["base"] = "cannot_connect"
            else:
                return self.async_update_reload_and_abort(
                    entry,
                    data_updates={CONF_HOST: info.host, CONF_TOKEN: info.token},
                )

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema(
                {
                    vol.Optional(CONF_TOKEN, default=""): TextSelector(
                        TextSelectorConfig(type=TextSelectorType.PASSWORD)
                    )
                }
            ),
            errors=errors,
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Update host or local API key."""
        errors: dict[str, str] = {}
        entry = self._get_reconfigure_entry()
        if user_input is not None:
            try:
                info = await async_validate_input(
                    user_input[CONF_HOST], user_input.get(CONF_TOKEN, "")
                )
            except BusyBarApiDisabled:
                errors["base"] = "api_disabled"
            except BusyBarInvalidAuth:
                errors["base"] = "invalid_auth"
            except BusyBarCannotConnect:
                errors["base"] = "cannot_connect"
            else:
                await self.async_set_unique_id(info.unique_id)
                self._abort_if_unique_id_mismatch()
                return self.async_update_reload_and_abort(
                    entry,
                    data_updates={CONF_HOST: info.host, CONF_TOKEN: info.token},
                )

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=_user_schema(dict(entry.data) | (user_input or {})),
            errors=errors,
        )


class BusyBarOptionsFlow(OptionsFlow):
    """Configure update frequency and default display ownership priority."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_SCAN_INTERVAL,
                        default=self.config_entry.options.get(
                            CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
                        ),
                    ): NumberSelector(
                        NumberSelectorConfig(
                            min=MIN_SCAN_INTERVAL,
                            max=MAX_SCAN_INTERVAL,
                            step=1,
                            mode=NumberSelectorMode.BOX,
                        )
                    ),
                    vol.Required(
                        CONF_DEFAULT_PRIORITY,
                        default=self.config_entry.options.get(
                            CONF_DEFAULT_PRIORITY, DEFAULT_PRIORITY
                        ),
                    ): NumberSelector(
                        NumberSelectorConfig(
                            min=1,
                            max=100,
                            step=1,
                            mode=NumberSelectorMode.SLIDER,
                        )
                    ),
                }
            ),
        )
