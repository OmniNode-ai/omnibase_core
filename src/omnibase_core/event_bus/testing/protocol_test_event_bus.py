# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Local structural protocol for the ``event_bus_substrate`` contract tests.

Split into its own module (from ``contract_event_bus_substrate.py``) to
satisfy the single-class-per-file convention.

.. versionadded:: OMN-15789
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Protocol, runtime_checkable

from omnibase_core.event_bus.testing.protocol_test_event_message import (
    ProtocolTestEventMessage,
)
from omnibase_core.event_bus.testing.protocol_test_node_identity import (
    ProtocolTestNodeIdentity,
)


@runtime_checkable
class ProtocolTestEventBus(Protocol):
    """The substrate surface the shared contract tests actually call.

    Deliberately NOT the canonical ``ProtocolEventBus``: under mypy --strict,
    none of the three concrete substrates (``EventBusInmemory``,
    ``EventBusSemanticFake``, ``EventBusKafka``) statically satisfy that
    protocol as declared today -- e.g. its ``publish_envelope`` wants a
    ``ProtocolEventEnvelope`` with a ``get_payload()`` method, but every
    concrete ``publish_envelope`` takes a plain ``object`` and every concrete
    ``ModelEventEnvelope`` has no such method; its ``adapter`` property wants
    a ``ProtocolKafkaEventBusAdapter``, but the in-process substrates return
    ``self``. All three are ``ProtocolEventBus``-conformant by DUCK TYPING at
    runtime per ONEX convention (see each class's own docstring); nothing in
    this repo declares a ``-> ProtocolEventBus`` return type today, so this
    static/duck-typing gap is pre-existing and out of OMN-15789's scope to
    re-litigate. This local Protocol instead matches the concrete signatures
    every substrate actually implements, including the ``auto_offset_reset``
    extension that ``EventBusSemanticFake`` (in ``omnibase_core``) and
    ``EventBusKafka`` (infra-side extension, see that repo's PR) add to
    ``subscribe()`` beyond the canonical protocol -- the same way
    ``EventBusInmemory`` already adds ``group_id``/``required_for_readiness``
    beyond it.
    """

    async def publish(
        self,
        topic: str,
        key: bytes | None,
        value: bytes,
    ) -> None: ...

    async def publish_envelope(
        self,
        envelope: object,
        topic: str,
    ) -> None: ...

    async def subscribe(
        self,
        topic: str,
        node_identity: ProtocolTestNodeIdentity | None = ...,
        on_message: Callable[[ProtocolTestEventMessage], Awaitable[None]] | None = ...,
        *,
        auto_offset_reset: str = ...,
    ) -> Callable[[], Awaitable[None]]: ...


__all__: list[str] = ["ProtocolTestEventBus"]
