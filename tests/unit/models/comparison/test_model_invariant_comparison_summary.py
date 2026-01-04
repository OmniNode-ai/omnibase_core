"""Tests for ModelInvariantComparisonSummary."""

from typing import Any

import pytest
from pydantic import ValidationError

from omnibase_core.models.comparison import ModelInvariantComparisonSummary


@pytest.mark.unit
class TestModelInvariantComparisonSummaryCreation:
    """Test ModelInvariantComparisonSummary creation and validation."""

    def test_create_summary_with_all_fields(self) -> None:
        """Summary can be created with all required fields."""
        summary = ModelInvariantComparisonSummary(
            total_invariants=10,
            both_passed=5,
            both_failed=2,
            new_violations=2,
            fixed_violations=1,
            regression_detected=True,
        )
        assert summary.total_invariants == 10
        assert summary.both_passed == 5
        assert summary.both_failed == 2
        assert summary.new_violations == 2
        assert summary.fixed_violations == 1
        assert summary.regression_detected is True

    def test_summary_requires_total_invariants(self) -> None:
        """total_invariants is a required field."""
        with pytest.raises(ValidationError) as exc_info:
            ModelInvariantComparisonSummary(
                both_passed=5,
                both_failed=2,
                new_violations=2,
                fixed_violations=1,
                regression_detected=True,
            )
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("total_invariants",) for e in errors)

    def test_summary_requires_all_fields(self) -> None:
        """All fields are required - validation fails if any is missing."""
        required_fields = [
            "total_invariants",
            "both_passed",
            "both_failed",
            "new_violations",
            "fixed_violations",
            "regression_detected",
        ]
        for field in required_fields:
            data: dict[str, Any] = {
                "total_invariants": 10,
                "both_passed": 5,
                "both_failed": 2,
                "new_violations": 2,
                "fixed_violations": 1,
                "regression_detected": True,
            }
            del data[field]
            with pytest.raises(ValidationError) as exc_info:
                ModelInvariantComparisonSummary(**data)
            errors = exc_info.value.errors()
            assert any(e["loc"] == (field,) for e in errors), (
                f"Field {field} should be required"
            )

    def test_summary_regression_detected_true_when_violations(self) -> None:
        """regression_detected should be True when new_violations > 0."""
        summary = ModelInvariantComparisonSummary(
            total_invariants=5,
            both_passed=3,
            both_failed=0,
            new_violations=2,
            fixed_violations=0,
            regression_detected=True,
        )
        assert summary.new_violations > 0
        assert summary.regression_detected is True

    def test_summary_regression_detected_false_when_no_violations(self) -> None:
        """regression_detected should be False when new_violations == 0."""
        summary = ModelInvariantComparisonSummary(
            total_invariants=5,
            both_passed=4,
            both_failed=1,
            new_violations=0,
            fixed_violations=0,
            regression_detected=False,
        )
        assert summary.new_violations == 0
        assert summary.regression_detected is False

    def test_summary_is_frozen(self) -> None:
        """Summary is immutable after creation."""
        summary = ModelInvariantComparisonSummary(
            total_invariants=5,
            both_passed=3,
            both_failed=1,
            new_violations=1,
            fixed_violations=0,
            regression_detected=True,
        )
        with pytest.raises(ValidationError):
            summary.total_invariants = 10
        with pytest.raises(ValidationError):
            summary.regression_detected = False


@pytest.mark.unit
class TestModelInvariantComparisonSummaryValidation:
    """Test validation logic for comparison summary."""

    def test_counts_must_be_non_negative(self) -> None:
        """All count fields must be >= 0."""
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
                "regression_detected": True,
            }
            data[field] = -1
            with pytest.raises(ValidationError) as exc_info:
                ModelInvariantComparisonSummary(**data)
            errors = exc_info.value.errors()
            assert any(
                e["loc"] == (field,) and "greater than or equal to 0" in str(e["msg"])
                for e in errors
            ), f"Field {field} should reject negative values"

    def test_total_equals_sum_of_parts(self) -> None:
        """Test that counts are consistent (both_passed + both_failed + new + fixed = total).

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
            regression_detected=True,
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
            regression_detected=False,
        )
        computed = (
            summary_no_changes.both_passed
            + summary_no_changes.both_failed
            + summary_no_changes.new_violations
            + summary_no_changes.fixed_violations
        )
        assert computed == summary_no_changes.total_invariants

    def test_summary_serialization(self) -> None:
        """Summary can be serialized to dict and JSON."""
        summary = ModelInvariantComparisonSummary(
            total_invariants=10,
            both_passed=5,
            both_failed=2,
            new_violations=2,
            fixed_violations=1,
            regression_detected=True,
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

    def test_summary_from_attributes(self) -> None:
        """Summary can be created from object attributes."""

        class SummaryData:
            """Mock object with summary attributes."""

            def __init__(self) -> None:
                self.total_invariants = 8
                self.both_passed = 4
                self.both_failed = 1
                self.new_violations = 2
                self.fixed_violations = 1
                self.regression_detected = True

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

    def test_summary_with_zero_invariants(self) -> None:
        """Summary can represent empty comparison with zero invariants."""
        summary = ModelInvariantComparisonSummary(
            total_invariants=0,
            both_passed=0,
            both_failed=0,
            new_violations=0,
            fixed_violations=0,
            regression_detected=False,
        )
        assert summary.total_invariants == 0
        assert summary.regression_detected is False

    def test_summary_all_passed(self) -> None:
        """Summary can represent all invariants passing in both runs."""
        summary = ModelInvariantComparisonSummary(
            total_invariants=10,
            both_passed=10,
            both_failed=0,
            new_violations=0,
            fixed_violations=0,
            regression_detected=False,
        )
        assert summary.both_passed == summary.total_invariants
        assert summary.regression_detected is False

    def test_summary_all_failed(self) -> None:
        """Summary can represent all invariants failing in both runs."""
        summary = ModelInvariantComparisonSummary(
            total_invariants=10,
            both_passed=0,
            both_failed=10,
            new_violations=0,
            fixed_violations=0,
            regression_detected=False,
        )
        assert summary.both_failed == summary.total_invariants
        assert summary.regression_detected is False

    def test_summary_all_new_violations(self) -> None:
        """Summary can represent all invariants being new regressions."""
        summary = ModelInvariantComparisonSummary(
            total_invariants=5,
            both_passed=0,
            both_failed=0,
            new_violations=5,
            fixed_violations=0,
            regression_detected=True,
        )
        assert summary.new_violations == summary.total_invariants
        assert summary.regression_detected is True

    def test_summary_all_fixed(self) -> None:
        """Summary can represent all invariants being fixed."""
        summary = ModelInvariantComparisonSummary(
            total_invariants=5,
            both_passed=0,
            both_failed=0,
            new_violations=0,
            fixed_violations=5,
            regression_detected=False,
        )
        assert summary.fixed_violations == summary.total_invariants
        assert summary.regression_detected is False


@pytest.mark.unit
class TestModelInvariantComparisonSummaryEquality:
    """Test equality and comparison behavior."""

    def test_summaries_with_same_values_are_equal(self) -> None:
        """Summaries with identical values should be equal."""
        summary1 = ModelInvariantComparisonSummary(
            total_invariants=10,
            both_passed=5,
            both_failed=2,
            new_violations=2,
            fixed_violations=1,
            regression_detected=True,
        )
        summary2 = ModelInvariantComparisonSummary(
            total_invariants=10,
            both_passed=5,
            both_failed=2,
            new_violations=2,
            fixed_violations=1,
            regression_detected=True,
        )
        assert summary1 == summary2

    def test_summaries_with_different_values_are_not_equal(self) -> None:
        """Summaries with different values should not be equal."""
        summary1 = ModelInvariantComparisonSummary(
            total_invariants=10,
            both_passed=5,
            both_failed=2,
            new_violations=2,
            fixed_violations=1,
            regression_detected=True,
        )
        summary2 = ModelInvariantComparisonSummary(
            total_invariants=10,
            both_passed=6,  # Different value
            both_failed=2,
            new_violations=1,  # Different value
            fixed_violations=1,
            regression_detected=True,
        )
        assert summary1 != summary2


@pytest.mark.unit
class TestModelInvariantComparisonSummaryWithFixture:
    """Test using fixtures from conftest.py."""

    def test_create_from_fixture_data(
        self, sample_invariant_comparison_summary: dict[str, Any]
    ) -> None:
        """Summary can be created from fixture data."""
        summary = ModelInvariantComparisonSummary(**sample_invariant_comparison_summary)
        assert summary.total_invariants == 5
        assert summary.both_passed == 3
        assert summary.both_failed == 0
        assert summary.new_violations == 1
        assert summary.fixed_violations == 1
        assert summary.regression_detected is True
