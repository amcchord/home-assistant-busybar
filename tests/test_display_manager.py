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
    draws: list[str] = []
    clears = 0

    async def draw(payload: dict) -> None:
        draws.append(payload["name"])

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
    assert draws == ["ambient", "alert"]
    assert manager.active_layer_id == alert

    await manager.async_dismiss(alert)
    assert draws[-1] == "ambient"
    await manager.async_dismiss(ambient)
    assert draws[-1] == "lower"
    await manager.async_dismiss(lower)
    assert clears == 1
    await manager.async_shutdown()


async def test_temporary_layer_expires_and_restores() -> None:
    """Expiry redraws the persistent layer rather than leaving a blank Bar."""
    draws: list[str] = []

    async def draw(payload: dict) -> None:
        draws.append(payload["name"])

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
    assert draws == ["ambient", "temporary", "ambient"]
    await manager.async_shutdown()
