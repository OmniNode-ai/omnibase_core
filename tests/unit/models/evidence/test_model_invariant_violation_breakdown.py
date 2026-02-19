# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for ModelInvariantViolationBreakdown.

Tests the breakdown model for invariant violations by type and severity
for corpus replay aggregation (OMN-1195).
"""

import pytest
from pydantic import ValidationError

from omnibase_core.enums import EnumSeverity
from omnibase_core.models.evidence.model_invariant_violation_breakdown import (
    ModelInvariantViolationBreakdown,
)


@pytest.mark.unit
class TestBreakdownCreation:
    """Test model instantiation."""

    def test_create_with_all_fields(self) -> None:
        """Create model with all required fields."""
        breakdown = ModelInvariantViolationBreakdown(
            total_violations=5,
            by_type={"output_equivalence": 3, "latency": 2},
            by_severity={
                EnumSeverity.CRITICAL.value: 2,
                EnumSeverity.WARNING.value: 3,
            },
            new_violations=2,
            new_critical_violations=1,
            fixed_violations=1,
        )

        assert breakdown.total_violations == 5
        assert breakdown.by_type == {"output_equivalence": 3, "latency": 2}
        assert breakdown.by_severity == {"critical": 2, "warning": 3}
        assert breakdown.new_violations == 2
        assert breakdown.new_critical_violations == 1
        assert breakdown.fixed_violations == 1

    def test_immutable_after_creation(self) -> None:
        """Model should be frozen (immutable)."""
        breakdown = ModelInvariantViolationBreakdown(
            total_violations=3,
            by_type={"test": 3},
            by_severity={EnumSeverity.WARNING.value: 3},
            new_violations=1,
            new_critical_violations=0,
            fixed_violations=0,
        )

        with pytest.raises(ValidationError):
            breakdown.total_violations = 10

    def test_by_severity_uses_enum_values(self) -> None:
        """by_severity dict uses EnumSeverity values."""
        breakdown = ModelInvariantViolationBreakdown(
            total_violations=6,
            by_type={"cost": 6},
            by_severity={
                EnumSeverity.CRITICAL.value: 2,
                EnumSeverity.WARNING.value: 3,
                EnumSeverity.INFO.value: 1,
            },
            new_violations=3,
            new_critical_violations=1,
            fixed_violations=1,
        )

        # Verify the keys match enum values
        assert "critical" in breakdown.by_severity
        assert "warning" in breakdown.by_severity
        assert "info" in breakdown.by_severity
        assert breakdown.by_severity["critical"] == 2
        assert breakdown.by_severity["warning"] == 3
        assert breakdown.by_severity["info"] == 1


@pytest.mark.unit
class TestViolationCounting:
    """Test violation counting logic."""

    def test_total_violations_matches_sum(self) -> None:
        """total_violations equals sum of by_type values."""
        by_type = {"output_equivalence": 3, "latency": 2, "cost": 1}
        total = sum(by_type.values())

        breakdown = ModelInvariantViolationBreakdown(
            total_violations=total,
            by_type=by_type,
            by_severity={EnumSeverity.WARNING.value: total},
            new_violations=2,
            new_critical_violations=0,
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
            by_severity={EnumSeverity.CRITICAL.value: 4},
            new_violations=3,  # 3 new regressions
            new_critical_violations=2,  # 2 of them are critical
            fixed_violations=1,
        )

        assert breakdown.new_violations == 3
        assert breakdown.new_critical_violations == 2
        # New violations represent things that broke since baseline

    def test_fixed_violations_count(self) -> None:
        """fixed_violations: passed in replay but failed in baseline."""
        # This tests the semantic meaning - fixed violations are improvements
        breakdown = ModelInvariantViolationBreakdown(
            total_violations=2,
            by_type={"type_b": 2},
            by_severity={EnumSeverity.WARNING.value: 2},
            new_violations=0,
            new_critical_violations=0,
            fixed_violations=5,  # 5 things got fixed
        )

        assert breakdown.fixed_violations == 5
        # Fixed violations represent improvements


@pytest.mark.unit
class TestFromViolationDeltas:
    """Test factory method from violation delta records."""

    def test_from_deltas_groups_by_type(self) -> None:
        """Correctly groups violations by type."""
        deltas = [
            {
                "type": "output_equivalence",
                "severity": EnumSeverity.CRITICAL.value,
                "baseline_passed": True,
                "replay_passed": False,
            },
            {
                "type": "output_equivalence",
                "severity": EnumSeverity.CRITICAL.value,
                "baseline_passed": False,
                "replay_passed": False,
            },
            {
                "type": "latency",
                "severity": EnumSeverity.WARNING.value,
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
                "severity": EnumSeverity.CRITICAL.value,
                "baseline_passed": False,
                "replay_passed": False,
            },
            {
                "type": "type_b",
                "severity": EnumSeverity.WARNING.value,
                "baseline_passed": False,
                "replay_passed": False,
            },
            {
                "type": "type_c",
                "severity": EnumSeverity.WARNING.value,
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
                "severity": EnumSeverity.CRITICAL.value,
                "baseline_passed": True,
                "replay_passed": False,
            },
            # New violation: passed in baseline, failed in replay
            {
                "type": "latency",
                "severity": EnumSeverity.WARNING.value,
                "baseline_passed": True,
                "replay_passed": False,
            },
            # Not new: failed in both
            {
                "type": "cost",
                "severity": EnumSeverity.INFO.value,
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
                "severity": EnumSeverity.CRITICAL.value,
                "baseline_passed": False,
                "replay_passed": True,
            },
            # Fixed violation: failed in baseline, passed in replay
            {
                "type": "latency",
                "severity": EnumSeverity.WARNING.value,
                "baseline_passed": False,
                "replay_passed": True,
            },
            # Not fixed: failed in both
            {
                "type": "cost",
                "severity": EnumSeverity.INFO.value,
                "baseline_passed": False,
                "replay_passed": False,
            },
            # Not fixed: passed in both
            {
                "type": "schema",
                "severity": EnumSeverity.INFO.value,
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
                "severity": EnumSeverity.CRITICAL.value,
                "baseline_passed": True,
                "replay_passed": True,
            },
            {
                "type": "latency",
                "severity": EnumSeverity.WARNING.value,
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


@pytest.mark.unit
class TestTotalViolationsConsistency:
    """Test that total_violations is always consistent."""

    def test_total_equals_sum_by_type(self) -> None:
        """total_violations == sum(by_type.values())."""
        by_type = {"a": 5, "b": 3, "c": 2}
        expected_total = 10

        breakdown = ModelInvariantViolationBreakdown(
            total_violations=expected_total,
            by_type=by_type,
            by_severity={EnumSeverity.WARNING.value: 10},
            new_violations=4,
            new_critical_violations=0,
            fixed_violations=2,
        )

        assert sum(breakdown.by_type.values()) == breakdown.total_violations
        assert breakdown.total_violations == 10

    def test_total_equals_sum_by_severity(self) -> None:
        """total_violations == sum(by_severity.values())."""
        by_severity = {
            EnumSeverity.CRITICAL.value: 3,
            EnumSeverity.WARNING.value: 5,
            EnumSeverity.INFO.value: 2,
        }
        expected_total = 10

        breakdown = ModelInvariantViolationBreakdown(
            total_violations=expected_total,
            by_type={"all": 10},
            by_severity=by_severity,
            new_violations=2,
            new_critical_violations=1,
            fixed_violations=1,
        )

        assert sum(breakdown.by_severity.values()) == breakdown.total_violations
        assert breakdown.total_violations == 10

    def test_from_deltas_consistency(self) -> None:
        """Factory method produces consistent totals."""
        deltas = [
            {
                "type": "a",
                "severity": EnumSeverity.CRITICAL.value,
                "baseline_passed": False,
                "replay_passed": False,
            },
            {
                "type": "a",
                "severity": EnumSeverity.WARNING.value,
                "baseline_passed": False,
                "replay_passed": False,
            },
            {
                "type": "b",
                "severity": EnumSeverity.WARNING.value,
                "baseline_passed": True,
                "replay_passed": False,
            },
            {
                "type": "c",
                "severity": EnumSeverity.INFO.value,
                "baseline_passed": True,
                "replay_passed": False,
            },
        ]

        breakdown = ModelInvariantViolationBreakdown.from_violation_deltas(deltas)

        # Verify all totals are consistent
        assert breakdown.total_violations == sum(breakdown.by_type.values())
        assert breakdown.total_violations == sum(breakdown.by_severity.values())
        assert breakdown.total_violations == 4


@pytest.mark.unit
class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_single_violation(self) -> None:
        """Handle single violation correctly."""
        breakdown = ModelInvariantViolationBreakdown(
            total_violations=1,
            by_type={"single": 1},
            by_severity={EnumSeverity.CRITICAL.value: 1},
            new_violations=1,
            new_critical_violations=1,
            fixed_violations=0,
        )

        assert breakdown.total_violations == 1
        assert breakdown.by_type == {"single": 1}
        assert breakdown.new_violations == 1
        assert breakdown.new_critical_violations == 1

    def test_only_fixed_no_new(self) -> None:
        """Scenario with only fixed violations (improvement)."""
        deltas = [
            {
                "type": "fixed_type",
                "severity": EnumSeverity.CRITICAL.value,
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
                "severity": EnumSeverity.WARNING.value,
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
            new_critical_violations=0,
            fixed_violations=0,
        )

        assert breakdown.total_violations == 0
        assert len(breakdown.by_type) == 0
        assert len(breakdown.by_severity) == 0
        assert breakdown.new_critical_violations == 0

    def test_negative_count_rejected(self) -> None:
        """Negative counts should be rejected."""
        with pytest.raises(ValidationError):
            ModelInvariantViolationBreakdown(
                total_violations=-1,
                by_type={},
                by_severity={},
                new_violations=0,
                new_critical_violations=0,
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
                new_critical_violations=0,
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
                new_critical_violations=0,
                fixed_violations=-1,
            )


@pytest.mark.unit
class TestSerialization:
    """Test model serialization/deserialization."""

    def test_model_dump(self) -> None:
        """Model can be dumped to dict."""
        breakdown = ModelInvariantViolationBreakdown(
            total_violations=5,
            by_type={"a": 3, "b": 2},
            by_severity={"critical": 2, "warning": 3},
            new_violations=2,
            new_critical_violations=1,
            fixed_violations=1,
        )

        data = breakdown.model_dump()

        assert data["total_violations"] == 5
        assert data["by_type"] == {"a": 3, "b": 2}
        assert data["new_violations"] == 2
        assert data["new_critical_violations"] == 1

    def test_model_from_dict(self) -> None:
        """Model can be created from dict."""
        data = {
            "total_violations": 3,
            "by_type": {"x": 3},
            "by_severity": {"warning": 3},
            "new_violations": 1,
            "new_critical_violations": 0,
            "fixed_violations": 0,
        }

        breakdown = ModelInvariantViolationBreakdown.model_validate(data)

        assert breakdown.total_violations == 3
        assert breakdown.by_type == {"x": 3}
        assert breakdown.new_critical_violations == 0


@pytest.mark.unit
class TestNewCriticalViolations:
    """Test new_critical_violations tracking."""

    def test_new_critical_violations_counted_correctly(self) -> None:
        """Count only new violations with critical severity."""
        deltas = [
            # New critical violation (should count)
            {
                "type": "output_equivalence",
                "severity": EnumSeverity.CRITICAL.value,
                "baseline_passed": True,
                "replay_passed": False,
            },
            # New warning violation (should NOT count)
            {
                "type": "latency",
                "severity": EnumSeverity.WARNING.value,
                "baseline_passed": True,
                "replay_passed": False,
            },
            # Existing critical (not new, should NOT count)
            {
                "type": "cost",
                "severity": EnumSeverity.CRITICAL.value,
                "baseline_passed": False,
                "replay_passed": False,
            },
        ]

        breakdown = ModelInvariantViolationBreakdown.from_violation_deltas(deltas)

        assert breakdown.new_critical_violations == 1  # Only the first one
        assert breakdown.new_violations == 2  # First two are new
        assert breakdown.by_severity["critical"] == 2  # Both critical violations

    def test_no_new_critical_when_all_existing(self) -> None:
        """Zero new_critical when all critical violations existed before."""
        deltas = [
            {
                "type": "output",
                "severity": EnumSeverity.CRITICAL.value,
                "baseline_passed": False,  # Already existed
                "replay_passed": False,
            },
        ]

        breakdown = ModelInvariantViolationBreakdown.from_violation_deltas(deltas)

        assert breakdown.new_critical_violations == 0
        assert breakdown.by_severity["critical"] == 1

    def test_empty_deltas_zero_new_critical(self) -> None:
        """Empty deltas yields zero new_critical_violations."""
        breakdown = ModelInvariantViolationBreakdown.from_violation_deltas([])

        assert breakdown.new_critical_violations == 0

    def test_new_critical_violations_in_current_not_baseline(self) -> None:
        """Verify new critical violations are correctly identified.

        A "new critical violation" is one that:
        - Failed in replay (current) - replay_passed=False
        - Passed in baseline - baseline_passed=True
        - Has critical severity

        This test verifies the fix for correctly identifying violations
        that are in current but not in baseline.
        """
        deltas = [
            # New critical #1: was passing, now failing with critical severity
            {
                "type": "output_equivalence",
                "severity": EnumSeverity.CRITICAL.value,
                "baseline_passed": True,  # Was passing in baseline
                "replay_passed": False,  # Now failing in current
            },
            # New critical #2: another new critical violation
            {
                "type": "schema_validation",
                "severity": EnumSeverity.CRITICAL.value,
                "baseline_passed": True,  # Was passing in baseline
                "replay_passed": False,  # Now failing in current
            },
            # NOT new critical: existed in baseline (was already failing)
            {
                "type": "data_integrity",
                "severity": EnumSeverity.CRITICAL.value,
                "baseline_passed": False,  # Was already failing in baseline
                "replay_passed": False,  # Still failing in current
            },
            # NOT new critical: passing in both (not a violation at all)
            {
                "type": "performance",
                "severity": EnumSeverity.CRITICAL.value,
                "baseline_passed": True,  # Passing in baseline
                "replay_passed": True,  # Still passing in current
            },
            # NOT new critical: fixed (was failing, now passing)
            {
                "type": "security",
                "severity": EnumSeverity.CRITICAL.value,
                "baseline_passed": False,  # Was failing in baseline
                "replay_passed": True,  # Now passing in current (fixed!)
            },
        ]

        breakdown = ModelInvariantViolationBreakdown.from_violation_deltas(deltas)

        # Verify new_critical_violations: only counts violations that are
        # (1) in current (replay_passed=False), (2) not in baseline (baseline_passed=True),
        # and (3) critical severity
        assert breakdown.new_critical_violations == 2  # Only first two

        # Verify total critical violations (all that failed in replay)
        assert breakdown.by_severity[EnumSeverity.CRITICAL.value] == 3

        # Verify new violations (any severity that passed in baseline, failed in replay)
        assert breakdown.new_violations == 2

        # Verify fixed violations (failed in baseline, passed in replay)
        assert breakdown.fixed_violations == 1

        # Verify total violations (all that failed in replay)
        assert breakdown.total_violations == 3
