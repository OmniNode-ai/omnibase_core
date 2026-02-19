# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for batch invariant evaluation.

This module tests the batch evaluation methods of ServiceInvariantEvaluator:
- evaluate_batch(): Evaluates all invariants in a set
- evaluate_all(): Evaluates with summary statistics and optional fail_fast

Test Coverage:
- All invariants in set are evaluated
- Results returned for each invariant even on failures
- fail_fast stops on first critical failure
- Default continues evaluating after failure
- Results preserve invariant order
- Summary statistics are correctly computed
"""

import pytest

from omnibase_core.enums import EnumInvariantType, EnumSeverity
from omnibase_core.models.invariant import ModelInvariant, ModelInvariantSet
from omnibase_core.services.invariant.service_invariant_evaluator import (
    ServiceInvariantEvaluator,
)


@pytest.mark.unit
class TestBatchEvaluation:
    """Test suite for batch evaluation methods."""

    @pytest.fixture
    def sample_invariant_set(self) -> ModelInvariantSet:
        """Create a sample invariant set for testing."""
        return ModelInvariantSet(
            name="Test Set",
            target="test_node",
            invariants=[
                ModelInvariant(
                    name="Field Check",
                    type=EnumInvariantType.FIELD_PRESENCE,
                    severity=EnumSeverity.CRITICAL,
                    config={"fields": ["status"]},
                ),
                ModelInvariant(
                    name="Value Check",
                    type=EnumInvariantType.FIELD_VALUE,
                    severity=EnumSeverity.WARNING,
                    config={"field_path": "status", "expected_value": "ok"},
                ),
                ModelInvariant(
                    name="Threshold Check",
                    type=EnumInvariantType.THRESHOLD,
                    severity=EnumSeverity.CRITICAL,
                    config={"metric_name": "score", "min_value": 0.5},
                ),
            ],
        )

    def test_evaluate_batch_runs_all(
        self,
        evaluator: ServiceInvariantEvaluator,
        sample_invariant_set: ModelInvariantSet,
    ) -> None:
        """All invariants in set are evaluated."""
        output = {"status": "ok", "score": 0.8}

        results = evaluator.evaluate_batch(sample_invariant_set, output)

        assert len(results) == 3
        assert all(r.passed for r in results)

    def test_evaluate_batch_returns_all_results(
        self,
        evaluator: ServiceInvariantEvaluator,
        sample_invariant_set: ModelInvariantSet,
    ) -> None:
        """Results returned for each invariant even on failures."""
        output = {"status": "error", "score": 0.3}  # Will fail value and threshold

        results = evaluator.evaluate_batch(sample_invariant_set, output)

        assert len(results) == 3
        passed = [r for r in results if r.passed]
        failed = [r for r in results if not r.passed]
        assert len(passed) == 1  # Field presence passes
        assert len(failed) == 2  # Value and threshold fail

    def test_evaluate_batch_fail_fast_stops_on_first_critical(
        self, evaluator: ServiceInvariantEvaluator
    ) -> None:
        """fail_fast=True stops on first critical failure."""
        invariant_set = ModelInvariantSet(
            name="Fail Fast Test",
            target="test",
            invariants=[
                ModelInvariant(
                    name="First Critical",
                    type=EnumInvariantType.FIELD_PRESENCE,
                    severity=EnumSeverity.CRITICAL,
                    config={"fields": ["missing_field"]},  # Will fail
                ),
                ModelInvariant(
                    name="Second",
                    type=EnumInvariantType.FIELD_PRESENCE,
                    severity=EnumSeverity.WARNING,
                    config={"fields": ["other"]},
                ),
            ],
        )

        summary = evaluator.evaluate_all(invariant_set, {}, fail_fast=True)

        # Should stop after first critical failure
        assert summary.overall_passed is False
        assert summary.critical_failures >= 1
        # May have fewer results than invariants due to fail_fast
        assert len(summary.results) <= 2

    def test_evaluate_batch_fail_fast_stops_on_fatal(
        self, evaluator: ServiceInvariantEvaluator
    ) -> None:
        """fail_fast=True stops on first FATAL failure (same as CRITICAL)."""
        invariant_set = ModelInvariantSet(
            name="Fail Fast Fatal Test",
            target="test",
            invariants=[
                ModelInvariant(
                    name="First Fatal",
                    type=EnumInvariantType.FIELD_PRESENCE,
                    severity=EnumSeverity.FATAL,
                    config={"fields": ["missing_field"]},  # Will fail
                ),
                ModelInvariant(
                    name="Second",
                    type=EnumInvariantType.FIELD_PRESENCE,
                    severity=EnumSeverity.WARNING,
                    config={"fields": ["other"]},
                ),
            ],
        )

        summary = evaluator.evaluate_all(invariant_set, {}, fail_fast=True)

        # Should stop after first FATAL failure
        assert summary.overall_passed is False
        assert summary.fatal_failures >= 1
        # Should have only 1 result due to fail_fast stopping on FATAL
        assert len(summary.results) == 1
        assert summary.results[0].severity == EnumSeverity.FATAL

    def test_evaluate_batch_continues_on_failure(
        self,
        evaluator: ServiceInvariantEvaluator,
        sample_invariant_set: ModelInvariantSet,
    ) -> None:
        """Default continues evaluating after failure."""
        output = {"status": "error", "score": 0.3}

        results = evaluator.evaluate_batch(sample_invariant_set, output)

        # All invariants evaluated despite failures
        assert len(results) == 3

    def test_evaluate_batch_preserves_order(
        self,
        evaluator: ServiceInvariantEvaluator,
        sample_invariant_set: ModelInvariantSet,
    ) -> None:
        """Results preserve invariant order."""
        output = {"status": "ok", "score": 0.8}

        results = evaluator.evaluate_batch(sample_invariant_set, output)

        assert results[0].invariant_name == "Field Check"
        assert results[1].invariant_name == "Value Check"
        assert results[2].invariant_name == "Threshold Check"

    def test_evaluate_all_returns_summary(
        self,
        evaluator: ServiceInvariantEvaluator,
        sample_invariant_set: ModelInvariantSet,
    ) -> None:
        """evaluate_all returns proper summary statistics."""
        output = {"status": "ok", "score": 0.8}

        summary = evaluator.evaluate_all(sample_invariant_set, output)

        assert summary.passed_count == 3
        assert summary.failed_count == 0
        assert summary.fatal_failures == 0
        assert summary.critical_failures == 0
        assert summary.overall_passed is True
        assert summary.total_duration_ms >= 0
        assert len(summary.results) == 3

    def test_evaluate_all_counts_failure_severities(
        self, evaluator: ServiceInvariantEvaluator
    ) -> None:
        """evaluate_all correctly counts failures by severity."""
        invariant_set = ModelInvariantSet(
            name="Severity Test",
            target="test",
            invariants=[
                ModelInvariant(
                    name="Critical Fail",
                    type=EnumInvariantType.FIELD_PRESENCE,
                    severity=EnumSeverity.CRITICAL,
                    config={"fields": ["missing_critical"]},
                ),
                ModelInvariant(
                    name="Warning Fail",
                    type=EnumInvariantType.FIELD_PRESENCE,
                    severity=EnumSeverity.WARNING,
                    config={"fields": ["missing_warning"]},
                ),
                ModelInvariant(
                    name="Info Fail",
                    type=EnumInvariantType.FIELD_PRESENCE,
                    severity=EnumSeverity.INFO,
                    config={"fields": ["missing_info"]},
                ),
            ],
        )

        summary = evaluator.evaluate_all(invariant_set, {})

        assert summary.critical_failures == 1
        assert summary.warning_failures == 1
        assert summary.info_failures == 1
        assert summary.failed_count == 3
        assert summary.passed_count == 0
        # overall_passed is False because of critical failures
        assert summary.overall_passed is False

    def test_evaluate_all_counts_all_severity_levels(
        self, evaluator: ServiceInvariantEvaluator
    ) -> None:
        """evaluate_all correctly counts all severity levels including FATAL, ERROR, DEBUG."""
        invariant_set = ModelInvariantSet(
            name="All Severities Test",
            target="test",
            invariants=[
                ModelInvariant(
                    name="Fatal Fail",
                    type=EnumInvariantType.FIELD_PRESENCE,
                    severity=EnumSeverity.FATAL,
                    config={"fields": ["missing_fatal"]},
                ),
                ModelInvariant(
                    name="Critical Fail",
                    type=EnumInvariantType.FIELD_PRESENCE,
                    severity=EnumSeverity.CRITICAL,
                    config={"fields": ["missing_critical"]},
                ),
                ModelInvariant(
                    name="Error Fail",
                    type=EnumInvariantType.FIELD_PRESENCE,
                    severity=EnumSeverity.ERROR,
                    config={"fields": ["missing_error"]},
                ),
                ModelInvariant(
                    name="Warning Fail",
                    type=EnumInvariantType.FIELD_PRESENCE,
                    severity=EnumSeverity.WARNING,
                    config={"fields": ["missing_warning"]},
                ),
                ModelInvariant(
                    name="Info Fail",
                    type=EnumInvariantType.FIELD_PRESENCE,
                    severity=EnumSeverity.INFO,
                    config={"fields": ["missing_info"]},
                ),
                ModelInvariant(
                    name="Debug Fail",
                    type=EnumInvariantType.FIELD_PRESENCE,
                    severity=EnumSeverity.DEBUG,
                    config={"fields": ["missing_debug"]},
                ),
            ],
        )

        summary = evaluator.evaluate_all(invariant_set, {})

        # FATAL and CRITICAL are counted separately
        assert summary.fatal_failures == 1
        assert summary.critical_failures == 1
        assert summary.error_failures == 1
        assert summary.warning_failures == 1
        # INFO and DEBUG are counted together in info_failures
        assert summary.info_failures == 2  # 1 INFO + 1 DEBUG
        assert summary.failed_count == 6
        assert summary.passed_count == 0
        # overall_passed is False because of critical/fatal failures
        assert summary.overall_passed is False

    def test_evaluate_all_overall_passed_without_critical_or_fatal_failures(
        self, evaluator: ServiceInvariantEvaluator
    ) -> None:
        """overall_passed is True when no critical or fatal failures exist."""
        invariant_set = ModelInvariantSet(
            name="Warning Only",
            target="test",
            invariants=[
                ModelInvariant(
                    name="Warning Fail",
                    type=EnumInvariantType.FIELD_PRESENCE,
                    severity=EnumSeverity.WARNING,
                    config={"fields": ["missing"]},
                ),
                ModelInvariant(
                    name="Pass",
                    type=EnumInvariantType.FIELD_PRESENCE,
                    severity=EnumSeverity.CRITICAL,
                    config={"fields": ["present"]},
                ),
            ],
        )

        summary = evaluator.evaluate_all(invariant_set, {"present": True})

        assert summary.warning_failures == 1
        assert summary.fatal_failures == 0
        assert summary.critical_failures == 0
        # overall_passed is True because no CRITICAL or FATAL failures
        assert summary.overall_passed is True

    def test_evaluate_batch_enabled_only_filter(
        self, evaluator: ServiceInvariantEvaluator
    ) -> None:
        """enabled_only parameter filters disabled invariants."""
        invariant_set = ModelInvariantSet(
            name="Enabled Filter Test",
            target="test",
            invariants=[
                ModelInvariant(
                    name="Enabled",
                    type=EnumInvariantType.FIELD_PRESENCE,
                    severity=EnumSeverity.WARNING,
                    config={"fields": ["field1"]},
                    enabled=True,
                ),
                ModelInvariant(
                    name="Disabled",
                    type=EnumInvariantType.FIELD_PRESENCE,
                    severity=EnumSeverity.WARNING,
                    config={"fields": ["field2"]},
                    enabled=False,
                ),
            ],
        )

        # With enabled_only=True (default)
        results_enabled = evaluator.evaluate_batch(invariant_set, {"field1": True})
        assert len(results_enabled) == 1
        assert results_enabled[0].invariant_name == "Enabled"

        # With enabled_only=False
        results_all = evaluator.evaluate_batch(
            invariant_set, {"field1": True}, enabled_only=False
        )
        assert len(results_all) == 2

    def test_evaluate_all_fail_fast_preserves_results_before_failure(
        self, evaluator: ServiceInvariantEvaluator
    ) -> None:
        """fail_fast preserves all results evaluated before the critical failure."""
        invariant_set = ModelInvariantSet(
            name="Fail Fast Order",
            target="test",
            invariants=[
                ModelInvariant(
                    name="First Pass",
                    type=EnumInvariantType.FIELD_PRESENCE,
                    severity=EnumSeverity.WARNING,
                    config={"fields": ["exists"]},
                ),
                ModelInvariant(
                    name="Second Critical Fail",
                    type=EnumInvariantType.FIELD_PRESENCE,
                    severity=EnumSeverity.CRITICAL,
                    config={"fields": ["missing"]},
                ),
                ModelInvariant(
                    name="Third Never Evaluated",
                    type=EnumInvariantType.FIELD_PRESENCE,
                    severity=EnumSeverity.WARNING,
                    config={"fields": ["exists"]},
                ),
            ],
        )

        summary = evaluator.evaluate_all(
            invariant_set, {"exists": True}, fail_fast=True
        )

        # Should have 2 results (first pass, second fail) but not third
        assert len(summary.results) == 2
        assert summary.results[0].passed is True
        assert summary.results[0].invariant_name == "First Pass"
        assert summary.results[1].passed is False
        assert summary.results[1].invariant_name == "Second Critical Fail"

    def test_evaluate_batch_empty_set(
        self, evaluator: ServiceInvariantEvaluator
    ) -> None:
        """Empty invariant set returns empty results."""
        invariant_set = ModelInvariantSet(
            name="Empty Set",
            target="test",
            invariants=[],
        )

        results = evaluator.evaluate_batch(invariant_set, {"any": "data"})

        assert len(results) == 0

    def test_evaluate_all_empty_set(self, evaluator: ServiceInvariantEvaluator) -> None:
        """Empty invariant set returns passing summary."""
        invariant_set = ModelInvariantSet(
            name="Empty Set",
            target="test",
            invariants=[],
        )

        summary = evaluator.evaluate_all(invariant_set, {"any": "data"})

        assert summary.passed_count == 0
        assert summary.failed_count == 0
        assert summary.fatal_failures == 0
        assert summary.critical_failures == 0
        assert summary.overall_passed is True
        assert len(summary.results) == 0


@pytest.mark.unit
class TestFatalSeverityBehavior:
    """Test suite for FATAL severity-specific behavior.

    FATAL is the highest severity level (priority 0), above CRITICAL.
    These tests verify:
    - FATAL triggers fail-fast behavior
    - FATAL is counted separately from CRITICAL in analytics
    - overall_passed fails when only FATAL fails
    - Severity ordering is respected (FATAL > CRITICAL > ERROR > WARNING > INFO > DEBUG)
    """

    def test_fatal_triggers_fail_fast(
        self, evaluator: ServiceInvariantEvaluator
    ) -> None:
        """FATAL severity triggers immediate stop when fail_fast=True.

        When fail_fast is enabled, a FATAL failure should stop evaluation
        immediately, preventing subsequent invariants from being evaluated.
        """
        invariant_set = ModelInvariantSet(
            name="Fatal Fail Fast",
            target="test",
            invariants=[
                ModelInvariant(
                    name="First Pass",
                    type=EnumInvariantType.FIELD_PRESENCE,
                    severity=EnumSeverity.WARNING,
                    config={"fields": ["exists"]},
                ),
                ModelInvariant(
                    name="Fatal Failure",
                    type=EnumInvariantType.FIELD_PRESENCE,
                    severity=EnumSeverity.FATAL,
                    config={"fields": ["missing_fatal"]},  # Will fail
                ),
                ModelInvariant(
                    name="Should Not Run",
                    type=EnumInvariantType.FIELD_PRESENCE,
                    severity=EnumSeverity.INFO,
                    config={"fields": ["exists"]},
                ),
            ],
        )

        summary = evaluator.evaluate_all(
            invariant_set, {"exists": True}, fail_fast=True
        )

        # Verify fail-fast behavior
        assert summary.overall_passed is False
        assert summary.fatal_failures == 1
        # Should stop after FATAL - third invariant should not run
        assert len(summary.results) == 2
        # Verify the invariants that ran
        assert summary.results[0].invariant_name == "First Pass"
        assert summary.results[0].passed is True
        assert summary.results[1].invariant_name == "Fatal Failure"
        assert summary.results[1].passed is False
        assert summary.results[1].severity == EnumSeverity.FATAL

    def test_fatal_counted_separately_from_critical(
        self, evaluator: ServiceInvariantEvaluator
    ) -> None:
        """FATAL and CRITICAL failures are counted in separate counters.

        The fatal_failures and critical_failures counters should be independent,
        each accurately counting only their respective severity level.
        """
        invariant_set = ModelInvariantSet(
            name="Separate Counters",
            target="test",
            invariants=[
                ModelInvariant(
                    name="Fatal 1",
                    type=EnumInvariantType.FIELD_PRESENCE,
                    severity=EnumSeverity.FATAL,
                    config={"fields": ["missing_1"]},
                ),
                ModelInvariant(
                    name="Fatal 2",
                    type=EnumInvariantType.FIELD_PRESENCE,
                    severity=EnumSeverity.FATAL,
                    config={"fields": ["missing_2"]},
                ),
                ModelInvariant(
                    name="Critical 1",
                    type=EnumInvariantType.FIELD_PRESENCE,
                    severity=EnumSeverity.CRITICAL,
                    config={"fields": ["missing_3"]},
                ),
                ModelInvariant(
                    name="Critical 2",
                    type=EnumInvariantType.FIELD_PRESENCE,
                    severity=EnumSeverity.CRITICAL,
                    config={"fields": ["missing_4"]},
                ),
                ModelInvariant(
                    name="Critical 3",
                    type=EnumInvariantType.FIELD_PRESENCE,
                    severity=EnumSeverity.CRITICAL,
                    config={"fields": ["missing_5"]},
                ),
            ],
        )

        # Evaluate without fail_fast to count all failures
        summary = evaluator.evaluate_all(invariant_set, {}, fail_fast=False)

        # FATAL and CRITICAL should be counted separately
        assert summary.fatal_failures == 2
        assert summary.critical_failures == 3
        # Total failed should be sum
        assert summary.failed_count == 5
        assert summary.passed_count == 0
        # overall_passed fails due to both FATAL and CRITICAL
        assert summary.overall_passed is False

    def test_overall_passed_fails_on_fatal_only(
        self, evaluator: ServiceInvariantEvaluator
    ) -> None:
        """overall_passed is False when only FATAL fails (no CRITICAL failures).

        Even when there are no CRITICAL failures, a FATAL failure alone
        should cause overall_passed to be False.
        """
        invariant_set = ModelInvariantSet(
            name="Fatal Only Failure",
            target="test",
            invariants=[
                ModelInvariant(
                    name="Warning Pass",
                    type=EnumInvariantType.FIELD_PRESENCE,
                    severity=EnumSeverity.WARNING,
                    config={"fields": ["exists"]},
                ),
                ModelInvariant(
                    name="Error Pass",
                    type=EnumInvariantType.FIELD_PRESENCE,
                    severity=EnumSeverity.ERROR,
                    config={"fields": ["exists"]},
                ),
                ModelInvariant(
                    name="Fatal Fails",
                    type=EnumInvariantType.FIELD_PRESENCE,
                    severity=EnumSeverity.FATAL,
                    config={"fields": ["missing_fatal"]},
                ),
            ],
        )

        summary = evaluator.evaluate_all(invariant_set, {"exists": True})

        # No CRITICAL failures, but FATAL failure exists
        assert summary.critical_failures == 0
        assert summary.fatal_failures == 1
        # overall_passed should be False due to FATAL alone
        assert summary.overall_passed is False
        # Verify other stats
        assert summary.passed_count == 2
        assert summary.failed_count == 1

    def test_severity_ordering_in_results(
        self, evaluator: ServiceInvariantEvaluator
    ) -> None:
        """Results preserve evaluation order (invariant order), not severity order.

        The results list should maintain the order in which invariants were
        defined in the set, not reordered by severity. However, the severity
        priority system (FATAL > CRITICAL > ERROR > WARNING > INFO > DEBUG)
        determines fail_fast behavior.
        """
        invariant_set = ModelInvariantSet(
            name="Mixed Severity Order",
            target="test",
            invariants=[
                ModelInvariant(
                    name="Debug First",
                    type=EnumInvariantType.FIELD_PRESENCE,
                    severity=EnumSeverity.DEBUG,
                    config={"fields": ["a"]},
                ),
                ModelInvariant(
                    name="Critical Second",
                    type=EnumInvariantType.FIELD_PRESENCE,
                    severity=EnumSeverity.CRITICAL,
                    config={"fields": ["a"]},
                ),
                ModelInvariant(
                    name="Fatal Third",
                    type=EnumInvariantType.FIELD_PRESENCE,
                    severity=EnumSeverity.FATAL,
                    config={"fields": ["a"]},
                ),
                ModelInvariant(
                    name="Warning Fourth",
                    type=EnumInvariantType.FIELD_PRESENCE,
                    severity=EnumSeverity.WARNING,
                    config={"fields": ["a"]},
                ),
                ModelInvariant(
                    name="Info Fifth",
                    type=EnumInvariantType.FIELD_PRESENCE,
                    severity=EnumSeverity.INFO,
                    config={"fields": ["a"]},
                ),
                ModelInvariant(
                    name="Error Sixth",
                    type=EnumInvariantType.FIELD_PRESENCE,
                    severity=EnumSeverity.ERROR,
                    config={"fields": ["a"]},
                ),
            ],
        )

        summary = evaluator.evaluate_all(invariant_set, {"a": True})

        # All should pass
        assert summary.overall_passed is True
        assert summary.passed_count == 6
        assert summary.failed_count == 0

        # Verify results maintain original invariant order
        assert summary.results[0].invariant_name == "Debug First"
        assert summary.results[0].severity == EnumSeverity.DEBUG
        assert summary.results[1].invariant_name == "Critical Second"
        assert summary.results[1].severity == EnumSeverity.CRITICAL
        assert summary.results[2].invariant_name == "Fatal Third"
        assert summary.results[2].severity == EnumSeverity.FATAL
        assert summary.results[3].invariant_name == "Warning Fourth"
        assert summary.results[3].severity == EnumSeverity.WARNING
        assert summary.results[4].invariant_name == "Info Fifth"
        assert summary.results[4].severity == EnumSeverity.INFO
        assert summary.results[5].invariant_name == "Error Sixth"
        assert summary.results[5].severity == EnumSeverity.ERROR

    def test_fatal_higher_priority_than_critical_for_fail_fast(
        self, evaluator: ServiceInvariantEvaluator
    ) -> None:
        """Both FATAL and CRITICAL trigger fail_fast, confirming severity parity.

        The fail_fast mechanism treats FATAL and CRITICAL equally - both
        should stop evaluation immediately when encountered.
        """
        # Test FATAL first in order
        fatal_first = ModelInvariantSet(
            name="Fatal Before Critical",
            target="test",
            invariants=[
                ModelInvariant(
                    name="Fatal Fail",
                    type=EnumInvariantType.FIELD_PRESENCE,
                    severity=EnumSeverity.FATAL,
                    config={"fields": ["missing"]},
                ),
                ModelInvariant(
                    name="Critical After",
                    type=EnumInvariantType.FIELD_PRESENCE,
                    severity=EnumSeverity.CRITICAL,
                    config={"fields": ["missing"]},
                ),
            ],
        )

        summary_fatal_first = evaluator.evaluate_all(fatal_first, {}, fail_fast=True)
        assert summary_fatal_first.fatal_failures == 1
        assert summary_fatal_first.critical_failures == 0  # Never evaluated
        assert len(summary_fatal_first.results) == 1

        # Test CRITICAL first in order
        critical_first = ModelInvariantSet(
            name="Critical Before Fatal",
            target="test",
            invariants=[
                ModelInvariant(
                    name="Critical Fail",
                    type=EnumInvariantType.FIELD_PRESENCE,
                    severity=EnumSeverity.CRITICAL,
                    config={"fields": ["missing"]},
                ),
                ModelInvariant(
                    name="Fatal After",
                    type=EnumInvariantType.FIELD_PRESENCE,
                    severity=EnumSeverity.FATAL,
                    config={"fields": ["missing"]},
                ),
            ],
        )

        summary_critical_first = evaluator.evaluate_all(
            critical_first, {}, fail_fast=True
        )
        assert summary_critical_first.critical_failures == 1
        assert summary_critical_first.fatal_failures == 0  # Never evaluated
        assert len(summary_critical_first.results) == 1

    def test_fatal_does_not_trigger_fail_fast_when_disabled(
        self, evaluator: ServiceInvariantEvaluator
    ) -> None:
        """FATAL failures do not stop evaluation when fail_fast=False.

        With fail_fast disabled, all invariants should be evaluated
        regardless of severity level.
        """
        invariant_set = ModelInvariantSet(
            name="All Evaluated",
            target="test",
            invariants=[
                ModelInvariant(
                    name="First Fatal",
                    type=EnumInvariantType.FIELD_PRESENCE,
                    severity=EnumSeverity.FATAL,
                    config={"fields": ["missing_1"]},
                ),
                ModelInvariant(
                    name="Second Warning",
                    type=EnumInvariantType.FIELD_PRESENCE,
                    severity=EnumSeverity.WARNING,
                    config={"fields": ["missing_2"]},
                ),
                ModelInvariant(
                    name="Third Critical",
                    type=EnumInvariantType.FIELD_PRESENCE,
                    severity=EnumSeverity.CRITICAL,
                    config={"fields": ["missing_3"]},
                ),
            ],
        )

        # fail_fast=False is the default
        summary = evaluator.evaluate_all(invariant_set, {}, fail_fast=False)

        # All three should be evaluated
        assert len(summary.results) == 3
        assert summary.fatal_failures == 1
        assert summary.warning_failures == 1
        assert summary.critical_failures == 1
        assert summary.failed_count == 3
