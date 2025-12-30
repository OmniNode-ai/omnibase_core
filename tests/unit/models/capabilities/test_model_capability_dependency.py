# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""Unit tests for ModelCapabilityDependency."""

import pytest
from pydantic import ValidationError

from omnibase_core.models.capabilities.model_capability_dependency import (
    ModelCapabilityDependency,
)
from omnibase_core.models.capabilities.model_requirement_set import ModelRequirementSet
from omnibase_core.models.errors.model_onex_error import ModelOnexError


@pytest.mark.unit
class TestModelCapabilityDependencyInstantiation:
    """Tests for ModelCapabilityDependency instantiation."""

    def test_basic_instantiation_with_required_fields(self) -> None:
        """Test creating dependency with required alias and capability."""
        dep = ModelCapabilityDependency(alias="db", capability="database.relational")
        assert dep.alias == "db"
        assert dep.capability == "database.relational"
        assert dep.requirements.is_empty
        assert dep.selection_policy == "auto_if_unique"
        assert dep.strict is True

    def test_instantiation_with_requirements(self) -> None:
        """Test creating dependency with requirements."""
        reqs = ModelRequirementSet(
            must={"engine": "postgres"},
            prefer={"latency_ms": 20},
        )
        dep = ModelCapabilityDependency(
            alias="db",
            capability="database.relational",
            requirements=reqs,
        )
        assert dep.requirements.must == {"engine": "postgres"}
        assert dep.requirements.prefer == {"latency_ms": 20}

    def test_instantiation_with_selection_policy_best_score(self) -> None:
        """Test creating dependency with best_score selection policy."""
        dep = ModelCapabilityDependency(
            alias="cache",
            capability="cache.distributed",
            selection_policy="best_score",
        )
        assert dep.selection_policy == "best_score"

    def test_instantiation_with_selection_policy_require_explicit(self) -> None:
        """Test creating dependency with require_explicit selection policy."""
        dep = ModelCapabilityDependency(
            alias="secrets",
            capability="secrets.vault",
            selection_policy="require_explicit",
        )
        assert dep.selection_policy == "require_explicit"

    def test_instantiation_with_strict_false(self) -> None:
        """Test creating dependency with strict=False."""
        dep = ModelCapabilityDependency(
            alias="cache",
            capability="cache.kv",
            strict=False,
        )
        assert dep.strict is False

    def test_instantiation_with_all_fields(self) -> None:
        """Test creating dependency with all fields specified."""
        reqs = ModelRequirementSet(
            must={"encryption": True},
            prefer={"region": "us-east-1"},
            forbid={"deprecated": True},
            hints={"vendor": ["aws", "azure"]},
        )
        dep = ModelCapabilityDependency(
            alias="storage",
            capability="object.storage.s3compatible",
            requirements=reqs,
            selection_policy="best_score",
            strict=False,
        )
        assert dep.alias == "storage"
        assert dep.capability == "object.storage.s3compatible"
        assert dep.requirements == reqs
        assert dep.selection_policy == "best_score"
        assert dep.strict is False


@pytest.mark.unit
class TestModelCapabilityDependencyAliasValidation:
    """Tests for alias validation."""

    def test_valid_alias_simple(self) -> None:
        """Test valid simple alias."""
        dep = ModelCapabilityDependency(alias="db", capability="database.relational")
        assert dep.alias == "db"

    def test_valid_alias_with_underscore(self) -> None:
        """Test valid alias with underscores."""
        dep = ModelCapabilityDependency(
            alias="my_database", capability="database.relational"
        )
        assert dep.alias == "my_database"

    def test_valid_alias_with_numbers(self) -> None:
        """Test valid alias with numbers."""
        dep = ModelCapabilityDependency(alias="cache1", capability="cache.kv")
        assert dep.alias == "cache1"

    def test_invalid_alias_empty(self) -> None:
        """Test that empty alias raises ValidationError."""
        with pytest.raises(ValidationError):
            ModelCapabilityDependency(alias="", capability="database.relational")

    def test_invalid_alias_uppercase(self) -> None:
        """Test that uppercase alias raises ModelOnexError."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelCapabilityDependency(alias="DB", capability="database.relational")
        assert "must start with a lowercase letter" in str(exc_info.value)

    def test_invalid_alias_starts_with_number(self) -> None:
        """Test that alias starting with number raises ModelOnexError."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelCapabilityDependency(alias="1cache", capability="cache.kv")
        assert "must start with a lowercase letter" in str(exc_info.value)

    def test_invalid_alias_with_hyphen(self) -> None:
        """Test that alias with hyphen raises ModelOnexError."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelCapabilityDependency(alias="my-cache", capability="cache.kv")
        assert "must start with a lowercase letter" in str(exc_info.value)

    def test_invalid_alias_with_dot(self) -> None:
        """Test that alias with dot raises ModelOnexError."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelCapabilityDependency(alias="db.main", capability="database.relational")
        assert "must start with a lowercase letter" in str(exc_info.value)


@pytest.mark.unit
class TestModelCapabilityDependencyCapabilityValidation:
    """Tests for capability validation."""

    def test_valid_capability_two_tokens(self) -> None:
        """Test valid capability with two tokens."""
        dep = ModelCapabilityDependency(alias="db", capability="database.relational")
        assert dep.capability == "database.relational"

    def test_valid_capability_three_tokens(self) -> None:
        """Test valid capability with three tokens."""
        dep = ModelCapabilityDependency(alias="cache", capability="cache.kv.redis")
        assert dep.capability == "cache.kv.redis"

    def test_valid_capability_with_numbers(self) -> None:
        """Test valid capability with numbers."""
        dep = ModelCapabilityDependency(alias="db", capability="database.postgres14")
        assert dep.capability == "database.postgres14"

    def test_invalid_capability_single_token(self) -> None:
        """Test that single-token capability raises ModelOnexError."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelCapabilityDependency(alias="db", capability="database")
        assert "must follow pattern" in str(exc_info.value)

    def test_invalid_capability_uppercase(self) -> None:
        """Test that uppercase capability raises ModelOnexError."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelCapabilityDependency(alias="db", capability="Database.Relational")
        assert "must follow pattern" in str(exc_info.value)

    def test_invalid_capability_consecutive_dots(self) -> None:
        """Test that consecutive dots raise ModelOnexError."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelCapabilityDependency(alias="db", capability="database..relational")
        assert "must follow pattern" in str(exc_info.value)

    def test_invalid_capability_leading_dot(self) -> None:
        """Test that leading dot raises ModelOnexError."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelCapabilityDependency(alias="db", capability=".database.relational")
        assert "must follow pattern" in str(exc_info.value)

    def test_invalid_capability_trailing_dot(self) -> None:
        """Test that trailing dot raises ModelOnexError."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelCapabilityDependency(alias="db", capability="database.relational.")
        assert "must follow pattern" in str(exc_info.value)

    def test_invalid_capability_special_chars(self) -> None:
        """Test that special characters raise ModelOnexError."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelCapabilityDependency(alias="db", capability="database-relational")
        assert "must follow pattern" in str(exc_info.value)

    def test_invalid_capability_empty(self) -> None:
        """Test that empty capability raises ValidationError."""
        with pytest.raises(ValidationError):
            ModelCapabilityDependency(alias="db", capability="")


@pytest.mark.unit
class TestModelCapabilityDependencyProperties:
    """Tests for ModelCapabilityDependency properties."""

    def test_domain_extracts_first_token(self) -> None:
        """Test domain property extracts first token."""
        dep = ModelCapabilityDependency(alias="db", capability="database.relational")
        assert dep.domain == "database"

    def test_capability_type_extracts_second_token(self) -> None:
        """Test capability_type property extracts second token."""
        dep = ModelCapabilityDependency(alias="db", capability="database.relational")
        assert dep.capability_type == "relational"

    def test_variant_none_for_two_tokens(self) -> None:
        """Test variant is None for two-token capability."""
        dep = ModelCapabilityDependency(alias="db", capability="database.relational")
        assert dep.variant is None

    def test_variant_extracts_third_token(self) -> None:
        """Test variant extracts third token."""
        dep = ModelCapabilityDependency(alias="cache", capability="cache.kv.redis")
        assert dep.variant == "redis"

    def test_variant_joins_multiple_trailing_tokens(self) -> None:
        """Test variant joins multiple trailing tokens."""
        dep = ModelCapabilityDependency(
            alias="store", capability="object.storage.s3.compatible"
        )
        assert dep.variant == "s3.compatible"

    def test_has_requirements_false_for_empty(self) -> None:
        """Test has_requirements is False when empty."""
        dep = ModelCapabilityDependency(alias="db", capability="database.relational")
        assert dep.has_requirements is False

    def test_has_requirements_true_when_populated(self) -> None:
        """Test has_requirements is True when populated."""
        dep = ModelCapabilityDependency(
            alias="db",
            capability="database.relational",
            requirements=ModelRequirementSet(must={"engine": "postgres"}),
        )
        assert dep.has_requirements is True

    def test_requires_explicit_binding_false_for_auto_if_unique(self) -> None:
        """Test requires_explicit_binding is False for auto_if_unique."""
        dep = ModelCapabilityDependency(
            alias="db",
            capability="database.relational",
            selection_policy="auto_if_unique",
        )
        assert dep.requires_explicit_binding is False

    def test_requires_explicit_binding_false_for_best_score(self) -> None:
        """Test requires_explicit_binding is False for best_score."""
        dep = ModelCapabilityDependency(
            alias="db",
            capability="database.relational",
            selection_policy="best_score",
        )
        assert dep.requires_explicit_binding is False

    def test_requires_explicit_binding_true_for_require_explicit(self) -> None:
        """Test requires_explicit_binding is True for require_explicit."""
        dep = ModelCapabilityDependency(
            alias="secrets",
            capability="secrets.vault",
            selection_policy="require_explicit",
        )
        assert dep.requires_explicit_binding is True


@pytest.mark.unit
class TestModelCapabilityDependencyImmutability:
    """Tests for ModelCapabilityDependency frozen immutability."""

    def test_frozen_immutability_alias(self) -> None:
        """Test that alias cannot be modified."""
        dep = ModelCapabilityDependency(alias="db", capability="database.relational")
        with pytest.raises(ValidationError, match="frozen"):
            dep.alias = "modified"  # type: ignore[misc]

    def test_frozen_immutability_capability(self) -> None:
        """Test that capability cannot be modified."""
        dep = ModelCapabilityDependency(alias="db", capability="database.relational")
        with pytest.raises(ValidationError, match="frozen"):
            dep.capability = "cache.kv"  # type: ignore[misc]

    def test_frozen_immutability_selection_policy(self) -> None:
        """Test that selection_policy cannot be modified."""
        dep = ModelCapabilityDependency(alias="db", capability="database.relational")
        with pytest.raises(ValidationError, match="frozen"):
            dep.selection_policy = "best_score"  # type: ignore[misc]

    def test_frozen_immutability_strict(self) -> None:
        """Test that strict cannot be modified."""
        dep = ModelCapabilityDependency(alias="db", capability="database.relational")
        with pytest.raises(ValidationError, match="frozen"):
            dep.strict = False  # type: ignore[misc]


@pytest.mark.unit
class TestModelCapabilityDependencyExtraFields:
    """Tests for extra fields rejection."""

    def test_extra_fields_rejected(self) -> None:
        """Test that extra fields are rejected."""
        with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
            ModelCapabilityDependency(
                alias="db",
                capability="database.relational",
                extra_field="should_fail",  # type: ignore[call-arg]
            )


@pytest.mark.unit
class TestModelCapabilityDependencyStringRepresentation:
    """Tests for string representation."""

    def test_str_returns_arrow_format(self) -> None:
        """Test __str__ returns 'alias -> capability' format."""
        dep = ModelCapabilityDependency(alias="db", capability="database.relational")
        assert str(dep) == "db -> database.relational"

    def test_repr_minimal(self) -> None:
        """Test __repr__ with minimal fields."""
        dep = ModelCapabilityDependency(alias="db", capability="database.relational")
        repr_str = repr(dep)
        assert "ModelCapabilityDependency" in repr_str
        assert "alias='db'" in repr_str
        assert "capability='database.relational'" in repr_str
        assert "selection_policy" not in repr_str  # Default not shown
        assert "strict" not in repr_str  # Default not shown

    def test_repr_with_requirements(self) -> None:
        """Test __repr__ shows requirements when present."""
        dep = ModelCapabilityDependency(
            alias="db",
            capability="database.relational",
            requirements=ModelRequirementSet(must={"engine": "postgres"}),
        )
        repr_str = repr(dep)
        assert "requirements=" in repr_str

    def test_repr_with_non_default_policy(self) -> None:
        """Test __repr__ shows selection_policy when non-default."""
        dep = ModelCapabilityDependency(
            alias="db",
            capability="database.relational",
            selection_policy="best_score",
        )
        repr_str = repr(dep)
        assert "selection_policy='best_score'" in repr_str

    def test_repr_with_strict_false(self) -> None:
        """Test __repr__ shows strict=False when set."""
        dep = ModelCapabilityDependency(
            alias="db",
            capability="database.relational",
            strict=False,
        )
        repr_str = repr(dep)
        assert "strict=False" in repr_str


@pytest.mark.unit
class TestModelCapabilityDependencyEquality:
    """Tests for equality (not hashable due to dict fields)."""

    def test_unhashable_due_to_dict_fields(self) -> None:
        """Test that ModelCapabilityDependency is NOT hashable due to dict fields.

        Models with dict[str, Any] fields (like ModelRequirementSet's must/prefer/forbid/hints)
        are frozen but cannot be hashed. This test verifies all unhashability scenarios:
        - Direct hash() call fails
        - Cannot be used in sets (sets require hashable elements)
        - Cannot be used as dict keys (dict keys require hashable elements)
        """
        dep = ModelCapabilityDependency(alias="db", capability="database.relational")

        # Direct hash() call should fail
        with pytest.raises(TypeError, match="unhashable"):
            hash(dep)

        # Cannot add to set (sets use hashing internally)
        with pytest.raises(TypeError, match="unhashable"):
            _ = {dep}

        # Cannot use as dict key (dict keys must be hashable)
        with pytest.raises(TypeError, match="unhashable"):
            _ = {dep: "value"}

    def test_equality_same_dependencies(self) -> None:
        """Test equality for identical dependencies."""
        dep1 = ModelCapabilityDependency(alias="db", capability="database.relational")
        dep2 = ModelCapabilityDependency(alias="db", capability="database.relational")
        assert dep1 == dep2

    def test_inequality_different_alias(self) -> None:
        """Test inequality for different aliases."""
        dep1 = ModelCapabilityDependency(alias="db", capability="database.relational")
        dep2 = ModelCapabilityDependency(
            alias="database", capability="database.relational"
        )
        assert dep1 != dep2

    def test_inequality_different_capability(self) -> None:
        """Test inequality for different capabilities."""
        dep1 = ModelCapabilityDependency(alias="db", capability="database.relational")
        dep2 = ModelCapabilityDependency(alias="db", capability="database.document")
        assert dep1 != dep2


@pytest.mark.unit
class TestModelCapabilityDependencySelectionPolicyValidation:
    """Tests for selection_policy validation."""

    def test_valid_policy_auto_if_unique(self) -> None:
        """Test auto_if_unique is valid."""
        dep = ModelCapabilityDependency(
            alias="db",
            capability="database.relational",
            selection_policy="auto_if_unique",
        )
        assert dep.selection_policy == "auto_if_unique"

    def test_valid_policy_best_score(self) -> None:
        """Test best_score is valid."""
        dep = ModelCapabilityDependency(
            alias="db",
            capability="database.relational",
            selection_policy="best_score",
        )
        assert dep.selection_policy == "best_score"

    def test_valid_policy_require_explicit(self) -> None:
        """Test require_explicit is valid."""
        dep = ModelCapabilityDependency(
            alias="db",
            capability="database.relational",
            selection_policy="require_explicit",
        )
        assert dep.selection_policy == "require_explicit"

    def test_invalid_policy_rejected(self) -> None:
        """Test that invalid policy is rejected."""
        with pytest.raises(ValidationError):
            ModelCapabilityDependency(
                alias="db",
                capability="database.relational",
                selection_policy="invalid_policy",  # type: ignore[arg-type]
            )


@pytest.mark.unit
class TestModelCapabilityDependencyFromAttributes:
    """Tests for from_attributes configuration."""

    def test_from_attributes_allows_object_construction(self) -> None:
        """Test that from_attributes=True allows construction from objects."""

        class MockDep:
            alias = "db"
            capability = "database.relational"
            requirements = ModelRequirementSet()
            selection_policy = "auto_if_unique"
            strict = True

        # This should work due to from_attributes=True
        dep = ModelCapabilityDependency.model_validate(MockDep())
        assert dep.alias == "db"
        assert dep.capability == "database.relational"


@pytest.mark.unit
class TestModelCapabilityDependencyCaching:
    """Tests for capability parsing cache behavior."""

    def test_capability_parts_are_cached(self) -> None:
        """Test that capability parts are computed once and cached.

        The _cached_capability_parts PrivateAttr should be None before first access
        and populated after accessing any of domain/capability_type/variant.
        """
        dep = ModelCapabilityDependency(
            alias="store", capability="object.storage.s3.compatible"
        )
        # Before any property access, cache should be None
        assert dep._cached_capability_parts is None

        # Access domain (triggers parsing)
        _ = dep.domain
        # Now cache should be populated
        assert dep._cached_capability_parts is not None
        assert dep._cached_capability_parts == ("object", "storage", "s3.compatible")

    def test_multiple_property_accesses_use_same_cache(self) -> None:
        """Test that multiple property accesses use the same cached tuple."""
        dep = ModelCapabilityDependency(alias="db", capability="database.relational")

        # Access all properties
        domain = dep.domain
        cap_type = dep.capability_type
        variant = dep.variant

        # Verify correctness
        assert domain == "database"
        assert cap_type == "relational"
        assert variant is None

        # Verify all came from the same cached tuple
        cached = dep._cached_capability_parts
        assert cached is not None
        assert cached[0] == domain
        assert cached[1] == cap_type
        assert cached[2] == variant

    def test_cache_stability_across_repeated_accesses(self) -> None:
        """Test that repeated accesses return consistent values from cache."""
        dep = ModelCapabilityDependency(alias="vec", capability="storage.vector.qdrant")

        # Multiple accesses should all use the same cached tuple
        for _ in range(10):
            assert dep.domain == "storage"
            assert dep.capability_type == "vector"
            assert dep.variant == "qdrant"

        # Cache object identity should remain stable
        cache_ref = dep._cached_capability_parts
        _ = dep.domain
        assert dep._cached_capability_parts is cache_ref
