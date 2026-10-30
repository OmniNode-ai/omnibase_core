# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Bus protocol of the node announcement step (OMN-21589)."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Protocol, TypeVar, runtime_checkable

MessageT_co = TypeVar("MessageT_co", covariant=True)


@runtime_checkable
class ProtocolAnnounceBus(Protocol[MessageT_co]):
    """The three bus operations the announcer and the catalog need.

    The lane overlay binds an implementation: core's in-memory bus before the
    container exists, or a durable bus. The protocol is generic in the message type
    the bus delivers, so core's in-memory bus (``ModelEventMessage``) and a durable
    bus bind without an adapter and without this protocol importing either.
    """

    async def start(self) -> None:
        """Make the bus ready to publish and deliver."""
        ...

    async def publish(self, topic: str, key: bytes | None, value: bytes) -> None:
        """Publish one message."""
        ...

    async def subscribe(
        self,
        topic: str,
        *,
        on_message: Callable[[MessageT_co], Awaitable[None]],
        group_id: str,
    ) -> Callable[[], Awaitable[None]]:
        """Subscribe to a topic; the returned callable cancels the subscription."""
        ...
