"""Tests for priority-aware display composition."""

import asyncio

from custom_components.busybar.display_manager import BusyBarDisplayManager


def _payload(name: str, priority: int) -> dict:
    return {
        "name": name,
        "priority": priority,
        "elements": [{"id": name, "type": "text", "text": name}],
    }


async def test_priority_and_restoration() -> None:
    """Lower layers wait, and dismissing an alert restores prior content."""
    draws: list[tuple[str, bool]] = []
    clears = 0

    async def draw(payload: dict, replace: bool) -> None:
        draws.append((payload["name"], replace))

    async def clear() -> None:
        nonlocal clears
        clears += 1

    manager = BusyBarDisplayManager(
        draw,
        clear,
        lambda coro, name: asyncio.create_task(coro, name=name),
    )
    ambient = await manager.async_present(_payload("ambient", 20))
    alert = await manager.async_present(_payload("alert", 90))
    lower = await manager.async_present(_payload("lower", 10))
    assert draws == [("ambient", True), ("alert", True)]
    assert manager.active_layer_id == alert

    await manager.async_dismiss(alert)
    assert draws[-1] == ("ambient", True)
    await manager.async_dismiss(ambient)
    assert draws[-1] == ("lower", True)
    await manager.async_dismiss(lower)
    assert clears == 1
    await manager.async_shutdown()


async def test_temporary_layer_expires_and_restores() -> None:
    """Expiry redraws the persistent layer rather than leaving a blank Bar."""
    draws: list[tuple[str, bool]] = []

    async def draw(payload: dict, replace: bool) -> None:
        draws.append((payload["name"], replace))

    async def clear() -> None:
        return None

    manager = BusyBarDisplayManager(
        draw,
        clear,
        lambda coro, name: asyncio.create_task(coro, name=name),
    )
    await manager.async_present(_payload("ambient", 20))
    await manager.async_present(_payload("temporary", 50), duration=0.01)
    await asyncio.sleep(0.03)
    assert draws == [
        ("ambient", True),
        ("temporary", True),
        ("ambient", True),
    ]
    await manager.async_shutdown()


async def test_active_layer_updates_without_clearing_between_frames() -> None:
    """Animation frames update in place while layer changes replace content."""
    draws: list[tuple[str, bool]] = []

    async def draw(payload: dict, replace: bool) -> None:
        draws.append((payload["name"], replace))

    async def clear() -> None:
        return None

    manager = BusyBarDisplayManager(
        draw,
        clear,
        lambda coro, name: asyncio.create_task(coro, name=name),
    )
    layer_id = await manager.async_present(_payload("frame-1", 50))
    await manager.async_update(layer_id, _payload("frame-2", 50))

    assert draws == [("frame-1", True), ("frame-2", False)]
    await manager.async_shutdown()
