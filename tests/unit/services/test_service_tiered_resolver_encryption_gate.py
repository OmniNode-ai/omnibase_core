# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for ServiceTieredResolver encryption and redaction gate enforcement.

Tests cover:
- Gate with require_encryption=True blocks domain where encryption_enforced=False
- Gate with require_redaction=True blocks domain where redaction_enforced=False
- Gate passes when domain satisfies all requirements

.. versionadded:: 0.22.0
    Task 1 of tiered dependency resolution gap remediation (OMN-4320).
"""

from __future__ import annotations

from typing import Any
from uuid import uuid4

import pytest

from omnibase_core.enums.enum_classification import EnumClassification
from omnibase_core.enums.enum_resolution_tier import EnumResolutionTier
from omnibase_core.models.capabilities.model_capability_dependency import (
    ModelCapabilityDependency,
)
from omnibase_core.models.health.model_health_status import (
    ModelHealthStatus,  # noqa: F401 - imported for forward reference resolution
)
from omnibase_core.models.providers.model_provider_descriptor import (
    ModelProviderDescriptor,
)
from omnibase_core.models.routing.model_classification_gate import ModelClassificationGate
from omnibase_core.models.routing.model_policy_bundle import ModelPolicyBundle
from omnibase_core.models.routing.model_trust_domain import ModelTrustDomain
from omnibase_core.models.security.model_trustpolicy import ModelTrustPolicy
from omnibase_core.services.service_capability_resolver import ServiceCapabilityResolver
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
# Helpers
# =============================================================================


def _make_trust_policy() -> ModelTrustPolicy:
    """Create a minimal trust policy for tests."""
    return ModelTrustPolicy(
        name="Test Policy",
        version="1.0.0",
        created_by="test-suite",
    )


def _make_policy_bundle(gates: list[ModelClassificationGate]) -> ModelPolicyBundle:
    """Create a policy bundle with the given classification gates."""
    return ModelPolicyBundle(
        trust_policy=_make_trust_policy(),
        classification_gates=gates,
        redaction_policies=[],
        version="1.0",
    )


def _make_provider(capability: str) -> ModelProviderDescriptor:
    """Create a test provider descriptor."""
    return ModelProviderDescriptor(
        provider_id=uuid4(),
        capabilities=[capability],
        adapter="test.adapters.TestAdapter",
        connection_ref="env://TEST_DSN",
        attributes={},
    )


def _make_resolver(
    capability: str = "database.relational",
) -> tuple[ServiceTieredResolver, ModelCapabilityDependency]:
    """Create a resolver with a single provider for the given capability."""
    provider = _make_provider(capability)
    registry = MockProviderRegistry([provider])
    resolver = ServiceTieredResolver(
        base_resolver=ServiceCapabilityResolver(),
        registry=registry,
    )
    dep = ModelCapabilityDependency(alias="db", capability=capability)
    return resolver, dep


# =============================================================================
# Tests
# =============================================================================


@pytest.mark.unit
def test_encryption_required_gate_blocks_unencrypted_tier() -> None:
    """Gate with require_encryption=True blocks domain where encryption_enforced=False."""
    resolver, dep = _make_resolver()

    gate = ModelClassificationGate(
        classification=EnumClassification.CONFIDENTIAL,
        allowed_tiers=[EnumResolutionTier.LOCAL_EXACT, EnumResolutionTier.ORG_TRUSTED],
        require_encryption=True,
        require_redaction=False,
    )
    policy = _make_policy_bundle([gate])
    domain = ModelTrustDomain(
        domain_id="local.default",
        tier=EnumResolutionTier.LOCAL_EXACT,
        trust_root_public_key="dGVzdA==",
        allowed_capabilities=["database.relational"],
        policy_bundle_hash="sha256:none",
        encryption_enforced=False,  # no encryption on this domain
    )

    result = resolver.resolve_tiered(
        dependency=dep,
        trust_domains=[domain],
        policy_bundle=policy,
    )

    assert result.route_plan is None, "Expected resolution to be blocked by encryption gate"
    assert result.structured_failure is not None


@pytest.mark.unit
def test_redaction_required_gate_blocks_non_redacted_tier() -> None:
    """Gate with require_redaction=True blocks domain where redaction_enforced=False."""
    resolver, dep = _make_resolver()

    gate = ModelClassificationGate(
        classification=EnumClassification.RESTRICTED,
        allowed_tiers=[EnumResolutionTier.LOCAL_EXACT],
        require_encryption=False,
        require_redaction=True,
    )
    policy = _make_policy_bundle([gate])
    domain = ModelTrustDomain(
        domain_id="local.default",
        tier=EnumResolutionTier.LOCAL_EXACT,
        trust_root_public_key="dGVzdA==",
        allowed_capabilities=["database.relational"],
        policy_bundle_hash="sha256:none",
        redaction_enforced=False,  # no redaction on this domain
    )

    result = resolver.resolve_tiered(
        dependency=dep,
        trust_domains=[domain],
        policy_bundle=policy,
    )

    assert result.route_plan is None, "Expected resolution to be blocked by redaction gate"


@pytest.mark.unit
def test_gates_pass_when_requirements_met() -> None:
    """Gate should not block when domain satisfies all requirements."""
    resolver, dep = _make_resolver()

    gate = ModelClassificationGate(
        classification=EnumClassification.INTERNAL,
        allowed_tiers=[EnumResolutionTier.LOCAL_EXACT],
        require_encryption=True,
        require_redaction=False,
    )
    policy = _make_policy_bundle([gate])
    domain = ModelTrustDomain(
        domain_id="local.default",
        tier=EnumResolutionTier.LOCAL_EXACT,
        trust_root_public_key="dGVzdA==",
        allowed_capabilities=["database.relational"],
        policy_bundle_hash="sha256:none",
        encryption_enforced=True,  # satisfies require_encryption
    )

    result = resolver.resolve_tiered(
        dependency=dep,
        trust_domains=[domain],
        policy_bundle=policy,
    )

    assert result.route_plan is not None, (
        "Expected resolution to succeed when domain satisfies all gate requirements"
    )
