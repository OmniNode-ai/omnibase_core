# SPDX-FileCopyrightText: 2025 OmniNode Team
# SPDX-License-Identifier: Apache-2.0
"""
Unit tests for ModelExecutionConstraints.

Tests execution constraint specification including:
- Basic creation and validation
- Dependency reference format validation
- Helper methods for constraint analysis
- Immutability
"""

import pytest
from pydantic import ValidationError

from omnibase_core.models.contracts.model_execution_constraints import (
    ModelExecutionConstraints,
)


@pytest.mark.unit
class TestModelExecutionConstraintsCreation:
    """Tests for ModelExecutionConstraints creation."""

    def test_default_creation(self) -> None:
        """Test creation with all defaults."""
        constraints = ModelExecutionConstraints()
        assert constraints.requires_before == []
        assert constraints.requires_after == []
        assert constraints.must_run is False
        assert constraints.can_run_parallel is True
        assert constraints.nondeterministic_effect is False

    def test_full_creation(self) -> None:
        """Test creation with all fields."""
        constraints = ModelExecutionConstraints(
            requires_before=["capability:auth", "handler:validation"],
            requires_after=["capability:logging"],
            must_run=True,
            can_run_parallel=False,
            nondeterministic_effect=True,
        )
        assert constraints.requires_before == ["capability:auth", "handler:validation"]
        assert constraints.requires_after == ["capability:logging"]
        assert constraints.must_run is True
        assert constraints.can_run_parallel is False
        assert constraints.nondeterministic_effect is True

    def test_creation_with_tag_references(self) -> None:
        """Test creation with tag-based references."""
        constraints = ModelExecutionConstraints(
            requires_before=["tag:security", "tag:audit"],
        )
        assert constraints.requires_before == ["tag:security", "tag:audit"]


@pytest.mark.unit
class TestDependencyReferenceValidation:
    """Tests for dependency reference format validation."""

    @pytest.mark.parametrize(
        "ref",
        [
            "capability:auth",
            "capability:database.relational",
            "handler:metrics",
            "handler:user_registration",
            "tag:security",
            "tag:phase1",
        ],
    )
    def test_valid_reference_formats(self, ref: str) -> None:
        """Test all valid reference prefix formats."""
        constraints = ModelExecutionConstraints(requires_before=[ref])
        assert ref in constraints.requires_before

    def test_reference_without_prefix_rejected(self) -> None:
        """Test that reference without valid prefix is rejected."""
        with pytest.raises(ValidationError, match="must start with one of"):
            ModelExecutionConstraints(requires_before=["auth"])

    def test_reference_with_invalid_prefix_rejected(self) -> None:
        """Test that reference with invalid prefix is rejected."""
        with pytest.raises(ValidationError, match="must start with one of"):
            ModelExecutionConstraints(requires_before=["invalid:auth"])

    def test_empty_reference_rejected(self) -> None:
        """Test that empty reference is rejected."""
        with pytest.raises(ValidationError, match="cannot be empty"):
            ModelExecutionConstraints(requires_before=[""])

    def test_reference_with_empty_value_rejected(self) -> None:
        """Test that reference with empty value after prefix is rejected."""
        with pytest.raises(ValidationError, match="must have a value after the prefix"):
            ModelExecutionConstraints(requires_before=["capability:"])

    def test_reference_with_whitespace_only_rejected(self) -> None:
        """Test that whitespace-only reference is rejected."""
        with pytest.raises(ValidationError, match="cannot be empty"):
            ModelExecutionConstraints(requires_before=["   "])

    def test_requires_after_validation(self) -> None:
        """Test that requires_after has same validation as requires_before."""
        with pytest.raises(ValidationError, match="must start with one of"):
            ModelExecutionConstraints(requires_after=["invalid_ref"])


@pytest.mark.unit
class TestConstraintHelperMethods:
    """Tests for constraint analysis helper methods."""

    def test_has_ordering_constraints_empty(self) -> None:
        """Test has_ordering_constraints with no constraints."""
        constraints = ModelExecutionConstraints()
        assert constraints.has_ordering_constraints() is False

    def test_has_ordering_constraints_with_before(self) -> None:
        """Test has_ordering_constraints with requires_before."""
        constraints = ModelExecutionConstraints(
            requires_before=["capability:auth"],
        )
        assert constraints.has_ordering_constraints() is True

    def test_has_ordering_constraints_with_after(self) -> None:
        """Test has_ordering_constraints with requires_after."""
        constraints = ModelExecutionConstraints(
            requires_after=["capability:logging"],
        )
        assert constraints.has_ordering_constraints() is True

    def test_has_ordering_constraints_with_both(self) -> None:
        """Test has_ordering_constraints with both before and after."""
        constraints = ModelExecutionConstraints(
            requires_before=["capability:auth"],
            requires_after=["capability:logging"],
        )
        assert constraints.has_ordering_constraints() is True

    def test_get_all_dependencies_empty(self) -> None:
        """Test get_all_dependencies with no constraints."""
        constraints = ModelExecutionConstraints()
        assert constraints.get_all_dependencies() == []

    def test_get_all_dependencies_combined(self) -> None:
        """Test get_all_dependencies combines before and after."""
        constraints = ModelExecutionConstraints(
            requires_before=["capability:auth", "handler:validation"],
            requires_after=["capability:logging"],
        )
        deps = constraints.get_all_dependencies()
        assert len(deps) == 3
        assert "capability:auth" in deps
        assert "handler:validation" in deps
        assert "capability:logging" in deps


@pytest.mark.unit
class TestConstraintFlags:
    """Tests for constraint boolean flags."""

    def test_must_run_default_false(self) -> None:
        """Test must_run defaults to False."""
        constraints = ModelExecutionConstraints()
        assert constraints.must_run is False

    def test_must_run_explicit_true(self) -> None:
        """Test must_run can be set to True."""
        constraints = ModelExecutionConstraints(must_run=True)
        assert constraints.must_run is True

    def test_can_run_parallel_default_true(self) -> None:
        """Test can_run_parallel defaults to True."""
        constraints = ModelExecutionConstraints()
        assert constraints.can_run_parallel is True

    def test_can_run_parallel_explicit_false(self) -> None:
        """Test can_run_parallel can be set to False."""
        constraints = ModelExecutionConstraints(can_run_parallel=False)
        assert constraints.can_run_parallel is False

    def test_nondeterministic_effect_default_false(self) -> None:
        """Test nondeterministic_effect defaults to False."""
        constraints = ModelExecutionConstraints()
        assert constraints.nondeterministic_effect is False

    def test_nondeterministic_effect_explicit_true(self) -> None:
        """Test nondeterministic_effect can be set to True."""
        constraints = ModelExecutionConstraints(nondeterministic_effect=True)
        assert constraints.nondeterministic_effect is True


@pytest.mark.unit
class TestImmutability:
    """Tests for model immutability."""

    def test_model_is_frozen(self) -> None:
        """Test that model instances are immutable."""
        constraints = ModelExecutionConstraints(
            requires_before=["capability:auth"],
        )
        with pytest.raises(ValidationError):
            constraints.must_run = True  # type: ignore[misc]

    def test_extra_fields_forbidden(self) -> None:
        """Test that extra fields are not allowed."""
        with pytest.raises(ValidationError):
            ModelExecutionConstraints(
                unknown_field="value",  # type: ignore[call-arg]
            )
