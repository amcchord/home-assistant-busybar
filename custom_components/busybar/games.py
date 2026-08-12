"""Tiny local-first apps and games for the BUSY Bar."""

from __future__ import annotations

import asyncio
import random
import time
from collections.abc import Awaitable, Callable
from typing import Any

from .effects import _background, _base, _rect, _text, message_payload
from .stream import BusyBarStreamEvent

GAMES = (
    "dice",
    "coin_flip",
    "magic_8_ball",
    "reaction",
    "pong",
    "snake",
    "pixel_pet",
)

type RenderCallback = Callable[[dict[str, Any]], Awaitable[None]]


async def run_game(
    game: str,
    render: RenderCallback,
    events: asyncio.Queue[BusyBarStreamEvent],
    *,
    duration: float,
    fps: int,
    mood: str = "happy",
    priority: int = 50,
) -> None:
    """Run one bounded app, consuming only local physical-input events."""
    if game not in GAMES:
        raise ValueError(f"Unknown game: {game}")
    if game in {"dice", "coin_flip", "magic_8_ball", "pixel_pet"}:
        await _run_instant(game, render, duration, mood, priority)
    elif game == "reaction":
        await _run_reaction(render, events, duration, priority)
    elif game == "pong":
        await _run_pong(render, events, duration, fps, priority)
    else:
        await _run_snake(render, events, duration, fps, priority)


async def _run_instant(
    game: str,
    render: RenderCallback,
    duration: float,
    mood: str,
    priority: int,
) -> None:
    rng = random.SystemRandom()
    if game == "dice":
        value = f"DICE: {rng.randint(1, 6)}"
        color = "#FDE047FF"
    elif game == "coin_flip":
        value = rng.choice(("HEADS", "TAILS"))
        color = "#F59E0BFF"
    elif game == "magic_8_ball":
        value = rng.choice(("YES", "NO", "MAYBE", "ASK LATER", "ABSOLUTELY"))
        color = "#A78BFAFF"
    else:
        pets = {
            "happy": "(^_^)",
            "sleepy": "(-_-) zZ",
            "excited": "\\(^o^)/",
            "sad": "(T_T)",
            "busy": "(>_<)",
            "cool": "B-)",
        }
        value = pets.get(mood, pets["happy"])
        color = "#4ADE80FF"
    await render(
        message_payload(
            value,
            color=color,
            background="#111827FF",
            priority=priority,
            duration=max(1, round(duration)),
            scroll=False,
        )
    )
    await asyncio.sleep(duration)


async def _run_reaction(
    render: RenderCallback,
    events: asyncio.Queue[BusyBarStreamEvent],
    duration: float,
    priority: int,
) -> None:
    await render(
        message_payload(
            "WAIT...",
            color="#FDE047FF",
            background="#450A0AFF",
            priority=priority,
            duration=0,
            scroll=False,
        )
    )
    wait = random.SystemRandom().uniform(1.5, min(4.0, max(1.6, duration / 2)))
    if await _wait_for_press(events, wait):
        await render(
            message_payload(
                "TOO SOON!",
                color="#FFFFFFFF",
                background="#DC2626FF",
                priority=priority,
                duration=2,
            )
        )
        await asyncio.sleep(2)
        return
    await render(
        message_payload(
            "GO!",
            color="#FFFFFFFF",
            background="#16A34AFF",
            priority=priority,
            duration=0,
            scroll=False,
        )
    )
    started = time.monotonic()
    if await _wait_for_press(events, max(1.0, duration - wait)):
        elapsed = round((time.monotonic() - started) * 1000)
        result = f"{elapsed} ms"
        background = "#052E16FF"
    else:
        result = "MISSED!"
        background = "#450A0AFF"
    await render(
        message_payload(
            result,
            color="#FFFFFFFF",
            background=background,
            priority=priority,
            duration=3,
            scroll=False,
        )
    )
    await asyncio.sleep(3)


async def _run_pong(
    render: RenderCallback,
    events: asyncio.Queue[BusyBarStreamEvent],
    duration: float,
    fps: int,
    priority: int,
) -> None:
    paddle_y = 5
    ball_x, ball_y = 35.0, 7.0
    velocity_x, velocity_y = 1.5, 0.75
    score = 0
    deadline = time.monotonic() + duration
    while time.monotonic() < deadline:
        for event in _drain(events):
            if event.category == "encoder":
                paddle_y += 2 if event.event_type == "clockwise" else -2
            elif event.category == "button" and event.event_type == "press":
                paddle_y += 2 if event.source == "ok" else -2
        paddle_y = max(0, min(10, paddle_y))
        ball_x += velocity_x
        ball_y += velocity_y
        if ball_y <= 0 or ball_y >= 14:
            velocity_y *= -1
            ball_y = max(0, min(14, ball_y))
        if ball_x >= 69:
            velocity_x *= -1
        if ball_x <= 3:
            if paddle_y - 1 <= ball_y <= paddle_y + 7:
                velocity_x = abs(velocity_x) + 0.05
                score += 1
            else:
                ball_x, ball_y = 35.0, 7.0
                velocity_x = abs(velocity_x)

        elements = [
            _background("#020617FF"),
            _rect("paddle", 1, paddle_y, 2, 6, "#22D3EEFF"),
            _rect(
                "opponent", 69, max(0, min(10, round(ball_y - 3))), 2, 6, "#F43F5EFF"
            ),
            _rect("ball", round(ball_x), round(ball_y), 2, 2, "#FFFFFFFF"),
            _text(str(score), "#64748BFF", element_id="score", scroll=False),
        ]
        await render(_base(priority, elements))
        await asyncio.sleep(1 / fps)


async def _run_snake(
    render: RenderCallback,
    events: asyncio.Queue[BusyBarStreamEvent],
    duration: float,
    fps: int,
    priority: int,
) -> None:
    rng = random.Random(0x5A4E)
    snake = [(18, 4), (17, 4), (16, 4)]
    direction = (1, 0)
    food = (rng.randrange(2, 34), rng.randrange(1, 7))
    deadline = time.monotonic() + duration
    while time.monotonic() < deadline:
        for event in _drain(events):
            if event.category == "encoder":
                dx, dy = direction
                direction = (-dy, dx) if event.event_type == "clockwise" else (dy, -dx)
        head = ((snake[0][0] + direction[0]) % 36, (snake[0][1] + direction[1]) % 8)
        if head in snake:
            snake = [(18, 4), (17, 4), (16, 4)]
            direction = (1, 0)
        else:
            snake.insert(0, head)
            if head == food:
                while food in snake:
                    food = (rng.randrange(0, 36), rng.randrange(0, 8))
            else:
                snake.pop()
        elements = [_background("#020617FF")]
        elements.extend(
            _rect(f"snake-{index}", x * 2, y * 2, 2, 2, "#4ADE80FF")
            for index, (x, y) in enumerate(snake[:28])
        )
        elements.append(_rect("food", food[0] * 2, food[1] * 2, 2, 2, "#F43F5EFF"))
        await render(_base(priority, elements))
        await asyncio.sleep(max(0.08, 2 / fps))


async def _wait_for_press(
    events: asyncio.Queue[BusyBarStreamEvent], timeout_seconds: float
) -> bool:
    deadline = time.monotonic() + timeout_seconds
    while (remaining := deadline - time.monotonic()) > 0:
        try:
            event = await asyncio.wait_for(events.get(), remaining)
        except TimeoutError:
            return False
        if event.category == "button" and event.event_type == "press":
            return True
    return False


def _drain(
    events: asyncio.Queue[BusyBarStreamEvent],
) -> list[BusyBarStreamEvent]:
    drained: list[BusyBarStreamEvent] = []
    while not events.empty():
        try:
            drained.append(events.get_nowait())
        except asyncio.QueueEmpty:
            break
    return drained
