"""Tests for local physical-control mini-apps."""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest
from busylib import types

from custom_components.busybar.games import run_game
from custom_components.busybar.stream import BusyBarStreamEvent


def _input(category: str, event_type: str, source: str) -> BusyBarStreamEvent:
    return BusyBarStreamEvent(category, event_type, source, {})


@pytest.mark.parametrize("game", ["dice", "coin_flip", "magic_8_ball", "pixel_pet"])
async def test_instant_apps_render_valid_payloads(game: str) -> None:
    """Every one-shot app produces device-valid display elements."""
    frames: list[dict] = []

    async def render(payload: dict) -> None:
        frames.append(payload)

    with patch("custom_components.busybar.games.asyncio.sleep", AsyncMock()):
        await run_game(
            game,
            render,
            asyncio.Queue(),
            duration=2,
            fps=8,
            mood="cool",
        )
    assert len(frames) == 1
    types.DisplayElements.model_validate(frames[0])


async def test_reaction_detects_an_early_physical_press() -> None:
    """A queued local button event drives the reaction-game branch."""
    events: asyncio.Queue[BusyBarStreamEvent] = asyncio.Queue()
    events.put_nowait(_input("button", "press", "ok"))
    frames: list[dict] = []

    async def render(payload: dict) -> None:
        frames.append(payload)

    with patch("custom_components.busybar.games.asyncio.sleep", AsyncMock()):
        await run_game("reaction", render, events, duration=4, fps=8)
    assert len(frames) == 2
    assert frames[-1]["elements"][-1]["text"] == "TOO SOON!"


@pytest.mark.parametrize(
    ("game", "event"),
    [
        ("pong", _input("encoder", "clockwise", "encoder")),
        ("snake", _input("encoder", "counterclockwise", "encoder")),
    ],
)
async def test_interactive_games_consume_encoder_events(
    game: str, event: BusyBarStreamEvent
) -> None:
    """Pong and Snake can render a physical-input-driven frame."""
    events: asyncio.Queue[BusyBarStreamEvent] = asyncio.Queue()
    events.put_nowait(event)
    frames: list[dict] = []

    async def render(payload: dict) -> None:
        frames.append(payload)

    with (
        patch(
            "custom_components.busybar.games.time.monotonic",
            side_effect=[0.0, 0.0, 2.0],
        ),
        patch("custom_components.busybar.games.asyncio.sleep", AsyncMock()),
    ):
        await run_game(game, render, events, duration=1, fps=8)
    assert len(frames) == 1
    types.DisplayElements.model_validate(frames[0])
