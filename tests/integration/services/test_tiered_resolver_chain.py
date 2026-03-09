# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Integration tests for the full tiered resolver chain.

Tests the complete pipeline from ModelCapabilityDependency through
ServiceTieredResolver -> FilteredProviderRegistry -> ServiceCapabilityResolver
-> ModelRoutePlan or fail-closed result.

These tests exercise composition of all parts, not individual units.
They are marked @pytest.mark.integration and require no external services.

.. versionadded:: 0.24.x
    OMN-4322: Integration tests for the full tiered responder chain (OMN-2547).
"""

from __future__ import annotations

import pytest

from omnibase_core.enums.enum_classification import EnumClassification
from omnibase_core.enums.enum_resolution_failure_code import EnumResolutionFailureCode
from omnibase_core.enums.enum_resolution_tier import EnumResolutionTier
from omnibase_core.models.capabilities.model_capability_dependency import (
    ModelCapabilityDependency,
)

# Import ModelHealthStatus FIRST to avoid circular import issues.
from omnibase_core.models.health.model_health_status import (
    ModelHealthStatus,  # noqa: F401 - imported for forward reference resolution
)
from omnibase_core.models.routing.model_classification_gate import (
    ModelClassificationGate,
)
from omnibase_core.models.routing.model_policy_bundle import ModelPolicyBundle
from omnibase_core.models.security.model_trustpolicy import ModelTrustPolicy
from omnibase_core.services.service_capability_resolver import (
    ServiceCapabilityResolver,
)
from omnibase_core.services.service_tiered_resolver import ServiceTieredResolver

from .conftest import (
    InMemoryProviderRegistry,
    _make_trust_domain,
)


def _make_dep(
    alias: str = "db",
    capability: str = "database.relational",
) -> ModelCapabilityDependency:
    """Create a basic capability dependency with no special constraints."""
    return ModelCapabilityDependency(
        alias=alias,
        capability=capability,
        selection_policy="best_score",
    )


def _make_policy_bundle(
    gates: list[ModelClassificationGate] | None = None,
) -> ModelPolicyBundle:
    """Create a minimal policy bundle for testing."""
    return ModelPolicyBundle(
        trust_policy=ModelTrustPolicy(
            name="test-policy",
            version="1.0.0",
            created_by="test",
        ),
        classification_gates=gates or [],
        redaction_policies=[],
        version="1.0.0",
    )


@pytest.mark.integration
class TestHappyPath:
    """Scenario 1: single local_exact tier, no policy, provider exists -> succeeds."""

    def test_happy_path_local_exact_no_policy(
        self,
        populated_registry: InMemoryProviderRegistry,
        base_resolver: ServiceCapabilityResolver,
        local_trust_domain: "ModelTrustDomain",  # type: ignore[name-defined]
    ) -> None:
        """Single LOCAL_EXACT domain with a matching provider resolves end-to-end.

        The full chain: ModelCapabilityDependency -> ServiceTieredResolver
        -> FilteredProviderRegistry -> ServiceCapabilityResolver -> ModelRoutePlan.
        """
        from omnibase_core.models.routing.model_trust_domain import ModelTrustDomain

        assert isinstance(local_trust_domain, ModelTrustDomain)
        resolver = ServiceTieredResolver(
            base_resolver=base_resolver,
            registry=populated_registry,
        )
        dep = _make_dep()

        result = resolver.resolve_tiered(dep, [local_trust_domain])

        assert result.route_plan is not None
        assert result.final_tier == EnumResolutionTier.LOCAL_EXACT
        assert result.structured_failure is None
        assert result.fail_closed is True
        assert len(result.tier_progression) == 1
        assert result.tier_progression[0].tier == EnumResolutionTier.LOCAL_EXACT
        assert result.tier_progression[0].failure_code is None


@pytest.mark.integration
class TestTierEscalation:
    """Scenario 2: no local provider; escalates to org tier -> succeeds."""

    def test_escalation_local_to_org(
        self,
        populated_registry: InMemoryProviderRegistry,
        base_resolver: ServiceCapabilityResolver,
    ) -> None:
        """Resolver skips empty local tier and escalates to org tier.

        The tier_progression records both tiers: local (fail) and org (success).
        """
        resolver = ServiceTieredResolver(
            base_resolver=base_resolver,
            registry=populated_registry,
        )
        dep = _make_dep()

        local_empty_domain = _make_trust_domain(
            "local.empty", EnumResolutionTier.LOCAL_EXACT
        )
        # Provider exists only at org tier in the same registry — but since
        # FilteredProviderRegistry filters by domain, we need the provider to
        # exist without domain-specific filtering to simulate org escalation.
        # Use two domains: local (empty allowed_capabilities = filter all) and org (open).
        local_domain = _make_trust_domain(
            "local.empty",
            EnumResolutionTier.LOCAL_EXACT,
            allowed_capabilities=["storage.vector"],  # doesn't include db -> no match
        )
        org_domain = _make_trust_domain(
            "org.primary",
            EnumResolutionTier.ORG_TRUSTED,
            allowed_capabilities=[],  # empty = no capability filter in domain
        )

        result = resolver.resolve_tiered(dep, [local_domain, org_domain])

        assert result.route_plan is not None
        assert result.final_tier == EnumResolutionTier.ORG_TRUSTED
        assert result.structured_failure is None
        # tier_progression should record at least 2 entries (local fail + org success)
        assert len(result.tier_progression) >= 2


@pytest.mark.integration
class TestFailClosed:
    """Scenario 3: no providers in any tier -> TIER_EXHAUSTED, fail_closed=True."""

    def test_fail_closed_no_providers_anywhere(
        self,
        empty_registry: InMemoryProviderRegistry,
        base_resolver: ServiceCapabilityResolver,
        local_trust_domain: "ModelTrustDomain",  # type: ignore[name-defined]
        org_trust_domain: "ModelTrustDomain",  # type: ignore[name-defined]
    ) -> None:
        """When no providers exist in any tier, resolution fails closed.

        The result must have:
        - route_plan = None
        - structured_failure = TIER_EXHAUSTED
        - fail_closed = True
        """
        resolver = ServiceTieredResolver(
            base_resolver=base_resolver,
            registry=empty_registry,
        )
        dep = _make_dep()

        result = resolver.resolve_tiered(dep, [local_trust_domain, org_trust_domain])

        assert result.route_plan is None
        assert result.structured_failure == EnumResolutionFailureCode.TIER_EXHAUSTED
        assert result.fail_closed is True


@pytest.mark.integration
class TestPolicyGateBlock:
    """Scenario 4: policy gate requiring FEDERATED_TRUSTED blocks local -> POLICY_DENIED."""

    def test_policy_gate_blocks_all_tiers(
        self,
        populated_registry: InMemoryProviderRegistry,
        base_resolver: ServiceCapabilityResolver,
        local_trust_domain: "ModelTrustDomain",  # type: ignore[name-defined]
    ) -> None:
        """Classification gate that only allows FEDERATED_TRUSTED blocks LOCAL_EXACT.

        When the only available tier (LOCAL_EXACT) is not in the gate's allowed_tiers,
        resolution fails. The tier_progression records a POLICY_DENIED attempt.
        """
        gate = ModelClassificationGate(
            classification=EnumClassification.CONFIDENTIAL,
            allowed_tiers=[EnumResolutionTier.FEDERATED_TRUSTED],
        )
        policy = _make_policy_bundle(gates=[gate])
        resolver = ServiceTieredResolver(
            base_resolver=base_resolver,
            registry=populated_registry,
        )
        dep = _make_dep()

        result = resolver.resolve_tiered(
            dep, [local_trust_domain], policy_bundle=policy
        )

        assert result.route_plan is None
        # All tiers exhausted after policy block
        assert result.structured_failure in (
            EnumResolutionFailureCode.TIER_EXHAUSTED,
            EnumResolutionFailureCode.POLICY_DENIED,
        )
        # Verify tier_progression recorded the policy denial
        policy_denied_attempts = [
            a
            for a in result.tier_progression
            if a.failure_code == EnumResolutionFailureCode.POLICY_DENIED
        ]
        assert len(policy_denied_attempts) >= 1


@pytest.mark.integration
class TestRoutePlanDeterminism:
    """Scenario 6: same inputs produce identical registry_snapshot_hash and trust_graph_hash."""

    def test_route_plan_determinism(
        self,
        populated_registry: InMemoryProviderRegistry,
        base_resolver: ServiceCapabilityResolver,
        local_trust_domain: "ModelTrustDomain",  # type: ignore[name-defined]
    ) -> None:
        """Two calls with identical inputs produce identical hash values.

        This verifies that registry_snapshot_hash and trust_graph_hash
        are deterministic — a contract for audit and caching.
        """
        resolver = ServiceTieredResolver(
            base_resolver=base_resolver,
            registry=populated_registry,
        )
        dep = _make_dep()

        result1 = resolver.resolve_tiered(dep, [local_trust_domain])
        result2 = resolver.resolve_tiered(dep, [local_trust_domain])

        assert result1.route_plan is not None
        assert result2.route_plan is not None

        assert (
            result1.route_plan.registry_snapshot_hash
            == result2.route_plan.registry_snapshot_hash
        )
        assert (
            result1.route_plan.trust_graph_hash == result2.route_plan.trust_graph_hash
        )
        assert (
            result1.route_plan.policy_bundle_hash
            == result2.route_plan.policy_bundle_hash
        )


@pytest.mark.integration
class TestEmptyTrustDomains:
    """Edge case: empty trust domain list -> TIER_EXHAUSTED immediately."""

    def test_empty_trust_domains_fail_closed(
        self,
        populated_registry: InMemoryProviderRegistry,
        base_resolver: ServiceCapabilityResolver,
    ) -> None:
        """No trust domains configured -> fail-closed with TIER_EXHAUSTED."""
        resolver = ServiceTieredResolver(
            base_resolver=base_resolver,
            registry=populated_registry,
        )
        dep = _make_dep()

        result = resolver.resolve_tiered(dep, [])

        assert result.route_plan is None
        assert result.structured_failure == EnumResolutionFailureCode.TIER_EXHAUSTED
        assert result.fail_closed is True
