"""Helpers for fire-and-forget asyncio tasks.

A bare ``asyncio.create_task`` call keeps no strong reference, so the task can be
garbage-collected mid-flight and is silently lost on shutdown. Everything that
must outlive the request uses :func:`spawn`.
"""
import asyncio
from typing import Any, Coroutine, Set

_background_tasks: Set["asyncio.Task[Any]"] = set()


def spawn(coro: Coroutine[Any, Any, Any]) -> "asyncio.Task[Any]":
    """Schedules ``coro`` and retains a reference until it completes."""
    task = asyncio.create_task(coro)
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)
    return task


def pending_count() -> int:
    """Number of background tasks still tracked (used by tests/diagnostics)."""
    return len(_background_tasks)


async def drain(timeout: float = 5.0) -> None:
    """Best-effort wait for outstanding background tasks (graceful shutdown)."""
    if not _background_tasks:
        return
    await asyncio.wait(list(_background_tasks), timeout=timeout)
