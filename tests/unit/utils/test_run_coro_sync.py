# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for util_run_coro_sync.

Graduated from omnibase_compat into omnibase_core (OMN-13763).
Covers the two execution paths: no running loop (asyncio.run) and
running loop (ThreadPoolExecutor dispatch).
"""

import asyncio

import pytest

from omnibase_core.utils.util_run_coro_sync import run_coro_sync


async def _return_value(value: int) -> int:
    return value


async def _raise_error() -> int:
    raise ValueError("expected error")


@pytest.mark.unit
def test_run_coro_sync_no_loop_returns_value() -> None:
    """run_coro_sync runs the cheap path when no event loop is active."""
    result = run_coro_sync(_return_value(42))
    assert result == 42


@pytest.mark.unit
def test_run_coro_sync_no_loop_propagates_exception() -> None:
    """run_coro_sync propagates coroutine exceptions via the cheap path."""
    with pytest.raises(ValueError, match="expected error"):
        run_coro_sync(_raise_error())


@pytest.mark.unit
def test_run_coro_sync_inside_running_loop_returns_value() -> None:
    """run_coro_sync dispatches to a worker thread when a loop is already running."""

    async def _driver() -> int:
        # run_coro_sync must not call asyncio.run on this thread --
        # it detects the running loop and spawns a worker thread instead.
        return run_coro_sync(_return_value(99))

    result = asyncio.run(_driver())
    assert result == 99


@pytest.mark.unit
def test_run_coro_sync_inside_running_loop_propagates_exception() -> None:
    """run_coro_sync propagates coroutine exceptions via the thread-pool path."""

    async def _driver() -> None:
        run_coro_sync(_raise_error())

    with pytest.raises(ValueError, match="expected error"):
        asyncio.run(_driver())
