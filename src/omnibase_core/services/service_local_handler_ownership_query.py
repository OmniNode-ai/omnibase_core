# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Ownership query — does THIS runtime host the node owning this handler?

Phase 1 semantics: "hosted here" is resolved against the set of locally
discovered contracts — i.e. the frozen `node_name` set produced by
`discover_contracts()` at manifest boot. No SQL call is made.

Why no projection read:
    The ``registration_projections`` table (omnibase_infra/docker/migrations/
    forward/001_registration_projection.sql:51-108) carries entity_id +
    node_type + state but no ``runtime_id`` column. Cluster-level ownership
    therefore cannot be answered from the projection today; "hosted here"
    operationally means "did the local manifest see this contract at boot."

Forward-compat:
    A future ``ServiceClusterHandlerOwnershipQuery`` — implementing the same
    ``ProtocolHandlerOwnershipQuery`` shape over a runtime-aware projection —
    is deliberately left as follow-on work once runtime identity is modeled
    explicitly. See plan §"Forward-Compat Seams".

Layering:
    This module is intentionally free of ``omnibase_spi`` imports. The Round 3
    layering ruling forbids core→spi. The protocol-conformance check
    (isinstance against ``ProtocolHandlerOwnershipQuery``) is performed at the
    infra boundary (see ``omnibase_infra/runtime/auto_wiring/handler_wiring.py``
    in Task 5), NOT here. Callers in core rely on the duck-typed
    ``is_owned_here(node_name: str) -> bool`` shape.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ServiceLocalHandlerOwnershipQuery(BaseModel):
    """Answer Phase 1 ownership via local set-membership.

    Construction is frozen — the ``local_node_names`` set passed at init time
    is immutable for the lifetime of the service. Callers pre-compute this set
    from ``ModelAutoWiringManifest`` at boot.

    Attributes:
        local_node_names: Frozen set of ``node_name`` strings the local runtime
            discovered via ``discover_contracts()`` at boot. Membership in
            this set IS the Phase 1 ownership answer.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    local_node_names: frozenset[str] = Field(
        ...,
        description=(
            "Frozen set of node_name strings discovered locally at boot. "
            "Membership in this set is the Phase 1 definition of 'hosted here'."
        ),
    )

    def is_owned_here(self, node_name: str) -> bool:
        """Return True iff ``node_name`` is in the locally discovered set.

        Pure in-memory set-membership. No I/O, no SQL, no projection reads.
        Deterministic and idempotent — safe to call from hot paths.

        Args:
            node_name: The node name to check for local ownership.

        Returns:
            True if the local manifest saw this contract at boot, else False.
        """
        return node_name in self.local_node_names
