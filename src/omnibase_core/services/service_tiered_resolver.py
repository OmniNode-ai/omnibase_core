# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tiered resolution service wrapping ServiceCapabilityResolver.

Implements trust-domain-scoped, tiered dependency resolution by
iterating through trust domains ordered by tier, scoping the provider
registry to each domain via ``FilteredProviderRegistry``, and delegating
to the base ``ServiceCapabilityResolver``.

Algorithm:
    1. Sort trust domains by tier order.
    2. For each tier:
       a. Scope registry to trust domain (FilteredProviderRegistry).
       b. Check classification gates (if policy bundle present).
       c. Verify capability tokens (if tier > local_exact) -- Phase 3 stub.
       d. Delegate to base ServiceCapabilityResolver.
       e. If success: build ModelRoutePlan with hop, return result.
       f. Else: record ModelTierAttempt, continue.
    3. If all tiers exhausted: return fail-closed result with TIER_EXHAUSTED.

Design:
    Composition, not modification. Existing ``ServiceCapabilityResolver``
    callers are unaffected. This service wraps the base resolver and
    adds tier escalation logic on top.

Determinism:
    ``compute_registry_snapshot_hash()`` produces a BLAKE3 hash of
    sorted provider descriptors for a capability. Combined with the
    policy bundle hash and trust graph hash, identical inputs yield
    identical ``ModelRoutePlan`` outputs.

.. versionadded:: 0.21.0
    Phase 2 of authenticated dependency resolution (OMN-2891).
"""

from __future__ import annotations

__all__ = ["ServiceTieredResolver"]

import hashlib
import json
import logging
import time
from datetime import UTC, datetime
from uuid import uuid4

from omnibase_core.crypto.crypto_blake3_hasher import hash_bytes
from omnibase_core.enums.enum_resolution_failure_code import EnumResolutionFailureCode
from omnibase_core.enums.enum_resolution_tier import EnumResolutionTier
from omnibase_core.models.bindings.model_resolution_result import ModelResolutionResult
from omnibase_core.models.capabilities.model_capability_dependency import (
    ModelCapabilityDependency,
)
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.routing.model_hop_constraints import ModelHopConstraints
from omnibase_core.models.routing.model_resolution_route_hop import (
    ModelResolutionRouteHop,
)
from omnibase_core.models.routing.model_route_plan import ModelRoutePlan
from omnibase_core.models.routing.model_tier_attempt import ModelTierAttempt
from omnibase_core.models.routing.model_tiered_resolution_result import (
    ModelTieredResolutionResult,
)
from omnibase_core.models.routing.model_trust_domain import ModelTrustDomain
from omnibase_core.protocols.crypto.protocol_key_provider import ProtocolKeyProvider
from omnibase_core.protocols.resolution.protocol_capability_resolver import (
    ProtocolProviderRegistry,
)
from omnibase_core.services.registry.filtered_provider_registry import (
    FilteredProviderRegistry,
)
from omnibase_core.services.service_capability_resolver import (
    ServiceCapabilityResolver,
)

logger = logging.getLogger(__name__)

# Canonical tier ordering for escalation
_TIER_ORDER: list[EnumResolutionTier] = [
    EnumResolutionTier.LOCAL_EXACT,
    EnumResolutionTier.LOCAL_COMPATIBLE,
    EnumResolutionTier.ORG_TRUSTED,
    EnumResolutionTier.FEDERATED_TRUSTED,
    EnumResolutionTier.QUARANTINE,
]


def _compute_trust_graph_hash(trust_domains: list[ModelTrustDomain]) -> str:
    """Compute a deterministic SHA-256 hash of the trust domain graph.

    Sorts domains by domain_id for determinism, then hashes the canonical
    JSON representation.

    Args:
        trust_domains: The trust domains to hash.

    Returns:
        Hex-encoded SHA-256 digest prefixed with ``sha256:``.
    """
    sorted_domains = sorted(trust_domains, key=lambda d: d.domain_id)
    serializable = [
        {
            "domain_id": d.domain_id,
            "tier": d.tier.value,
            "trust_root_public_key": d.trust_root_public_key,
            "allowed_capabilities": sorted(d.allowed_capabilities),
            "policy_bundle_hash": d.policy_bundle_hash,
        }
        for d in sorted_domains
    ]
    canonical = json.dumps(serializable, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


class ServiceTieredResolver:
    """Tiered resolution service wrapping ``ServiceCapabilityResolver``.

    Resolves capability dependencies through ordered trust tiers, scoping
    the provider registry to each trust domain before delegating to the
    base flat resolver. The first tier that yields a successful resolution
    wins; if all tiers are exhausted, resolution fails closed.

    Args:
        base_resolver: The flat capability resolver to delegate to.
        registry: The provider registry to query.
        key_provider: Optional key provider for token verification
            (Phase 3 integration point). Currently unused.

    Thread Safety:
        Stateless after construction. Thread safety depends on the
        underlying registry and resolver implementations.

    .. versionadded:: 0.21.0
    """

    def __init__(
        self,
        base_resolver: ServiceCapabilityResolver,
        registry: ProtocolProviderRegistry,
        key_provider: ProtocolKeyProvider | None = None,
    ) -> None:
        self._base_resolver = base_resolver
        self._registry = registry
        self._key_provider = key_provider

    def resolve_tiered(
        self,
        dependency: ModelCapabilityDependency,
        trust_domains: list[ModelTrustDomain],
        policy_bundle: object | None = None,
    ) -> ModelTieredResolutionResult:
        """Resolve a dependency through ordered trust tiers.

        Iterates through trust domains ordered by tier, attempting
        resolution at each. Returns the first successful result or
        a fail-closed result if all tiers are exhausted.

        Args:
            dependency: The capability dependency to resolve.
            trust_domains: Trust domains to attempt, resolved in tier order.
            policy_bundle: Optional policy bundle for classification gates
                (Phase 4 integration point). Currently used only for
                hash computation.

        Returns:
            A ``ModelTieredResolutionResult`` containing the route plan
            (on success) or structured failure information.
        """
        if not trust_domains:
            return self._fail_closed_result(
                dependency=dependency,
                tier_attempts=[],
                failure_code=EnumResolutionFailureCode.TIER_EXHAUSTED,
                failure_reason="No trust domains configured",
                trust_domains=trust_domains,
                policy_bundle=policy_bundle,
            )

        # Sort trust domains by canonical tier order
        sorted_domains = sorted(
            trust_domains,
            key=lambda d: _TIER_ORDER.index(d.tier)
            if d.tier in _TIER_ORDER
            else len(_TIER_ORDER),
        )

        tier_attempts: list[ModelTierAttempt] = []

        for domain in sorted_domains:
            tier_start = time.perf_counter()
            attempt_timestamp = datetime.now(UTC)

            # Check classification gates (Phase 4 stub)
            if policy_bundle is not None:
                gate_result = self._check_classification_gates(domain, policy_bundle)
                if gate_result is not None:
                    tier_end = time.perf_counter()
                    duration_ms = (tier_end - tier_start) * 1000
                    tier_attempts.append(
                        ModelTierAttempt(
                            tier=domain.tier,
                            attempted_at=attempt_timestamp,
                            candidates_found=0,
                            candidates_after_trust_filter=0,
                            failure_code=EnumResolutionFailureCode.POLICY_DENIED,
                            failure_reason=gate_result,
                            duration_ms=duration_ms,
                        )
                    )
                    continue

            # Scope registry to trust domain
            filtered_registry = FilteredProviderRegistry(self._registry, domain)

            # Check how many candidates are available
            all_providers = filtered_registry.get_providers_for_capability(
                dependency.capability
            )
            candidates_found = len(all_providers)

            if candidates_found == 0:
                tier_end = time.perf_counter()
                duration_ms = (tier_end - tier_start) * 1000
                tier_attempts.append(
                    ModelTierAttempt(
                        tier=domain.tier,
                        attempted_at=attempt_timestamp,
                        candidates_found=0,
                        candidates_after_trust_filter=0,
                        failure_code=EnumResolutionFailureCode.NO_MATCH,
                        failure_reason=(
                            f"No providers for '{dependency.capability}' "
                            f"in domain '{domain.domain_id}'"
                        ),
                        duration_ms=duration_ms,
                    )
                )
                continue

            # Delegate to base resolver
            try:
                base_result = self._base_resolver.resolve_all(
                    [dependency], filtered_registry
                )
            except ModelOnexError:
                tier_end = time.perf_counter()
                duration_ms = (tier_end - tier_start) * 1000
                tier_attempts.append(
                    ModelTierAttempt(
                        tier=domain.tier,
                        attempted_at=attempt_timestamp,
                        candidates_found=candidates_found,
                        candidates_after_trust_filter=candidates_found,
                        failure_code=EnumResolutionFailureCode.NO_MATCH,
                        failure_reason=(
                            f"Base resolver failed for '{dependency.capability}' "
                            f"in domain '{domain.domain_id}'"
                        ),
                        duration_ms=duration_ms,
                    )
                )
                continue

            if base_result.is_successful and dependency.alias in base_result.bindings:
                tier_end = time.perf_counter()
                duration_ms = (tier_end - tier_start) * 1000

                # Record successful tier attempt
                tier_attempts.append(
                    ModelTierAttempt(
                        tier=domain.tier,
                        attempted_at=attempt_timestamp,
                        candidates_found=candidates_found,
                        candidates_after_trust_filter=candidates_found,
                        failure_code=None,
                        failure_reason=None,
                        duration_ms=duration_ms,
                    )
                )

                # Build route plan
                binding = base_result.bindings[dependency.alias]
                registry_snapshot_hash = self.compute_registry_snapshot_hash(
                    dependency.capability
                )
                trust_graph_hash = _compute_trust_graph_hash(trust_domains)
                policy_hash = self._get_policy_bundle_hash(policy_bundle, trust_domains)

                hop = ModelResolutionRouteHop(
                    hop_index=0,
                    adapter_id=binding.adapter,
                    trust_domain=domain.domain_id,
                    tier=domain.tier,
                    required_proofs=self._get_required_proofs(domain.tier),
                    constraints=ModelHopConstraints(),
                )

                route_plan = ModelRoutePlan(
                    plan_id=uuid4(),
                    hops=[hop],
                    source_capability=dependency.capability,
                    resolved_at=datetime.now(UTC),
                    resolution_tier_used=domain.tier,
                    tier_progression=tier_attempts,
                    registry_snapshot_hash=registry_snapshot_hash,
                    policy_bundle_hash=policy_hash,
                    trust_graph_hash=trust_graph_hash,
                )

                return ModelTieredResolutionResult(
                    route_plan=route_plan,
                    base_resolution=base_result,
                    tier_progression=tier_attempts,
                    final_tier=domain.tier,
                    fail_closed=True,
                    structured_failure=None,
                )

            # Resolution failed at this tier
            tier_end = time.perf_counter()
            duration_ms = (tier_end - tier_start) * 1000
            failure_reason = (
                "; ".join(base_result.errors) if base_result.errors else "No match"
            )
            tier_attempts.append(
                ModelTierAttempt(
                    tier=domain.tier,
                    attempted_at=attempt_timestamp,
                    candidates_found=candidates_found,
                    candidates_after_trust_filter=candidates_found,
                    failure_code=EnumResolutionFailureCode.NO_MATCH,
                    failure_reason=failure_reason,
                    duration_ms=duration_ms,
                )
            )

        # All tiers exhausted
        return self._fail_closed_result(
            dependency=dependency,
            tier_attempts=tier_attempts,
            failure_code=EnumResolutionFailureCode.TIER_EXHAUSTED,
            failure_reason="All configured tiers attempted without resolution",
            trust_domains=trust_domains,
            policy_bundle=policy_bundle,
        )

    def compute_registry_snapshot_hash(self, capability: str) -> str:
        """Compute a BLAKE3 hash of the registry state for a capability.

        Queries the underlying (unfiltered) registry for all providers
        offering the capability, sorts them deterministically by
        provider_id, serializes to canonical JSON, and produces a
        BLAKE3 hash.

        Args:
            capability: The capability identifier to snapshot.

        Returns:
            Hex-encoded BLAKE3 digest prefixed with ``blake3:``.
        """
        providers = self._registry.get_providers_for_capability(capability)
        sorted_providers = sorted(providers, key=lambda p: str(p.provider_id))

        serializable = [
            {
                "provider_id": str(p.provider_id),
                "capabilities": sorted(p.capabilities),
                "adapter": p.adapter,
                "connection_ref": p.connection_ref,
                "attributes": dict(sorted(p.attributes.items()))
                if p.attributes
                else {},
            }
            for p in sorted_providers
        ]

        canonical = json.dumps(serializable, sort_keys=True, separators=(",", ":"))
        digest = hash_bytes(canonical.encode("utf-8"))
        return f"blake3:{digest}"

    def _fail_closed_result(
        self,
        dependency: ModelCapabilityDependency,
        tier_attempts: list[ModelTierAttempt],
        failure_code: EnumResolutionFailureCode,
        failure_reason: str,
        trust_domains: list[ModelTrustDomain],
        policy_bundle: object | None,
    ) -> ModelTieredResolutionResult:
        """Build a fail-closed result when resolution cannot proceed.

        Args:
            dependency: The dependency that failed to resolve.
            tier_attempts: All tier attempts made before failure.
            failure_code: The structured failure code.
            failure_reason: Human-readable failure reason.
            trust_domains: The trust domains that were configured.
            policy_bundle: The policy bundle (for hash computation).

        Returns:
            A fail-closed ``ModelTieredResolutionResult``.
        """
        final_tier = tier_attempts[-1].tier if tier_attempts else None

        base_result = ModelResolutionResult(
            bindings={},
            success=False,
            errors=[failure_reason],
        )

        return ModelTieredResolutionResult(
            route_plan=None,
            base_resolution=base_result,
            tier_progression=tier_attempts,
            final_tier=final_tier,
            fail_closed=True,
            structured_failure=failure_code,
        )

    def _check_classification_gates(
        self,
        domain: ModelTrustDomain,
        policy_bundle: object,
    ) -> str | None:
        """Check classification gates for a domain.

        Phase 4 integration point. Currently returns None (all gates
        pass). When Phase 4 is implemented, this will inspect the
        policy bundle's classification gates and verify the domain's
        tier is allowed for the data classification.

        Args:
            domain: The trust domain being checked.
            policy_bundle: The policy bundle with classification gates.

        Returns:
            None if all gates pass, or a failure reason string.
        """
        # TODO(OMN-2893): Implement classification gate checks (Phase 4).
        return None

    def _get_required_proofs(self, tier: EnumResolutionTier) -> list[str]:
        """Determine required proofs for a given tier.

        Higher tiers require progressively stronger proofs.

        Args:
            tier: The resolution tier.

        Returns:
            List of proof type identifiers required at this tier.
        """
        proof_map: dict[EnumResolutionTier, list[str]] = {
            EnumResolutionTier.LOCAL_EXACT: [],
            EnumResolutionTier.LOCAL_COMPATIBLE: ["node_identity"],
            EnumResolutionTier.ORG_TRUSTED: ["node_identity", "org_membership"],
            EnumResolutionTier.FEDERATED_TRUSTED: [
                "node_identity",
                "capability_attested",
            ],
            EnumResolutionTier.QUARANTINE: [
                "node_identity",
                "capability_attested",
                "policy_compliance",
            ],
        }
        return proof_map.get(tier, [])

    def _get_policy_bundle_hash(
        self,
        policy_bundle: object | None,
        trust_domains: list[ModelTrustDomain],
    ) -> str:
        """Get the policy bundle hash for determinism inputs.

        If a policy bundle is provided and has a ``compute_hash()`` method,
        calls it. Otherwise falls back to the first trust domain's
        policy_bundle_hash, or a default empty hash.

        Args:
            policy_bundle: Optional policy bundle object.
            trust_domains: The trust domains (fallback source for hash).

        Returns:
            Policy bundle hash string.
        """
        if policy_bundle is not None:
            compute_hash = getattr(policy_bundle, "compute_hash", None)
            if callable(compute_hash):
                return str(compute_hash())

        # Fall back to first trust domain's policy_bundle_hash
        if trust_domains:
            return trust_domains[0].policy_bundle_hash

        return "sha256:none"

    def __repr__(self) -> str:
        """Return representation for debugging."""
        return (
            f"ServiceTieredResolver("
            f"base_resolver={self._base_resolver!r}, "
            f"has_key_provider={self._key_provider is not None})"
        )

    def __str__(self) -> str:
        """Return string representation."""
        return "ServiceTieredResolver"
