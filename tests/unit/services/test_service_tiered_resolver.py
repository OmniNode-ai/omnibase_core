# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for ServiceTieredResolver.

Tests cover:
- Tier 1 only (regression: equivalent to flat resolver)
- Tier progression: providers at tier 3, tiers 1-2 empty
- Fail-closed: no match at any tier -> structured failure with tier_exhausted
- Determinism: same inputs -> same RoutePlan
- Filtered registry: only providers in domain are visible
- Empty trust domains

.. versionadded:: 0.21.0
    Phase 2 of authenticated dependency resolution (OMN-2891).
"""

from __future__ import annotations

from typing import Any
from uuid import uuid4

import pytest

from omnibase_core.enums.enum_resolution_failure_code import EnumResolutionFailureCode
from omnibase_core.enums.enum_resolution_tier import EnumResolutionTier
from omnibase_core.models.capabilities.model_capability_dependency import (
    ModelCapabilityDependency,
)

# Import ModelHealthStatus FIRST to avoid circular import issues.
from omnibase_core.models.health.model_health_status import (
    ModelHealthStatus,  # noqa: F401 - imported for forward reference resolution
)
from omnibase_core.models.providers.model_provider_descriptor import (
    ModelProviderDescriptor,
)
from omnibase_core.models.routing.model_trust_domain import ModelTrustDomain
from omnibase_core.services.registry.filtered_provider_registry import (
    FilteredProviderRegistry,
)
from omnibase_core.services.service_capability_resolver import (
    ServiceCapabilityResolver,
)
from omnibase_core.services.service_tiered_resolver import ServiceTieredResolver

# =============================================================================
# Mock Implementations
# =============================================================================


class MockProviderRegistry:
    """Mock implementation of ProtocolProviderRegistry for testing."""

    def __init__(self, providers: list[Any] | None = None) -> None:
        self.providers: list[Any] = providers or []

    def get_providers_for_capability(self, capability: str) -> list[Any]:
        return [p for p in self.providers if capability in p.capabilities]


# =============================================================================
# Fixtures
# =============================================================================


def _make_provider(
    capability: str,
    provider_id_str: str | None = None,
    attributes: dict[str, Any] | None = None,
) -> ModelProviderDescriptor:
    """Create a test provider descriptor."""
    pid = (
        uuid4() if provider_id_str is None else __import__("uuid").UUID(provider_id_str)
    )
    return ModelProviderDescriptor(
        provider_id=pid,
        capabilities=[capability],
        adapter="test.adapters.TestAdapter",
        connection_ref="env://TEST_DSN",
        attributes=attributes or {},
    )


def _make_trust_domain(
    domain_id: str,
    tier: EnumResolutionTier,
    allowed_capabilities: list[str] | None = None,
    policy_bundle_hash: str = "sha256:test-policy-hash",
) -> ModelTrustDomain:
    """Create a test trust domain."""
    return ModelTrustDomain(
        domain_id=domain_id,
        tier=tier,
        trust_root_public_key="dGVzdC1wdWJsaWMta2V5",  # base64 "test-public-key"
        allowed_capabilities=allowed_capabilities or [],
        policy_bundle_hash=policy_bundle_hash,
    )


def _make_dependency(
    alias: str = "db",
    capability: str = "database.relational",
) -> ModelCapabilityDependency:
    """Create a test capability dependency."""
    return ModelCapabilityDependency(
        alias=alias,
        capability=capability,
        selection_policy="best_score",
    )


# =============================================================================
# Tests: Tier 1 Only (Regression - Equivalent to Flat Resolver)
# =============================================================================


@pytest.mark.unit
class TestTier1Regression:
    """Verify that single-tier resolution produces equivalent results to flat."""

    def test_single_local_exact_tier_resolves(self) -> None:
        """A single LOCAL_EXACT domain with a matching provider resolves."""
        provider = _make_provider("database.relational")
        registry = MockProviderRegistry([provider])
        resolver = ServiceTieredResolver(
            base_resolver=ServiceCapabilityResolver(),
            registry=registry,
        )

        domain = _make_trust_domain("local.default", EnumResolutionTier.LOCAL_EXACT)
        dep = _make_dependency()

        result = resolver.resolve_tiered(dep, [domain])

        assert result.route_plan is not None
        assert result.final_tier == EnumResolutionTier.LOCAL_EXACT
        assert result.structured_failure is None
        assert result.fail_closed is True
        assert len(result.tier_progression) == 1
        assert result.tier_progression[0].failure_code is None

        # Route plan checks
        plan = result.route_plan
        assert len(plan.hops) == 1
        assert plan.hops[0].tier == EnumResolutionTier.LOCAL_EXACT
        assert plan.hops[0].trust_domain == "local.default"
        assert plan.source_capability == "database.relational"
        assert plan.registry_snapshot_hash.startswith("blake3:")
        assert plan.policy_bundle_hash.startswith("sha256:")
        assert plan.trust_graph_hash.startswith("sha256:")

    def test_single_tier_binding_matches_flat_resolver(self) -> None:
        """The binding from tiered resolution matches what flat resolver would produce."""
        provider = _make_provider("database.relational")
        registry = MockProviderRegistry([provider])
        base_resolver = ServiceCapabilityResolver()

        # Flat resolution
        dep = _make_dependency()
        flat_binding = base_resolver.resolve(dep, registry)

        # Tiered resolution
        tiered = ServiceTieredResolver(
            base_resolver=base_resolver,
            registry=registry,
        )
        domain = _make_trust_domain("local.default", EnumResolutionTier.LOCAL_EXACT)
        result = tiered.resolve_tiered(dep, [domain])

        assert result.base_resolution.is_successful
        tiered_binding = result.base_resolution.bindings[dep.alias]
        assert tiered_binding.resolved_provider == flat_binding.resolved_provider
        assert tiered_binding.adapter == flat_binding.adapter


# =============================================================================
# Tests: Tier Progression
# =============================================================================


@pytest.mark.unit
class TestTierProgression:
    """Verify resolution escalates through tiers correctly."""

    def test_providers_at_tier_3_skip_tiers_1_2(self) -> None:
        """Providers only at ORG_TRUSTED tier; tiers 1-2 should fail then 3 succeeds."""
        provider = _make_provider("database.relational")
        registry = MockProviderRegistry([provider])

        resolver = ServiceTieredResolver(
            base_resolver=ServiceCapabilityResolver(),
            registry=registry,
        )

        # Tier 1 and 2 have no matching capabilities in their domain
        domain_local = _make_trust_domain(
            "local.default",
            EnumResolutionTier.LOCAL_EXACT,
            allowed_capabilities=["cache.*"],  # no database
        )
        domain_compat = _make_trust_domain(
            "local.compat",
            EnumResolutionTier.LOCAL_COMPATIBLE,
            allowed_capabilities=["messaging.*"],  # no database
        )
        # Tier 3 allows database
        domain_org = _make_trust_domain(
            "org.omninode",
            EnumResolutionTier.ORG_TRUSTED,
            allowed_capabilities=["database.*"],
        )

        dep = _make_dependency()
        result = resolver.resolve_tiered(dep, [domain_local, domain_compat, domain_org])

        assert result.route_plan is not None
        assert result.final_tier == EnumResolutionTier.ORG_TRUSTED
        assert len(result.tier_progression) == 3

        # First two attempts failed
        assert (
            result.tier_progression[0].failure_code
            == EnumResolutionFailureCode.NO_MATCH
        )
        assert (
            result.tier_progression[1].failure_code
            == EnumResolutionFailureCode.NO_MATCH
        )
        # Third succeeded
        assert result.tier_progression[2].failure_code is None

        # Route plan hop should be at org tier
        assert result.route_plan.hops[0].tier == EnumResolutionTier.ORG_TRUSTED
        assert result.route_plan.hops[0].trust_domain == "org.omninode"

    def test_tier_ordering_is_canonical(self) -> None:
        """Trust domains are sorted by canonical tier order regardless of input order."""
        provider = _make_provider("database.relational")
        registry = MockProviderRegistry([provider])
        resolver = ServiceTieredResolver(
            base_resolver=ServiceCapabilityResolver(),
            registry=registry,
        )

        # Provide in reverse order
        domain_fed = _make_trust_domain(
            "fed.partner",
            EnumResolutionTier.FEDERATED_TRUSTED,
        )
        domain_local = _make_trust_domain(
            "local.default",
            EnumResolutionTier.LOCAL_EXACT,
        )

        dep = _make_dependency()
        result = resolver.resolve_tiered(dep, [domain_fed, domain_local])

        # Should resolve at LOCAL_EXACT first (lower tier)
        assert result.route_plan is not None
        assert result.final_tier == EnumResolutionTier.LOCAL_EXACT

    def test_required_proofs_escalate_with_tier(self) -> None:
        """Higher tiers require more proofs."""
        provider = _make_provider("database.relational")
        registry = MockProviderRegistry([provider])
        resolver = ServiceTieredResolver(
            base_resolver=ServiceCapabilityResolver(),
            registry=registry,
        )

        # Only ORG_TRUSTED allows database
        domain = _make_trust_domain(
            "org.omninode",
            EnumResolutionTier.ORG_TRUSTED,
            allowed_capabilities=["database.*"],
        )

        dep = _make_dependency()
        result = resolver.resolve_tiered(dep, [domain])

        assert result.route_plan is not None
        hop = result.route_plan.hops[0]
        assert "node_identity" in hop.required_proofs
        assert "org_membership" in hop.required_proofs


# =============================================================================
# Tests: Fail-Closed
# =============================================================================


@pytest.mark.unit
class TestFailClosed:
    """Verify fail-closed behavior when no tier can satisfy the dependency."""

    def test_no_match_any_tier_returns_tier_exhausted(self) -> None:
        """If no provider matches at any tier, return TIER_EXHAUSTED."""
        registry = MockProviderRegistry([])  # no providers at all
        resolver = ServiceTieredResolver(
            base_resolver=ServiceCapabilityResolver(),
            registry=registry,
        )

        domain = _make_trust_domain("local.default", EnumResolutionTier.LOCAL_EXACT)
        dep = _make_dependency()

        result = resolver.resolve_tiered(dep, [domain])

        assert result.route_plan is None
        assert result.fail_closed is True
        assert result.structured_failure == EnumResolutionFailureCode.TIER_EXHAUSTED
        assert len(result.tier_progression) == 1
        assert (
            result.tier_progression[0].failure_code
            == EnumResolutionFailureCode.NO_MATCH
        )

    def test_empty_trust_domains_returns_tier_exhausted(self) -> None:
        """Empty trust domains list returns TIER_EXHAUSTED immediately."""
        registry = MockProviderRegistry([])
        resolver = ServiceTieredResolver(
            base_resolver=ServiceCapabilityResolver(),
            registry=registry,
        )

        dep = _make_dependency()
        result = resolver.resolve_tiered(dep, [])

        assert result.route_plan is None
        assert result.fail_closed is True
        assert result.structured_failure == EnumResolutionFailureCode.TIER_EXHAUSTED
        assert len(result.tier_progression) == 0

    def test_fail_closed_has_structured_failure_info(self) -> None:
        """Failed results carry full tier progression audit trail."""
        provider = _make_provider("cache.redis")  # wrong capability
        registry = MockProviderRegistry([provider])
        resolver = ServiceTieredResolver(
            base_resolver=ServiceCapabilityResolver(),
            registry=registry,
        )

        domains = [
            _make_trust_domain("local.default", EnumResolutionTier.LOCAL_EXACT),
            _make_trust_domain("org.omninode", EnumResolutionTier.ORG_TRUSTED),
        ]
        dep = _make_dependency(capability="database.relational")

        result = resolver.resolve_tiered(dep, domains)

        assert result.route_plan is None
        assert result.structured_failure == EnumResolutionFailureCode.TIER_EXHAUSTED
        assert len(result.tier_progression) == 2
        for attempt in result.tier_progression:
            assert attempt.failure_code is not None
            assert attempt.duration_ms >= 0.0


# =============================================================================
# Tests: Determinism
# =============================================================================


@pytest.mark.unit
class TestDeterminism:
    """Verify that identical inputs produce identical results."""

    def test_same_inputs_produce_same_snapshot_hash(self) -> None:
        """compute_registry_snapshot_hash is deterministic for same registry state."""
        provider = _make_provider(
            "database.relational",
            provider_id_str="00000000-0000-0000-0000-000000000001",
        )
        registry = MockProviderRegistry([provider])
        resolver = ServiceTieredResolver(
            base_resolver=ServiceCapabilityResolver(),
            registry=registry,
        )

        hash1 = resolver.compute_registry_snapshot_hash("database.relational")
        hash2 = resolver.compute_registry_snapshot_hash("database.relational")

        assert hash1 == hash2
        assert hash1.startswith("blake3:")

    def test_same_inputs_produce_same_route_plan_hashes(self) -> None:
        """Determinism: identical dependency + domains + registry -> same hashes."""
        provider = _make_provider(
            "database.relational",
            provider_id_str="00000000-0000-0000-0000-000000000001",
        )
        registry = MockProviderRegistry([provider])
        resolver = ServiceTieredResolver(
            base_resolver=ServiceCapabilityResolver(),
            registry=registry,
        )

        domain = _make_trust_domain("local.default", EnumResolutionTier.LOCAL_EXACT)
        dep = _make_dependency()

        result1 = resolver.resolve_tiered(dep, [domain])
        result2 = resolver.resolve_tiered(dep, [domain])

        assert result1.route_plan is not None
        assert result2.route_plan is not None

        # Hashes should be identical
        assert (
            result1.route_plan.registry_snapshot_hash
            == result2.route_plan.registry_snapshot_hash
        )
        assert (
            result1.route_plan.policy_bundle_hash
            == result2.route_plan.policy_bundle_hash
        )
        assert (
            result1.route_plan.trust_graph_hash == result2.route_plan.trust_graph_hash
        )

    def test_different_providers_produce_different_snapshot_hash(self) -> None:
        """Different registry state produces different snapshot hashes."""
        provider1 = _make_provider(
            "database.relational",
            provider_id_str="00000000-0000-0000-0000-000000000001",
        )
        provider2 = _make_provider(
            "database.relational",
            provider_id_str="00000000-0000-0000-0000-000000000002",
        )

        registry1 = MockProviderRegistry([provider1])
        registry2 = MockProviderRegistry([provider1, provider2])

        resolver1 = ServiceTieredResolver(
            base_resolver=ServiceCapabilityResolver(),
            registry=registry1,
        )
        resolver2 = ServiceTieredResolver(
            base_resolver=ServiceCapabilityResolver(),
            registry=registry2,
        )

        hash1 = resolver1.compute_registry_snapshot_hash("database.relational")
        hash2 = resolver2.compute_registry_snapshot_hash("database.relational")

        assert hash1 != hash2


# =============================================================================
# Tests: Filtered Registry
# =============================================================================


@pytest.mark.unit
class TestFilteredProviderRegistry:
    """Verify FilteredProviderRegistry scopes providers by trust domain."""

    def test_open_domain_passes_all_providers(self) -> None:
        """Domain with no allowed_capabilities lets all providers through."""
        provider = _make_provider("database.relational")
        base_registry = MockProviderRegistry([provider])
        domain = _make_trust_domain(
            "local.default",
            EnumResolutionTier.LOCAL_EXACT,
            allowed_capabilities=[],
        )

        filtered = FilteredProviderRegistry(base_registry, domain)
        result = filtered.get_providers_for_capability("database.relational")

        assert len(result) == 1
        assert result[0].provider_id == provider.provider_id

    def test_matching_glob_passes_providers(self) -> None:
        """Domain with matching glob pattern passes providers."""
        provider = _make_provider("database.relational")
        base_registry = MockProviderRegistry([provider])
        domain = _make_trust_domain(
            "org.omninode",
            EnumResolutionTier.ORG_TRUSTED,
            allowed_capabilities=["database.*"],
        )

        filtered = FilteredProviderRegistry(base_registry, domain)
        result = filtered.get_providers_for_capability("database.relational")

        assert len(result) == 1

    def test_non_matching_glob_blocks_providers(self) -> None:
        """Domain with non-matching glob pattern blocks providers."""
        provider = _make_provider("database.relational")
        base_registry = MockProviderRegistry([provider])
        domain = _make_trust_domain(
            "org.omninode",
            EnumResolutionTier.ORG_TRUSTED,
            allowed_capabilities=["cache.*"],  # doesn't match database
        )

        filtered = FilteredProviderRegistry(base_registry, domain)
        result = filtered.get_providers_for_capability("database.relational")

        assert len(result) == 0

    def test_multiple_glob_patterns(self) -> None:
        """Domain with multiple glob patterns; matches any."""
        provider = _make_provider("database.relational")
        base_registry = MockProviderRegistry([provider])
        domain = _make_trust_domain(
            "org.omninode",
            EnumResolutionTier.ORG_TRUSTED,
            allowed_capabilities=["cache.*", "database.*", "messaging.*"],
        )

        filtered = FilteredProviderRegistry(base_registry, domain)
        result = filtered.get_providers_for_capability("database.relational")

        assert len(result) == 1

    def test_trust_domain_property(self) -> None:
        """The trust_domain property returns the configured domain."""
        domain = _make_trust_domain("local.default", EnumResolutionTier.LOCAL_EXACT)
        filtered = FilteredProviderRegistry(MockProviderRegistry([]), domain)

        assert filtered.trust_domain.domain_id == "local.default"
        assert filtered.trust_domain.tier == EnumResolutionTier.LOCAL_EXACT
