# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Structural protocol for the canonical delivery context (OMN-15665).

Declared purely structurally (read-only properties typed with stdlib ``UUID`` /
``str`` / ``int`` only) so this module imports **no** ``omnibase_core.models``
symbol — a new ``protocols -> models`` edge is frozen at its ceiling (OMN-14340
growth ratchet, ``scripts/ci/check_import_ratchet.py``: ``FROZEN_PROTOCOLS_MODELS_MAX
= 65``) and a new edge hard-fails CI. The concrete
``omnibase_core.models.runtime.model_delivery_context.ModelDeliveryContext``
satisfies this protocol structurally (duck typing via ``runtime_checkable``)
without either side importing the other.

This is the public Core-resident structural seam the OMN-15665 acceptance
criteria call for: "the concrete ``ModelDeliveryContext`` satisfies that protocol
statically and at runtime."
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable
from uuid import UUID


@runtime_checkable
class ProtocolDeliveryContext(Protocol):
    """Read-only, four-field structural shape of one inbound record's identity.

    Deliberately NOT importable-by / dependent-on the disposition-adapter
    protocols (OMN-15663/OMN-15666/OMN-15667 territory) — this protocol describes
    identity only, never a terminal-disposition outcome.
    """

    @property
    def envelope_id(self) -> UUID:
        """The inbound envelope's own authoritative id, as delivered."""
        ...

    @property
    def topic(self) -> str:
        """Source topic the record was polled from."""
        ...

    @property
    def partition(self) -> int:
        """Partition the record belongs to."""
        ...

    @property
    def offset(self) -> int:
        """Monotonic per-partition offset of the record."""
        ...


__all__ = ["ProtocolDeliveryContext"]
