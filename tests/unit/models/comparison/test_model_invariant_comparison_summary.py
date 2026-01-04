"""Tests for ModelInvariantComparisonSummary."""

from typing import Any

import pytest
from pydantic import ValidationError

from omnibase_core.models.comparison import ModelInvariantComparisonSummary


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

    def test_regression_detected_true_when_new_violations_present(self) -> None:
        """regression_detected is True when new_violations > 0."""
        summary = ModelInvariantComparisonSummary(
            total_invariants=5,
            both_passed=3,
            both_failed=0,
            new_violations=2,
            fixed_violations=0,
        )
        assert summary.new_violations > 0
        assert summary.regression_detected is True

    def test_regression_detected_false_when_no_new_violations(self) -> None:
        """regression_detected is False when new_violations == 0."""
        summary = ModelInvariantComparisonSummary(
            total_invariants=5,
            both_passed=4,
            both_failed=1,
            new_violations=0,
            fixed_violations=0,
        )
        assert summary.new_violations == 0
        assert summary.regression_detected is False

    def test_model_is_immutable_after_creation(self) -> None:
        """Model is immutable (frozen) after creation."""
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

    def test_serialization_to_dict_and_json(self) -> None:
        """Model can be serialized to dict and JSON."""
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

    def test_model_validate_from_object_attributes(self) -> None:
        """Model can be created from object attributes via model_validate."""

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

    def test_handles_zero_total_invariants(self) -> None:
        """Model accepts zero total_invariants for empty comparisons."""
        summary = ModelInvariantComparisonSummary(
            total_invariants=0,
            both_passed=0,
            both_failed=0,
            new_violations=0,
            fixed_violations=0,
        )
        assert summary.total_invariants == 0
        assert summary.regression_detected is False

    def test_handles_all_invariants_passed_in_both(self) -> None:
        """Model accepts all invariants passing in both baseline and replay."""
        summary = ModelInvariantComparisonSummary(
            total_invariants=10,
            both_passed=10,
            both_failed=0,
            new_violations=0,
            fixed_violations=0,
        )
        assert summary.both_passed == summary.total_invariants
        assert summary.regression_detected is False

    def test_handles_all_invariants_failed_in_both(self) -> None:
        """Model accepts all invariants failing in both baseline and replay."""
        summary = ModelInvariantComparisonSummary(
            total_invariants=10,
            both_passed=0,
            both_failed=10,
            new_violations=0,
            fixed_violations=0,
        )
        assert summary.both_failed == summary.total_invariants
        assert summary.regression_detected is False

    def test_handles_all_invariants_as_new_violations(self) -> None:
        """Model accepts all invariants as new violations (regressions)."""
        summary = ModelInvariantComparisonSummary(
            total_invariants=5,
            both_passed=0,
            both_failed=0,
            new_violations=5,
            fixed_violations=0,
        )
        assert summary.new_violations == summary.total_invariants
        assert summary.regression_detected is True

    def test_handles_all_invariants_as_fixed(self) -> None:
        """Model accepts all invariants as fixed violations."""
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
