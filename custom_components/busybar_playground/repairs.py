"""Proactive Home Assistant Repairs issues for BUSY Bar."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir

from .const import DOMAIN
from .coordinator import BusyBarData


def async_update_issues(
    hass: HomeAssistant,
    entry: ConfigEntry,
    data: BusyBarData,
    *,
    stream_failures: int = 0,
) -> None:
    """Create and clear actionable device-health issues."""
    storage = data.snapshot.storage
    storage_low = bool(
        storage
        and storage.free is not None
        and (
            storage.free < 50_000_000
            or (
                storage.total is not None
                and storage.total > 0
                and storage.free / storage.total < 0.05
            )
        )
    )
    _set_issue(
        hass,
        entry,
        "storage_low",
        storage_low,
        translation_key="storage_low",
        persistent=False,
    )

    install = data.update_status.install if data.update_status else None
    update_available = bool(data.snapshot.update_available_version)
    _set_issue(
        hass,
        entry,
        "update_battery_low",
        bool(update_available and install and install.is_allowed is False),
        translation_key="update_battery_low",
        persistent=False,
    )
    update_failed = bool(
        install
        and install.status
        not in {
            None,
            "ok",
            "battery_low",
            "busy",
            "download_abort",
        }
    )
    _set_issue(
        hass,
        entry,
        "update_failed",
        update_failed,
        translation_key="update_failed",
        persistent=True,
        placeholders={"detail": install.detail or install.status or "unknown"}
        if install
        else None,
    )
    _set_issue(
        hass,
        entry,
        "stream_unstable",
        stream_failures >= 5,
        translation_key="stream_unstable",
        persistent=False,
    )


def _set_issue(
    hass: HomeAssistant,
    entry: ConfigEntry,
    suffix: str,
    active: bool,
    *,
    translation_key: str,
    persistent: bool,
    placeholders: dict[str, str] | None = None,
) -> None:
    issue_id = f"{entry.entry_id}_{suffix}"
    if not active:
        ir.async_delete_issue(hass, DOMAIN, issue_id)
        return
    ir.async_create_issue(
        hass,
        DOMAIN,
        issue_id,
        is_fixable=False,
        is_persistent=persistent,
        severity=ir.IssueSeverity.WARNING,
        translation_key=translation_key,
        translation_placeholders=placeholders,
    )
