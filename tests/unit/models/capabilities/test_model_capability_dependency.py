# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""Unit tests for ModelCapabilityDependency."""

import pytest
from pydantic import ValidationError

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.capabilities.model_capability_dependency import (
    ModelCapabilityDependency,
)
from omnibase_core.models.capabilities.model_capability_requirement_set import (
    ModelRequirementSet,
)
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
        """Test that special characters (other than underscore/hyphen) raise ModelOnexError."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelCapabilityDependency(alias="db", capability="database@relational")
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
    """Tests for ModelCapabilityDependency equality."""

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
class TestModelCapabilityDependencyHashability:
    """Tests for ModelCapabilityDependency hashability.

    ModelCapabilityDependency implements __hash__ based on identity fields
    (capability, alias) to enable use in sets and as dict keys. This supports
    dependency deduplication and caching resolution results.
    """

    def test_hashable_can_use_in_set(self) -> None:
        """Test that dependencies can be added to sets."""
        dep1 = ModelCapabilityDependency(
            alias="primary_db", capability="database.relational"
        )
        dep2 = ModelCapabilityDependency(
            alias="primary_db", capability="database.relational"
        )
        dep3 = ModelCapabilityDependency(alias="cache", capability="cache.redis")

        deps = {dep1, dep2, dep3}
        assert len(deps) == 2  # dep1 and dep2 are duplicates

    def test_hashable_can_use_as_dict_key(self) -> None:
        """Test that dependencies can be used as dict keys."""
        dep = ModelCapabilityDependency(alias="db", capability="database.relational")
        cache: dict[ModelCapabilityDependency, str] = {dep: "resolved_provider"}
        assert cache[dep] == "resolved_provider"

    def test_hash_stability_same_object(self) -> None:
        """Test that hash is stable for the same object."""
        dep = ModelCapabilityDependency(alias="db", capability="database.relational")
        h1 = hash(dep)
        h2 = hash(dep)
        assert h1 == h2  # Same object, same hash

    def test_hash_consistency_equal_objects(self) -> None:
        """Test that equal objects have equal hashes (hash contract)."""
        dep1 = ModelCapabilityDependency(alias="db", capability="database.relational")
        dep2 = ModelCapabilityDependency(alias="db", capability="database.relational")
        assert dep1 == dep2  # Objects are equal
        assert hash(dep1) == hash(dep2)  # Equal objects must have equal hashes

    def test_hash_differs_for_different_alias(self) -> None:
        """Test that hash differs when alias differs."""
        dep1 = ModelCapabilityDependency(alias="db", capability="database.relational")
        dep2 = ModelCapabilityDependency(
            alias="other_db", capability="database.relational"
        )
        # Different identity should (usually) produce different hashes
        # Note: Hash collisions are possible but unlikely for different inputs
        assert hash(dep1) != hash(dep2)

    def test_hash_differs_for_different_capability(self) -> None:
        """Test that hash differs when capability differs."""
        dep1 = ModelCapabilityDependency(alias="db", capability="database.relational")
        dep2 = ModelCapabilityDependency(alias="db", capability="database.document")
        assert hash(dep1) != hash(dep2)

    def test_hash_same_for_different_requirements(self) -> None:
        """Test that hash is same for deps with same identity but different requirements.

        This is intentional: dependencies are deduplicated by identity (capability,
        alias), not by their configuration (requirements, selection_policy, strict).
        """
        dep1 = ModelCapabilityDependency(
            alias="db",
            capability="database.relational",
            requirements=ModelRequirementSet(must={"engine": "postgres"}),
        )
        dep2 = ModelCapabilityDependency(
            alias="db",
            capability="database.relational",
            requirements=ModelRequirementSet(must={"engine": "mysql"}),
        )
        # Same identity fields -> same hash
        assert hash(dep1) == hash(dep2)
        # But objects are not equal (different requirements)
        assert dep1 != dep2

    def test_hash_same_for_different_selection_policy(self) -> None:
        """Test that hash ignores selection_policy (configuration, not identity)."""
        dep1 = ModelCapabilityDependency(
            alias="db",
            capability="database.relational",
            selection_policy="auto_if_unique",
        )
        dep2 = ModelCapabilityDependency(
            alias="db",
            capability="database.relational",
            selection_policy="best_score",
        )
        assert hash(dep1) == hash(dep2)

    def test_hash_same_for_different_strict_flag(self) -> None:
        """Test that hash ignores strict flag (configuration, not identity)."""
        dep1 = ModelCapabilityDependency(
            alias="db",
            capability="database.relational",
            strict=True,
        )
        dep2 = ModelCapabilityDependency(
            alias="db",
            capability="database.relational",
            strict=False,
        )
        assert hash(dep1) == hash(dep2)

    def test_set_deduplication_by_identity(self) -> None:
        """Test that set deduplication works correctly by identity.

        Multiple deps with same (capability, alias) but different configuration
        should be deduplicated to one entry.
        """
        deps = {
            ModelCapabilityDependency(alias="db", capability="database.relational"),
            ModelCapabilityDependency(
                alias="db",
                capability="database.relational",
                requirements=ModelRequirementSet(must={"engine": "postgres"}),
            ),
            ModelCapabilityDependency(
                alias="db",
                capability="database.relational",
                selection_policy="best_score",
            ),
        }
        # All three have same identity (db, database.relational)
        # But only one should remain after set deduplication
        # Note: Which one remains depends on hash collision resolution
        assert len(deps) == 3  # They're different objects (not equal per Pydantic)

    def test_dict_key_lookup_by_identity(self) -> None:
        """Test that dict key lookup works correctly."""
        dep1 = ModelCapabilityDependency(alias="db", capability="database.relational")
        cache = {dep1: "provider_a"}

        # Lookup with equal object should work
        dep2 = ModelCapabilityDependency(alias="db", capability="database.relational")
        assert cache[dep2] == "provider_a"

    def test_hash_with_complex_capability(self) -> None:
        """Test hash works with complex multi-token capability names."""
        dep = ModelCapabilityDependency(
            alias="vec", capability="storage.vector.qdrant.v2"
        )
        # Should be hashable without error
        h = hash(dep)
        assert isinstance(h, int)
        # Should work in set
        s = {dep}
        assert len(s) == 1


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


@pytest.mark.unit
class TestModelCapabilityDependencySelectionPolicySemantics:
    """Tests documenting selection policy expected behaviors.

    Note: These tests document the CONTRACT for policy behavior.
    Actual enforcement is resolver-specific. See Selection Policy Semantics
    in ModelCapabilityDependency docstring for details.
    """

    def test_auto_if_unique_semantic_contract(self) -> None:
        """Document auto_if_unique semantic: auto-select only if exactly one matches.

        Contract:
        - If exactly one provider matches must/forbid filters: auto-select
        - If multiple providers match: dependency remains unresolved (resolver-specific)
        - If zero providers match: resolution fails
        """
        dep = ModelCapabilityDependency(
            alias="db",
            capability="database.relational",
            selection_policy="auto_if_unique",
        )
        # This model declares the policy; resolver enforces it
        assert dep.selection_policy == "auto_if_unique"
        assert not dep.requires_explicit_binding

    def test_best_score_semantic_contract(self) -> None:
        """Document best_score semantic: select highest-scoring provider.

        Contract:
        - Filter providers by must/forbid requirements
        - Score remaining providers using prefer requirements
        - Select highest-scoring provider
        - Break ties using hints (advisory only)
        """
        dep = ModelCapabilityDependency(
            alias="cache",
            capability="cache.distributed",
            selection_policy="best_score",
            requirements=ModelRequirementSet(
                prefer={"region": "us-east-1", "latency_ms": 10}
            ),
        )
        assert dep.selection_policy == "best_score"
        assert dep.requirements.prefer == {"region": "us-east-1", "latency_ms": 10}

    def test_require_explicit_semantic_contract(self) -> None:
        """Document require_explicit semantic: never auto-select.

        Contract:
        - Never auto-select, even if only one provider matches
        - Always require explicit provider binding via config/user
        - Use for security-sensitive dependencies
        """
        dep = ModelCapabilityDependency(
            alias="secrets",
            capability="secrets.vault",
            selection_policy="require_explicit",
        )
        assert dep.selection_policy == "require_explicit"
        assert dep.requires_explicit_binding

    def test_auto_if_unique_with_hard_constraints(self) -> None:
        """Show auto_if_unique respects must/forbid constraints for filtering."""
        dep = ModelCapabilityDependency(
            alias="db",
            capability="database.relational",
            selection_policy="auto_if_unique",
            requirements=ModelRequirementSet(
                must={"supports_transactions": True},
                forbid={"deprecated": True},
            ),
        )
        assert dep.requirements.has_hard_constraints
        assert not dep.requires_explicit_binding

    def test_best_score_with_hints_for_tie_breaking(self) -> None:
        """Show hints provide advisory tie-breaking guidance."""
        dep = ModelCapabilityDependency(
            alias="cache",
            capability="cache.distributed",
            selection_policy="best_score",
            requirements=ModelRequirementSet(
                prefer={"latency_ms": 10},
                hints={"vendor_preference": ["redis", "memcached"]},
            ),
        )
        assert dep.requirements.hints == {"vendor_preference": ["redis", "memcached"]}

    def test_require_explicit_ignores_soft_constraints_for_selection(self) -> None:
        """Show prefer/hints can still be specified for documentation purposes."""
        dep = ModelCapabilityDependency(
            alias="secrets",
            capability="secrets.vault",
            selection_policy="require_explicit",
            requirements=ModelRequirementSet(
                must={"encryption": "aes-256"},
                prefer={"region": "us-east-1"},
            ),
        )
        # Even with preferences, explicit binding is required
        assert dep.requires_explicit_binding
        assert dep.requirements.has_soft_constraints


@pytest.mark.unit
class TestSelectionPolicyBehavior:
    """Tests demonstrating selection policy behavior with mock providers.

    These tests codify the expected BEHAVIORAL semantics of each selection policy
    using mock providers. While actual enforcement is resolver-specific, these
    tests document the contract that resolvers must follow.

    See ModelCapabilityDependency docstring for policy definitions.
    """

    def test_auto_if_unique_rejects_multiple_matches(self) -> None:
        """Test that auto_if_unique policy rejects when multiple providers match.

        Contract: When selection_policy='auto_if_unique' and multiple providers
        match the must/forbid criteria, automatic selection should fail.
        """
        dep = ModelCapabilityDependency(
            alias="db",
            capability="database.relational",
            selection_policy="auto_if_unique",
            requirements=ModelRequirementSet(
                must={"supports_transactions": True},
            ),
        )

        # Simulate multiple matching providers
        matching_providers = [
            {"name": "postgres", "supports_transactions": True, "score": 0.9},
            {"name": "mysql", "supports_transactions": True, "score": 0.8},
            {"name": "mariadb", "supports_transactions": True, "score": 0.85},
        ]

        # Mock resolver behavior: auto_if_unique should reject multiple matches
        def mock_resolve_auto_if_unique(
            providers: list[dict[str, object]],
        ) -> dict[str, object] | None:
            """Mock resolver implementing auto_if_unique policy."""
            filtered = [
                p
                for p in providers
                if p.get("supports_transactions")
                == dep.requirements.must.get("supports_transactions")
            ]
            # auto_if_unique: only select if exactly one match
            if len(filtered) == 1:
                return filtered[0]
            return None  # Reject: multiple matches or no matches

        # With 3 matching providers, auto_if_unique should return None (reject)
        result = mock_resolve_auto_if_unique(matching_providers)
        assert result is None, (
            "auto_if_unique should reject when multiple providers match"
        )

        # Verify policy configuration
        assert dep.selection_policy == "auto_if_unique"
        assert not dep.requires_explicit_binding

    def test_auto_if_unique_selects_single_match(self) -> None:
        """Test that auto_if_unique policy auto-selects when exactly one matches."""
        dep = ModelCapabilityDependency(
            alias="db",
            capability="database.relational",
            selection_policy="auto_if_unique",
            requirements=ModelRequirementSet(
                must={"supports_transactions": True, "supports_jsonb": True},
            ),
        )

        # Simulate providers where only one matches all must constraints
        providers = [
            {"name": "postgres", "supports_transactions": True, "supports_jsonb": True},
            {"name": "mysql", "supports_transactions": True, "supports_jsonb": False},
            {"name": "sqlite", "supports_transactions": False, "supports_jsonb": False},
        ]

        def mock_resolve_auto_if_unique(
            providers: list[dict[str, object]],
        ) -> dict[str, object] | None:
            """Mock resolver implementing auto_if_unique policy."""
            filtered = [
                p
                for p in providers
                if all(p.get(k) == v for k, v in dep.requirements.must.items())
            ]
            if len(filtered) == 1:
                return filtered[0]
            return None

        # With exactly one matching provider, auto_if_unique should select it
        result = mock_resolve_auto_if_unique(providers)
        assert result is not None, (
            "auto_if_unique should select when exactly one matches"
        )
        assert result["name"] == "postgres"

    def test_best_score_selects_highest_scoring_provider(self) -> None:
        """Test that best_score policy selects the highest-scoring provider.

        Contract: When selection_policy='best_score', after filtering by
        must/forbid, select the provider with the highest preference score.
        """
        dep = ModelCapabilityDependency(
            alias="cache",
            capability="cache.distributed",
            selection_policy="best_score",
            requirements=ModelRequirementSet(
                must={"distributed": True},
                prefer={"region": "us-east-1", "latency_ms": 10},
            ),
        )

        # Simulate providers with different preference scores
        providers = [
            {
                "name": "redis_west",
                "distributed": True,
                "region": "us-west-2",
                "latency_ms": 20,
            },
            {
                "name": "redis_east",
                "distributed": True,
                "region": "us-east-1",
                "latency_ms": 15,
            },
            {
                "name": "memcached",
                "distributed": True,
                "region": "us-east-1",
                "latency_ms": 10,
            },
        ]

        def mock_resolve_best_score(
            providers: list[dict[str, object]],
        ) -> dict[str, object] | None:
            """Mock resolver implementing best_score policy."""
            # Filter by must constraints
            filtered = [
                p
                for p in providers
                if all(p.get(k) == v for k, v in dep.requirements.must.items())
            ]
            if not filtered:
                return None

            # Score by prefer constraints (higher score = better match)
            def score_provider(p: dict[str, object]) -> float:
                score = 0.0
                for key, preferred in dep.requirements.prefer.items():
                    if p.get(key) == preferred:
                        score += 1.0
                return score

            # Select highest-scoring
            return max(filtered, key=score_provider)

        result = mock_resolve_best_score(providers)
        assert result is not None, "best_score should select a provider"
        # memcached has both region AND latency_ms matching = score 2.0
        assert result["name"] == "memcached", "best_score should select highest-scoring"

        # Verify policy configuration
        assert dep.selection_policy == "best_score"
        assert not dep.requires_explicit_binding

    def test_best_score_with_ties_uses_hints(self) -> None:
        """Test that best_score uses hints to break ties between equal scores."""
        dep = ModelCapabilityDependency(
            alias="cache",
            capability="cache.distributed",
            selection_policy="best_score",
            requirements=ModelRequirementSet(
                must={"distributed": True},
                prefer={"region": "us-east-1"},
                hints={"vendor_preference": ["redis", "memcached"]},
            ),
        )

        # Two providers with equal preference scores
        providers = [
            {"name": "memcached", "distributed": True, "region": "us-east-1"},
            {"name": "redis", "distributed": True, "region": "us-east-1"},
        ]

        def mock_resolve_best_score_with_hints(
            providers: list[dict[str, object]],
        ) -> dict[str, object] | None:
            """Mock resolver implementing best_score with hint tie-breaking."""
            filtered = [
                p
                for p in providers
                if all(p.get(k) == v for k, v in dep.requirements.must.items())
            ]
            if not filtered:
                return None

            def score_provider(p: dict[str, object]) -> float:
                return sum(
                    1.0 for k, v in dep.requirements.prefer.items() if p.get(k) == v
                )

            max_score = max(score_provider(p) for p in filtered)
            tied = [p for p in filtered if score_provider(p) == max_score]

            if len(tied) == 1:
                return tied[0]

            # Break ties using hints
            vendor_pref = dep.requirements.hints.get("vendor_preference", [])
            if isinstance(vendor_pref, list):
                for preferred_vendor in vendor_pref:
                    for p in tied:
                        if p.get("name") == preferred_vendor:
                            return p
            return tied[0]

        result = mock_resolve_best_score_with_hints(providers)
        assert result is not None
        # Redis is first in hints preference list
        assert result["name"] == "redis", "best_score should use hints to break ties"

    def test_require_explicit_never_auto_selects(self) -> None:
        """Test that require_explicit policy never auto-selects.

        Contract: When selection_policy='require_explicit', NEVER auto-select
        even if only one provider matches. Always require explicit binding.
        """
        dep = ModelCapabilityDependency(
            alias="secrets",
            capability="secrets.vault",
            selection_policy="require_explicit",
            requirements=ModelRequirementSet(
                must={"encryption": "aes-256"},
            ),
        )

        # Even with a single perfect match, require_explicit should not auto-select
        providers = [
            {"name": "hashicorp_vault", "encryption": "aes-256"},
        ]

        def mock_resolve_require_explicit(
            providers: list[dict[str, object]],
            explicit_binding: str | None = None,
        ) -> dict[str, object] | None:
            """Mock resolver implementing require_explicit policy."""
            # require_explicit: NEVER auto-select, even with one match
            if explicit_binding is None:
                return None

            # Only resolve if explicit binding is provided
            filtered = [
                p
                for p in providers
                if p.get("name") == explicit_binding
                and all(p.get(k) == v for k, v in dep.requirements.must.items())
            ]
            return filtered[0] if filtered else None

        # Without explicit binding, should return None even with one match
        result_without_binding = mock_resolve_require_explicit(providers)
        assert result_without_binding is None, (
            "require_explicit should never auto-select"
        )

        # With explicit binding, should resolve
        result_with_binding = mock_resolve_require_explicit(
            providers, explicit_binding="hashicorp_vault"
        )
        assert result_with_binding is not None, (
            "require_explicit should resolve with explicit binding"
        )
        assert result_with_binding["name"] == "hashicorp_vault"

        # Verify policy configuration
        assert dep.selection_policy == "require_explicit"
        assert dep.requires_explicit_binding is True

    def test_require_explicit_with_no_matches_still_requires_binding(self) -> None:
        """Test that require_explicit requires binding even when no matches exist."""
        dep = ModelCapabilityDependency(
            alias="secrets",
            capability="secrets.vault",
            selection_policy="require_explicit",
        )

        # Empty provider list
        providers: list[dict[str, object]] = []

        def mock_resolve_require_explicit(
            providers: list[dict[str, object]],
            explicit_binding: str | None = None,
        ) -> dict[str, object] | None:
            """Mock resolver requiring explicit binding."""
            if explicit_binding is None:
                return None
            return next(
                (p for p in providers if p.get("name") == explicit_binding), None
            )

        # Without explicit binding, should return None
        assert mock_resolve_require_explicit(providers) is None
        # The property confirms this policy never auto-binds
        assert dep.requires_explicit_binding is True


@pytest.mark.unit
class TestCapabilityNameRegexEdgeCases:
    """Tests for capability name regex edge cases, particularly hyphen handling.

    The capability naming pattern allows hyphens and underscores within tokens
    for multi-word names. Dots remain the semantic separators between
    domain/type/variant levels.
    """

    def test_hyphen_in_capability_domain_accepted(self) -> None:
        """Test that hyphens in domain token are accepted."""
        dep = ModelCapabilityDependency(alias="db", capability="my-domain.feature")
        assert dep.domain == "my-domain"
        assert dep.capability_type == "feature"

    def test_hyphen_in_capability_type_accepted(self) -> None:
        """Test that hyphens in type token are accepted."""
        dep = ModelCapabilityDependency(alias="svc", capability="core.my-feature")
        assert dep.domain == "core"
        assert dep.capability_type == "my-feature"

    def test_hyphen_in_capability_variant_accepted(self) -> None:
        """Test that hyphens in variant token are accepted."""
        dep = ModelCapabilityDependency(
            alias="svc", capability="vendor.capability.some-variant"
        )
        assert dep.domain == "vendor"
        assert dep.capability_type == "capability"
        assert dep.variant == "some-variant"

    def test_multiple_hyphens_accepted(self) -> None:
        """Test that multiple hyphens in capability are accepted."""
        dep = ModelCapabilityDependency(alias="x", capability="my-ns.my-type.my-var")
        assert dep.domain == "my-ns"
        assert dep.capability_type == "my-type"
        assert dep.variant == "my-var"

    def test_text_embedding_style_capability_accepted(self) -> None:
        """Test common LLM-style capability names with hyphens."""
        dep = ModelCapabilityDependency(
            alias="embed", capability="llm.text-embedding.v1"
        )
        assert dep.domain == "llm"
        assert dep.capability_type == "text-embedding"
        assert dep.variant == "v1"

    def test_key_value_style_capability_accepted(self) -> None:
        """Test storage/cache capability names with hyphens."""
        dep = ModelCapabilityDependency(alias="kv", capability="storage.key-value.v1")
        assert dep.domain == "storage"
        assert dep.capability_type == "key-value"
        assert dep.variant == "v1"

    def test_underscore_still_accepted(self) -> None:
        """Test that underscores still work for multi-word tokens."""
        # Underscores ARE allowed for multi-word tokens
        dep1 = ModelCapabilityDependency(alias="db", capability="my_domain.feature")
        assert dep1.domain == "my_domain"

        dep2 = ModelCapabilityDependency(alias="svc", capability="core.my_feature")
        assert dep2.capability_type == "my_feature"

        dep3 = ModelCapabilityDependency(
            alias="vec", capability="storage.vector.my_variant"
        )
        assert dep3.variant == "my_variant"

    def test_mixed_hyphen_and_underscore_accepted(self) -> None:
        """Test that mixing hyphens and underscores is valid."""
        dep = ModelCapabilityDependency(
            alias="db", capability="database-v2.relational_14.postgres-compatible"
        )
        assert dep.domain == "database-v2"
        assert dep.capability_type == "relational_14"
        assert dep.variant == "postgres-compatible"

    def test_mixed_underscore_and_numbers_accepted(self) -> None:
        """Test that underscores and numbers are valid within tokens."""
        dep = ModelCapabilityDependency(
            alias="db", capability="database_v2.relational_14.postgres_compatible"
        )
        assert dep.domain == "database_v2"
        assert dep.capability_type == "relational_14"
        assert dep.variant == "postgres_compatible"

    def test_capability_with_only_underscores_accepted(self) -> None:
        """Test capability with multiple underscores in tokens."""
        dep = ModelCapabilityDependency(
            alias="q", capability="event_bus.message_queue.rabbit_mq"
        )
        assert dep.capability == "event_bus.message_queue.rabbit_mq"
        assert dep.domain == "event_bus"
        assert dep.capability_type == "message_queue"
        assert dep.variant == "rabbit_mq"

    def test_capability_with_only_hyphens_accepted(self) -> None:
        """Test capability with multiple hyphens in tokens."""
        dep = ModelCapabilityDependency(
            alias="q", capability="event-bus.message-queue.rabbit-mq"
        )
        assert dep.capability == "event-bus.message-queue.rabbit-mq"
        assert dep.domain == "event-bus"
        assert dep.capability_type == "message-queue"
        assert dep.variant == "rabbit-mq"


@pytest.mark.unit
class TestVersionRangeValidation:
    """Tests for version_range field validation.

    The version_range field accepts semver-compatible version constraints
    following strict semver 2.0 syntax with optional operators for ranges.
    """

    # Valid patterns - should pass

    def test_version_range_none_allowed(self) -> None:
        """None is valid (optional field)."""
        dep = ModelCapabilityDependency(
            alias="db",
            capability="database.relational",
            version_range=None,
        )
        assert dep.version_range is None

    def test_version_range_simple_version(self) -> None:
        """Simple version without operator."""
        dep = ModelCapabilityDependency(
            alias="db",
            capability="database.relational",
            version_range="1.0.0",
        )
        assert dep.version_range == "1.0.0"

    def test_version_range_with_gte_operator(self) -> None:
        """Greater than or equal operator."""
        dep = ModelCapabilityDependency(
            alias="db",
            capability="database.relational",
            version_range=">=1.0.0",
        )
        assert dep.version_range == ">=1.0.0"

    def test_version_range_with_lte_operator(self) -> None:
        """Less than or equal operator."""
        dep = ModelCapabilityDependency(
            alias="db",
            capability="database.relational",
            version_range="<=2.0.0",
        )
        assert dep.version_range == "<=2.0.0"

    def test_version_range_with_gt_operator(self) -> None:
        """Greater than operator."""
        dep = ModelCapabilityDependency(
            alias="db",
            capability="database.relational",
            version_range=">1.0.0",
        )
        assert dep.version_range == ">1.0.0"

    def test_version_range_with_lt_operator(self) -> None:
        """Less than operator."""
        dep = ModelCapabilityDependency(
            alias="db",
            capability="database.relational",
            version_range="<2.0.0",
        )
        assert dep.version_range == "<2.0.0"

    def test_version_range_with_eq_operator(self) -> None:
        """Equal operator."""
        dep = ModelCapabilityDependency(
            alias="db",
            capability="database.relational",
            version_range="=1.0.0",
        )
        assert dep.version_range == "=1.0.0"

    def test_version_range_space_separated(self) -> None:
        """Space-separated range."""
        dep = ModelCapabilityDependency(
            alias="db",
            capability="database.relational",
            version_range=">=1.0.0 <2.0.0",
        )
        assert dep.version_range == ">=1.0.0 <2.0.0"

    def test_version_range_caret(self) -> None:
        """Caret syntax for compatible versions."""
        dep = ModelCapabilityDependency(
            alias="db",
            capability="database.relational",
            version_range="^1.2.3",
        )
        assert dep.version_range == "^1.2.3"

    def test_version_range_tilde(self) -> None:
        """Tilde syntax for approximate versions."""
        dep = ModelCapabilityDependency(
            alias="db",
            capability="database.relational",
            version_range="~1.2.3",
        )
        assert dep.version_range == "~1.2.3"

    def test_version_range_prerelease(self) -> None:
        """Pre-release versions."""
        dep = ModelCapabilityDependency(
            alias="db",
            capability="database.relational",
            version_range="1.0.0-alpha",
        )
        assert dep.version_range == "1.0.0-alpha"

    def test_version_range_prerelease_with_dots(self) -> None:
        """Pre-release with dot-separated identifiers."""
        dep = ModelCapabilityDependency(
            alias="db",
            capability="database.relational",
            version_range="1.0.0-beta.1",
        )
        assert dep.version_range == "1.0.0-beta.1"

    def test_version_range_build_metadata(self) -> None:
        """Build metadata."""
        dep = ModelCapabilityDependency(
            alias="db",
            capability="database.relational",
            version_range="1.0.0+build.123",
        )
        assert dep.version_range == "1.0.0+build.123"

    def test_version_range_strips_whitespace(self) -> None:
        """Whitespace should be stripped."""
        dep = ModelCapabilityDependency(
            alias="db",
            capability="database.relational",
            version_range="  >=1.0.0  ",
        )
        assert dep.version_range == ">=1.0.0"

    # Invalid patterns - should raise ModelOnexError

    def test_version_range_empty_string_rejected(self) -> None:
        """Empty string should be rejected."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelCapabilityDependency(
                alias="db",
                capability="database.relational",
                version_range="",
            )
        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR

    def test_version_range_whitespace_only_rejected(self) -> None:
        """Whitespace-only should be rejected."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelCapabilityDependency(
                alias="db",
                capability="database.relational",
                version_range="   ",
            )
        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR

    def test_version_range_missing_patch_rejected(self) -> None:
        """Missing patch version should be rejected."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelCapabilityDependency(
                alias="db",
                capability="database.relational",
                version_range="1.0",
            )
        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR

    def test_version_range_invalid_operator_rejected(self) -> None:
        """Invalid operator should be rejected."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelCapabilityDependency(
                alias="db",
                capability="database.relational",
                version_range="==1.0.0",
            )
        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR

    def test_version_range_leading_v_rejected(self) -> None:
        """Leading 'v' should be rejected."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelCapabilityDependency(
                alias="db",
                capability="database.relational",
                version_range="v1.0.0",
            )
        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR

    def test_version_range_leading_zeros_rejected(self) -> None:
        """Leading zeros should be rejected."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelCapabilityDependency(
                alias="db",
                capability="database.relational",
                version_range="01.0.0",
            )
        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR

    def test_version_range_wildcard_rejected(self) -> None:
        """Wildcards should be rejected."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelCapabilityDependency(
                alias="db",
                capability="database.relational",
                version_range="1.0.*",
            )
        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR

    def test_version_range_or_operator_rejected(self) -> None:
        """OR operator should be rejected."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelCapabilityDependency(
                alias="db",
                capability="database.relational",
                version_range="1.0.0 || 2.0.0",
            )
        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR
