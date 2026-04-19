# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Unit test: get_service_sync() must not crash when called from an async context.

Handler __init__ methods are inherently sync (Python has no ``async __init__``)
but run during async auto-wiring. They call ``container.get_service_sync(...)``
for DI resolution. Prior to this fix the container used ``asyncio.run()``
internally, which raises ``RuntimeError: asyncio.run() cannot be called from
a running event loop`` in that scenario, breaking all auto-wiring.
"""

from __future__ import annotations

import asyncio

import pytest

from omnibase_core.models.container.model_onex_container import (
    create_model_onex_container,
)


@pytest.mark.unit
def test_get_service_sync_from_running_event_loop() -> None:
    """Calling get_service_sync from inside asyncio.run() must not raise."""

    async def _scenario() -> None:
        container = await create_model_onex_container()
        # This call happens SYNCHRONOUSLY inside a running event loop —
        # the same conditions handler __init__ runs under during auto-wiring.
        # Requesting an unregistered protocol is fine; we only care that the
        # asyncio.run() inside get_service_sync doesn't raise.
        try:
            container.get_service_sync(type("UnregisteredProtocol", (), {}))
        except RuntimeError as exc:
            if "asyncio.run() cannot be called from a running event loop" in str(exc):
                pytest.fail(
                    "get_service_sync raised the forbidden asyncio.run() "
                    "RuntimeError when called from within a running event loop; "
                    "it must dispatch the coroutine to a worker thread instead."
                )
            # Any other RuntimeError (e.g. service-not-found) is allowed —
            # we only guard against the async-context regression.
        except Exception:  # noqa: BLE001
            # Unrelated resolution failures (service not found etc.) are fine;
            # this test asserts ONLY the async-context invariant.
            pass

    asyncio.run(_scenario())
