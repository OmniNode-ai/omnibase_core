# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Minimal event-bus surface required by the Pattern B dispatch client."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Protocol, runtime_checkable

from omnibase_core.enums.enum_consumer_group_purpose import EnumConsumerGroupPurpose
from omnibase_core.models.event_bus.model_event_headers import ModelEventHeaders
from omnibase_core.models.event_bus.model_event_message import ModelEventMessage
from omnibase_core.protocols.event_bus.protocol_node_identity import (
    ProtocolNodeIdentity,
)


@runtime_checkable
class ProtocolDispatchBusClientTransport(Protocol):
    """Duck-typed publish/subscribe surface used by DispatchBusClient."""

    async def publish(
        self,
        topic: str,
        key: bytes | None,
        value: bytes,
        headers: ModelEventHeaders | None = None,
    ) -> None:
        pass

    async def subscribe(
        self,
        topic: str,
        node_identity: ProtocolNodeIdentity | None = None,
        on_message: Callable[[ModelEventMessage], Awaitable[None]] | None = None,
        *,
        group_id: str | None = None,
        purpose: EnumConsumerGroupPurpose = EnumConsumerGroupPurpose.CONSUME,
        required_for_readiness: bool = False,
    ) -> Callable[[], Awaitable[None]]:
        pass


__all__ = ["ProtocolDispatchBusClientTransport"]
