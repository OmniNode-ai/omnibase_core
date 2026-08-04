# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""``ProtocolTerminalDispositionAdapter`` — the OMN-15666 terminal-disposition seam.

Authority: Linear comment ``cfb64e0f-c2e6-4ae2-94cf-308c7e1a1efb`` on OMN-15666 —
"Generic ``ProtocolTerminalDispositionAdapter`` executes once by the exact
``ModelDeliveryContext`` identity and returns the typed terminal receipt. It is
separate from the unchanged OMN-15665 ``ProtocolDeliveryReceiptAdapter``
contract ``Callable[[], Awaitable[None]] -> None``."

That separation is load-bearing, not stylistic: collapsing the two shapes into
one was r1-rejection defect #3 (a mock disposition store wrongly required a
non-``None`` result from the zero-arg OMN-15665 receipt protocol). The two
protocols answer different questions — ``ProtocolDeliveryReceiptAdapter`` acks a
SUCCESSFUL delivery and returns nothing; this one terminalizes an EXHAUSTED one
and must return the typed receipt that licenses the commit.

Declared with plain ``TypeVar``s and no imports beyond ``typing`` so it adds
neither a ``protocols -> models`` edge (frozen at 65) nor a new importer into
the ``protocols`` hub (hard-fail) — ``scripts/ci/check_import_ratchet.py``.
Concrete implementations bind ``ModelDeliveryContext``,
``ModelTerminalDispositionRequest``, and the receipt union structurally.

``execute_once`` is idempotent BY the exact source identity carried on the
context: replaying the same ``(envelope_id, topic, partition, offset)`` after an
ambiguous process death must return the one already-durable terminal receipt and
publish nothing further (OMN-15666 acceptance criterion 7).
"""

from __future__ import annotations

from typing import Protocol, TypeVar, runtime_checkable

_ContextT_contra = TypeVar("_ContextT_contra", contravariant=True)
_RequestT_contra = TypeVar("_RequestT_contra", contravariant=True)
_ReceiptT_co = TypeVar("_ReceiptT_co", covariant=True)


@runtime_checkable
class ProtocolTerminalDispositionAdapter(
    Protocol[_ContextT_contra, _RequestT_contra, _ReceiptT_co]
):
    """Executes one terminal disposition, once per authoritative source identity."""

    async def execute_once(
        self,
        context: _ContextT_contra,
        request: _RequestT_contra,
        /,
    ) -> _ReceiptT_co:
        """Terminalize ``request``, keyed idempotently by ``context``'s identity.

        Returns the typed terminal receipt — the ONLY thing that licenses
        committing the source offset. Raises when neither sink became durable;
        the caller must then leave the source offset uncommitted.
        """
        ...


__all__ = ["ProtocolTerminalDispositionAdapter"]
