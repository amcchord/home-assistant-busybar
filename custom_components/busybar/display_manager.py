"""Priority-aware display composition for BUSY Bar."""

from __future__ import annotations

import asyncio
import math
import time
from collections.abc import Awaitable, Callable, Coroutine
from contextlib import suppress
from copy import deepcopy
from dataclasses import dataclass
from typing import Any
from uuid import uuid4

type DisplayPayload = dict[str, Any]
type DrawCallback = Callable[[DisplayPayload, bool], Awaitable[None]]
type ClearCallback = Callable[[], Awaitable[None]]
type TaskFactory = Callable[[Coroutine[Any, Any, None], str], asyncio.Task[None]]


@dataclass(slots=True)
class DisplayLayer:
    """One Home Assistant-owned layer in the display stack."""

    layer_id: str
    payload: DisplayPayload
    priority: int
    sequence: int
    expires_at: float | None

    @property
    def remaining(self) -> float | None:
        """Return remaining lifetime in seconds."""
        if self.expires_at is None:
            return None
        return max(0.0, self.expires_at - time.monotonic())


class BusyBarDisplayManager:
    """Serialize, prioritize, expire, and restore Home Assistant content."""

    def __init__(
        self,
        draw: DrawCallback,
        clear: ClearCallback,
        create_task: TaskFactory,
    ) -> None:
        """Initialize the display manager."""
        self._draw = draw
        self._clear = clear
        self._create_task = create_task
        self._layers: dict[str, DisplayLayer] = {}
        self._active_layer_id: str | None = None
        self._sequence = 0
        self._expiry_task: asyncio.Task[None] | None = None
        self._lock = asyncio.Lock()
        self._shutdown = False

    @property
    def active_layer_id(self) -> str | None:
        """Return the currently rendered layer identifier."""
        return self._active_layer_id

    @property
    def layer_count(self) -> int:
        """Return the number of live display layers."""
        return len(self._layers)

    async def async_present(
        self,
        payload: DisplayPayload,
        *,
        duration: float = 0,
        restore: bool = True,
        layer_id: str | None = None,
    ) -> str:
        """Add content and render it when it wins display priority."""
        if self._shutdown:
            raise RuntimeError("Display manager is shut down")

        layer_id = layer_id or uuid4().hex
        priority = int(payload.get("priority", 50))
        expires_at = time.monotonic() + duration if duration > 0 else None

        async with self._lock:
            previous_layers = self._layers.copy()
            previous_active = self._active_layer_id
            if not restore:
                self._layers.clear()
            self._sequence += 1
            self._layers[layer_id] = DisplayLayer(
                layer_id=layer_id,
                payload=deepcopy(payload),
                priority=priority,
                sequence=self._sequence,
                expires_at=expires_at,
            )
            next_active = self._select_active()
            try:
                if next_active and (
                    next_active.layer_id != previous_active
                    or next_active.layer_id == layer_id
                ):
                    await self._render(next_active, replace=True)
                    self._active_layer_id = next_active.layer_id
            except Exception:
                self._layers = previous_layers
                self._active_layer_id = previous_active
                raise
            self._reschedule_expiry()
        return layer_id

    async def async_update(
        self, layer_id: str, payload: DisplayPayload, *, duration: float | None = None
    ) -> None:
        """Update an existing layer, rendering it when active."""
        async with self._lock:
            layer = self._layers.get(layer_id)
            if layer is None:
                return
            layer.payload = deepcopy(payload)
            layer.priority = int(payload.get("priority", layer.priority))
            if duration is not None:
                layer.expires_at = time.monotonic() + duration if duration > 0 else None
            next_active = self._select_active()
            if next_active is None:
                await self._clear()
                self._active_layer_id = None
            elif (
                next_active.layer_id != self._active_layer_id
                or next_active.layer_id == layer_id
            ):
                await self._render(
                    next_active,
                    replace=next_active.layer_id != self._active_layer_id,
                )
                self._active_layer_id = next_active.layer_id
            self._reschedule_expiry()

    async def async_dismiss(self, layer_id: str) -> None:
        """Remove a layer and restore the next eligible layer."""
        async with self._lock:
            was_active = layer_id == self._active_layer_id
            self._layers.pop(layer_id, None)
            self._remove_expired()
            if was_active:
                await self._render_selected()
            self._reschedule_expiry()

    async def async_clear(self) -> None:
        """Remove every Home Assistant-owned layer and clear the device."""
        async with self._lock:
            self._layers.clear()
            self._active_layer_id = None
            self._cancel_expiry()
            await self._clear()

    async def async_shutdown(self) -> None:
        """Stop local scheduling without mutating the device display."""
        self._shutdown = True
        task = self._expiry_task
        self._cancel_expiry()
        if task is not None and not task.done():
            with suppress(asyncio.CancelledError):
                await task
        self._expiry_task = None

    def _select_active(self) -> DisplayLayer | None:
        self._remove_expired()
        if not self._layers:
            return None
        return max(
            self._layers.values(),
            key=lambda layer: (layer.priority, layer.sequence),
        )

    def _remove_expired(self) -> None:
        now = time.monotonic()
        expired = [
            layer_id
            for layer_id, layer in self._layers.items()
            if layer.expires_at is not None and layer.expires_at <= now
        ]
        for layer_id in expired:
            self._layers.pop(layer_id, None)

    async def _render_selected(self) -> None:
        next_active = self._select_active()
        if next_active is None:
            await self._clear()
            self._active_layer_id = None
            return
        await self._render(next_active, replace=True)
        self._active_layer_id = next_active.layer_id

    async def _render(self, layer: DisplayLayer, *, replace: bool) -> None:
        payload = deepcopy(layer.payload)
        if (remaining := layer.remaining) is not None:
            timeout = max(1, math.ceil(remaining))
            for element in payload.get("elements", []):
                if isinstance(element, dict):
                    element["timeout"] = timeout
        await self._draw(payload, replace)

    def _reschedule_expiry(self) -> None:
        self._cancel_expiry()
        deadlines = [
            layer.expires_at
            for layer in self._layers.values()
            if layer.expires_at is not None
        ]
        if not deadlines or self._shutdown:
            return
        delay = max(0.0, min(deadlines) - time.monotonic())
        self._expiry_task = self._create_task(
            self._async_expire_after(delay), "BUSY Bar display layer expiry"
        )

    def _cancel_expiry(self) -> None:
        task = self._expiry_task
        if task is not None and task is not asyncio.current_task() and not task.done():
            task.cancel()
        self._expiry_task = None

    async def _async_expire_after(self, delay: float) -> None:
        try:
            await asyncio.sleep(delay)
            async with self._lock:
                previous_active = self._active_layer_id
                self._remove_expired()
                next_active = self._select_active()
                next_active_id = next_active.layer_id if next_active else None
                if next_active_id != previous_active:
                    await self._render_selected()
                self._reschedule_expiry()
        except asyncio.CancelledError:
            raise
