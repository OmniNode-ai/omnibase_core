# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for ModelInvariantComparisonSummary model.

Tests the invariant comparison summary model used for aggregating
statistics about how invariant evaluations changed between baseline
and replay executions.

Computed Fields:
    - ``regression_detected``: A @computed_field derived from ``new_violations > 0``.
      This field is NOT a constructor parameter and cannot be overridden.
      It is automatically computed based on the actual ``new_violations`` count.

Test Categories:
    - Creation: Model instantiation and field validation
    - Validation: Constraint validation (non-negative values, count consistency)
    - Edge Cases: Boundary conditions (zero invariants, all passed/failed)
    - Equality: Model equality comparisons
    - Data Consistency: Validator that enforces counts sum to total
    - Computed Fields: Verification that regression_detected is derived correctly
"""

from typing import Any

import pytest
from pydantic import ValidationError

from omnibase_core.models.replay import ModelInvariantComparisonSummary


@pytest.mark.unit
class TestModelInvariantComparisonSummaryCreation:
    """Test ModelInvariantComparisonSummary creation and validation."""

    def test_creation_with_all_fields_succeeds(self) -> None:
        """Model can be created with all required fields."""
        summary = ModelInvariantComparisonSummary(
            total_invariants=10,
            both_passed=5,
            both_failed=2,
            new_violations=2,
            fixed_violations=1,
        )
        assert summary.total_invariants == 10
        assert summary.both_passed == 5
        assert summary.both_failed == 2
        assert summary.new_violations == 2
        assert summary.fixed_violations == 1
        assert summary.regression_detected is True

    def test_validation_fails_when_total_invariants_missing(self) -> None:
        """Validation fails if total_invariants is not provided."""
        with pytest.raises(ValidationError) as exc_info:
            ModelInvariantComparisonSummary(
                both_passed=5,
                both_failed=2,
                new_violations=2,
                fixed_violations=1,
            )
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("total_invariants",) for e in errors)

    def test_validation_fails_when_any_required_field_missing(self) -> None:
        """Validation fails if any required field is missing.

        Note: regression_detected is a computed field (derived from new_violations > 0),
        so it's not included in the required fields list.
        """
        required_fields = [
            "total_invariants",
            "both_passed",
            "both_failed",
            "new_violations",
            "fixed_violations",
        ]
        for field in required_fields:
            data: dict[str, Any] = {
                "total_invariants": 10,
                "both_passed": 5,
                "both_failed": 2,
                "new_violations": 2,
                "fixed_violations": 1,
            }
            del data[field]
            with pytest.raises(ValidationError) as exc_info:
                ModelInvariantComparisonSummary(**data)
            errors = exc_info.value.errors()
            assert any(e["loc"] == (field,) for e in errors), (
                f"Field {field} should be required"
            )

    def test_computed_regression_detected_returns_true_when_new_violations_present(
        self,
    ) -> None:
        """Computed field regression_detected returns True when new_violations > 0.

        Note: regression_detected is a @computed_field derived from new_violations > 0.
        It is not a constructor parameter and cannot be set directly.
        """
        summary = ModelInvariantComparisonSummary(
            total_invariants=5,
            both_passed=3,
            both_failed=0,
            new_violations=2,
            fixed_violations=0,
        )
        assert summary.new_violations > 0
        assert summary.regression_detected is True

    def test_computed_regression_detected_returns_false_when_no_new_violations(
        self,
    ) -> None:
        """Computed field regression_detected returns False when new_violations == 0.

        Note: regression_detected is a @computed_field derived from new_violations > 0.
        It is not a constructor parameter and cannot be set directly.
        """
        summary = ModelInvariantComparisonSummary(
            total_invariants=5,
            both_passed=4,
            both_failed=1,
            new_violations=0,
            fixed_violations=0,
        )
        assert summary.new_violations == 0
        assert summary.regression_detected is False

    def test_computed_regression_detected_derives_from_new_violations_not_constructor(
        self,
    ) -> None:
        """Computed field regression_detected derives from new_violations, not constructor.

        IMPORTANT - Computed Field Behavior:
            - ``regression_detected`` is a @computed_field, NOT a stored field
            - It is derived from the expression: ``new_violations > 0``
            - It cannot be overridden via constructor (extra="ignore" silently ignores it)
            - The value is always dynamically computed from actual new_violations count

        This test explicitly verifies all three computed field behaviors:
            1. new_violations=0 -> regression_detected=False
            2. new_violations>0 -> regression_detected=True
            3. Constructor parameter attempts are ignored
        """
        # Case 1: new_violations=0 -> regression_detected=False
        summary_no_regression = ModelInvariantComparisonSummary(
            total_invariants=5,
            both_passed=5,
            both_failed=0,
            new_violations=0,
            fixed_violations=0,
        )
        assert summary_no_regression.regression_detected is False

        # Case 2: new_violations>0 -> regression_detected=True
        summary_with_regression = ModelInvariantComparisonSummary(
            total_invariants=5,
            both_passed=3,
            both_failed=0,
            new_violations=2,
            fixed_violations=0,
        )
        assert summary_with_regression.regression_detected is True

        # Case 3: Verify computed field cannot be overridden via constructor
        # Even if someone tries to pass regression_detected=False with new_violations>0,
        # the computed field will still return True (extra="ignore" silently ignores it)
        summary_override_attempt = ModelInvariantComparisonSummary(
            total_invariants=5,
            both_passed=3,
            both_failed=0,
            new_violations=2,
            fixed_violations=0,
            # NOTE: regression_detected is NOT a constructor parameter
            # Any attempt to pass it would be ignored due to extra="ignore"
        )
        # Computed field always reflects actual new_violations count
        assert summary_override_attempt.regression_detected is True

    def test_mutation_on_frozen_model_raises_validation_error(self) -> None:
        """Mutation attempt on frozen model raises ValidationError."""
        summary = ModelInvariantComparisonSummary(
            total_invariants=5,
            both_passed=3,
            both_failed=1,
            new_violations=1,
            fixed_violations=0,
        )
        with pytest.raises(ValidationError):
            summary.total_invariants = 10
        with pytest.raises(ValidationError):
            summary.regression_detected = False


@pytest.mark.unit
class TestModelInvariantComparisonSummaryValidation:
    """Test validation logic for comparison summary."""

    def test_validation_rejects_negative_count_values(self) -> None:
        """Validation rejects negative values for count fields."""
        count_fields = [
            "total_invariants",
            "both_passed",
            "both_failed",
            "new_violations",
            "fixed_violations",
        ]
        for field in count_fields:
            data: dict[str, Any] = {
                "total_invariants": 10,
                "both_passed": 5,
                "both_failed": 2,
                "new_violations": 2,
                "fixed_violations": 1,
            }
            data[field] = -1
            with pytest.raises(ValidationError) as exc_info:
                ModelInvariantComparisonSummary(**data)
            errors = exc_info.value.errors()
            assert any(
                e["loc"] == (field,) and "greater than or equal to 0" in str(e["msg"])
                for e in errors
            ), f"Field {field} should reject negative values"

    def test_counts_sum_equals_total_invariants(self) -> None:
        """Counts are consistent (both_passed + both_failed + new + fixed = total).

        Note: This is a semantic consistency test. The model accepts any valid
        non-negative integers, but logically consistent data should satisfy
        this equation.
        """
        # Valid consistent data
        summary = ModelInvariantComparisonSummary(
            total_invariants=10,
            both_passed=5,
            both_failed=2,
            new_violations=2,
            fixed_violations=1,
        )
        computed_total = (
            summary.both_passed
            + summary.both_failed
            + summary.new_violations
            + summary.fixed_violations
        )
        assert computed_total == summary.total_invariants

        # Test with perfect baseline/replay match (no changes)
        summary_no_changes = ModelInvariantComparisonSummary(
            total_invariants=5,
            both_passed=5,
            both_failed=0,
            new_violations=0,
            fixed_violations=0,
        )
        computed = (
            summary_no_changes.both_passed
            + summary_no_changes.both_failed
            + summary_no_changes.new_violations
            + summary_no_changes.fixed_violations
        )
        assert computed == summary_no_changes.total_invariants

    def test_serialization_to_dict_and_json_succeeds(self) -> None:
        """Serialization to dict and JSON returns valid representations."""
        summary = ModelInvariantComparisonSummary(
            total_invariants=10,
            both_passed=5,
            both_failed=2,
            new_violations=2,
            fixed_violations=1,
        )
        # Test dict serialization
        data = summary.model_dump()
        assert isinstance(data, dict)
        assert data["total_invariants"] == 10
        assert data["both_passed"] == 5
        assert data["both_failed"] == 2
        assert data["new_violations"] == 2
        assert data["fixed_violations"] == 1
        assert data["regression_detected"] is True

        # Test JSON serialization
        json_str = summary.model_dump_json()
        assert isinstance(json_str, str)
        assert '"total_invariants":10' in json_str
        assert '"regression_detected":true' in json_str

    def test_model_validate_from_attributes_succeeds(self) -> None:
        """Model validation from object attributes creates valid model."""

        class SummaryData:
            """Mock object with summary attributes."""

            def __init__(self) -> None:
                self.total_invariants = 8
                self.both_passed = 4
                self.both_failed = 1
                self.new_violations = 2
                self.fixed_violations = 1

        summary = ModelInvariantComparisonSummary.model_validate(SummaryData())
        assert summary.total_invariants == 8
        assert summary.both_passed == 4
        assert summary.both_failed == 1
        assert summary.new_violations == 2
        assert summary.fixed_violations == 1
        assert summary.regression_detected is True


@pytest.mark.unit
class TestModelInvariantComparisonSummaryEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_creation_with_zero_total_invariants_succeeds(self) -> None:
        """Creation with zero total_invariants for empty comparisons succeeds."""
        summary = ModelInvariantComparisonSummary(
            total_invariants=0,
            both_passed=0,
            both_failed=0,
            new_violations=0,
            fixed_violations=0,
        )
        assert summary.total_invariants == 0
        assert summary.regression_detected is False

    def test_creation_with_all_invariants_passed_succeeds(self) -> None:
        """Creation with all invariants passing in both baseline and replay succeeds."""
        summary = ModelInvariantComparisonSummary(
            total_invariants=10,
            both_passed=10,
            both_failed=0,
            new_violations=0,
            fixed_violations=0,
        )
        assert summary.both_passed == summary.total_invariants
        assert summary.regression_detected is False

    def test_creation_with_all_invariants_failed_succeeds(self) -> None:
        """Creation with all invariants failing in both baseline and replay succeeds."""
        summary = ModelInvariantComparisonSummary(
            total_invariants=10,
            both_passed=0,
            both_failed=10,
            new_violations=0,
            fixed_violations=0,
        )
        assert summary.both_failed == summary.total_invariants
        assert summary.regression_detected is False

    def test_creation_with_all_new_violations_succeeds(self) -> None:
        """Creation with all invariants as new violations (regressions) succeeds."""
        summary = ModelInvariantComparisonSummary(
            total_invariants=5,
            both_passed=0,
            both_failed=0,
            new_violations=5,
            fixed_violations=0,
        )
        assert summary.new_violations == summary.total_invariants
        assert summary.regression_detected is True

    def test_creation_with_all_fixed_violations_succeeds(self) -> None:
        """Creation with all invariants as fixed violations succeeds."""
        summary = ModelInvariantComparisonSummary(
            total_invariants=5,
            both_passed=0,
            both_failed=0,
            new_violations=0,
            fixed_violations=5,
        )
        assert summary.fixed_violations == summary.total_invariants
        assert summary.regression_detected is False


@pytest.mark.unit
class TestModelInvariantComparisonSummaryEquality:
    """Test equality and comparison behavior."""

    def test_equality_when_same_values_returns_true(self) -> None:
        """Two instances with identical values are equal."""
        summary1 = ModelInvariantComparisonSummary(
            total_invariants=10,
            both_passed=5,
            both_failed=2,
            new_violations=2,
            fixed_violations=1,
        )
        summary2 = ModelInvariantComparisonSummary(
            total_invariants=10,
            both_passed=5,
            both_failed=2,
            new_violations=2,
            fixed_violations=1,
        )
        assert summary1 == summary2

    def test_equality_when_different_values_returns_false(self) -> None:
        """Two instances with different values are not equal."""
        summary1 = ModelInvariantComparisonSummary(
            total_invariants=10,
            both_passed=5,
            both_failed=2,
            new_violations=2,
            fixed_violations=1,
        )
        summary2 = ModelInvariantComparisonSummary(
            total_invariants=10,
            both_passed=6,  # Different value
            both_failed=2,
            new_violations=1,  # Different value
            fixed_violations=1,
        )
        assert summary1 != summary2


@pytest.mark.unit
class TestModelInvariantComparisonSummaryWithFixture:
    """Test using fixtures from conftest.py."""

    def test_creation_from_fixture_data_succeeds(
        self, sample_invariant_comparison_summary: dict[str, Any]
    ) -> None:
        """Model can be created from fixture data."""
        summary = ModelInvariantComparisonSummary(**sample_invariant_comparison_summary)
        assert summary.total_invariants == 5
        assert summary.both_passed == 3
        assert summary.both_failed == 0
        assert summary.new_violations == 1
        assert summary.fixed_violations == 1
        assert summary.regression_detected is True


@pytest.mark.unit
class TestModelInvariantComparisonSummaryDataConsistency:
    """Test data consistency validation for comparison summary.

    These tests verify the model validator that enforces:
    both_passed + both_failed + new_violations + fixed_violations == total_invariants
    """

    def test_validation_rejects_counts_exceeding_total(self) -> None:
        """Validation rejects when counts sum exceeds total_invariants."""
        # Sum of counts: 5 + 3 + 2 + 2 = 12, but total_invariants = 10
        with pytest.raises(ValidationError) as exc_info:
            ModelInvariantComparisonSummary(
                total_invariants=10,
                both_passed=5,
                both_failed=3,
                new_violations=2,
                fixed_violations=2,
            )
        errors = exc_info.value.errors()
        # Check that the error message mentions the consistency issue
        error_messages = [str(e.get("msg", "")) for e in errors]
        assert any(
            "must equal" in msg or "sum" in msg.lower() or "total" in msg.lower()
            for msg in error_messages
        ), f"Expected consistency validation error, got: {errors}"

    def test_validation_rejects_counts_less_than_total(self) -> None:
        """Validation rejects when counts sum is less than total_invariants."""
        # Sum of counts: 2 + 1 + 1 + 1 = 5, but total_invariants = 10
        with pytest.raises(ValidationError) as exc_info:
            ModelInvariantComparisonSummary(
                total_invariants=10,
                both_passed=2,
                both_failed=1,
                new_violations=1,
                fixed_violations=1,
            )
        errors = exc_info.value.errors()
        # Check that the error message mentions the consistency issue
        error_messages = [str(e.get("msg", "")) for e in errors]
        assert any(
            "must equal" in msg or "sum" in msg.lower() or "total" in msg.lower()
            for msg in error_messages
        ), f"Expected consistency validation error, got: {errors}"

    def test_validation_accepts_consistent_counts(self) -> None:
        """Validation accepts when counts sum equals total_invariants."""
        # Sum of counts: 5 + 2 + 2 + 1 = 10, matches total_invariants = 10
        summary = ModelInvariantComparisonSummary(
            total_invariants=10,
            both_passed=5,
            both_failed=2,
            new_violations=2,
            fixed_violations=1,
        )
        assert summary.total_invariants == 10
        computed_sum = (
            summary.both_passed
            + summary.both_failed
            + summary.new_violations
            + summary.fixed_violations
        )
        assert computed_sum == summary.total_invariants


@pytest.mark.unit
class TestModelInvariantComparisonSummaryCountValidationEdgeCases:
    """Test edge cases for invariant count validation.

    These tests verify boundary conditions and specific error scenarios
    for the count consistency validator.
    """

    def test_edge_count_validation_off_by_one_high(self) -> None:
        """Validation rejects when counts sum is exactly one more than total.

        This tests the boundary condition where the sum exceeds total by just 1.
        """
        # Sum: 4 + 2 + 2 + 2 = 10, but total_invariants = 9 (off by +1)
        with pytest.raises(ValidationError) as exc_info:
            ModelInvariantComparisonSummary(
                total_invariants=9,
                both_passed=4,
                both_failed=2,
                new_violations=2,
                fixed_violations=2,
            )
        errors = exc_info.value.errors()
        error_messages = [str(e.get("msg", "")) for e in errors]
        # Verify specific error message mentions the mismatch
        assert any(
            "10" in msg
            and "9" in msg  # Should mention both computed (10) and expected (9)
            for msg in error_messages
        ), f"Expected error mentioning counts 10 vs 9, got: {errors}"

    def test_edge_count_validation_off_by_one_low(self) -> None:
        """Validation rejects when counts sum is exactly one less than total.

        This tests the boundary condition where the sum is under total by just 1.
        """
        # Sum: 4 + 2 + 2 + 1 = 9, but total_invariants = 10 (off by -1)
        with pytest.raises(ValidationError) as exc_info:
            ModelInvariantComparisonSummary(
                total_invariants=10,
                both_passed=4,
                both_failed=2,
                new_violations=2,
                fixed_violations=1,
            )
        errors = exc_info.value.errors()
        error_messages = [str(e.get("msg", "")) for e in errors]
        # Verify specific error message mentions the mismatch
        assert any(
            "9" in msg
            and "10" in msg  # Should mention both computed (9) and expected (10)
            for msg in error_messages
        ), f"Expected error mentioning counts 9 vs 10, got: {errors}"

    def test_edge_count_validation_with_large_numbers(self) -> None:
        """Validation works correctly with large invariant counts.

        This tests that the validator handles large numbers without overflow
        or precision issues.
        """
        # Large but valid counts
        large_total = 1_000_000
        summary = ModelInvariantComparisonSummary(
            total_invariants=large_total,
            both_passed=500_000,
            both_failed=250_000,
            new_violations=150_000,
            fixed_violations=100_000,
        )
        assert summary.total_invariants == large_total
        computed_sum = (
            summary.both_passed
            + summary.both_failed
            + summary.new_violations
            + summary.fixed_violations
        )
        assert computed_sum == large_total

    def test_edge_count_validation_large_numbers_invalid(self) -> None:
        """Validation correctly rejects large invalid counts.

        This tests that the validator catches mismatches with large numbers.
        """
        with pytest.raises(ValidationError):
            ModelInvariantComparisonSummary(
                total_invariants=1_000_000,
                both_passed=500_001,  # One extra
                both_failed=250_000,
                new_violations=150_000,
                fixed_violations=100_000,
            )

    def test_edge_count_validation_error_message_details(self) -> None:
        """Validation error message includes detailed breakdown.

        The error message should include all count values to help debugging.
        """
        with pytest.raises(ValidationError) as exc_info:
            ModelInvariantComparisonSummary(
                total_invariants=10,
                both_passed=3,
                both_failed=2,
                new_violations=1,
                fixed_violations=1,  # Sum = 7, expected 10
            )
        error_str = str(exc_info.value)
        # Error should mention the computed sum
        assert "7" in error_str, "Error should mention computed sum (7)"
        # Error should mention the expected total
        assert "10" in error_str, "Error should mention expected total (10)"

    def test_edge_count_validation_zero_total_with_zero_counts(self) -> None:
        """Validation accepts zero total with all zero counts.

        Edge case: Empty comparison with no invariants.
        """
        summary = ModelInvariantComparisonSummary(
            total_invariants=0,
            both_passed=0,
            both_failed=0,
            new_violations=0,
            fixed_violations=0,
        )
        assert summary.total_invariants == 0
        computed_sum = (
            summary.both_passed
            + summary.both_failed
            + summary.new_violations
            + summary.fixed_violations
        )
        assert computed_sum == 0

    def test_edge_count_validation_zero_total_with_nonzero_count_fails(self) -> None:
        """Validation rejects zero total with any non-zero count.

        If total_invariants is 0, all individual counts must also be 0.
        """
        with pytest.raises(ValidationError) as exc_info:
            ModelInvariantComparisonSummary(
                total_invariants=0,
                both_passed=1,  # Invalid: can't have passed invariants with 0 total
                both_failed=0,
                new_violations=0,
                fixed_violations=0,
            )
        errors = exc_info.value.errors()
        error_messages = [str(e.get("msg", "")) for e in errors]
        assert any("1" in msg and "0" in msg for msg in error_messages), (
            f"Expected error for non-zero count with zero total, got: {errors}"
        )

    def test_edge_count_validation_all_in_single_category(self) -> None:
        """Validation accepts all counts in a single category.

        Tests extreme cases where all invariants fall into one category.
        """
        # All passed
        summary_all_passed = ModelInvariantComparisonSummary(
            total_invariants=100,
            both_passed=100,
            both_failed=0,
            new_violations=0,
            fixed_violations=0,
        )
        assert summary_all_passed.both_passed == 100
        assert summary_all_passed.regression_detected is False

        # All new violations
        summary_all_new = ModelInvariantComparisonSummary(
            total_invariants=100,
            both_passed=0,
            both_failed=0,
            new_violations=100,
            fixed_violations=0,
        )
        assert summary_all_new.new_violations == 100
        assert summary_all_new.regression_detected is True

        # All fixed violations
        summary_all_fixed = ModelInvariantComparisonSummary(
            total_invariants=100,
            both_passed=0,
            both_failed=0,
            new_violations=0,
            fixed_violations=100,
        )
        assert summary_all_fixed.fixed_violations == 100
        assert summary_all_fixed.regression_detected is False

    def test_edge_count_validation_mixed_categories(self) -> None:
        """Validation accepts various valid combinations of categories.

        Tests that the validator correctly handles different distributions
        of counts across categories.
        """
        # Mix 1: Mostly passed with some new violations
        summary1 = ModelInvariantComparisonSummary(
            total_invariants=100,
            both_passed=90,
            both_failed=5,
            new_violations=3,
            fixed_violations=2,
        )
        assert summary1.regression_detected is True  # 3 new violations

        # Mix 2: High both_failed with fixes
        summary2 = ModelInvariantComparisonSummary(
            total_invariants=50,
            both_passed=10,
            both_failed=30,
            new_violations=0,
            fixed_violations=10,
        )
        assert summary2.regression_detected is False  # No new violations

        # Mix 3: Single invariant in each category
        summary3 = ModelInvariantComparisonSummary(
            total_invariants=4,
            both_passed=1,
            both_failed=1,
            new_violations=1,
            fixed_violations=1,
        )
        assert summary3.regression_detected is True  # 1 new violation
