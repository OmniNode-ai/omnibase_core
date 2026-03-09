# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Shared fixtures for tiered resolver integration tests.

Provides in-memory registry fixtures for testing the full
ServiceTieredResolver -> FilteredProviderRegistry -> ServiceCapabilityResolver chain.

.. versionadded:: 0.24.x
    OMN-4322: Integration tests for the full tiered responder chain.
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from omnibase_core.enums.enum_resolution_tier import EnumResolutionTier
from omnibase_core.models.providers.model_provider_descriptor import (
    ModelProviderDescriptor,
)
from omnibase_core.models.routing.model_trust_domain import ModelTrustDomain
from omnibase_core.services.service_capability_resolver import (
    ServiceCapabilityResolver,
)

# =============================================================================
# Mock Registry
# =============================================================================


class InMemoryProviderRegistry:
    """Simple in-memory provider registry for integration tests."""

    def __init__(self, providers: list[ModelProviderDescriptor] | None = None) -> None:
        self._providers: list[ModelProviderDescriptor] = providers or []

    def get_providers_for_capability(
        self, capability: str
    ) -> list[ModelProviderDescriptor]:
        return [p for p in self._providers if capability in p.capabilities]

    def add_provider(self, provider: ModelProviderDescriptor) -> None:
        self._providers.append(provider)


# =============================================================================
# Provider Factories
# =============================================================================


def _make_provider(
    capability: str,
    adapter: str = "test.adapters.TestAdapter",
    connection_ref: str = "env://TEST_DSN",
) -> ModelProviderDescriptor:
    """Create a test provider descriptor."""
    return ModelProviderDescriptor(
        provider_id=uuid4(),
        capabilities=[capability],
        adapter=adapter,
        connection_ref=connection_ref,
        attributes={},
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
        trust_root_public_key="dGVzdC1wdWJsaWMta2V5",
        allowed_capabilities=allowed_capabilities or [],
        policy_bundle_hash=policy_bundle_hash,
    )


# =============================================================================
# Registry Fixtures
# =============================================================================


@pytest.fixture
def populated_registry() -> InMemoryProviderRegistry:
    """Registry with one provider offering database.relational capability."""
    provider = _make_provider("database.relational")
    return InMemoryProviderRegistry([provider])


@pytest.fixture
def org_only_registry() -> InMemoryProviderRegistry:
    """Registry with a provider that has an org domain attribute."""
    provider = ModelProviderDescriptor(
        provider_id=uuid4(),
        capabilities=["database.relational"],
        adapter="test.adapters.OrgAdapter",
        connection_ref="env://ORG_DB_DSN",
        attributes={"domain": "org"},
    )
    return InMemoryProviderRegistry([provider])


@pytest.fixture
def empty_registry() -> InMemoryProviderRegistry:
    """Registry with no providers."""
    return InMemoryProviderRegistry([])


# =============================================================================
# Resolver Fixtures
# =============================================================================


@pytest.fixture
def base_resolver() -> ServiceCapabilityResolver:
    """Base flat capability resolver."""
    return ServiceCapabilityResolver()


@pytest.fixture
def local_trust_domain() -> ModelTrustDomain:
    """LOCAL_EXACT trust domain for testing."""
    return _make_trust_domain("local.default", EnumResolutionTier.LOCAL_EXACT)


@pytest.fixture
def org_trust_domain() -> ModelTrustDomain:
    """ORG_TRUSTED trust domain for testing."""
    return _make_trust_domain("org.primary", EnumResolutionTier.ORG_TRUSTED)
