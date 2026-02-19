# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Unit tests for ModelCapabilityDependency.

Tests capability dependency specification including:
- Basic creation and validation
- Capability format validation (requires dot-separated format)
- Alias format validation
- Selection policy behavior
- Version range validation
"""

import pytest
from pydantic import ValidationError

from omnibase_core.models.capabilities import (
    ModelCapabilityDependency,
    ModelRequirementSet,
)
from omnibase_core.models.errors.model_onex_error import ModelOnexError


@pytest.mark.unit
class TestModelCapabilityDependencyCreation:
    """Tests for ModelCapabilityDependency creation and validation."""

    def test_minimal_creation(self) -> None:
        """Test creation with only required fields."""
        dep = ModelCapabilityDependency(
            alias="db",
            capability="database.relational",
        )
        assert dep.alias == "db"
        assert dep.capability == "database.relational"
        assert dep.strict is True  # default
        assert dep.selection_policy == "auto_if_unique"  # default

    def test_full_creation(self) -> None:
        """Test creation with all available fields."""
        requirements = ModelRequirementSet(
            must={"supports_transactions": True},
            prefer={"max_latency_ms": 20},
        )
        dep = ModelCapabilityDependency(
            alias="primary_db",
            capability="database.relational.postgresql",
            requirements=requirements,
            selection_policy="best_score",
            strict=False,
            version_range=">=1.0.0 <2.0.0",
        )
        assert dep.alias == "primary_db"
        assert dep.capability == "database.relational.postgresql"
        assert dep.requirements.must == {"supports_transactions": True}
        assert dep.selection_policy == "best_score"
        assert dep.strict is False
        assert dep.version_range == ">=1.0.0 <2.0.0"

    def test_default_requirements_is_empty(self) -> None:
        """Test that default requirements is an empty ModelRequirementSet."""
        dep = ModelCapabilityDependency(
            alias="cache",
            capability="cache.distributed",
        )
        assert dep.requirements.must == {}
        assert dep.requirements.prefer == {}
        assert dep.requirements.forbid == {}
        assert dep.requirements.hints == {}


@pytest.mark.unit
class TestCapabilityFormatValidation:
    """Tests for capability identifier format validation.

    Capabilities MUST follow the pattern <domain>.<type>[.<variant>]
    with at least one dot separator.
    """

    def test_valid_two_segment_capability(self) -> None:
        """Test capability with two segments (minimum required)."""
        dep = ModelCapabilityDependency(alias="x", capability="database.relational")
        assert dep.capability == "database.relational"

    def test_valid_multi_segment_capability(self) -> None:
        """Test capability with multiple segments."""
        dep = ModelCapabilityDependency(
            alias="x", capability="database.relational.postgresql"
        )
        assert dep.capability == "database.relational.postgresql"

    def test_capability_with_underscores(self) -> None:
        """Test capability with underscores in segments."""
        dep = ModelCapabilityDependency(alias="x", capability="message_queue.kafka")
        assert dep.capability == "message_queue.kafka"

    def test_capability_with_hyphens(self) -> None:
        """Test capability with hyphens in segments."""
        dep = ModelCapabilityDependency(alias="x", capability="cache.key-value")
        assert dep.capability == "cache.key-value"

    def test_empty_capability_rejected(self) -> None:
        """Test that empty capability is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelCapabilityDependency(alias="x", capability="")
        assert "capability" in str(exc_info.value).lower()

    def test_single_segment_capability_rejected(self) -> None:
        """Test that single-segment capability (no dot) is rejected."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelCapabilityDependency(alias="x", capability="database")
        assert "at least one dot separator" in str(exc_info.value).lower()

    def test_capability_with_empty_segment_rejected(self) -> None:
        """Test that capability with empty segment (consecutive dots) is rejected."""
        with pytest.raises(ModelOnexError):
            ModelCapabilityDependency(alias="x", capability="database..relational")

    def test_capability_with_uppercase_rejected(self) -> None:
        """Test that capability with uppercase letters is rejected."""
        with pytest.raises(ModelOnexError):
            ModelCapabilityDependency(alias="x", capability="Database.Relational")


@pytest.mark.unit
class TestAliasFormatValidation:
    """Tests for alias format validation."""

    def test_valid_simple_alias(self) -> None:
        """Test simple lowercase alias."""
        dep = ModelCapabilityDependency(alias="db", capability="database.relational")
        assert dep.alias == "db"

    def test_valid_snake_case_alias(self) -> None:
        """Test snake_case alias."""
        dep = ModelCapabilityDependency(
            alias="primary_db", capability="database.relational"
        )
        assert dep.alias == "primary_db"

    def test_alias_with_numbers(self) -> None:
        """Test alias with numbers (not at start)."""
        dep = ModelCapabilityDependency(alias="db2", capability="database.relational")
        assert dep.alias == "db2"

    def test_empty_alias_rejected(self) -> None:
        """Test that empty alias is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelCapabilityDependency(alias="", capability="database.relational")
        assert "alias" in str(exc_info.value).lower()

    def test_alias_starting_with_number_rejected(self) -> None:
        """Test that alias starting with number is rejected."""
        with pytest.raises(ModelOnexError):
            ModelCapabilityDependency(alias="2db", capability="database.relational")

    def test_uppercase_alias_rejected(self) -> None:
        """Test that uppercase alias is rejected."""
        with pytest.raises(ModelOnexError):
            ModelCapabilityDependency(alias="DB", capability="database.relational")

    def test_alias_with_hyphen_rejected(self) -> None:
        """Test that alias with hyphen is rejected."""
        with pytest.raises(ModelOnexError):
            ModelCapabilityDependency(
                alias="primary-db", capability="database.relational"
            )


@pytest.mark.unit
class TestSelectionPolicyValidation:
    """Tests for selection_policy validation."""

    @pytest.mark.parametrize(
        "policy",
        ["auto_if_unique", "best_score", "require_explicit"],
    )
    def test_valid_selection_policies(self, policy: str) -> None:
        """Test all valid selection policy values."""
        dep = ModelCapabilityDependency(
            alias="db",
            capability="database.relational",
            selection_policy=policy,  # type: ignore[arg-type]
        )
        assert dep.selection_policy == policy

    def test_invalid_selection_policy_rejected(self) -> None:
        """Test that invalid selection policy is rejected."""
        with pytest.raises(ValidationError):
            ModelCapabilityDependency(
                alias="db",
                capability="database.relational",
                selection_policy="invalid_policy",  # type: ignore[arg-type]
            )


@pytest.mark.unit
class TestVersionRangeValidation:
    """Tests for version_range validation."""

    def test_simple_version(self) -> None:
        """Test simple version string."""
        dep = ModelCapabilityDependency(
            alias="db",
            capability="database.relational",
            version_range="1.0.0",
        )
        assert dep.version_range == "1.0.0"

    def test_version_with_operator(self) -> None:
        """Test version with comparison operator."""
        dep = ModelCapabilityDependency(
            alias="db",
            capability="database.relational",
            version_range=">=1.0.0",
        )
        assert dep.version_range == ">=1.0.0"

    def test_version_range_space_separated(self) -> None:
        """Test space-separated version range."""
        dep = ModelCapabilityDependency(
            alias="db",
            capability="database.relational",
            version_range=">=1.0.0 <2.0.0",
        )
        assert dep.version_range == ">=1.0.0 <2.0.0"

    def test_caret_version(self) -> None:
        """Test caret version syntax."""
        dep = ModelCapabilityDependency(
            alias="db",
            capability="database.relational",
            version_range="^1.2.3",
        )
        assert dep.version_range == "^1.2.3"

    def test_tilde_version(self) -> None:
        """Test tilde version syntax."""
        dep = ModelCapabilityDependency(
            alias="db",
            capability="database.relational",
            version_range="~1.2.3",
        )
        assert dep.version_range == "~1.2.3"

    def test_invalid_version_range_rejected(self) -> None:
        """Test that invalid version range is rejected."""
        with pytest.raises(ModelOnexError):
            ModelCapabilityDependency(
                alias="db",
                capability="database.relational",
                version_range="invalid",
            )


@pytest.mark.unit
class TestCapabilityProperties:
    """Tests for capability parsing properties."""

    def test_domain_property(self) -> None:
        """Test domain extraction from capability."""
        dep = ModelCapabilityDependency(
            alias="db",
            capability="database.relational.postgresql",
        )
        assert dep.domain == "database"

    def test_capability_type_property(self) -> None:
        """Test capability_type extraction from capability."""
        dep = ModelCapabilityDependency(
            alias="db",
            capability="database.relational.postgresql",
        )
        assert dep.capability_type == "relational"

    def test_variant_property_with_variant(self) -> None:
        """Test variant extraction when present."""
        dep = ModelCapabilityDependency(
            alias="db",
            capability="database.relational.postgresql",
        )
        assert dep.variant == "postgresql"

    def test_variant_property_without_variant(self) -> None:
        """Test variant is None when not present."""
        dep = ModelCapabilityDependency(
            alias="db",
            capability="database.relational",
        )
        assert dep.variant is None

    def test_has_requirements_true(self) -> None:
        """Test has_requirements returns True when requirements exist."""
        dep = ModelCapabilityDependency(
            alias="db",
            capability="database.relational",
            requirements=ModelRequirementSet(must={"key": "value"}),
        )
        assert dep.has_requirements is True

    def test_has_requirements_false(self) -> None:
        """Test has_requirements returns False for empty requirements."""
        dep = ModelCapabilityDependency(
            alias="db",
            capability="database.relational",
        )
        assert dep.has_requirements is False

    def test_requires_explicit_binding_true(self) -> None:
        """Test requires_explicit_binding for require_explicit policy."""
        dep = ModelCapabilityDependency(
            alias="db",
            capability="database.relational",
            selection_policy="require_explicit",
        )
        assert dep.requires_explicit_binding is True

    def test_requires_explicit_binding_false(self) -> None:
        """Test requires_explicit_binding for other policies."""
        dep = ModelCapabilityDependency(
            alias="db",
            capability="database.relational",
            selection_policy="auto_if_unique",
        )
        assert dep.requires_explicit_binding is False


@pytest.mark.unit
class TestStrictBehavior:
    """Tests for strict flag behavior."""

    def test_strict_default_is_true(self) -> None:
        """Test that strict defaults to True."""
        dep = ModelCapabilityDependency(
            alias="db",
            capability="database.relational",
        )
        assert dep.strict is True

    def test_non_strict_dependency(self) -> None:
        """Test creation of non-strict dependency."""
        dep = ModelCapabilityDependency(
            alias="cache",
            capability="cache.distributed",
            strict=False,
        )
        assert dep.strict is False


@pytest.mark.unit
class TestImmutability:
    """Tests for model immutability."""

    def test_model_is_frozen(self) -> None:
        """Test that model instances are immutable."""
        dep = ModelCapabilityDependency(
            alias="db",
            capability="database.relational",
        )
        with pytest.raises(ValidationError):
            dep.alias = "new_alias"  # type: ignore[misc]

    def test_extra_fields_forbidden(self) -> None:
        """Test that extra fields are not allowed."""
        with pytest.raises(ValidationError):
            ModelCapabilityDependency(
                alias="db",
                capability="database.relational",
                unknown_field="value",  # type: ignore[call-arg]
            )


@pytest.mark.unit
class TestHashability:
    """Tests for hashability and use in collections."""

    def test_can_be_used_in_set(self) -> None:
        """Test that dependencies can be added to sets."""
        dep1 = ModelCapabilityDependency(alias="db", capability="database.relational")
        dep2 = ModelCapabilityDependency(alias="db", capability="database.relational")
        dep3 = ModelCapabilityDependency(alias="cache", capability="cache.distributed")

        deps = {dep1, dep2, dep3}
        # dep1 and dep2 should deduplicate (same alias + capability)
        assert len(deps) == 2

    def test_can_be_used_as_dict_key(self) -> None:
        """Test that dependencies can be used as dict keys."""
        dep = ModelCapabilityDependency(alias="db", capability="database.relational")
        cache = {dep: "resolved_provider"}
        assert cache[dep] == "resolved_provider"


@pytest.mark.unit
class TestStringRepresentation:
    """Tests for string representation methods."""

    def test_str_representation(self) -> None:
        """Test __str__ returns concise format."""
        dep = ModelCapabilityDependency(
            alias="db",
            capability="database.relational",
        )
        assert str(dep) == "db -> database.relational"

    def test_repr_representation(self) -> None:
        """Test __repr__ returns detailed format."""
        dep = ModelCapabilityDependency(
            alias="db",
            capability="database.relational",
        )
        repr_str = repr(dep)
        assert "ModelCapabilityDependency" in repr_str
        assert "alias='db'" in repr_str
        assert "capability='database.relational'" in repr_str
