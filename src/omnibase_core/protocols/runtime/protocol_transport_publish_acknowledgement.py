# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Structural protocol for a broker publish acknowledgement (OMN-15666).

Declared purely structurally (read-only properties typed with stdlib ``str`` /
``int`` only) so this module imports **no** ``omnibase_core.models`` symbol — a
new ``protocols -> models`` edge is frozen at its ceiling
(``scripts/ci/check_import_ratchet.py``: ``FROZEN_PROTOCOLS_MODELS_MAX = 65``)
and a new edge hard-fails CI. The concrete
``omnibase_core.models.event_bus.model_transport_publish_acknowledgement.ModelTransportPublishAcknowledgement``
satisfies this protocol structurally, without either side importing the other.

Authority: Linear comment ``cfb64e0f-c2e6-4ae2-94cf-308c7e1a1efb`` on OMN-15666
("Public structural ``ProtocolTransportPublishAcknowledgement``").

DELIBERATE DEVIATION from the same comment's next clause
("``ProtocolTransportProducer.send`` returns that acknowledgement"): that clause
is NOT implemented, and ``ProtocolTransportProducer`` is left byte-identical.
Changing its ``send`` return type from ``None`` to an acknowledgement breaks
every existing implementation's type conformance across repo boundaries
(``omnibase_core``'s ``InMemoryTransport``, ``omnibase_infra``'s
``kafka_transport``) — the exact CORE-PASS / CROSS-REPO-FAIL defect class the
2026-08-02 lane died on and that OMN-15665 landed an optional/defaulted kwarg
specifically to avoid repeating. Acknowledged publishing is therefore an
ADDITIVE, opt-in seam: the dual-sink primitive takes a ``publish`` callable
returning this acknowledgement, injected by the composition root. None of
OMN-15666's falsifiable acceptance criteria require mutating
``ProtocolTransportProducer``; a coordinated breaking two-repo landing of that
protocol is left to its own ticket.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class ProtocolTransportPublishAcknowledgement(Protocol):
    """Read-only, three-field structural shape of a broker acknowledgement."""

    @property
    def topic(self) -> str:
        """Topic the broker acknowledged the publish on."""
        ...

    @property
    def partition(self) -> int:
        """Partition assigned by the broker acknowledgement."""
        ...

    @property
    def offset(self) -> int:
        """Offset assigned by the broker acknowledgement."""
        ...


__all__ = ["ProtocolTransportPublishAcknowledgement"]
