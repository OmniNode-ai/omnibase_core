# SPDX-FileCopyrightText: 2025 OmniNode Team
# SPDX-License-Identifier: Apache-2.0
"""
Unit tests for ModelCapabilityDependency.

Tests capability dependency specification including:
- Basic creation and validation
- Capability format validation
- Alias format validation
- Provider matching via requirements
- Selection policy behavior
"""

import pytest
from pydantic import ValidationError

from omnibase_core.models.contracts.model_capability_dependency import (
    ModelCapabilityDependency,
)
from omnibase_core.models.requirements.model_requirement_set import ModelRequirementSet


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
        """Test creation with all fields."""
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
            vendor_hints={"preferred_vendor": "postgres"},
            description="Primary database for user data",
        )
        assert dep.alias == "primary_db"
        assert dep.capability == "database.relational.postgresql"
        assert dep.requirements.must == {"supports_transactions": True}
        assert dep.selection_policy == "best_score"
        assert dep.strict is False
        assert dep.version_range == ">=1.0.0 <2.0.0"
        assert dep.vendor_hints == {"preferred_vendor": "postgres"}
        assert dep.description == "Primary database for user data"

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
    """Tests for capability identifier format validation."""

    def test_valid_single_segment_capability(self) -> None:
        """Test capability with single segment."""
        dep = ModelCapabilityDependency(alias="x", capability="database")
        assert dep.capability == "database"

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

    def test_empty_capability_rejected(self) -> None:
        """Test that empty capability is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelCapabilityDependency(alias="x", capability="")
        assert "capability" in str(exc_info.value).lower()

    def test_capability_with_empty_segment_rejected(self) -> None:
        """Test that capability with empty segment is rejected."""
        with pytest.raises(ValidationError, match="empty segment"):
            ModelCapabilityDependency(alias="x", capability="database..relational")

    def test_capability_segment_starting_with_number_rejected(self) -> None:
        """Test that capability segment starting with number is rejected."""
        with pytest.raises(ValidationError, match="must start with a letter"):
            ModelCapabilityDependency(alias="x", capability="database.123sql")


@pytest.mark.unit
class TestAliasFormatValidation:
    """Tests for alias format validation."""

    def test_valid_simple_alias(self) -> None:
        """Test simple lowercase alias."""
        dep = ModelCapabilityDependency(alias="db", capability="database")
        assert dep.alias == "db"

    def test_valid_snake_case_alias(self) -> None:
        """Test snake_case alias."""
        dep = ModelCapabilityDependency(alias="primary_db", capability="database")
        assert dep.alias == "primary_db"

    def test_alias_with_numbers(self) -> None:
        """Test alias with numbers (not at start)."""
        dep = ModelCapabilityDependency(alias="db2", capability="database")
        assert dep.alias == "db2"

    def test_empty_alias_rejected(self) -> None:
        """Test that empty alias is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelCapabilityDependency(alias="", capability="database")
        assert "alias" in str(exc_info.value).lower()

    def test_alias_starting_with_number_rejected(self) -> None:
        """Test that alias starting with number is rejected."""
        with pytest.raises(ValidationError):
            ModelCapabilityDependency(alias="2db", capability="database")

    def test_uppercase_alias_rejected(self) -> None:
        """Test that uppercase alias is rejected."""
        with pytest.raises(ValidationError):
            ModelCapabilityDependency(alias="DB", capability="database")

    def test_alias_with_hyphen_rejected(self) -> None:
        """Test that alias with hyphen is rejected."""
        with pytest.raises(ValidationError):
            ModelCapabilityDependency(alias="primary-db", capability="database")


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
            capability="database",
            selection_policy=policy,  # type: ignore[arg-type]
        )
        assert dep.selection_policy == policy

    def test_invalid_selection_policy_rejected(self) -> None:
        """Test that invalid selection policy is rejected."""
        with pytest.raises(ValidationError):
            ModelCapabilityDependency(
                alias="db",
                capability="database",
                selection_policy="invalid_policy",  # type: ignore[arg-type]
            )


@pytest.mark.unit
class TestProviderMatching:
    """Tests for provider matching via requirements."""

    def test_matches_provider_with_must_satisfied(self) -> None:
        """Test matching when must requirements satisfied."""
        dep = ModelCapabilityDependency(
            alias="db",
            capability="database",
            requirements=ModelRequirementSet(
                must={"supports_transactions": True},
            ),
        )
        provider = {"supports_transactions": True, "max_connections": 100}
        matches, score, _warnings = dep.matches_provider(provider)
        assert matches is True
        assert score == 0.0  # No prefer requirements

    def test_matches_provider_with_must_not_satisfied(self) -> None:
        """Test matching when must requirements not satisfied."""
        dep = ModelCapabilityDependency(
            alias="db",
            capability="database",
            requirements=ModelRequirementSet(
                must={"supports_transactions": True},
            ),
        )
        provider = {"supports_transactions": False}
        matches, _score, _warnings = dep.matches_provider(provider)
        assert matches is False

    def test_matches_provider_with_prefer_scoring(self) -> None:
        """Test scoring based on prefer requirements."""
        dep = ModelCapabilityDependency(
            alias="db",
            capability="database",
            requirements=ModelRequirementSet(
                must={"active": True},
                prefer={"fast": True, "cheap": True},
            ),
        )
        # Provider satisfies must and one prefer
        provider = {"active": True, "fast": True, "cheap": False}
        matches, score, _warnings = dep.matches_provider(provider)
        assert matches is True
        assert score == 1.0  # One prefer satisfied

    def test_is_optional_for_non_strict(self) -> None:
        """Test is_optional returns True for non-strict dependencies."""
        dep = ModelCapabilityDependency(
            alias="cache",
            capability="cache",
            strict=False,
        )
        assert dep.is_optional() is True

    def test_is_optional_for_strict(self) -> None:
        """Test is_optional returns False for strict dependencies."""
        dep = ModelCapabilityDependency(
            alias="db",
            capability="database",
            strict=True,
        )
        assert dep.is_optional() is False


@pytest.mark.unit
class TestImmutability:
    """Tests for model immutability."""

    def test_model_is_frozen(self) -> None:
        """Test that model instances are immutable."""
        dep = ModelCapabilityDependency(
            alias="db",
            capability="database",
        )
        with pytest.raises(ValidationError):
            dep.alias = "new_alias"  # type: ignore[misc]

    def test_extra_fields_forbidden(self) -> None:
        """Test that extra fields are not allowed."""
        with pytest.raises(ValidationError):
            ModelCapabilityDependency(
                alias="db",
                capability="database",
                unknown_field="value",  # type: ignore[call-arg]
            )
