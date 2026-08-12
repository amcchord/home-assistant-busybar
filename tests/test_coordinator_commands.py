"""Tests for coordinator command helpers that protect device resources."""

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from busylib.exceptions import BusyBarAPIError

from custom_components.busybar.const import APPLICATION_NAME
from custom_components.busybar.coordinator import BusyBarCoordinator


def _bare_coordinator() -> BusyBarCoordinator:
    coordinator = BusyBarCoordinator.__new__(BusyBarCoordinator)
    coordinator.api = MagicMock()
    coordinator.api.assets_upload = AsyncMock(return_value=object())
    coordinator.api.assets_delete = AsyncMock(return_value=object())
    coordinator._asset_digests = {}
    return coordinator


async def test_identical_assets_are_uploaded_once_until_cleanup() -> None:
    """Hash caching saves flash writes and cleanup resets the cache."""
    coordinator = _bare_coordinator()
    await coordinator.async_upload_asset("same.png", b"pixels")
    await coordinator.async_upload_asset("same.png", b"pixels")
    coordinator.api.assets_upload.assert_awaited_once()

    await coordinator.async_delete_assets()
    assert coordinator._asset_digests == {}
    await coordinator.async_upload_asset("same.png", b"pixels")
    assert coordinator.api.assets_upload.await_count == 2


async def test_household_preset_delegates_safe_defaults() -> None:
    """Preset names resolve before an animation task is started."""
    coordinator = _bare_coordinator()
    coordinator.async_start_effect = AsyncMock()
    await coordinator.async_play_preset("package_delivered", message="AT THE DOOR")
    coordinator.async_start_effect.assert_awaited_once_with(
        "package_drop",
        color="#F59E0BFF",
        message="AT THE DOOR",
        duration=9,
        priority=65,
    )


async def test_pairing_qr_uses_owned_asset_and_rear_screen() -> None:
    """Pairing shows the returned code without exposing it outside the LAN."""
    coordinator = _bare_coordinator()
    coordinator.hass = MagicMock()
    coordinator.api.smart_home_pairing_start = AsyncMock(
        return_value=SimpleNamespace(qr_code="MT:LOCAL", manual_code=None)
    )
    coordinator.async_upload_asset = AsyncMock()
    coordinator.async_show_asset = AsyncMock()
    with patch(
        "custom_components.busybar.media.async_qr_png",
        AsyncMock(return_value=("pairing.png", b"png")),
    ):
        await coordinator.async_start_smart_home_pairing()
    coordinator.async_upload_asset.assert_awaited_once_with("pairing.png", b"png")
    coordinator.async_show_asset.assert_awaited_once_with(
        "pairing.png",
        display="back",
        duration=900,
        priority=80,
        layer_id="smart-home-pairing",
    )


async def test_stopping_finished_audio_is_idempotent() -> None:
    """A clip ending between UI state and Stop is not a user-facing failure."""
    coordinator = _bare_coordinator()
    coordinator.api.audio_stop = AsyncMock(
        side_effect=BusyBarAPIError(
            "No audio is playing",
            status_code=410,
        )
    )
    await coordinator.async_stop_sound()


async def test_draw_replaces_only_home_assistant_owned_content() -> None:
    """A layer change never invokes busylib's unscoped global clear path."""
    coordinator = _bare_coordinator()
    coordinator._draw_lock = asyncio.Lock()
    coordinator.api.display_clear = AsyncMock(return_value=object())
    coordinator.api.display_draw = AsyncMock(return_value=object())

    payload = {"priority": 50, "elements": []}
    await coordinator._async_draw_immediate(payload, True)
    await coordinator._async_draw_immediate(payload, False)

    coordinator.api.display_clear.assert_awaited_once_with(
        application_name=APPLICATION_NAME
    )
    assert coordinator.api.display_draw.await_count == 2
    for call in coordinator.api.display_draw.await_args_list:
        assert call.kwargs["clear_before_draw"] is False
