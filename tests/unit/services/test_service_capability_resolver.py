# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""
Comprehensive unit tests for ServiceCapabilityResolver.

Tests cover:
- Basic resolution with single/multiple/no providers
- Selection policy behavior (auto_if_unique, best_score, require_explicit)
- Filtering by must/forbid constraints
- Scoring based on prefer constraints and profile weights
- Batch resolution via resolve_all
- Audit trail verification
- Determinism guarantees
"""

from __future__ import annotations

import random
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

import pytest

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.capabilities import ModelRequirementSet
from omnibase_core.models.bindings.model_binding import ModelBinding
from omnibase_core.models.bindings.model_resolution_result import ModelResolutionResult
from omnibase_core.models.capabilities.model_capability_dependency import (
    ModelCapabilityDependency,
)
from omnibase_core.models.capabilities.model_capability_requirement_set import (
    ModelRequirementSet,
)
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.providers.model_provider_descriptor import (
    ModelProviderDescriptor,
)
from omnibase_core.services.service_capability_resolver import ServiceCapabilityResolver

# =============================================================================
# Mock Implementations
# =============================================================================


class MockProviderRegistry:
    """Mock implementation of ProtocolProviderRegistry for testing.

    Provides a simple in-memory registry of providers that can be queried
    by capability. Supports exact capability matching.
    """

    def __init__(self, providers: list[ModelProviderDescriptor] | None = None) -> None:
        """Initialize with optional list of providers.

        Args:
            providers: List of provider descriptors to register.
        """
        self.providers: list[ModelProviderDescriptor] = providers or []

    def get_providers_for_capability(
        self, capability: str
    ) -> list[ModelProviderDescriptor]:
        """Get all providers offering the specified capability.

        Args:
            capability: Exact capability identifier to match.

        Returns:
            List of providers that have this capability.
        """
        return [p for p in self.providers if capability in p.capabilities]

    def add_provider(self, provider: ModelProviderDescriptor) -> None:
        """Add a provider to the registry.

        Args:
            provider: Provider descriptor to add.
        """
        self.providers.append(provider)


class MockProfile:
    """Mock profile for testing profile-based resolution.

    Supports:
    - profile_id for identification
    - explicit_bindings for pinned providers
    - provider_weights for score adjustments
    """

    def __init__(
        self,
        profile_id: str = "test-profile",
        explicit_bindings: dict[str, str] | None = None,
        provider_weights: dict[str, float] | None = None,
    ) -> None:
        """Initialize mock profile.

        Args:
            profile_id: Unique profile identifier.
            explicit_bindings: Map of alias -> provider_id for pinned bindings.
            provider_weights: Map of provider_id -> weight adjustment.
        """
        self.profile_id = profile_id
        self.explicit_bindings = explicit_bindings or {}
        self.provider_weights = provider_weights or {}


# =============================================================================
# Test Fixtures and Helpers
# =============================================================================


def create_provider(
    provider_id: UUID | None = None,
    capabilities: list[str] | None = None,
    attributes: dict[str, Any] | None = None,
    declared_features: dict[str, Any] | None = None,
    observed_features: dict[str, Any] | None = None,
    adapter: str = "test.adapters.TestAdapter",
    connection_ref: str = "env://TEST_CONNECTION",
    tags: list[str] | None = None,
) -> ModelProviderDescriptor:
    """Create a test provider descriptor with defaults.

    Args:
        provider_id: UUID for provider (generated if not provided).
        capabilities: List of capability identifiers.
        attributes: Static provider attributes.
        declared_features: Declared feature flags.
        observed_features: Observed runtime features.
        adapter: Python import path for adapter.
        connection_ref: Connection reference URI.
        tags: Tags for categorization.

    Returns:
        Configured ModelProviderDescriptor.
    """
    return ModelProviderDescriptor(
        provider_id=provider_id or uuid4(),
        capabilities=capabilities or ["database.relational"],
        adapter=adapter,
        connection_ref=connection_ref,
        attributes=attributes or {},
        declared_features=declared_features or {},
        observed_features=observed_features or {},
        tags=tags or [],
    )


def create_dependency(
    alias: str = "db",
    capability: str = "database.relational",
    must: dict[str, Any] | None = None,
    prefer: dict[str, Any] | None = None,
    forbid: dict[str, Any] | None = None,
    hints: dict[str, Any] | None = None,
    selection_policy: str = "auto_if_unique",
    strict: bool = True,
) -> ModelCapabilityDependency:
    """Create a test capability dependency with defaults.

    Args:
        alias: Local binding name.
        capability: Capability identifier.
        must: Hard constraints (required).
        prefer: Soft preferences (scoring).
        forbid: Hard exclusions.
        hints: Advisory tie-breaking hints.
        selection_policy: Selection strategy.
        strict: Whether prefer failures cause errors.

    Returns:
        Configured ModelCapabilityDependency.
    """
    requirements = ModelRequirementSet(
        must=must or {},
        prefer=prefer or {},
        forbid=forbid or {},
        hints=hints or {},
    )
    return ModelCapabilityDependency(
        alias=alias,
        capability=capability,
        requirements=requirements,
        selection_policy=selection_policy,  # type: ignore[arg-type]
        strict=strict,
    )


# =============================================================================
# Basic Resolution Tests
# =============================================================================


@pytest.mark.unit
class TestResolveBasic:
    """Basic resolution tests for single provider scenarios."""

    def test_resolve_single_provider(self) -> None:
        """Test resolving when exactly one provider matches."""
        # Setup
        resolver = ServiceCapabilityResolver()
        provider = create_provider(
            capabilities=["database.relational"],
            adapter="omnibase.adapters.PostgresAdapter",
            connection_ref="secrets://postgres/primary",
        )
        registry = MockProviderRegistry([provider])
        dependency = create_dependency(
            alias="db",
            capability="database.relational",
        )

        # Act
        binding = resolver.resolve(dependency, registry)

        # Assert
        assert isinstance(binding, ModelBinding)
        assert binding.dependency_alias == "db"
        assert binding.capability == "database.relational"
        assert binding.resolved_provider == str(provider.provider_id)
        assert binding.adapter == "omnibase.adapters.PostgresAdapter"
        assert binding.connection_ref == "secrets://postgres/primary"
        assert binding.candidates_considered == 1

    def test_resolve_multiple_providers_with_best_score_policy(self) -> None:
        """Test resolving with multiple providers using best_score policy."""
        # Setup
        resolver = ServiceCapabilityResolver()
        provider1 = create_provider(
            provider_id=UUID("00000000-0000-0000-0000-000000000001"),
            capabilities=["cache.distributed"],
            attributes={"region": "us-west-1"},
        )
        provider2 = create_provider(
            provider_id=UUID("00000000-0000-0000-0000-000000000002"),
            capabilities=["cache.distributed"],
            attributes={"region": "us-east-1"},
        )
        registry = MockProviderRegistry([provider1, provider2])

        dependency = create_dependency(
            alias="cache",
            capability="cache.distributed",
            prefer={"region": "us-east-1"},
            selection_policy="best_score",
        )

        # Act
        binding = resolver.resolve(dependency, registry)

        # Assert
        assert binding.resolved_provider == str(provider2.provider_id)
        assert binding.candidates_considered == 2

    def test_resolve_no_providers_raises_error(self) -> None:
        """Test that resolving with no matching providers raises error."""
        # Setup
        resolver = ServiceCapabilityResolver()
        registry = MockProviderRegistry([])
        dependency = create_dependency(
            alias="db",
            capability="database.relational",
        )

        # Act & Assert
        with pytest.raises(ModelOnexError) as exc_info:
            resolver.resolve(dependency, registry)

        assert exc_info.value.error_code == EnumCoreErrorCode.REGISTRY_RESOLUTION_FAILED
        assert "No providers found" in exc_info.value.message
        assert "database.relational" in exc_info.value.message

    def test_resolve_preserves_capability_and_alias(self) -> None:
        """Test that resolved binding preserves dependency metadata."""
        # Setup
        resolver = ServiceCapabilityResolver()
        provider = create_provider(
            capabilities=["storage.vector"],
        )
        registry = MockProviderRegistry([provider])
        dependency = create_dependency(
            alias="vectors",
            capability="storage.vector",
        )

        # Act
        binding = resolver.resolve(dependency, registry)

        # Assert
        assert binding.dependency_alias == "vectors"
        assert binding.capability == "storage.vector"

    def test_resolve_records_resolved_at_timestamp(self) -> None:
        """Test that resolution records timestamp."""
        # Setup
        resolver = ServiceCapabilityResolver()
        provider = create_provider(capabilities=["database.relational"])
        registry = MockProviderRegistry([provider])
        dependency = create_dependency()

        before = datetime.now(UTC)

        # Act
        binding = resolver.resolve(dependency, registry)

        after = datetime.now(UTC)

        # Assert
        assert before <= binding.resolved_at <= after


# =============================================================================
# Selection Policy Tests
# =============================================================================


@pytest.mark.unit
class TestSelectionPolicyAutoIfUnique:
    """Tests for auto_if_unique selection policy."""

    def test_auto_if_unique_success_with_one_candidate(self) -> None:
        """Test auto_if_unique succeeds with exactly one candidate."""
        # Setup
        resolver = ServiceCapabilityResolver()
        provider = create_provider(capabilities=["database.relational"])
        registry = MockProviderRegistry([provider])
        dependency = create_dependency(
            selection_policy="auto_if_unique",
        )

        # Act
        binding = resolver.resolve(dependency, registry)

        # Assert
        assert binding.resolved_provider == str(provider.provider_id)
        assert "auto_if_unique" in " ".join(binding.resolution_notes)

    def test_auto_if_unique_fails_with_multiple_candidates(self) -> None:
        """Test auto_if_unique fails with multiple candidates."""
        # Setup
        resolver = ServiceCapabilityResolver()
        provider1 = create_provider(capabilities=["database.relational"])
        provider2 = create_provider(capabilities=["database.relational"])
        registry = MockProviderRegistry([provider1, provider2])
        dependency = create_dependency(
            selection_policy="auto_if_unique",
        )

        # Act & Assert
        with pytest.raises(ModelOnexError) as exc_info:
            resolver.resolve(dependency, registry)

        assert exc_info.value.error_code == EnumCoreErrorCode.REGISTRY_RESOLUTION_FAILED
        assert "Ambiguous" in exc_info.value.message
        assert "2 candidates" in exc_info.value.message


@pytest.mark.unit
class TestSelectionPolicyBestScore:
    """Tests for best_score selection policy."""

    def test_best_score_selects_highest_scoring_provider(self) -> None:
        """Test best_score selects provider with highest prefer satisfaction."""
        # Setup
        resolver = ServiceCapabilityResolver()
        low_score = create_provider(
            provider_id=UUID("00000000-0000-0000-0000-000000000001"),
            capabilities=["cache.distributed"],
            attributes={"region": "eu-west-1", "tier": "standard"},
        )
        high_score = create_provider(
            provider_id=UUID("00000000-0000-0000-0000-000000000002"),
            capabilities=["cache.distributed"],
            attributes={"region": "us-east-1", "tier": "premium"},
        )
        registry = MockProviderRegistry([low_score, high_score])

        dependency = create_dependency(
            alias="cache",
            capability="cache.distributed",
            prefer={"region": "us-east-1", "tier": "premium"},
            selection_policy="best_score",
        )

        # Act
        binding = resolver.resolve(dependency, registry)

        # Assert
        assert binding.resolved_provider == str(high_score.provider_id)
        assert "best_score" in " ".join(binding.resolution_notes)

    def test_best_score_deterministic_tie_breaking_by_provider_id(self) -> None:
        """Test best_score uses provider_id for deterministic tie-breaking."""
        # Setup - both providers have same score
        resolver = ServiceCapabilityResolver()

        # Provider IDs chosen so lexicographic order is clear
        provider_a = create_provider(
            provider_id=UUID("00000000-0000-0000-0000-000000000001"),
            capabilities=["database.relational"],
            attributes={"version": "15"},
        )
        provider_b = create_provider(
            provider_id=UUID("00000000-0000-0000-0000-000000000002"),
            capabilities=["database.relational"],
            attributes={"version": "15"},
        )
        # Register in reverse order to ensure sorting is applied
        registry = MockProviderRegistry([provider_b, provider_a])

        dependency = create_dependency(
            prefer={"version": "15"},
            selection_policy="best_score",
        )

        # Act
        binding = resolver.resolve(dependency, registry)

        # Assert - should pick provider_a (lower UUID lexicographically)
        assert binding.resolved_provider == str(provider_a.provider_id)
        assert "Tie-breaker" in " ".join(binding.resolution_notes)

    def test_best_score_with_zero_preferences_selects_first_by_id(self) -> None:
        """Test best_score with no prefer constraints picks by provider_id order."""
        # Setup
        resolver = ServiceCapabilityResolver()
        provider_z = create_provider(
            provider_id=UUID("ffffffff-ffff-ffff-ffff-ffffffffffff"),
            capabilities=["database.relational"],
        )
        provider_a = create_provider(
            provider_id=UUID("00000000-0000-0000-0000-000000000001"),
            capabilities=["database.relational"],
        )
        registry = MockProviderRegistry([provider_z, provider_a])

        dependency = create_dependency(
            selection_policy="best_score",
        )

        # Act
        binding = resolver.resolve(dependency, registry)

        # Assert - both have score 0, so first alphabetically by provider_id wins
        assert binding.resolved_provider == str(provider_a.provider_id)


@pytest.mark.unit
class TestSelectionPolicyRequireExplicit:
    """Tests for require_explicit selection policy."""

    def test_require_explicit_fails_without_profile_pin(self) -> None:
        """Test require_explicit fails when no profile pin is provided."""
        # Setup
        resolver = ServiceCapabilityResolver()
        provider = create_provider(capabilities=["secrets.vault"])
        registry = MockProviderRegistry([provider])
        dependency = create_dependency(
            alias="secrets",
            capability="secrets.vault",
            selection_policy="require_explicit",
        )

        # Act & Assert
        with pytest.raises(ModelOnexError) as exc_info:
            resolver.resolve(dependency, registry)

        assert exc_info.value.error_code == EnumCoreErrorCode.REGISTRY_RESOLUTION_FAILED
        assert "require_explicit" in exc_info.value.message
        assert "no profile pin" in exc_info.value.message.lower()

    def test_require_explicit_succeeds_with_profile_pin(self) -> None:
        """Test require_explicit succeeds when profile provides explicit binding."""
        # Setup
        resolver = ServiceCapabilityResolver()
        provider = create_provider(
            provider_id=UUID("11111111-1111-1111-1111-111111111111"),
            capabilities=["secrets.vault"],
        )
        registry = MockProviderRegistry([provider])
        dependency = create_dependency(
            alias="secrets",
            capability="secrets.vault",
            selection_policy="require_explicit",
        )
        profile = MockProfile(
            explicit_bindings={"secrets": "11111111-1111-1111-1111-111111111111"}
        )

        # Act
        binding = resolver.resolve(dependency, registry, profile)

        # Assert
        assert binding.resolved_provider == str(provider.provider_id)
        assert "profile pin" in " ".join(binding.resolution_notes).lower()

    def test_require_explicit_fails_if_pinned_provider_not_in_candidates(self) -> None:
        """Test require_explicit fails if pinned provider doesn't match filters."""
        # Setup
        resolver = ServiceCapabilityResolver()
        provider = create_provider(
            provider_id=UUID("11111111-1111-1111-1111-111111111111"),
            capabilities=["secrets.vault"],
            attributes={"encryption": "aes-128"},
        )
        registry = MockProviderRegistry([provider])
        dependency = create_dependency(
            alias="secrets",
            capability="secrets.vault",
            must={"encryption": "aes-256"},  # Provider doesn't match
            selection_policy="require_explicit",
        )
        profile = MockProfile(
            explicit_bindings={"secrets": "11111111-1111-1111-1111-111111111111"}
        )

        # Act & Assert
        with pytest.raises(ModelOnexError) as exc_info:
            resolver.resolve(dependency, registry, profile)

        # Provider was filtered out by must constraint, so pin can't find it
        assert exc_info.value.error_code == EnumCoreErrorCode.REGISTRY_RESOLUTION_FAILED


# =============================================================================
# Filtering Tests
# =============================================================================


@pytest.mark.unit
class TestMustFiltering:
    """Tests for must requirement filtering."""

    def test_must_filters_providers_missing_required_attribute(self) -> None:
        """Test that providers missing must attributes are filtered out."""
        # Setup
        resolver = ServiceCapabilityResolver()
        provider_with_attr = create_provider(
            provider_id=UUID("00000000-0000-0000-0000-000000000001"),
            capabilities=["database.relational"],
            attributes={"supports_transactions": True},
        )
        provider_without_attr = create_provider(
            provider_id=UUID("00000000-0000-0000-0000-000000000002"),
            capabilities=["database.relational"],
            attributes={},
        )
        registry = MockProviderRegistry([provider_with_attr, provider_without_attr])

        dependency = create_dependency(
            must={"supports_transactions": True},
        )

        # Act
        binding = resolver.resolve(dependency, registry)

        # Assert
        assert binding.resolved_provider == str(provider_with_attr.provider_id)

    def test_must_filters_providers_with_wrong_attribute_value(self) -> None:
        """Test that providers with wrong must attribute values are filtered."""
        # Setup
        resolver = ServiceCapabilityResolver()
        correct_version = create_provider(
            provider_id=UUID("00000000-0000-0000-0000-000000000001"),
            capabilities=["database.relational"],
            attributes={"version_major": 15},
        )
        wrong_version = create_provider(
            provider_id=UUID("00000000-0000-0000-0000-000000000002"),
            capabilities=["database.relational"],
            attributes={"version_major": 14},
        )
        registry = MockProviderRegistry([correct_version, wrong_version])

        dependency = create_dependency(
            must={"version_major": 15},
        )

        # Act
        binding = resolver.resolve(dependency, registry)

        # Assert
        assert binding.resolved_provider == str(correct_version.provider_id)

    def test_must_requires_all_constraints_satisfied(self) -> None:
        """Test that all must constraints must be satisfied."""
        # Setup
        resolver = ServiceCapabilityResolver()
        provider = create_provider(
            capabilities=["database.relational"],
            attributes={"supports_transactions": True, "encryption": "aes-128"},
        )
        registry = MockProviderRegistry([provider])

        dependency = create_dependency(
            must={"supports_transactions": True, "encryption": "aes-256"},
        )

        # Act & Assert
        with pytest.raises(ModelOnexError) as exc_info:
            resolver.resolve(dependency, registry)

        assert exc_info.value.error_code == EnumCoreErrorCode.REGISTRY_RESOLUTION_FAILED
        assert "constraints" in exc_info.value.message.lower()

    def test_must_checks_declared_features(self) -> None:
        """Test that must constraints check declared_features."""
        # Setup
        resolver = ServiceCapabilityResolver()
        provider = create_provider(
            capabilities=["database.relational"],
            declared_features={"supports_json": True},
        )
        registry = MockProviderRegistry([provider])

        dependency = create_dependency(
            must={"supports_json": True},
        )

        # Act
        binding = resolver.resolve(dependency, registry)

        # Assert
        assert binding.resolved_provider == str(provider.provider_id)


@pytest.mark.unit
class TestForbidFiltering:
    """Tests for forbid requirement filtering."""

    def test_forbid_excludes_providers_with_forbidden_values(self) -> None:
        """Test that providers matching forbid constraints are excluded."""
        # Setup
        resolver = ServiceCapabilityResolver()
        allowed_provider = create_provider(
            provider_id=UUID("00000000-0000-0000-0000-000000000001"),
            capabilities=["database.relational"],
            attributes={"scope": "private_network"},
        )
        forbidden_provider = create_provider(
            provider_id=UUID("00000000-0000-0000-0000-000000000002"),
            capabilities=["database.relational"],
            attributes={"scope": "public_internet"},
        )
        registry = MockProviderRegistry([allowed_provider, forbidden_provider])

        dependency = create_dependency(
            forbid={"scope": "public_internet"},
        )

        # Act
        binding = resolver.resolve(dependency, registry)

        # Assert
        assert binding.resolved_provider == str(allowed_provider.provider_id)

    def test_forbid_allows_providers_without_forbidden_attribute(self) -> None:
        """Test providers without the forbidden attribute are allowed."""
        # Setup
        resolver = ServiceCapabilityResolver()
        provider = create_provider(
            capabilities=["database.relational"],
            attributes={},  # No 'deprecated' attribute
        )
        registry = MockProviderRegistry([provider])

        dependency = create_dependency(
            forbid={"deprecated": True},
        )

        # Act
        binding = resolver.resolve(dependency, registry)

        # Assert
        assert binding.resolved_provider == str(provider.provider_id)

    def test_forbid_allows_providers_with_different_value(self) -> None:
        """Test forbid only excludes exact value matches."""
        # Setup
        resolver = ServiceCapabilityResolver()
        provider = create_provider(
            capabilities=["database.relational"],
            attributes={"deprecated": False},  # Different from forbidden value
        )
        registry = MockProviderRegistry([provider])

        dependency = create_dependency(
            forbid={"deprecated": True},
        )

        # Act
        binding = resolver.resolve(dependency, registry)

        # Assert
        assert binding.resolved_provider == str(provider.provider_id)


@pytest.mark.unit
class TestCombinedFiltering:
    """Tests for combined must and forbid filtering."""

    def test_must_and_forbid_combined(self) -> None:
        """Test that both must and forbid constraints are applied."""
        # Setup
        resolver = ServiceCapabilityResolver()
        # This provider passes must but fails forbid
        good_features_bad_scope = create_provider(
            provider_id=UUID("00000000-0000-0000-0000-000000000001"),
            capabilities=["database.relational"],
            attributes={"version": 15, "scope": "public_internet"},
        )
        # This provider passes both must and forbid
        good_both = create_provider(
            provider_id=UUID("00000000-0000-0000-0000-000000000002"),
            capabilities=["database.relational"],
            attributes={"version": 15, "scope": "private_network"},
        )
        # This provider fails must
        bad_version = create_provider(
            provider_id=UUID("00000000-0000-0000-0000-000000000003"),
            capabilities=["database.relational"],
            attributes={"version": 14, "scope": "private_network"},
        )
        registry = MockProviderRegistry(
            [good_features_bad_scope, good_both, bad_version]
        )

        dependency = create_dependency(
            must={"version": 15},
            forbid={"scope": "public_internet"},
        )

        # Act
        binding = resolver.resolve(dependency, registry)

        # Assert
        assert binding.resolved_provider == str(good_both.provider_id)


# =============================================================================
# Scoring Tests
# =============================================================================


@pytest.mark.unit
class TestPreferScoring:
    """Tests for prefer-based scoring."""

    def test_prefer_adds_to_score(self) -> None:
        """Test that matching prefer constraints add to provider score."""
        # Setup
        resolver = ServiceCapabilityResolver()
        no_match = create_provider(
            provider_id=UUID("00000000-0000-0000-0000-000000000001"),
            capabilities=["cache.distributed"],
            attributes={"region": "eu-west-1"},
        )
        one_match = create_provider(
            provider_id=UUID("00000000-0000-0000-0000-000000000002"),
            capabilities=["cache.distributed"],
            attributes={"region": "us-east-1"},
        )
        two_matches = create_provider(
            provider_id=UUID("00000000-0000-0000-0000-000000000003"),
            capabilities=["cache.distributed"],
            attributes={"region": "us-east-1", "tier": "premium"},
        )
        registry = MockProviderRegistry([no_match, one_match, two_matches])

        dependency = create_dependency(
            alias="cache",
            capability="cache.distributed",
            prefer={"region": "us-east-1", "tier": "premium"},
            selection_policy="best_score",
        )

        # Act
        binding = resolver.resolve(dependency, registry)

        # Assert - should select provider with most prefer matches
        assert binding.resolved_provider == str(two_matches.provider_id)

    def test_prefer_checks_features_and_attributes(self) -> None:
        """Test that prefer checks both attributes and effective features."""
        # Setup
        resolver = ServiceCapabilityResolver()
        provider = create_provider(
            capabilities=["database.relational"],
            attributes={"region": "us-east-1"},
            declared_features={"supports_json": True},
        )
        registry = MockProviderRegistry([provider])

        dependency = create_dependency(
            prefer={"region": "us-east-1", "supports_json": True},
            selection_policy="best_score",
        )

        # Act
        binding = resolver.resolve(dependency, registry)

        # Assert
        assert binding.resolved_provider == str(provider.provider_id)
        assert "2.00" in " ".join(binding.resolution_notes)  # Score of 2.0


@pytest.mark.unit
class TestProfileWeights:
    """Tests for profile-based weight adjustments."""

    def test_profile_weights_affect_scoring(self) -> None:
        """Test that profile weights adjust provider scores."""
        # Setup
        resolver = ServiceCapabilityResolver()
        provider1 = create_provider(
            provider_id=UUID("00000000-0000-0000-0000-000000000001"),
            capabilities=["database.relational"],
            attributes={"version": 15},
        )
        provider2 = create_provider(
            provider_id=UUID("00000000-0000-0000-0000-000000000002"),
            capabilities=["database.relational"],
            attributes={"version": 15},
        )
        registry = MockProviderRegistry([provider1, provider2])

        dependency = create_dependency(
            prefer={"version": 15},
            selection_policy="best_score",
        )

        # Profile gives provider2 a weight boost
        profile = MockProfile(
            provider_weights={
                "00000000-0000-0000-0000-000000000002": 5.0,
            }
        )

        # Act
        binding = resolver.resolve(dependency, registry, profile)

        # Assert - provider2 should win due to weight boost
        assert binding.resolved_provider == str(provider2.provider_id)

    def test_resolution_profile_recorded_in_binding(self) -> None:
        """Test that resolution_profile is recorded in the binding."""
        # Setup
        resolver = ServiceCapabilityResolver()
        provider = create_provider(capabilities=["database.relational"])
        registry = MockProviderRegistry([provider])
        dependency = create_dependency()
        profile = MockProfile(profile_id="production-us-east")

        # Act
        binding = resolver.resolve(dependency, registry, profile)

        # Assert
        assert binding.resolution_profile == "production-us-east"

    def test_default_resolution_profile_when_no_profile(self) -> None:
        """Test that default resolution_profile is used when no profile provided."""
        # Setup
        resolver = ServiceCapabilityResolver()
        provider = create_provider(capabilities=["database.relational"])
        registry = MockProviderRegistry([provider])
        dependency = create_dependency()

        # Act
        binding = resolver.resolve(dependency, registry, profile=None)

        # Assert
        assert binding.resolution_profile == "default"


# =============================================================================
# resolve_all Tests
# =============================================================================


@pytest.mark.unit
class TestResolveAll:
    """Tests for batch resolution via resolve_all."""

    def test_resolve_all_multiple_dependencies(self) -> None:
        """Test resolving multiple dependencies in a single call."""
        # Setup
        resolver = ServiceCapabilityResolver()
        db_provider = create_provider(
            capabilities=["database.relational"],
            adapter="omnibase.adapters.PostgresAdapter",
        )
        cache_provider = create_provider(
            capabilities=["cache.distributed"],
            adapter="omnibase.adapters.RedisAdapter",
        )
        registry = MockProviderRegistry([db_provider, cache_provider])

        dependencies = [
            create_dependency(alias="db", capability="database.relational"),
            create_dependency(alias="cache", capability="cache.distributed"),
        ]

        # Act
        result = resolver.resolve_all(dependencies, registry)

        # Assert
        assert isinstance(result, ModelResolutionResult)
        assert result.is_successful
        assert len(result.bindings) == 2
        assert "db" in result.bindings
        assert "cache" in result.bindings
        assert result.bindings["db"].adapter == "omnibase.adapters.PostgresAdapter"
        assert result.bindings["cache"].adapter == "omnibase.adapters.RedisAdapter"

    def test_resolve_all_partial_success(self) -> None:
        """Test resolve_all with some resolutions failing."""
        # Setup
        resolver = ServiceCapabilityResolver()
        db_provider = create_provider(capabilities=["database.relational"])
        registry = MockProviderRegistry([db_provider])

        dependencies = [
            create_dependency(alias="db", capability="database.relational"),
            create_dependency(
                alias="cache", capability="cache.distributed"
            ),  # No provider
        ]

        # Act
        result = resolver.resolve_all(dependencies, registry)

        # Assert
        assert not result.is_successful
        assert len(result.bindings) == 1
        assert "db" in result.bindings
        assert "cache" not in result.bindings
        assert result.has_errors
        assert len(result.errors) == 1
        assert "cache" in result.errors[0]

    def test_resolve_all_complete_failure(self) -> None:
        """Test resolve_all when all resolutions fail."""
        # Setup
        resolver = ServiceCapabilityResolver()
        registry = MockProviderRegistry([])  # No providers

        dependencies = [
            create_dependency(alias="db", capability="database.relational"),
            create_dependency(alias="cache", capability="cache.distributed"),
        ]

        # Act
        result = resolver.resolve_all(dependencies, registry)

        # Assert
        assert not result.is_successful
        assert len(result.bindings) == 0
        assert len(result.errors) == 2

    def test_resolve_all_records_duration(self) -> None:
        """Test that resolve_all records resolution duration."""
        # Setup
        resolver = ServiceCapabilityResolver()
        provider = create_provider(capabilities=["database.relational"])
        registry = MockProviderRegistry([provider])
        dependencies = [create_dependency()]

        # Act
        result = resolver.resolve_all(dependencies, registry)

        # Assert
        assert result.resolution_duration_ms >= 0


# =============================================================================
# Audit Trail Tests
# =============================================================================


@pytest.mark.unit
class TestAuditTrail:
    """Tests for audit trail information in resolution results."""

    def test_candidates_considered_is_correct(self) -> None:
        """Test that candidates_considered reflects all providers checked."""
        # Setup
        resolver = ServiceCapabilityResolver()
        providers = [
            create_provider(
                provider_id=UUID(f"00000000-0000-0000-0000-00000000000{i}"),
                capabilities=["database.relational"],
            )
            for i in range(5)
        ]
        registry = MockProviderRegistry(providers)
        dependency = create_dependency(selection_policy="best_score")

        # Act
        binding = resolver.resolve(dependency, registry)

        # Assert
        assert binding.candidates_considered == 5

    def test_resolution_notes_explain_selection(self) -> None:
        """Test that resolution notes explain why a provider was selected."""
        # Setup
        resolver = ServiceCapabilityResolver()
        provider = create_provider(capabilities=["database.relational"])
        registry = MockProviderRegistry([provider])
        dependency = create_dependency(selection_policy="auto_if_unique")

        # Act
        binding = resolver.resolve(dependency, registry)

        # Assert
        notes = " ".join(binding.resolution_notes)
        assert "auto_if_unique" in notes
        assert "Score" in notes

    def test_resolve_all_records_rejection_reasons(self) -> None:
        """Test that resolve_all records rejection reasons for filtered providers."""
        # Setup
        resolver = ServiceCapabilityResolver()
        passing_provider = create_provider(
            provider_id=UUID("00000000-0000-0000-0000-000000000001"),
            capabilities=["database.relational"],
            attributes={"encryption": "aes-256"},
        )
        failing_provider = create_provider(
            provider_id=UUID("00000000-0000-0000-0000-000000000002"),
            capabilities=["database.relational"],
            attributes={"encryption": "aes-128"},
        )
        registry = MockProviderRegistry([passing_provider, failing_provider])

        dependencies = [
            create_dependency(
                alias="db",
                must={"encryption": "aes-256"},
            ),
        ]

        # Act
        result = resolver.resolve_all(dependencies, registry)

        # Assert
        assert "db" in result.rejection_reasons
        rejections = result.rejection_reasons["db"]
        assert "00000000-0000-0000-0000-000000000002" in rejections
        assert "encryption" in rejections["00000000-0000-0000-0000-000000000002"]

    def test_resolve_all_records_scores_by_alias(self) -> None:
        """Test that resolve_all records scores for all candidates."""
        # Setup
        resolver = ServiceCapabilityResolver()
        provider1 = create_provider(
            provider_id=UUID("00000000-0000-0000-0000-000000000001"),
            capabilities=["cache.distributed"],
            attributes={"region": "us-east-1"},
        )
        provider2 = create_provider(
            provider_id=UUID("00000000-0000-0000-0000-000000000002"),
            capabilities=["cache.distributed"],
            attributes={"region": "eu-west-1"},
        )
        registry = MockProviderRegistry([provider1, provider2])

        dependencies = [
            create_dependency(
                alias="cache",
                capability="cache.distributed",
                prefer={"region": "us-east-1"},
                selection_policy="best_score",
            ),
        ]

        # Act
        result = resolver.resolve_all(dependencies, registry)

        # Assert
        assert "cache" in result.scores_by_alias
        scores = result.scores_by_alias["cache"]
        assert "00000000-0000-0000-0000-000000000001" in scores
        assert "00000000-0000-0000-0000-000000000002" in scores
        # Provider1 should have higher score (matches prefer)
        assert (
            scores["00000000-0000-0000-0000-000000000001"]
            > scores["00000000-0000-0000-0000-000000000002"]
        )

    def test_resolve_all_records_candidates_by_alias(self) -> None:
        """Test that resolve_all records which candidates were considered."""
        # Setup
        resolver = ServiceCapabilityResolver()
        provider1 = create_provider(
            provider_id=UUID("00000000-0000-0000-0000-000000000001"),
            capabilities=["database.relational"],
        )
        provider2 = create_provider(
            provider_id=UUID("00000000-0000-0000-0000-000000000002"),
            capabilities=["database.relational"],
        )
        registry = MockProviderRegistry([provider1, provider2])

        dependencies = [
            create_dependency(alias="db", selection_policy="best_score"),
        ]

        # Act
        result = resolver.resolve_all(dependencies, registry)

        # Assert
        assert "db" in result.candidates_by_alias
        candidates = result.candidates_by_alias["db"]
        assert len(candidates) == 2
        assert "00000000-0000-0000-0000-000000000001" in candidates
        assert "00000000-0000-0000-0000-000000000002" in candidates

    def test_requirements_hash_is_deterministic(self) -> None:
        """Test that requirements hash is deterministic for same inputs."""
        # Setup
        resolver = ServiceCapabilityResolver()
        provider = create_provider(
            capabilities=["database.relational"],
            attributes={"version": 15, "region": "us-east-1"},
        )
        registry = MockProviderRegistry([provider])
        dependency = create_dependency(
            must={"version": 15},
            prefer={"region": "us-east-1"},
            forbid={"deprecated": True},
        )

        # Act
        binding1 = resolver.resolve(dependency, registry)
        binding2 = resolver.resolve(dependency, registry)

        # Assert
        assert binding1.requirements_hash == binding2.requirements_hash
        assert binding1.requirements_hash.startswith("sha256:")


# =============================================================================
# Determinism Tests
# =============================================================================


@pytest.mark.unit
class TestDeterminism:
    """Tests for deterministic resolution behavior."""

    def test_same_inputs_produce_same_output(self) -> None:
        """Test that identical inputs always produce identical results."""
        # Setup
        resolver = ServiceCapabilityResolver()
        providers = [
            create_provider(
                provider_id=UUID(f"00000000-0000-0000-0000-00000000000{i}"),
                capabilities=["database.relational"],
                attributes={"score_factor": i},
            )
            for i in range(1, 6)
        ]
        dependency = create_dependency(
            prefer={"score_factor": 3},
            selection_policy="best_score",
        )

        # Run multiple times
        results = []
        for _ in range(10):
            registry = MockProviderRegistry(providers.copy())
            binding = resolver.resolve(dependency, registry)
            results.append(binding.resolved_provider)

        # Assert - all results should be identical
        assert len(set(results)) == 1

    def test_provider_ordering_does_not_affect_result(self) -> None:
        """Test that provider order in registry doesn't affect selection."""
        # Setup
        resolver = ServiceCapabilityResolver()
        provider_a = create_provider(
            provider_id=UUID("00000000-0000-0000-0000-000000000001"),
            capabilities=["database.relational"],
            attributes={"version": 15},
        )
        provider_b = create_provider(
            provider_id=UUID("00000000-0000-0000-0000-000000000002"),
            capabilities=["database.relational"],
            attributes={"version": 15},
        )

        dependency = create_dependency(
            prefer={"version": 15},
            selection_policy="best_score",
        )

        # Create registries with different orderings
        registry1 = MockProviderRegistry([provider_a, provider_b])
        registry2 = MockProviderRegistry([provider_b, provider_a])

        # Act
        binding1 = resolver.resolve(dependency, registry1)
        binding2 = resolver.resolve(dependency, registry2)

        # Assert - both should select same provider (lexicographically first by ID)
        assert binding1.resolved_provider == binding2.resolved_provider

    def test_determinism_across_multiple_dependencies(self) -> None:
        """Test determinism with batch resolution of multiple dependencies."""
        # Setup
        resolver = ServiceCapabilityResolver()
        db_providers = [
            create_provider(
                provider_id=UUID(f"10000000-0000-0000-0000-00000000000{i}"),
                capabilities=["database.relational"],
            )
            for i in range(3)
        ]
        cache_providers = [
            create_provider(
                provider_id=UUID(f"20000000-0000-0000-0000-00000000000{i}"),
                capabilities=["cache.distributed"],
            )
            for i in range(3)
        ]
        all_providers = db_providers + cache_providers

        dependencies = [
            create_dependency(
                alias="db",
                capability="database.relational",
                selection_policy="best_score",
            ),
            create_dependency(
                alias="cache",
                capability="cache.distributed",
                selection_policy="best_score",
            ),
        ]

        # Run multiple times with shuffled provider order
        results = []
        for _ in range(5):
            shuffled = all_providers.copy()
            random.shuffle(shuffled)
            registry = MockProviderRegistry(shuffled)
            result = resolver.resolve_all(dependencies, registry)
            results.append(
                (
                    result.bindings.get("db", None),
                    result.bindings.get("cache", None),
                )
            )

        # Assert - all results should have same provider IDs
        db_ids = {r[0].resolved_provider if r[0] else None for r in results}
        cache_ids = {r[1].resolved_provider if r[1] else None for r in results}
        assert len(db_ids) == 1
        assert len(cache_ids) == 1


# =============================================================================
# Edge Cases and Error Handling
# =============================================================================


@pytest.mark.unit
class TestEdgeCases:
    """Tests for edge cases and error conditions."""

    def test_empty_requirements_matches_all(self) -> None:
        """Test that empty requirements match all providers."""
        # Setup
        resolver = ServiceCapabilityResolver()
        provider = create_provider(
            capabilities=["database.relational"],
            attributes={"version": 15, "region": "us-east-1"},
        )
        registry = MockProviderRegistry([provider])
        dependency = create_dependency()  # No requirements

        # Act
        binding = resolver.resolve(dependency, registry)

        # Assert
        assert binding.resolved_provider == str(provider.provider_id)

    def test_observed_features_take_precedence_over_declared(self) -> None:
        """Test that observed features override declared features in matching."""
        # Setup
        resolver = ServiceCapabilityResolver()
        provider = create_provider(
            capabilities=["database.relational"],
            declared_features={"supports_json": False},  # Declared as False
            observed_features={"supports_json": True},  # Observed as True
        )
        registry = MockProviderRegistry([provider])
        dependency = create_dependency(
            must={"supports_json": True},
        )

        # Act
        binding = resolver.resolve(dependency, registry)

        # Assert - should match because observed_features takes precedence
        assert binding.resolved_provider == str(provider.provider_id)

    def test_all_providers_filtered_raises_error(self) -> None:
        """Test that filtering out all providers raises an error."""
        # Setup
        resolver = ServiceCapabilityResolver()
        providers = [
            create_provider(
                provider_id=UUID(f"00000000-0000-0000-0000-00000000000{i}"),
                capabilities=["database.relational"],
                attributes={"version": i},
            )
            for i in range(1, 4)
        ]
        registry = MockProviderRegistry(providers)
        dependency = create_dependency(
            must={"version": 999},  # No provider has this
        )

        # Act & Assert
        with pytest.raises(ModelOnexError) as exc_info:
            resolver.resolve(dependency, registry)

        assert exc_info.value.error_code == EnumCoreErrorCode.REGISTRY_RESOLUTION_FAILED
        assert "constraints" in exc_info.value.message.lower()
        assert "3 provider(s) were rejected" in exc_info.value.message

    def test_resolver_is_stateless(self) -> None:
        """Test that resolver is stateless between calls."""
        # Setup
        resolver = ServiceCapabilityResolver()

        # First resolution
        provider1 = create_provider(
            provider_id=UUID("00000000-0000-0000-0000-000000000001"),
            capabilities=["database.relational"],
        )
        registry1 = MockProviderRegistry([provider1])
        dependency1 = create_dependency(alias="db1")
        binding1 = resolver.resolve(dependency1, registry1)

        # Second resolution with different data
        provider2 = create_provider(
            provider_id=UUID("00000000-0000-0000-0000-000000000002"),
            capabilities=["cache.distributed"],
        )
        registry2 = MockProviderRegistry([provider2])
        dependency2 = create_dependency(alias="cache", capability="cache.distributed")
        binding2 = resolver.resolve(dependency2, registry2)

        # Assert - resolutions are independent
        assert binding1.resolved_provider == str(provider1.provider_id)
        assert binding2.resolved_provider == str(provider2.provider_id)
        assert binding1.dependency_alias == "db1"
        assert binding2.dependency_alias == "cache"

    def test_repr_and_str_methods(self) -> None:
        """Test that resolver has sensible repr and str."""
        resolver = ServiceCapabilityResolver()
        assert "ServiceCapabilityResolver" in repr(resolver)
        assert "ServiceCapabilityResolver" in str(resolver)
