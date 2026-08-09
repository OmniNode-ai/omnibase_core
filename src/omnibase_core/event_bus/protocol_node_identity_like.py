# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Structural duck type for a node-identity-shaped ``subscribe()`` argument.

Split into its own module (from ``event_bus_semantic_fake.py``) to satisfy
the single-class-per-file convention.

.. versionadded:: OMN-15789
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class ProtocolNodeIdentityLike(Protocol):
    """Structural duck type for the ``node_identity`` subscribe() argument.

    Defined locally (not imported from ``omnibase_core.protocols``) because
    the OMN-14340 import-layering ratchet hard-fails any NEW core module
    importing into the ``protocols`` hub -- the same reason
    ``util_consumer_group.compute_consumer_group_id`` takes four explicit
    strings instead of a ``ProtocolNodeIdentity`` object (see that module's
    docstring). ``EventBusInmemory`` predates the ratchet and keeps its
    existing ``ProtocolNodeIdentity`` import; ``EventBusSemanticFake`` (new,
    OMN-15789) does not add a fresh edge into that hub.
    """

    env: str
    service: str
    node_name: str
    version: str


__all__: list[str] = ["ProtocolNodeIdentityLike"]
