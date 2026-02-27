# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Protocol for tiered authenticated dependency resolution.

Defines the interface for resolving capability dependencies through
ordered trust tiers. Implementations wrap a base capability resolver
with tier escalation logic, trust domain scoping, and deterministic
registry snapshot hashing.

.. versionadded:: 0.21.0
    Phase 2 of authenticated dependency resolution (OMN-2891).
"""

from __future__ import annotations

__all__ = ["ProtocolTieredResolver"]

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from omnibase_core.models.capabilities.model_capability_dependency import (
        ModelCapabilityDependency,
    )
    from omnibase_core.models.routing.model_tiered_resolution_result import (
        ModelTieredResolutionResult,
    )
    from omnibase_core.models.routing.model_trust_domain import ModelTrustDomain


@runtime_checkable
class ProtocolTieredResolver(Protocol):
    """Protocol for tiered dependency resolution with trust domain scoping.

    Tiered resolution iterates through trust domains ordered by tier,
    scoping the provider registry to each domain before delegating to
    a base capability resolver. The first tier that yields a successful
    resolution wins; if all tiers are exhausted, resolution fails closed.

    Determinism:
        ``compute_registry_snapshot_hash()`` provides a BLAKE3 hash of
        the sorted provider descriptors for a given capability. Combined
        with the policy bundle hash and trust graph hash, this guarantees
        that identical inputs produce identical ``ModelRoutePlan`` outputs.

    .. versionadded:: 0.21.0
    """

    def resolve_tiered(
        self,
        dependency: ModelCapabilityDependency,
        trust_domains: list[ModelTrustDomain],
        policy_bundle: object | None = None,
    ) -> ModelTieredResolutionResult:
        """Resolve a dependency through ordered trust tiers.

        Iterates through trust domains ordered by tier, attempting
        resolution at each tier. The first successful resolution is
        returned. If all tiers are exhausted, returns a fail-closed
        result with ``structured_failure=TIER_EXHAUSTED``.

        Args:
            dependency: The capability dependency to resolve.
            trust_domains: Trust domains to attempt, resolved in tier order.
            policy_bundle: Optional policy bundle for classification gates.
                Accepts any object to allow future policy bundle types
                without coupling to a specific model (Phase 4).

        Returns:
            A ``ModelTieredResolutionResult`` containing the route plan
            (on success) or structured failure information.
        """
        ...

    def compute_registry_snapshot_hash(
        self,
        capability: str,
    ) -> str:
        """Compute a deterministic hash of registry state for a capability.

        Produces a BLAKE3 hash of the sorted provider descriptors that
        offer the given capability. This hash is a determinism input to
        ``ModelRoutePlan`` and ensures that identical registry state
        yields identical resolution outcomes.

        Args:
            capability: The capability identifier to snapshot.

        Returns:
            Hex-encoded BLAKE3 digest of the sorted provider descriptors.
        """
        ...
