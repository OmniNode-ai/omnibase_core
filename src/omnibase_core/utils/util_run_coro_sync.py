# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Sync-from-async coroutine runner.

Graduated from ``omnibase_compat.concurrency.util_run_coro_sync`` (OMN-13763)
into ``omnibase_core`` so the core->spi->infra spine no longer depends on
``omnibase_compat`` for this primitive.

The underlying problem: ``asyncio.run()`` raises ``RuntimeError`` when invoked
from inside a running event loop. That case arises during async auto-wiring
when handler ``__init__`` methods (which are inherently sync -- Python does not
allow ``async __init__``) call container helpers such as
``get_service_sync(...)`` while the enclosing wiring coroutine is being
awaited.

See plan ``docs/plans/2026-04-19-runtime-permanent-fix-and-regression-guard-part-1.md``
Task 2 and Linear ticket OMN-9237.
"""

from __future__ import annotations

import asyncio
import concurrent.futures
from collections.abc import Coroutine
from typing import Any


def run_coro_sync[T](coro: Coroutine[Any, Any, T]) -> T:
    """Run a coroutine to completion from sync code, safe inside a running loop.

    Returns the coroutine's result. Safe from both sync AND async contexts --
    the coroutine is awaited exactly once.

    When no event loop is running in the calling thread, the coroutine is
    executed via ``asyncio.run()`` -- the cheap path. When a loop IS running,
    the coroutine is dispatched to a short-lived worker thread with its own
    event loop via ``concurrent.futures.ThreadPoolExecutor(max_workers=1)``,
    and the calling thread blocks on the resulting future's ``.result()``
    until the coroutine completes. This is O(thread-spawn); callers that can
    await directly should prefer the async equivalent.

    Exceptions raised inside ``coro`` propagate unchanged to the caller along
    either path.

    Args:
        coro: A coroutine object (i.e. ``some_async_fn(...)``). The coroutine
            is awaited exactly once by this helper; do not await it elsewhere.

    Returns:
        The value returned by awaiting ``coro``.
    """
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        # No running loop -- cheap path.
        return asyncio.run(coro)

    # Running loop detected -- dispatch to a worker thread with its own loop.
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        return executor.submit(asyncio.run, coro).result()
