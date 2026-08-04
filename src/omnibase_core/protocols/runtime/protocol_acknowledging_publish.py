# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""``ProtocolAcknowledgingPublish`` — the OMN-15666 acknowledged-publish binding.

The ONE publish shape a mock sink and a real Kafka producer both satisfy, so the
dual-sink scenario table runs unchanged against either. Generic over the
acknowledgement type and declared with no imports beyond ``typing``: a concrete
``omnibase_core.models.event_bus.model_transport_publish_acknowledgement.ModelTransportPublishAcknowledgement``
binds structurally without adding a ``protocols -> models`` edge (frozen at
``FROZEN_PROTOCOLS_MODELS_MAX = 65``, ``scripts/ci/check_import_ratchet.py``).

Deliberately keyword-only, and ``headers`` is a SEQUENCE of pairs, never a
mapping: a mapping silently collapses repeated header names and can reorder
them — exactly the loss OMN-15667's ``source_headers_b64`` exists to prevent.

Distinct from ``ProtocolTransportProducer``, which is left byte-identical
(``send -> None``). See ``protocol_transport_publish_acknowledgement.py`` for
why acknowledged publishing is an additive opt-in seam rather than a mutation
of that protocol.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol, TypeVar, runtime_checkable

_AckT_co = TypeVar("_AckT_co", covariant=True)


@runtime_checkable
class ProtocolAcknowledgingPublish(Protocol[_AckT_co]):
    """Publish one record and return the BROKER's acknowledgement.

    Raising is the only admissible "not durable" signal. Returning normally
    means the broker acknowledged; the returned coordinates are the sole
    evidence a terminal receipt may be built from.
    """

    async def __call__(
        self,
        *,
        topic: str,
        key: bytes | None,
        value: bytes,
        headers: Sequence[tuple[str, bytes]],
    ) -> _AckT_co: ...


__all__ = ["ProtocolAcknowledgingPublish"]
