# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Structural protocol for a message pulled from a transport.

Net-new, currently UNUSED (ticket OMN-14719, epic OMN-14717).

The transport protocols speak in terms of this structural shape rather than
importing the concrete ``ModelTransportMessage`` from ``omnibase_core.models``. This
mirrors the existing ``ProtocolLocalRuntimeMessage`` convention in this directory and
keeps the ``protocols`` layer free of a ``protocols -> models`` import edge — that
edge family is frozen at its ceiling by the OMN-14340 growth ratchet
(``scripts/ci/check_import_ratchet.py``), so a new one would hard-fail CI. Dependency
inversion resolves it: the concrete
``omnibase_core.models.runtime.model_transport_message.ModelTransportMessage``
structurally satisfies this protocol without the protocol importing it.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol, runtime_checkable


@runtime_checkable
class ProtocolTransportMessage(Protocol):
    """Read-only shape of a message pulled from a transport.

    The runtime groups a poll batch by ``partition`` and orders by ``offset`` to
    commit a contiguous per-partition prefix; it treats ``ack_token`` as opaque.
    """

    topic: str
    """Source topic the message was polled from."""

    partition: int
    """Partition the message belongs to (per-partition identity)."""

    offset: int
    """Monotonic per-partition offset coordinate of the message."""

    key: bytes | None
    """Raw partition / routing key, or None when the message is unkeyed."""

    value: bytes
    """Raw message payload bytes."""

    headers: Mapping[str, bytes]
    """Raw transport headers (header name -> raw bytes)."""

    ack_token: object
    """Opaque commit / redeliver cursor the runtime hands back unmodified."""


__all__ = ["ProtocolTransportMessage"]
