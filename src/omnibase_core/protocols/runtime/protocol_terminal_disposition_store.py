# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""``ProtocolTerminalDispositionStore`` — the OMN-15666 replay-safety seam.

The durable, identity-keyed store that makes terminal disposition idempotent:
replaying a source record after an ambiguous process death must yield the ONE
already-durable terminal receipt, never a second divergent terminal outcome
(OMN-15666 acceptance criterion 7).

The key is the exact authoritative source identity carried on the OMN-15665
``ModelDeliveryContext`` — ``(envelope_id, topic, partition, offset)``. A
distinct ``source_offset`` is always a distinct event.

Generic over the context and receipt types, with no imports beyond ``typing``,
so a concrete implementation binds structurally without adding a
``protocols -> models`` edge (frozen at ``FROZEN_PROTOCOLS_MODELS_MAX = 65``,
``scripts/ci/check_import_ratchet.py``).
"""

from __future__ import annotations

from typing import Protocol, TypeVar, runtime_checkable

_ContextT_contra = TypeVar("_ContextT_contra", contravariant=True)
# Invariant on purpose: the receipt is both loaded (return position) and saved
# (parameter position), so neither variance is sound here.
_ReceiptT = TypeVar("_ReceiptT")


@runtime_checkable
class ProtocolTerminalDispositionStore(Protocol[_ContextT_contra, _ReceiptT]):
    """Durable terminal-disposition record, keyed by authoritative source identity."""

    async def load(self, context: _ContextT_contra) -> _ReceiptT | None:
        """Return the already-durable receipt for this source identity, if any."""
        ...

    async def save(self, context: _ContextT_contra, receipt: _ReceiptT) -> None:
        """Durably record the terminal receipt against this source identity."""
        ...


__all__ = ["ProtocolTerminalDispositionStore"]
