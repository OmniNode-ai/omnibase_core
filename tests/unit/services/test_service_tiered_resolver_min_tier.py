# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for min_tier guard in ServiceTieredResolver.

Tests verify that resolve_tiered() enforces the never-silently-downgrade
invariant: when a dependency specifies a min_tier via ModelTieredResolutionConfig,
resolution at a less-trusted tier fails with MATCH_INSUFFICIENT_TRUST.

.. versionadded:: 0.24.x
    OMN-4321: Add explicit no-silent-downgrade guard in tier escalation.
"""

from __future__ import annotations

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
from omnibase_core.models.routing.model_tiered_resolution_config import (
    ModelTieredResolutionConfig,
)
from omnibase_core.models.routing.model_trust_domain import ModelTrustDomain
from omnibase_core.services.service_capability_resolver import (
    ServiceCapabilityResolver,
)
from omnibase_core.services.service_tiered_resolver import ServiceTieredResolver

# =============================================================================
# Helpers
# =============================================================================


class MockProviderRegistry:
    """Mock implementation of ProtocolProviderRegistry for testing."""

    def __init__(self, providers: list[ModelProviderDescriptor] | None = None) -> None:
        self.providers: list[ModelProviderDescriptor] = providers or []

    def get_providers_for_capability(
        self, capability: str
    ) -> list[ModelProviderDescriptor]:
        return [p for p in self.providers if capability in p.capabilities]


def _make_provider(capability: str) -> ModelProviderDescriptor:
    """Create a test provider descriptor."""
    return ModelProviderDescriptor(
        provider_id=uuid4(),
        capabilities=[capability],
        adapter="test.adapters.TestAdapter",
        connection_ref="env://TEST_DSN",
        attributes={},
    )


def _make_trust_domain(
    domain_id: str,
    tier: EnumResolutionTier,
    allowed_capabilities: list[str] | None = None,
) -> ModelTrustDomain:
    """Create a test trust domain."""
    return ModelTrustDomain(
        domain_id=domain_id,
        tier=tier,
        trust_root_public_key="dGVzdC1wdWJsaWMta2V5",
        allowed_capabilities=allowed_capabilities or [],
        policy_bundle_hash="sha256:test-policy-hash",
    )


def _make_dependency(
    alias: str = "db",
    capability: str = "database.relational",
    min_tier: EnumResolutionTier | None = None,
) -> ModelCapabilityDependency:
    """Create a test dependency with optional min_tier constraint."""
    tiered_resolution = (
        ModelTieredResolutionConfig(min_tier=min_tier) if min_tier is not None else None
    )
    return ModelCapabilityDependency(
        alias=alias,
        capability=capability,
        selection_policy="best_score",
        tiered_resolution=tiered_resolution,
    )


# =============================================================================
# Tests: min_tier guard
# =============================================================================


@pytest.mark.unit
class TestMinTierGuard:
    """Verify the no-silent-downgrade invariant via min_tier enforcement."""

    def test_resolution_fails_when_best_available_tier_below_min(self) -> None:
        """Only local_exact available but min_tier=ORG_TRUSTED -> MATCH_INSUFFICIENT_TRUST.

        The dependency requires ORG_TRUSTED as the minimum acceptable trust level.
        Only a LOCAL_EXACT domain is configured, which is less trusted (lower index
        in the canonical ordering doesn't mean less trusted: LOCAL_EXACT = 0,
        ORG_TRUSTED = 2). Because the resolved tier (LOCAL_EXACT, index 0) is below
        the required min_tier (ORG_TRUSTED, index 2), resolution must fail with
        MATCH_INSUFFICIENT_TRUST rather than silently proceeding.
        """
        provider = _make_provider("database.relational")
        registry = MockProviderRegistry([provider])
        resolver = ServiceTieredResolver(
            base_resolver=ServiceCapabilityResolver(),
            registry=registry,
        )

        local_domain = _make_trust_domain(
            "local.default", EnumResolutionTier.LOCAL_EXACT
        )
        dep = _make_dependency(min_tier=EnumResolutionTier.ORG_TRUSTED)

        result = resolver.resolve_tiered(dep, [local_domain])

        assert result.route_plan is None
        assert (
            result.structured_failure
            == EnumResolutionFailureCode.MATCH_INSUFFICIENT_TRUST
        )
        assert result.fail_closed is True

    def test_resolution_succeeds_at_exactly_min_tier(self) -> None:
        """Org tier available and min_tier=ORG_TRUSTED -> succeeds.

        The dependency requires ORG_TRUSTED as the minimum acceptable trust level.
        An ORG_TRUSTED domain is configured. Resolution at exactly the required tier
        must succeed.
        """
        provider = _make_provider("database.relational")
        registry = MockProviderRegistry([provider])
        resolver = ServiceTieredResolver(
            base_resolver=ServiceCapabilityResolver(),
            registry=registry,
        )

        org_domain = _make_trust_domain("org.primary", EnumResolutionTier.ORG_TRUSTED)
        dep = _make_dependency(min_tier=EnumResolutionTier.ORG_TRUSTED)

        result = resolver.resolve_tiered(dep, [org_domain])

        assert result.route_plan is not None
        assert result.final_tier == EnumResolutionTier.ORG_TRUSTED
        assert result.structured_failure is None
        assert result.fail_closed is True

    def test_resolution_succeeds_above_min_tier(self) -> None:
        """Federated tier available and min_tier=ORG_TRUSTED -> succeeds (above min).

        A more trusted tier than min_tier must also be accepted.
        """
        provider = _make_provider("database.relational")
        registry = MockProviderRegistry([provider])
        resolver = ServiceTieredResolver(
            base_resolver=ServiceCapabilityResolver(),
            registry=registry,
        )

        fed_domain = _make_trust_domain(
            "fed.partner", EnumResolutionTier.FEDERATED_TRUSTED
        )
        dep = _make_dependency(min_tier=EnumResolutionTier.ORG_TRUSTED)

        result = resolver.resolve_tiered(dep, [fed_domain])

        assert result.route_plan is not None
        assert result.final_tier == EnumResolutionTier.FEDERATED_TRUSTED
        assert result.structured_failure is None

    def test_no_min_tier_resolves_at_any_tier(self) -> None:
        """No min_tier constraint: resolution succeeds at any available tier (backward compat)."""
        provider = _make_provider("database.relational")
        registry = MockProviderRegistry([provider])
        resolver = ServiceTieredResolver(
            base_resolver=ServiceCapabilityResolver(),
            registry=registry,
        )

        local_domain = _make_trust_domain(
            "local.default", EnumResolutionTier.LOCAL_EXACT
        )
        dep = _make_dependency()  # no min_tier

        result = resolver.resolve_tiered(dep, [local_domain])

        assert result.route_plan is not None
        assert result.final_tier == EnumResolutionTier.LOCAL_EXACT
        assert result.structured_failure is None
