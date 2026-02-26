# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for ServiceTieredResolver policy bundle integration.

Tests cover:
- Classification gate blocks certain tiers (POLICY_DENIED)
- Multiple gates: any blocking gate denies the tier
- No gates: all tiers pass (backward compatible)
- Policy bundle hash used in route plan
- Full integration: gate + tier escalation

.. versionadded:: 0.21.0
    Phase 4 of authenticated dependency resolution (OMN-2893).
"""

from __future__ import annotations

from typing import Any
from uuid import uuid4

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
from omnibase_core.models.providers.model_provider_descriptor import (
    ModelProviderDescriptor,
)
from omnibase_core.models.routing.model_classification_gate import (
    ModelClassificationGate,
)
from omnibase_core.models.routing.model_policy_bundle import ModelPolicyBundle
from omnibase_core.models.routing.model_redaction_policy import ModelRedactionPolicy
from omnibase_core.models.routing.model_trust_domain import ModelTrustDomain
from omnibase_core.models.security.model_trustpolicy import ModelTrustPolicy
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
) -> ModelProviderDescriptor:
    pid = (
        uuid4() if provider_id_str is None else __import__("uuid").UUID(provider_id_str)
    )
    return ModelProviderDescriptor(
        provider_id=pid,
        capabilities=[capability],
        adapter="test.adapters.TestAdapter",
        connection_ref="env://TEST_DSN",
        attributes={},
    )


def _make_trust_domain(
    domain_id: str,
    tier: EnumResolutionTier,
    allowed_capabilities: list[str] | None = None,
    policy_bundle_hash: str = "sha256:test-policy-hash",
) -> ModelTrustDomain:
    return ModelTrustDomain(
        domain_id=domain_id,
        tier=tier,
        trust_root_public_key="dGVzdC1wdWJsaWMta2V5",
        allowed_capabilities=allowed_capabilities or [],
        policy_bundle_hash=policy_bundle_hash,
    )


def _make_dependency(
    alias: str = "db",
    capability: str = "database.relational",
) -> ModelCapabilityDependency:
    return ModelCapabilityDependency(
        alias=alias,
        capability=capability,
        selection_policy="best_score",
    )


def _make_trust_policy() -> ModelTrustPolicy:
    return ModelTrustPolicy(
        name="Test Policy",
        version="1.0.0",
        created_by="test-suite",
    )


def _make_policy_bundle(
    classification_gates: list[ModelClassificationGate] | None = None,
    redaction_policies: list[ModelRedactionPolicy] | None = None,
) -> ModelPolicyBundle:
    return ModelPolicyBundle(
        bundle_id=uuid4(),
        trust_policy=_make_trust_policy(),
        classification_gates=classification_gates or [],
        redaction_policies=redaction_policies or [],
        version="1.0.0",
    )


# =============================================================================
# Tests: Classification Gate Blocks Tiers
# =============================================================================


@pytest.mark.unit
class TestClassificationGateBlocking:
    """Verify that classification gates block tiers not in allowed_tiers."""

    def test_gate_blocks_tier_not_in_allowed_list(self) -> None:
        """A gate allowing only LOCAL_EXACT blocks ORG_TRUSTED tier."""
        provider = _make_provider("database.relational")
        registry = MockProviderRegistry([provider])
        resolver = ServiceTieredResolver(
            base_resolver=ServiceCapabilityResolver(),
            registry=registry,
        )

        # Gate allows only LOCAL_EXACT
        gate = ModelClassificationGate(
            classification=EnumClassification.CONFIDENTIAL,
            allowed_tiers=[EnumResolutionTier.LOCAL_EXACT],
            require_encryption=True,
        )
        bundle = _make_policy_bundle(classification_gates=[gate])

        # Only ORG_TRUSTED domain available -- gate should block it
        domain = _make_trust_domain(
            "org.omninode",
            EnumResolutionTier.ORG_TRUSTED,
        )
        dep = _make_dependency()

        result = resolver.resolve_tiered(dep, [domain], policy_bundle=bundle)

        assert result.route_plan is None
        assert result.structured_failure == EnumResolutionFailureCode.TIER_EXHAUSTED
        assert len(result.tier_progression) == 1
        assert (
            result.tier_progression[0].failure_code
            == EnumResolutionFailureCode.POLICY_DENIED
        )
        assert "confidential" in (result.tier_progression[0].failure_reason or "")

    def test_gate_allows_matching_tier(self) -> None:
        """A gate allowing LOCAL_EXACT permits resolution at that tier."""
        provider = _make_provider("database.relational")
        registry = MockProviderRegistry([provider])
        resolver = ServiceTieredResolver(
            base_resolver=ServiceCapabilityResolver(),
            registry=registry,
        )

        gate = ModelClassificationGate(
            classification=EnumClassification.INTERNAL,
            allowed_tiers=[
                EnumResolutionTier.LOCAL_EXACT,
                EnumResolutionTier.LOCAL_COMPATIBLE,
            ],
        )
        bundle = _make_policy_bundle(classification_gates=[gate])

        domain = _make_trust_domain(
            "local.default",
            EnumResolutionTier.LOCAL_EXACT,
        )
        dep = _make_dependency()

        result = resolver.resolve_tiered(dep, [domain], policy_bundle=bundle)

        assert result.route_plan is not None
        assert result.final_tier == EnumResolutionTier.LOCAL_EXACT
        assert result.structured_failure is None

    def test_empty_allowed_tiers_blocks_all(self) -> None:
        """A gate with empty allowed_tiers does not block (no restriction)."""
        provider = _make_provider("database.relational")
        registry = MockProviderRegistry([provider])
        resolver = ServiceTieredResolver(
            base_resolver=ServiceCapabilityResolver(),
            registry=registry,
        )

        # Empty allowed_tiers means no tier restriction from this gate
        gate = ModelClassificationGate(
            classification=EnumClassification.PUBLIC,
            allowed_tiers=[],
        )
        bundle = _make_policy_bundle(classification_gates=[gate])

        domain = _make_trust_domain(
            "org.omninode",
            EnumResolutionTier.ORG_TRUSTED,
        )
        dep = _make_dependency()

        result = resolver.resolve_tiered(dep, [domain], policy_bundle=bundle)

        assert result.route_plan is not None

    def test_multiple_gates_any_blocking_denies(self) -> None:
        """If any gate blocks the tier, the tier is denied."""
        provider = _make_provider("database.relational")
        registry = MockProviderRegistry([provider])
        resolver = ServiceTieredResolver(
            base_resolver=ServiceCapabilityResolver(),
            registry=registry,
        )

        # First gate allows everything
        gate_public = ModelClassificationGate(
            classification=EnumClassification.PUBLIC,
            allowed_tiers=[
                EnumResolutionTier.LOCAL_EXACT,
                EnumResolutionTier.ORG_TRUSTED,
            ],
        )
        # Second gate restricts to LOCAL_EXACT only
        gate_restricted = ModelClassificationGate(
            classification=EnumClassification.RESTRICTED,
            allowed_tiers=[EnumResolutionTier.LOCAL_EXACT],
        )
        bundle = _make_policy_bundle(
            classification_gates=[gate_public, gate_restricted]
        )

        # ORG_TRUSTED domain -- blocked by restricted gate
        domain = _make_trust_domain(
            "org.omninode",
            EnumResolutionTier.ORG_TRUSTED,
        )
        dep = _make_dependency()

        result = resolver.resolve_tiered(dep, [domain], policy_bundle=bundle)

        assert result.route_plan is None
        assert (
            result.tier_progression[0].failure_code
            == EnumResolutionFailureCode.POLICY_DENIED
        )

    def test_gate_blocks_lower_tier_escalates_to_allowed_tier(self) -> None:
        """Gate blocks LOCAL_EXACT but allows ORG_TRUSTED; resolver skips blocked tier."""
        provider = _make_provider("database.relational")
        registry = MockProviderRegistry([provider])
        resolver = ServiceTieredResolver(
            base_resolver=ServiceCapabilityResolver(),
            registry=registry,
        )

        # Gate only allows ORG_TRUSTED and above (blocks local tiers)
        gate = ModelClassificationGate(
            classification=EnumClassification.INTERNAL,
            allowed_tiers=[
                EnumResolutionTier.ORG_TRUSTED,
                EnumResolutionTier.FEDERATED_TRUSTED,
            ],
        )
        bundle = _make_policy_bundle(classification_gates=[gate])

        # Both tiers available; gate blocks LOCAL_EXACT
        domain_local = _make_trust_domain(
            "local.default",
            EnumResolutionTier.LOCAL_EXACT,
        )
        domain_org = _make_trust_domain(
            "org.omninode",
            EnumResolutionTier.ORG_TRUSTED,
        )
        dep = _make_dependency()

        result = resolver.resolve_tiered(
            dep, [domain_org, domain_local], policy_bundle=bundle
        )

        # Should resolve at ORG_TRUSTED (LOCAL_EXACT blocked by gate)
        assert result.route_plan is not None
        assert result.final_tier == EnumResolutionTier.ORG_TRUSTED

        # LOCAL_EXACT attempt should be POLICY_DENIED
        local_attempt = [
            a
            for a in result.tier_progression
            if a.tier == EnumResolutionTier.LOCAL_EXACT
        ]
        assert len(local_attempt) == 1
        assert local_attempt[0].failure_code == EnumResolutionFailureCode.POLICY_DENIED


# =============================================================================
# Tests: No Gates (Backward Compatible)
# =============================================================================


@pytest.mark.unit
class TestNoPolicyBundle:
    """Verify backward compatibility when no policy bundle is provided."""

    def test_no_policy_bundle_resolves_normally(self) -> None:
        """Without a policy bundle, resolution proceeds as before."""
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

    def test_empty_gates_bundle_resolves_normally(self) -> None:
        """A policy bundle with no gates does not block any tier."""
        provider = _make_provider("database.relational")
        registry = MockProviderRegistry([provider])
        resolver = ServiceTieredResolver(
            base_resolver=ServiceCapabilityResolver(),
            registry=registry,
        )

        bundle = _make_policy_bundle(classification_gates=[])
        domain = _make_trust_domain("org.omninode", EnumResolutionTier.ORG_TRUSTED)
        dep = _make_dependency()

        result = resolver.resolve_tiered(dep, [domain], policy_bundle=bundle)

        assert result.route_plan is not None
        assert result.final_tier == EnumResolutionTier.ORG_TRUSTED


# =============================================================================
# Tests: Policy Bundle Hash in Route Plan
# =============================================================================


@pytest.mark.unit
class TestPolicyBundleHash:
    """Verify policy bundle hash is used in route plan determinism inputs."""

    def test_policy_bundle_hash_in_route_plan(self) -> None:
        """Route plan uses policy bundle's compute_hash()."""
        provider = _make_provider("database.relational")
        registry = MockProviderRegistry([provider])
        resolver = ServiceTieredResolver(
            base_resolver=ServiceCapabilityResolver(),
            registry=registry,
        )

        bundle = _make_policy_bundle()
        expected_hash = bundle.compute_hash()

        domain = _make_trust_domain("local.default", EnumResolutionTier.LOCAL_EXACT)
        dep = _make_dependency()

        result = resolver.resolve_tiered(dep, [domain], policy_bundle=bundle)

        assert result.route_plan is not None
        assert result.route_plan.policy_bundle_hash == expected_hash
        assert result.route_plan.policy_bundle_hash.startswith("sha256:")

    def test_no_bundle_uses_domain_hash(self) -> None:
        """Without a policy bundle, falls back to trust domain hash."""
        provider = _make_provider("database.relational")
        registry = MockProviderRegistry([provider])
        resolver = ServiceTieredResolver(
            base_resolver=ServiceCapabilityResolver(),
            registry=registry,
        )

        domain_hash = "sha256:domain-policy-hash"
        domain = _make_trust_domain(
            "local.default",
            EnumResolutionTier.LOCAL_EXACT,
            policy_bundle_hash=domain_hash,
        )
        dep = _make_dependency()

        result = resolver.resolve_tiered(dep, [domain])

        assert result.route_plan is not None
        assert result.route_plan.policy_bundle_hash == domain_hash
