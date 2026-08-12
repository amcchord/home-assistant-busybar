"""Data coordinator and command surface for BUSY Bar."""

from __future__ import annotations

import asyncio
import time
from contextlib import suppress
from dataclasses import dataclass, replace
from datetime import timedelta
from typing import Any
from uuid import uuid4

from busylib import AsyncBusyBar, types
from busylib.exceptions import BusyBarAPIError, BusyBarError
from busylib.features import (
    DeviceSnapshot,
    apply_state_stream_update,
    collect_device_snapshot,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, HomeAssistantError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    APPLICATION_NAME,
    CONF_DEFAULT_PRIORITY,
    CONF_SCAN_INTERVAL,
    CONF_TOKEN,
    DEFAULT_PRIORITY,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    LOGGER,
)
from .effects import effect_frames, message_payload, progress_payload, scene_payload


@dataclass(frozen=True, slots=True)
class BusyBarData:
    """Latest collected state."""

    snapshot: DeviceSnapshot
    timer: types.BusySnapshot | None


type BusyBarConfigEntry = ConfigEntry["BusyBarCoordinator"]


class BusyBarCoordinator(DataUpdateCoordinator[BusyBarData]):
    """Keep a BUSY Bar in sync and serialize display commands."""

    config_entry: BusyBarConfigEntry

    def __init__(self, hass: HomeAssistant, entry: BusyBarConfigEntry) -> None:
        """Initialize a coordinator."""
        scan_interval = int(
            entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        )
        token = entry.data.get(CONF_TOKEN) or None
        self.api = AsyncBusyBar(entry.data[CONF_HOST], token=token)
        self.default_priority = int(
            entry.options.get(CONF_DEFAULT_PRIORITY, DEFAULT_PRIORITY)
        )
        self.last_message = ""
        self.active_scene = "available"
        self._effect_task: asyncio.Task[None] | None = None
        self._stream_task: asyncio.Task[None] | None = None
        self._draw_lock = asyncio.Lock()
        self._shutdown = False
        super().__init__(
            hass,
            LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_interval),
        )

    async def _async_update_data(self) -> BusyBarData:
        """Fetch all useful local state."""
        try:
            # Unlike /api/version, this protected call verifies both access and
            # reachability.
            status = await self.api.status()
            snapshot, timer_result = await asyncio.gather(
                collect_device_snapshot(self.api),
                self.api.busy_snapshot(),
                return_exceptions=True,
            )
        except BusyBarAPIError as err:
            if err.status_code == 403:
                raise ConfigEntryAuthFailed(
                    "BUSY Bar rejected the local API credentials"
                ) from err
            raise UpdateFailed(f"BUSY Bar API error: {err.error}") from err
        except BusyBarError as err:
            raise UpdateFailed(f"Unable to reach BUSY Bar: {err}") from err

        if isinstance(snapshot, BaseException):
            raise UpdateFailed(f"Unable to collect BUSY Bar state: {snapshot}")
        snapshot.status = status

        timer: types.BusySnapshot | None
        if isinstance(timer_result, BaseException):
            LOGGER.debug("Could not read BUSY Bar timer state: %s", timer_result)
            timer = None
        else:
            timer = timer_result
        return BusyBarData(snapshot=snapshot, timer=timer)

    def async_start_stream(self) -> None:
        """Start the best-effort real-time status stream."""
        if self._stream_task is not None:
            return
        self._stream_task = self.config_entry.async_create_background_task(
            self.hass,
            self._async_stream_loop(),
            f"{DOMAIN} status stream",
        )

    async def _async_stream_loop(self) -> None:
        """Apply status deltas and reconnect after transient failures."""
        while True:
            try:
                async for message in self.api.stream_status_ws():
                    if not isinstance(message, dict) or self.data is None:
                        continue
                    snapshot = apply_state_stream_update(self.data.snapshot, message)
                    self.async_set_updated_data(replace(self.data, snapshot=snapshot))

                    updates = message.get("updates")
                    if isinstance(updates, list) and any(
                        isinstance(update, dict) and "timer" in update
                        for update in updates
                    ):
                        self.config_entry.async_create_background_task(
                            self.hass,
                            self.async_request_refresh(),
                            f"{DOMAIN} timer refresh",
                        )
            except asyncio.CancelledError:
                raise
            except BusyBarError as err:
                LOGGER.debug("BUSY Bar status stream disconnected: %s", err)
                await asyncio.sleep(5)
            except Exception:
                LOGGER.exception("Unexpected BUSY Bar status stream failure")
                await asyncio.sleep(5)

    async def async_shutdown(self) -> None:
        """Stop local work and release the HTTP client."""
        if self._shutdown:
            return
        self._shutdown = True
        await self.async_cancel_effect()
        if self._stream_task is not None and not self._stream_task.done():
            self._stream_task.cancel()
            with suppress(asyncio.CancelledError):
                await self._stream_task
            self._stream_task = None
        await self.api.aclose()

    async def _async_command(self, awaitable: Any, description: str) -> Any:
        """Translate library failures into user-facing Home Assistant errors."""
        try:
            return await awaitable
        except BusyBarAPIError as err:
            if err.status_code == 409:
                raise HomeAssistantError(
                    "The BUSY Bar is running a higher-priority app. Increase the "
                    "display priority only if this message should interrupt it."
                ) from err
            raise HomeAssistantError(f"Could not {description}: {err.error}") from err
        except BusyBarError as err:
            raise HomeAssistantError(f"Could not {description}: {err}") from err

    async def async_cancel_effect(self) -> None:
        """Cancel an in-flight local animation."""
        task = self._effect_task
        if task is None or task.done() or task is asyncio.current_task():
            return
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task
        self._effect_task = None

    async def async_draw(
        self,
        payload: dict[str, Any],
        *,
        clear_before_draw: bool = False,
        cancel_effect: bool = True,
    ) -> None:
        """Draw a validated payload under Home Assistant's application ownership."""
        if cancel_effect:
            await self.async_cancel_effect()
        payload = {**payload, "application_name": APPLICATION_NAME}
        async with self._draw_lock:
            await self._async_command(
                self.api.display_draw(
                    payload,
                    clear_before_draw=clear_before_draw,
                    sanitize_text=True,
                ),
                "draw on the display",
            )

    async def async_clear(self) -> None:
        """Clear only Home Assistant-owned display elements."""
        await self.async_cancel_effect()
        async with self._draw_lock:
            await self._async_command(
                self.api.display_clear(application_name=APPLICATION_NAME),
                "clear the display",
            )

    async def async_show_message(
        self,
        message: str,
        *,
        color: str = "#FFFFFFFF",
        background: str = "#000000FF",
        priority: int | None = None,
        duration: int = 10,
        led_color: str | None = None,
        scroll: bool = True,
    ) -> None:
        """Show a friendly text message."""
        self.last_message = message
        await self.async_draw(
            message_payload(
                message,
                color=color,
                background=background,
                priority=priority or self.default_priority,
                duration=duration,
                led_color=led_color,
                scroll=scroll,
            )
        )

    async def async_show_progress(
        self,
        value: float,
        *,
        label: str = "",
        color: str = "#22C55EFF",
        background: str = "#111827FF",
        priority: int | None = None,
        duration: int = 10,
    ) -> None:
        """Show a compact progress display."""
        await self.async_draw(
            progress_payload(
                value,
                label=label,
                color=color,
                background=background,
                priority=priority or self.default_priority,
                duration=duration,
            )
        )

    async def async_show_scene(self, scene: str) -> None:
        """Apply an opinionated status scene."""
        self.active_scene = scene
        await self.async_draw(scene_payload(scene, priority=self.default_priority))

    async def async_start_effect(
        self,
        effect: str,
        *,
        color: str = "#22D3EEFF",
        message: str = "",
        priority: int | None = None,
        fps: int = 8,
        duration: float = 5.0,
    ) -> None:
        """Start a bounded animation and return without blocking the service call."""
        await self.async_cancel_effect()
        self._effect_task = self.config_entry.async_create_background_task(
            self.hass,
            self._async_effect_loop(
                effect,
                color=color,
                message=message,
                priority=priority or self.default_priority,
                fps=fps,
                duration=duration,
            ),
            f"{DOMAIN} {effect} effect",
        )

    async def _async_effect_loop(
        self,
        effect: str,
        *,
        color: str,
        message: str,
        priority: int,
        fps: int,
        duration: float,
    ) -> None:
        frame_delay = 1 / max(2, min(12, fps))
        completed = False
        try:
            for frame in effect_frames(
                effect,
                color=color,
                message=message,
                priority=priority,
                fps=fps,
                duration=duration,
            ):
                await self.async_draw(frame, cancel_effect=False)
                await asyncio.sleep(frame_delay)
            completed = True
        finally:
            if self._effect_task is asyncio.current_task():
                self._effect_task = None
        if completed:
            await self.async_clear()

    async def async_send_key(self, key: str) -> None:
        """Send one virtual key press."""
        await self.async_cancel_effect()
        await self._async_command(
            self.api.input(types.InputKey(key)), f"send {key} key"
        )
        await self.async_request_refresh()

    async def async_start_focus(
        self,
        minutes: int,
        *,
        theme: str = "on_air",
        trigger_smart_home: bool = True,
    ) -> None:
        """Start a finite focus timer without modifying the device's saved profiles."""
        now_ms = round(time.time() * 1000)
        payload = {
            "snapshot": {
                "type": "SIMPLE",
                "card_id": str(uuid4()),
                "time_left_ms": minutes * 60_000,
                "is_paused": False,
                "busy_bar_settings": {
                    "theme": theme,
                    "show_work_phase_only": False,
                    "trigger_smart_home": trigger_smart_home,
                },
            },
            "snapshot_timestamp_ms": now_ms,
        }
        await self.async_cancel_effect()
        await self._async_command(
            self.api.api_request("PUT", "/api/busy/snapshot", json_payload=payload),
            "start the focus timer",
        )
        await self.async_request_refresh()
