"""Data coordinator and command surface for BUSY Bar."""

from __future__ import annotations

import asyncio
import hashlib
import time
from collections.abc import Callable
from contextlib import suppress
from dataclasses import dataclass, replace
from datetime import timedelta
from functools import partial
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
from homeassistant.core import HomeAssistant, callback
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
    EVENT_BUSYBAR,
    LOGGER,
)
from .display_manager import BusyBarDisplayManager
from .effects import effect_frames, message_payload, progress_payload, scene_payload
from .games import run_game
from .presets import preset_spec
from .stream import (
    BusyBarStreamEvent,
    parse_input_events,
    parse_timer_snapshot,
    timer_transition_events,
)


@dataclass(frozen=True, slots=True)
class BusyBarData:
    """Latest collected state."""

    snapshot: DeviceSnapshot
    timer: types.BusySnapshot | None
    profiles: dict[str, types.BusyProfile]
    update_status: types.UpdateStatus | None
    autoupdate: types.AutoupdateSettings | None
    smart_home: types.SmartHomeSwitchState | None
    screen_revision: int = 0


type BusyBarConfigEntry = ConfigEntry["BusyBarCoordinator"]


class BusyBarCoordinator(DataUpdateCoordinator[BusyBarData]):
    """Keep a BUSY Bar in sync and serialize display commands."""

    config_entry: BusyBarConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        entry: BusyBarConfigEntry,
        api: AsyncBusyBar,
    ) -> None:
        """Initialize a coordinator."""
        scan_interval = int(
            entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        )
        self.api = api
        self.default_priority = int(
            entry.options.get(CONF_DEFAULT_PRIORITY, DEFAULT_PRIORITY)
        )
        self.last_message = ""
        self.active_scene = "available"
        self._effect_task: asyncio.Task[None] | None = None
        self._effect_layer_id: str | None = None
        self._game_task: asyncio.Task[None] | None = None
        self._game_layer_id: str | None = None
        self._game_events: asyncio.Queue[BusyBarStreamEvent] = asyncio.Queue(maxsize=32)
        self._stream_task: asyncio.Task[None] | None = None
        self._stream_listeners: list[Callable[[BusyBarStreamEvent], None]] = []
        self._stream_failures = 0
        self._draw_lock = asyncio.Lock()
        self._asset_digests: dict[str, str] = {}
        self._shutdown = False
        self.display_manager = BusyBarDisplayManager(
            self._async_draw_immediate,
            self._async_clear_immediate,
            lambda coro, name: entry.async_create_background_task(hass, coro, name),
        )
        super().__init__(
            hass,
            LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_interval),
        )

    @classmethod
    async def async_create(
        cls, hass: HomeAssistant, entry: BusyBarConfigEntry
    ) -> BusyBarCoordinator:
        """Create the HTTP client off the event loop, then build a coordinator."""
        token = entry.data.get(CONF_TOKEN) or None
        api = await hass.async_add_executor_job(
            partial(AsyncBusyBar, entry.data[CONF_HOST], token=token)
        )
        return cls(hass, entry, api)

    async def _async_update_data(self) -> BusyBarData:
        """Fetch all useful local state."""
        try:
            # Unlike /api/version, this protected call verifies both access and
            # reachability.
            status = await self.api.status()
            (
                snapshot,
                timer_result,
                busy_profile,
                custom_profile,
                update_status,
                autoupdate,
                smart_home,
            ) = await asyncio.gather(
                collect_device_snapshot(self.api),
                self.api.busy_snapshot(),
                self.api.busy_profile("busy"),
                self.api.busy_profile("custom"),
                self.api.update_status(),
                self.api.update_autoupdate(),
                self.api.smart_home_switch(),
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
        if self.data is not None:
            snapshot.screen_front = (
                snapshot.screen_front or self.data.snapshot.screen_front
            )
            snapshot.screen_back = (
                snapshot.screen_back or self.data.snapshot.screen_back
            )

        timer: types.BusySnapshot | None
        if isinstance(timer_result, BaseException):
            LOGGER.debug("Could not read BUSY Bar timer state: %s", timer_result)
            timer = None
        else:
            timer = timer_result

        profiles: dict[str, types.BusyProfile] = {}
        if not isinstance(busy_profile, BaseException):
            profiles["busy"] = busy_profile
        if not isinstance(custom_profile, BaseException):
            profiles["custom"] = custom_profile

        parsed_update = (
            None if isinstance(update_status, BaseException) else update_status
        )
        if (
            parsed_update
            and parsed_update.check
            and parsed_update.check.available_version
        ):
            snapshot.update_available_version = parsed_update.check.available_version

        data = BusyBarData(
            snapshot=snapshot,
            timer=timer,
            profiles=profiles,
            update_status=parsed_update,
            autoupdate=None if isinstance(autoupdate, BaseException) else autoupdate,
            smart_home=None if isinstance(smart_home, BaseException) else smart_home,
            screen_revision=self.data.screen_revision if self.data else 0,
        )
        self._update_repairs(data)
        return data

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
                    if self._stream_failures:
                        self._stream_failures = 0
                        self._update_repairs(self.data)
                    snapshot = apply_state_stream_update(self.data.snapshot, message)
                    updates = message.get("updates")
                    has_frame = isinstance(updates, list) and any(
                        isinstance(update, dict) and "frame" in update
                        for update in updates
                    )
                    timer = parse_timer_snapshot(message)
                    previous_timer = self.data.timer
                    self.async_set_updated_data(
                        replace(
                            self.data,
                            snapshot=snapshot,
                            timer=timer or previous_timer,
                            screen_revision=(
                                self.data.screen_revision + 1
                                if has_frame
                                else self.data.screen_revision
                            ),
                        )
                    )

                    for event in parse_input_events(message):
                        self._emit_stream_event(event)
                    if timer is not None:
                        for event in timer_transition_events(previous_timer, timer):
                            self._emit_stream_event(event)

                    if (
                        timer is None
                        and isinstance(updates, list)
                        and any(
                            isinstance(update, dict) and "timer" in update
                            for update in updates
                        )
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
                self._stream_failures += 1
                if self.data is not None:
                    self._update_repairs(self.data)
                await asyncio.sleep(5)
            except Exception:
                LOGGER.exception("Unexpected BUSY Bar status stream failure")
                self._stream_failures += 1
                if self.data is not None:
                    self._update_repairs(self.data)
                await asyncio.sleep(5)

    def _update_repairs(self, data: BusyBarData) -> None:
        """Refresh proactive device-health issues."""
        from .repairs import async_update_issues

        async_update_issues(
            self.hass,
            self.config_entry,
            data,
            stream_failures=self._stream_failures,
        )

    async def async_shutdown(self) -> None:
        """Stop local work and release the HTTP client."""
        if self._shutdown:
            return
        self._shutdown = True
        await self.async_cancel_effect()
        await self.async_cancel_game()
        await self.display_manager.async_shutdown()
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

    async def async_cancel_game(self) -> None:
        """Cancel a running mini-app and restore underlying content."""
        task = self._game_task
        if task is None or task.done() or task is asyncio.current_task():
            return
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task
        self._game_task = None

    @callback
    def async_add_stream_listener(
        self, listener: Callable[[BusyBarStreamEvent], None]
    ) -> Callable[[], None]:
        """Subscribe to normalized physical and timer events."""
        self._stream_listeners.append(listener)

        @callback
        def remove_listener() -> None:
            with suppress(ValueError):
                self._stream_listeners.remove(listener)

        return remove_listener

    @callback
    def _emit_stream_event(self, event: BusyBarStreamEvent) -> None:
        """Notify entities and device automations about one stream event."""
        event_data = {
            "entry_id": self.config_entry.entry_id,
            "category": event.category,
            "type": event.event_type,
            "source": event.source,
            **event.data,
        }
        self.hass.bus.async_fire(EVENT_BUSYBAR, event_data)
        if self._game_task is not None and not self._game_task.done():
            if self._game_events.full():
                with suppress(asyncio.QueueEmpty):
                    self._game_events.get_nowait()
            self._game_events.put_nowait(event)
        for listener in list(self._stream_listeners):
            listener(event)

    async def _async_draw_immediate(
        self, payload: dict[str, Any], replace: bool
    ) -> None:
        """Draw one compositor-selected layer immediately."""
        payload = {**payload, "application_name": APPLICATION_NAME}
        async with self._draw_lock:
            if replace:
                await self._async_command(
                    self.api.display_clear(application_name=APPLICATION_NAME),
                    "clear Home Assistant display content",
                )
            await self._async_command(
                self.api.display_draw(
                    payload,
                    clear_before_draw=False,
                    sanitize_text=True,
                ),
                "draw on the display",
            )

    async def _async_clear_immediate(self) -> None:
        """Clear Home Assistant-owned display elements immediately."""
        async with self._draw_lock:
            await self._async_command(
                self.api.display_clear(application_name=APPLICATION_NAME),
                "clear the display",
            )

    async def async_draw(
        self,
        payload: dict[str, Any],
        *,
        clear_before_draw: bool = False,
        cancel_effect: bool = True,
        duration: float | None = None,
        restore: bool = True,
        layer_id: str | None = None,
    ) -> str:
        """Draw a validated payload under Home Assistant's application ownership."""
        if cancel_effect:
            await self.async_cancel_effect()
            await self.async_cancel_game()
        payload = {**payload, "application_name": APPLICATION_NAME}
        if duration is None:
            duration = max(
                (
                    float(element.get("timeout", 0))
                    for element in payload.get("elements", [])
                    if isinstance(element, dict)
                ),
                default=0,
            )
        return await self.display_manager.async_present(
            payload,
            duration=duration,
            restore=restore and not clear_before_draw,
            layer_id=layer_id,
        )

    async def async_clear(self) -> None:
        """Clear only Home Assistant-owned display elements."""
        await self.async_cancel_effect()
        await self.async_cancel_game()
        await self.display_manager.async_clear()

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
            ),
            duration=duration,
            layer_id="message" if duration == 0 else None,
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
            ),
            duration=duration,
            layer_id="progress" if duration == 0 else None,
        )

    async def async_show_scene(self, scene: str) -> None:
        """Apply an opinionated status scene."""
        self.active_scene = scene
        await self.async_draw(
            scene_payload(scene, priority=self.default_priority),
            duration=0,
            layer_id="scene",
        )

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
        await self.async_cancel_game()
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

    async def async_play_preset(
        self,
        preset: str,
        *,
        message: str = "",
        duration: float | None = None,
        priority: int | None = None,
    ) -> None:
        """Play one opinionated household moment with useful defaults."""
        spec = preset_spec(preset, message=message)
        await self.async_start_effect(
            spec.effect,
            color=spec.color,
            message=spec.message,
            duration=duration if duration is not None else spec.duration,
            priority=priority if priority is not None else spec.priority,
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
        next_frame_at = asyncio.get_running_loop().time()
        completed = False
        layer_id: str | None = None
        try:
            for frame in effect_frames(
                effect,
                color=color,
                message=message,
                priority=priority,
                fps=fps,
                duration=duration,
            ):
                if layer_id is None:
                    layer_id = await self.async_draw(
                        frame,
                        cancel_effect=False,
                        duration=duration,
                    )
                    self._effect_layer_id = layer_id
                else:
                    await self.display_manager.async_update(layer_id, frame)
                next_frame_at += frame_delay
                await asyncio.sleep(
                    max(0, next_frame_at - asyncio.get_running_loop().time())
                )
            completed = True
        finally:
            if layer_id is not None:
                await self.display_manager.async_dismiss(layer_id)
            self._effect_layer_id = None
            if self._effect_task is asyncio.current_task():
                self._effect_task = None
        if completed:
            LOGGER.debug("BUSY Bar %s effect completed", effect)

    async def async_start_game(
        self,
        game: str,
        *,
        duration: float = 30,
        fps: int = 8,
        mood: str = "happy",
        priority: int | None = None,
    ) -> None:
        """Start a bounded mini-app controlled by the physical Bar."""
        await self.async_cancel_effect()
        await self.async_cancel_game()
        while not self._game_events.empty():
            with suppress(asyncio.QueueEmpty):
                self._game_events.get_nowait()
        self._game_task = self.config_entry.async_create_background_task(
            self.hass,
            self._async_game_loop(
                game,
                duration=duration,
                fps=fps,
                mood=mood,
                priority=priority or self.default_priority,
            ),
            f"{DOMAIN} {game} game",
        )

    async def _async_game_loop(
        self,
        game: str,
        *,
        duration: float,
        fps: int,
        mood: str,
        priority: int,
    ) -> None:
        layer_id: str | None = None

        async def render(payload: dict[str, Any]) -> None:
            nonlocal layer_id
            if layer_id is None:
                layer_id = await self.display_manager.async_present(
                    payload,
                    duration=duration + 5,
                    restore=True,
                )
                self._game_layer_id = layer_id
            else:
                await self.display_manager.async_update(layer_id, payload)

        try:
            await run_game(
                game,
                render,
                self._game_events,
                duration=duration,
                fps=max(2, min(12, fps)),
                mood=mood,
                priority=priority,
            )
        finally:
            if layer_id is not None:
                await self.display_manager.async_dismiss(layer_id)
            self._game_layer_id = None
            if self._game_task is asyncio.current_task():
                self._game_task = None

    async def async_send_key(self, key: str) -> None:
        """Send one virtual key press."""
        await self.async_cancel_effect()
        await self._async_command(
            self.api.input(types.InputKey(key)), f"send {key} key"
        )
        await self.async_request_refresh()

    async def async_play_sound(
        self, *, path: str | None = None, stock_path: str | None = None
    ) -> None:
        """Play an uploaded or stock sound."""
        await self._async_command(
            self.api.audio_play(
                path=path,
                stock_path=stock_path,
                application_name=APPLICATION_NAME,
            ),
            "play audio",
        )

    async def async_upload_asset(self, filename: str, data: bytes) -> None:
        """Upload one already-converted asset into HA's device namespace."""
        digest = hashlib.sha256(data).hexdigest()
        if self._asset_digests.get(filename) == digest:
            return
        await self._async_command(
            self.api.assets_upload(APPLICATION_NAME, filename, data),
            f"upload asset {filename}",
        )
        self._asset_digests[filename] = digest

    async def async_show_asset(
        self,
        filename: str,
        *,
        media_type: str = "image",
        display: str = "front",
        duration: int = 10,
        priority: int | None = None,
        loop: bool = True,
        opacity: int = 100,
        layer_id: str | None = None,
    ) -> str:
        """Show an uploaded image or animation asset."""
        element: dict[str, Any] = {
            "id": "media",
            "type": media_type,
            "path": filename,
            "x": 36 if display == "front" else 80,
            "y": 8 if display == "front" else 40,
            "align": "center",
            "display": display,
            "opacity": opacity,
            "timeout": duration,
        }
        if media_type == "animation":
            element["loop"] = loop
        return await self.async_draw(
            {
                "application_name": APPLICATION_NAME,
                "priority": priority or self.default_priority,
                "elements": [element],
            },
            duration=duration,
            layer_id=layer_id,
        )

    async def async_delete_assets(self) -> None:
        """Delete only assets owned by this integration."""
        await self._async_command(
            self.api.assets_delete(APPLICATION_NAME),
            "delete Home Assistant assets",
        )
        self._asset_digests.clear()

    async def async_start_smart_home_pairing(self) -> None:
        """Open the device pairing window and show its QR code on the rear."""
        from .media import async_qr_png

        response = await self._async_command(
            self.api.smart_home_pairing_start(), "start smart-home pairing"
        )
        pairing_value = response.qr_code or response.manual_code
        if pairing_value:
            filename, data = await async_qr_png(self.hass, pairing_value)
            await self.async_upload_asset(filename, data)
            await self.async_show_asset(
                filename,
                display="back",
                duration=900,
                priority=80,
                layer_id="smart-home-pairing",
            )

    async def async_stop_smart_home_pairing(self) -> None:
        """Close the current smart-home pairing window."""
        await self._async_command(
            self.api.smart_home_pairing_stop(), "stop smart-home pairing"
        )
        await self.display_manager.async_dismiss("smart-home-pairing")

    async def async_stop_sound(self) -> None:
        """Stop audio playback, including when it just finished naturally."""
        try:
            await self.api.audio_stop()
        except BusyBarAPIError as err:
            if err.status_code == 410:
                return
            raise HomeAssistantError(f"Could not stop audio: {err.error}") from err
        except BusyBarError as err:
            raise HomeAssistantError(f"Could not stop audio: {err}") from err

    async def async_check_update(self) -> None:
        """Ask the device to check for firmware updates."""
        await self._async_command(self.api.update_check(), "check for firmware updates")

        async def delayed_refresh() -> None:
            await asyncio.sleep(2)
            await self.async_request_refresh()

        self.config_entry.async_create_background_task(
            self.hass,
            delayed_refresh(),
            f"{DOMAIN} update check refresh",
        )

    async def async_abort_update(self) -> None:
        """Abort an in-progress firmware download."""
        await self._async_command(
            self.api.update_abort_download(), "abort the firmware download"
        )
        await self.async_request_refresh()

    async def async_set_profile(
        self,
        slot: str,
        *,
        title: str,
        timer_type: str,
        minutes: int = 25,
        work_minutes: int = 25,
        rest_minutes: int = 5,
        cycles: int = 4,
        autostart: bool = False,
        theme: str = "busy",
        show_work_only: bool = True,
        trigger_smart_home: bool = True,
    ) -> None:
        """Replace one physical BUSY Bar timer profile."""
        timer_settings: dict[str, Any]
        if timer_type == "infinite":
            timer_settings = {"type": "INFINITE"}
        elif timer_type == "simple":
            timer_settings = {
                "type": "SIMPLE",
                "total_time_ms": minutes * 60_000,
            }
        elif timer_type == "interval":
            timer_settings = {
                "type": "INTERVAL",
                "interval_work_ms": work_minutes * 60_000,
                "interval_rest_ms": rest_minutes * 60_000,
                "interval_work_cycles_count": cycles,
                "is_autostart_enabled": autostart,
            }
        else:
            raise HomeAssistantError(f"Unsupported timer type: {timer_type}")

        existing = self.data.profiles.get(slot)
        profile = types.BusyProfile.model_validate(
            {
                "sort_order": existing.sort_order if existing else -1,
                "title": title,
                "id": existing.id if existing else str(uuid4()),
                "timer_settings": timer_settings,
                "busy_bar_settings": {
                    "theme": theme,
                    "show_work_phase_only": show_work_only,
                    "trigger_smart_home": trigger_smart_home,
                },
                "profile_timestamp_ms": round(time.time() * 1000),
            }
        )
        await self._async_command(
            self.api.busy_profile_set(slot, profile), f"set the {slot} profile"
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
        await self.async_cancel_game()
        await self._async_command(
            self.api.api_request("PUT", "/api/busy/snapshot", json_payload=payload),
            "start the focus timer",
        )
        await self.async_request_refresh()
