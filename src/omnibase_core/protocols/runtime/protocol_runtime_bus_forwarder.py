# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Protocol for the forwarder that carries a runtime-local in-memory bus's recorded events to the hosted bus."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol, TypeVar, runtime_checkable

EventT_contra = TypeVar("EventT_contra", contravariant=True)
ReceiptT_co = TypeVar("ReceiptT_co", covariant=True)


@runtime_checkable
class ProtocolRuntimeBusForwarder(Protocol[EventT_contra, ReceiptT_co]):
    """Carries the events a runtime-local in-memory bus recorded to the hosted bus.

    Registered under the ``onex.runtime_bus_forwarders`` entry-point group.
    An implementation answers ``ModelRuntimeBusForwardReceipt``.
    """

    def forward(self, events: Sequence[EventT_contra]) -> ReceiptT_co:
        """Carry the recorded events to the hosted bus (sync; the runtime calls it in a worker thread)."""
        ...


__all__ = ["EventT_contra", "ReceiptT_co", "ProtocolRuntimeBusForwarder"]
