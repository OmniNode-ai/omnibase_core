# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""Unit tests for ModelInvariantViolationBreakdown.

Tests the breakdown model for invariant violations by type and severity
for corpus replay aggregation (OMN-1195).
"""

import pytest
from pydantic import ValidationError

from omnibase_core.enums import EnumViolationSeverity
from omnibase_core.models.evidence.model_invariant_violation_breakdown import (
    ModelInvariantViolationBreakdown,
)


class TestBreakdownCreation:
    """Test model instantiation."""

    def test_create_with_all_fields(self) -> None:
        """Create model with all required fields."""
        breakdown = ModelInvariantViolationBreakdown(
            total_violations=5,
            by_type={"output_equivalence": 3, "latency": 2},
            by_severity={
                EnumViolationSeverity.CRITICAL.value: 2,
                EnumViolationSeverity.WARNING.value: 3,
            },
            new_violations=2,
            fixed_violations=1,
        )

        assert breakdown.total_violations == 5
        assert breakdown.by_type == {"output_equivalence": 3, "latency": 2}
        assert breakdown.by_severity == {"critical": 2, "warning": 3}
        assert breakdown.new_violations == 2
        assert breakdown.fixed_violations == 1

    def test_immutable_after_creation(self) -> None:
        """Model should be frozen (immutable)."""
        breakdown = ModelInvariantViolationBreakdown(
            total_violations=3,
            by_type={"test": 3},
            by_severity={EnumViolationSeverity.WARNING.value: 3},
            new_violations=1,
            fixed_violations=0,
        )

        with pytest.raises(ValidationError):
            breakdown.total_violations = 10

    def test_by_severity_uses_enum_values(self) -> None:
        """by_severity dict uses EnumViolationSeverity values."""
        breakdown = ModelInvariantViolationBreakdown(
            total_violations=6,
            by_type={"cost": 6},
            by_severity={
                EnumViolationSeverity.CRITICAL.value: 2,
                EnumViolationSeverity.WARNING.value: 3,
                EnumViolationSeverity.INFO.value: 1,
            },
            new_violations=3,
            fixed_violations=1,
        )

        # Verify the keys match enum values
        assert "critical" in breakdown.by_severity
        assert "warning" in breakdown.by_severity
        assert "info" in breakdown.by_severity
        assert breakdown.by_severity["critical"] == 2
        assert breakdown.by_severity["warning"] == 3
        assert breakdown.by_severity["info"] == 1


class TestViolationCounting:
    """Test violation counting logic."""

    def test_total_violations_matches_sum(self) -> None:
        """total_violations equals sum of by_type values."""
        by_type = {"output_equivalence": 3, "latency": 2, "cost": 1}
        total = sum(by_type.values())

        breakdown = ModelInvariantViolationBreakdown(
            total_violations=total,
            by_type=by_type,
            by_severity={EnumViolationSeverity.WARNING.value: total},
            new_violations=2,
            fixed_violations=1,
        )

        assert breakdown.total_violations == 6
        assert sum(breakdown.by_type.values()) == breakdown.total_violations

    def test_new_violations_count(self) -> None:
        """new_violations: failed in replay but passed in baseline."""
        # This tests the semantic meaning - new violations are regressions
        breakdown = ModelInvariantViolationBreakdown(
            total_violations=4,
            by_type={"type_a": 4},
            by_severity={EnumViolationSeverity.CRITICAL.value: 4},
            new_violations=3,  # 3 new regressions
            fixed_violations=1,
        )

        assert breakdown.new_violations == 3
        # New violations represent things that broke since baseline

    def test_fixed_violations_count(self) -> None:
        """fixed_violations: passed in replay but failed in baseline."""
        # This tests the semantic meaning - fixed violations are improvements
        breakdown = ModelInvariantViolationBreakdown(
            total_violations=2,
            by_type={"type_b": 2},
            by_severity={EnumViolationSeverity.WARNING.value: 2},
            new_violations=0,
            fixed_violations=5,  # 5 things got fixed
        )

        assert breakdown.fixed_violations == 5
        # Fixed violations represent improvements


class TestFromViolationDeltas:
    """Test factory method from violation delta records."""

    def test_from_deltas_groups_by_type(self) -> None:
        """Correctly groups violations by type."""
        deltas = [
            {
                "type": "output_equivalence",
                "severity": EnumViolationSeverity.CRITICAL.value,
                "baseline_passed": True,
                "replay_passed": False,
            },
            {
                "type": "output_equivalence",
                "severity": EnumViolationSeverity.CRITICAL.value,
                "baseline_passed": False,
                "replay_passed": False,
            },
            {
                "type": "latency",
                "severity": EnumViolationSeverity.WARNING.value,
                "baseline_passed": True,
                "replay_passed": False,
            },
        ]

        breakdown = ModelInvariantViolationBreakdown.from_violation_deltas(deltas)

        assert breakdown.by_type == {"output_equivalence": 2, "latency": 1}
        assert breakdown.total_violations == 3

    def test_from_deltas_groups_by_severity(self) -> None:
        """Correctly groups violations by severity."""
        deltas = [
            {
                "type": "type_a",
                "severity": EnumViolationSeverity.CRITICAL.value,
                "baseline_passed": False,
                "replay_passed": False,
            },
            {
                "type": "type_b",
                "severity": EnumViolationSeverity.WARNING.value,
                "baseline_passed": False,
                "replay_passed": False,
            },
            {
                "type": "type_c",
                "severity": EnumViolationSeverity.WARNING.value,
                "baseline_passed": False,
                "replay_passed": False,
            },
        ]

        breakdown = ModelInvariantViolationBreakdown.from_violation_deltas(deltas)

        assert breakdown.by_severity == {"critical": 1, "warning": 2}

    def test_from_deltas_counts_new_violations(self) -> None:
        """Counts violations where baseline_passed=True, replay_passed=False."""
        deltas = [
            # New violation: passed in baseline, failed in replay
            {
                "type": "output",
                "severity": EnumViolationSeverity.CRITICAL.value,
                "baseline_passed": True,
                "replay_passed": False,
            },
            # New violation: passed in baseline, failed in replay
            {
                "type": "latency",
                "severity": EnumViolationSeverity.WARNING.value,
                "baseline_passed": True,
                "replay_passed": False,
            },
            # Not new: failed in both
            {
                "type": "cost",
                "severity": EnumViolationSeverity.INFO.value,
                "baseline_passed": False,
                "replay_passed": False,
            },
        ]

        breakdown = ModelInvariantViolationBreakdown.from_violation_deltas(deltas)

        assert breakdown.new_violations == 2

    def test_from_deltas_counts_fixed_violations(self) -> None:
        """Counts violations where baseline_passed=False, replay_passed=True."""
        deltas = [
            # Fixed violation: failed in baseline, passed in replay
            {
                "type": "output",
                "severity": EnumViolationSeverity.CRITICAL.value,
                "baseline_passed": False,
                "replay_passed": True,
            },
            # Fixed violation: failed in baseline, passed in replay
            {
                "type": "latency",
                "severity": EnumViolationSeverity.WARNING.value,
                "baseline_passed": False,
                "replay_passed": True,
            },
            # Not fixed: failed in both
            {
                "type": "cost",
                "severity": EnumViolationSeverity.INFO.value,
                "baseline_passed": False,
                "replay_passed": False,
            },
            # Not fixed: passed in both
            {
                "type": "schema",
                "severity": EnumViolationSeverity.INFO.value,
                "baseline_passed": True,
                "replay_passed": True,
            },
        ]

        breakdown = ModelInvariantViolationBreakdown.from_violation_deltas(deltas)

        assert breakdown.fixed_violations == 2

    def test_from_deltas_empty_list(self) -> None:
        """Empty delta list returns zeroed breakdown."""
        breakdown = ModelInvariantViolationBreakdown.from_violation_deltas([])

        assert breakdown.total_violations == 0
        assert breakdown.by_type == {}
        assert breakdown.by_severity == {}
        assert breakdown.new_violations == 0
        assert breakdown.fixed_violations == 0

    def test_from_deltas_all_passed(self) -> None:
        """No violations when all passed."""
        deltas = [
            {
                "type": "output",
                "severity": EnumViolationSeverity.CRITICAL.value,
                "baseline_passed": True,
                "replay_passed": True,
            },
            {
                "type": "latency",
                "severity": EnumViolationSeverity.WARNING.value,
                "baseline_passed": True,
                "replay_passed": True,
            },
        ]

        breakdown = ModelInvariantViolationBreakdown.from_violation_deltas(deltas)

        # All passed means no violations to count
        assert breakdown.total_violations == 0
        assert breakdown.by_type == {}
        assert breakdown.by_severity == {}
        assert breakdown.new_violations == 0
        assert breakdown.fixed_violations == 0


class TestTotalViolationsConsistency:
    """Test that total_violations is always consistent."""

    def test_total_equals_sum_by_type(self) -> None:
        """total_violations == sum(by_type.values())."""
        by_type = {"a": 5, "b": 3, "c": 2}
        expected_total = 10

        breakdown = ModelInvariantViolationBreakdown(
            total_violations=expected_total,
            by_type=by_type,
            by_severity={EnumViolationSeverity.WARNING.value: 10},
            new_violations=4,
            fixed_violations=2,
        )

        assert sum(breakdown.by_type.values()) == breakdown.total_violations
        assert breakdown.total_violations == 10

    def test_total_equals_sum_by_severity(self) -> None:
        """total_violations == sum(by_severity.values())."""
        by_severity = {
            EnumViolationSeverity.CRITICAL.value: 3,
            EnumViolationSeverity.WARNING.value: 5,
            EnumViolationSeverity.INFO.value: 2,
        }
        expected_total = 10

        breakdown = ModelInvariantViolationBreakdown(
            total_violations=expected_total,
            by_type={"all": 10},
            by_severity=by_severity,
            new_violations=2,
            fixed_violations=1,
        )

        assert sum(breakdown.by_severity.values()) == breakdown.total_violations
        assert breakdown.total_violations == 10

    def test_from_deltas_consistency(self) -> None:
        """Factory method produces consistent totals."""
        deltas = [
            {
                "type": "a",
                "severity": EnumViolationSeverity.CRITICAL.value,
                "baseline_passed": False,
                "replay_passed": False,
            },
            {
                "type": "a",
                "severity": EnumViolationSeverity.WARNING.value,
                "baseline_passed": False,
                "replay_passed": False,
            },
            {
                "type": "b",
                "severity": EnumViolationSeverity.WARNING.value,
                "baseline_passed": True,
                "replay_passed": False,
            },
            {
                "type": "c",
                "severity": EnumViolationSeverity.INFO.value,
                "baseline_passed": True,
                "replay_passed": False,
            },
        ]

        breakdown = ModelInvariantViolationBreakdown.from_violation_deltas(deltas)

        # Verify all totals are consistent
        assert breakdown.total_violations == sum(breakdown.by_type.values())
        assert breakdown.total_violations == sum(breakdown.by_severity.values())
        assert breakdown.total_violations == 4


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_single_violation(self) -> None:
        """Handle single violation correctly."""
        breakdown = ModelInvariantViolationBreakdown(
            total_violations=1,
            by_type={"single": 1},
            by_severity={EnumViolationSeverity.CRITICAL.value: 1},
            new_violations=1,
            fixed_violations=0,
        )

        assert breakdown.total_violations == 1
        assert breakdown.by_type == {"single": 1}
        assert breakdown.new_violations == 1

    def test_only_fixed_no_new(self) -> None:
        """Scenario with only fixed violations (improvement)."""
        deltas = [
            {
                "type": "fixed_type",
                "severity": EnumViolationSeverity.CRITICAL.value,
                "baseline_passed": False,
                "replay_passed": True,  # Fixed!
            },
        ]

        breakdown = ModelInvariantViolationBreakdown.from_violation_deltas(deltas)

        assert breakdown.new_violations == 0
        assert breakdown.fixed_violations == 1
        # Fixed violations don't count as current violations
        assert breakdown.total_violations == 0

    def test_only_new_no_fixed(self) -> None:
        """Scenario with only new violations (regression)."""
        deltas = [
            {
                "type": "new_type",
                "severity": EnumViolationSeverity.WARNING.value,
                "baseline_passed": True,
                "replay_passed": False,  # Regression!
            },
        ]

        breakdown = ModelInvariantViolationBreakdown.from_violation_deltas(deltas)

        assert breakdown.new_violations == 1
        assert breakdown.fixed_violations == 0
        assert breakdown.total_violations == 1

    def test_zero_counts_valid(self) -> None:
        """Zero counts are valid."""
        breakdown = ModelInvariantViolationBreakdown(
            total_violations=0,
            by_type={},
            by_severity={},
            new_violations=0,
            fixed_violations=0,
        )

        assert breakdown.total_violations == 0
        assert len(breakdown.by_type) == 0
        assert len(breakdown.by_severity) == 0

    def test_negative_count_rejected(self) -> None:
        """Negative counts should be rejected."""
        with pytest.raises(ValidationError):
            ModelInvariantViolationBreakdown(
                total_violations=-1,
                by_type={},
                by_severity={},
                new_violations=0,
                fixed_violations=0,
            )

    def test_negative_new_violations_rejected(self) -> None:
        """Negative new_violations should be rejected."""
        with pytest.raises(ValidationError):
            ModelInvariantViolationBreakdown(
                total_violations=0,
                by_type={},
                by_severity={},
                new_violations=-1,
                fixed_violations=0,
            )

    def test_negative_fixed_violations_rejected(self) -> None:
        """Negative fixed_violations should be rejected."""
        with pytest.raises(ValidationError):
            ModelInvariantViolationBreakdown(
                total_violations=0,
                by_type={},
                by_severity={},
                new_violations=0,
                fixed_violations=-1,
            )


class TestSerialization:
    """Test model serialization/deserialization."""

    def test_model_dump(self) -> None:
        """Model can be dumped to dict."""
        breakdown = ModelInvariantViolationBreakdown(
            total_violations=5,
            by_type={"a": 3, "b": 2},
            by_severity={"critical": 2, "warning": 3},
            new_violations=2,
            fixed_violations=1,
        )

        data = breakdown.model_dump()

        assert data["total_violations"] == 5
        assert data["by_type"] == {"a": 3, "b": 2}
        assert data["new_violations"] == 2

    def test_model_from_dict(self) -> None:
        """Model can be created from dict."""
        data = {
            "total_violations": 3,
            "by_type": {"x": 3},
            "by_severity": {"warning": 3},
            "new_violations": 1,
            "fixed_violations": 0,
        }

        breakdown = ModelInvariantViolationBreakdown.model_validate(data)

        assert breakdown.total_violations == 3
        assert breakdown.by_type == {"x": 3}
