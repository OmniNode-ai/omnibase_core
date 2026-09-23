# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Protocol for local runtime event bus interactions."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Protocol, runtime_checkable

from omnibase_core.protocols.runtime.protocol_local_runtime_message import (
    ProtocolLocalRuntimeMessage,
)

UnsubscribeCallback = Callable[[], Awaitable[None]]


@runtime_checkable
class ProtocolLocalRuntimeBus(Protocol):
    """Minimal event bus shape used by ``RuntimeLocal``."""

    async def start(self) -> None:
        """Start the bus."""
        ...

    async def close(self) -> None:
        """Close the bus."""
        ...

    async def publish(self, topic: str, key: object, value: bytes) -> object:
        """Publish serialized bytes to a topic."""
        ...

    async def subscribe(
        self,
        topic: str,
        *,
        on_message: Callable[[ProtocolLocalRuntimeMessage], Awaitable[None]],
        group_id: str,
    ) -> UnsubscribeCallback:
        """Subscribe to a topic and return an unsubscribe callback."""
        ...


__all__: list[str] = ["ProtocolLocalRuntimeBus", "UnsubscribeCallback"]
