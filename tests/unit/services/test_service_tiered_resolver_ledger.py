# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for ServiceTieredResolver — resolution event publisher wiring.

Tests cover:
- Publisher is called once after a successful resolution
- Publisher is called once even when resolution fails
- Publisher is optional; resolver works unchanged when not provided

Related:
    - OMN-4324: Wire ServiceResolutionEventPublisher into ServiceTieredResolver
    - OMN-2895: Resolution Event Ledger
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

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
# Helpers
# =============================================================================


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
) -> ModelCapabilityDependency:
    """Create a test capability dependency."""
    return ModelCapabilityDependency(
        alias=alias,
        capability=capability,
        selection_policy="best_score",
    )


def _make_resolver_with_provider(
    capability: str,
) -> tuple[ServiceTieredResolver, MockProviderRegistry]:
    """Build a resolver + registry that will succeed for the given capability."""
    provider = _make_provider(capability)
    registry = MockProviderRegistry(providers=[provider])
    base_resolver = ServiceCapabilityResolver()
    resolver = ServiceTieredResolver(base_resolver=base_resolver, registry=registry)
    return resolver, registry


def _make_empty_resolver() -> tuple[ServiceTieredResolver, MockProviderRegistry]:
    """Build a resolver + empty registry (always fails)."""
    registry = MockProviderRegistry(providers=[])
    base_resolver = ServiceCapabilityResolver()
    resolver = ServiceTieredResolver(base_resolver=base_resolver, registry=registry)
    return resolver, registry


# =============================================================================
# Test: publisher called on success
# =============================================================================


@pytest.mark.unit
class TestPublisherCalledOnSuccess:
    """Publisher.publish() is called exactly once after a successful resolution."""

    def test_resolver_calls_publisher_on_success(self) -> None:
        """Publisher is called once when resolution succeeds."""
        capability = "database.relational"
        provider = _make_provider(capability)
        registry = MockProviderRegistry(providers=[provider])
        base_resolver = ServiceCapabilityResolver()

        mock_publisher = MagicMock()
        mock_publisher.publish = MagicMock()

        resolver = ServiceTieredResolver(
            base_resolver=base_resolver,
            registry=registry,
            resolution_event_publisher=mock_publisher,
        )

        dependency = _make_dependency(capability=capability)
        domain = _make_trust_domain(
            "local",
            EnumResolutionTier.LOCAL_EXACT,
            allowed_capabilities=[capability],
        )

        result = resolver.resolve_tiered(dependency, [domain])

        assert result.route_plan is not None
        mock_publisher.publish.assert_called_once()

    def test_publisher_receives_success_event(self) -> None:
        """Publisher receives an event with success=True on successful resolution."""
        capability = "database.relational"
        provider = _make_provider(capability)
        registry = MockProviderRegistry(providers=[provider])
        base_resolver = ServiceCapabilityResolver()

        published_events: list[Any] = []
        mock_publisher = MagicMock()
        mock_publisher.publish = MagicMock(side_effect=published_events.append)

        resolver = ServiceTieredResolver(
            base_resolver=base_resolver,
            registry=registry,
            resolution_event_publisher=mock_publisher,
        )

        dependency = _make_dependency(capability=capability)
        domain = _make_trust_domain(
            "local",
            EnumResolutionTier.LOCAL_EXACT,
            allowed_capabilities=[capability],
        )

        resolver.resolve_tiered(dependency, [domain])

        assert len(published_events) == 1
        event = published_events[0]
        assert event.success is True


# =============================================================================
# Test: publisher called on failure
# =============================================================================


@pytest.mark.unit
class TestPublisherCalledOnFailure:
    """Publisher.publish() is called exactly once even when resolution fails."""

    def test_resolver_calls_publisher_on_failure(self) -> None:
        """Publisher is called once when resolution fails (all tiers exhausted)."""
        registry = MockProviderRegistry(providers=[])
        base_resolver = ServiceCapabilityResolver()

        mock_publisher = MagicMock()
        mock_publisher.publish = MagicMock()

        resolver = ServiceTieredResolver(
            base_resolver=base_resolver,
            registry=registry,
            resolution_event_publisher=mock_publisher,
        )

        dependency = _make_dependency()
        domain = _make_trust_domain(
            "local",
            EnumResolutionTier.LOCAL_EXACT,
            allowed_capabilities=["database.relational"],
        )

        result = resolver.resolve_tiered(dependency, [domain])

        assert result.route_plan is None
        mock_publisher.publish.assert_called_once()

    def test_publisher_receives_failure_event(self) -> None:
        """Publisher receives an event with success=False on failed resolution."""
        registry = MockProviderRegistry(providers=[])
        base_resolver = ServiceCapabilityResolver()

        published_events: list[Any] = []
        mock_publisher = MagicMock()
        mock_publisher.publish = MagicMock(side_effect=published_events.append)

        resolver = ServiceTieredResolver(
            base_resolver=base_resolver,
            registry=registry,
            resolution_event_publisher=mock_publisher,
        )

        dependency = _make_dependency()
        domain = _make_trust_domain(
            "local",
            EnumResolutionTier.LOCAL_EXACT,
            allowed_capabilities=["database.relational"],
        )

        resolver.resolve_tiered(dependency, [domain])

        assert len(published_events) == 1
        event = published_events[0]
        assert event.success is False

    def test_resolver_calls_publisher_on_empty_domains(self) -> None:
        """Publisher is called when no trust domains are configured (early failure)."""
        registry = MockProviderRegistry(providers=[])
        base_resolver = ServiceCapabilityResolver()

        mock_publisher = MagicMock()
        mock_publisher.publish = MagicMock()

        resolver = ServiceTieredResolver(
            base_resolver=base_resolver,
            registry=registry,
            resolution_event_publisher=mock_publisher,
        )

        dependency = _make_dependency()
        result = resolver.resolve_tiered(dependency, [])

        assert result.route_plan is None
        mock_publisher.publish.assert_called_once()


# =============================================================================
# Test: publisher is optional
# =============================================================================


@pytest.mark.unit
class TestPublisherIsOptional:
    """Publisher is optional; resolver works unchanged when not provided."""

    def test_resolver_works_without_publisher(self) -> None:
        """Resolver produces correct results when no publisher is provided."""
        capability = "database.relational"
        provider = _make_provider(capability)
        registry = MockProviderRegistry(providers=[provider])
        base_resolver = ServiceCapabilityResolver()

        # No publisher — default (None)
        resolver = ServiceTieredResolver(base_resolver=base_resolver, registry=registry)

        dependency = _make_dependency(capability=capability)
        domain = _make_trust_domain(
            "local",
            EnumResolutionTier.LOCAL_EXACT,
            allowed_capabilities=[capability],
        )

        result = resolver.resolve_tiered(dependency, [domain])

        # Should succeed without raising
        assert result.route_plan is not None
        assert result.fail_closed is True

    def test_resolver_fails_gracefully_without_publisher(self) -> None:
        """Resolver fails correctly when publisher is None and resolution fails."""
        registry = MockProviderRegistry(providers=[])
        base_resolver = ServiceCapabilityResolver()

        # No publisher
        resolver = ServiceTieredResolver(base_resolver=base_resolver, registry=registry)

        dependency = _make_dependency()
        domain = _make_trust_domain(
            "local",
            EnumResolutionTier.LOCAL_EXACT,
            allowed_capabilities=["database.relational"],
        )

        result = resolver.resolve_tiered(dependency, [domain])

        assert result.route_plan is None
        assert result.structured_failure is not None

    def test_publisher_errors_do_not_propagate(self) -> None:
        """If publisher.publish() raises, the resolver swallows the error."""
        capability = "database.relational"
        provider = _make_provider(capability)
        registry = MockProviderRegistry(providers=[provider])
        base_resolver = ServiceCapabilityResolver()

        mock_publisher = MagicMock()
        mock_publisher.publish = MagicMock(side_effect=RuntimeError("Kafka down"))

        resolver = ServiceTieredResolver(
            base_resolver=base_resolver,
            registry=registry,
            resolution_event_publisher=mock_publisher,
        )

        dependency = _make_dependency(capability=capability)
        domain = _make_trust_domain(
            "local",
            EnumResolutionTier.LOCAL_EXACT,
            allowed_capabilities=[capability],
        )

        # Should not raise despite publisher error
        result = resolver.resolve_tiered(dependency, [domain])
        assert result.route_plan is not None
