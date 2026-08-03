# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""``ProtocolDeliveryReceiptAdapter`` — the OMN-15665 receipt-ack callable.

Authority: Linear comment ``cfb64e0f-c2e6-4ae2-94cf-308c7e1a1efb`` on OMN-15666
(the frozen r2 contract decision) states this OMN-15665 contract is UNCHANGED by
r2: "the unchanged OMN-15665 ``ProtocolDeliveryReceiptAdapter`` contract
``Callable[[], Awaitable[None]] -> None``". The R2 harness pin
(``omninode_infra``'s
``tests/fixtures/omn_15663_r2/target_models.py::ProtocolDeliveryReceiptAdapter``)
reproduces the identical zero-argument shape.

Deliberately a zero-argument awaitable, NOT ``execute_once(context)`` /
``dispose(context)`` — that shape belongs to the separate, context-consuming
disposition-adapter protocols owned by OMN-15663/OMN-15666/OMN-15667
(``ProtocolTerminalDispositionAdapter``). Collapsing the two into one shape was
r1-rejection defect #3 (a mock disposition store wrongly required a non-None
result from *this* protocol) and must never recur.

Per-delivery context is threaded through a **factory**, not through this
protocol's call signature: ``RuntimeDispatch`` accepts an optional
``delivery_receipt_adapter_factory: Callable[[ModelDeliveryContext],
Callable[[], Awaitable[None]]]`` (see ``runtime_dispatch.py``) that closes over
one message's ``ModelDeliveryContext`` and returns a zero-arg callable satisfying
this exact protocol. This reconciles "the adapter needs per-message identity"
with "the adapter's public shape is frozen at zero-arg."
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class ProtocolDeliveryReceiptAdapter(Protocol):
    """Zero-argument, no-return awaitable receipt-ack callable."""

    async def __call__(self) -> None: ...


__all__ = ["ProtocolDeliveryReceiptAdapter"]
