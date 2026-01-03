# SPDX-FileCopyrightText: 2025 OmniNode Team
# SPDX-License-Identifier: Apache-2.0
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

from omnibase_core.enums import EnumInvariantSeverity, EnumInvariantType
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
                    severity=EnumInvariantSeverity.CRITICAL,
                    config={"fields": ["status"]},
                ),
                ModelInvariant(
                    name="Value Check",
                    type=EnumInvariantType.FIELD_VALUE,
                    severity=EnumInvariantSeverity.WARNING,
                    config={"field_path": "status", "expected_value": "ok"},
                ),
                ModelInvariant(
                    name="Threshold Check",
                    type=EnumInvariantType.THRESHOLD,
                    severity=EnumInvariantSeverity.CRITICAL,
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
                    severity=EnumInvariantSeverity.CRITICAL,
                    config={"fields": ["missing_field"]},  # Will fail
                ),
                ModelInvariant(
                    name="Second",
                    type=EnumInvariantType.FIELD_PRESENCE,
                    severity=EnumInvariantSeverity.WARNING,
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
                    severity=EnumInvariantSeverity.CRITICAL,
                    config={"fields": ["missing_critical"]},
                ),
                ModelInvariant(
                    name="Warning Fail",
                    type=EnumInvariantType.FIELD_PRESENCE,
                    severity=EnumInvariantSeverity.WARNING,
                    config={"fields": ["missing_warning"]},
                ),
                ModelInvariant(
                    name="Info Fail",
                    type=EnumInvariantType.FIELD_PRESENCE,
                    severity=EnumInvariantSeverity.INFO,
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

    def test_evaluate_all_overall_passed_without_critical_failures(
        self, evaluator: ServiceInvariantEvaluator
    ) -> None:
        """overall_passed is True when no critical failures exist."""
        invariant_set = ModelInvariantSet(
            name="Warning Only",
            target="test",
            invariants=[
                ModelInvariant(
                    name="Warning Fail",
                    type=EnumInvariantType.FIELD_PRESENCE,
                    severity=EnumInvariantSeverity.WARNING,
                    config={"fields": ["missing"]},
                ),
                ModelInvariant(
                    name="Pass",
                    type=EnumInvariantType.FIELD_PRESENCE,
                    severity=EnumInvariantSeverity.CRITICAL,
                    config={"fields": ["present"]},
                ),
            ],
        )

        summary = evaluator.evaluate_all(invariant_set, {"present": True})

        assert summary.warning_failures == 1
        assert summary.critical_failures == 0
        # overall_passed is True because no CRITICAL failures
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
                    severity=EnumInvariantSeverity.WARNING,
                    config={"fields": ["field1"]},
                    enabled=True,
                ),
                ModelInvariant(
                    name="Disabled",
                    type=EnumInvariantType.FIELD_PRESENCE,
                    severity=EnumInvariantSeverity.WARNING,
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
                    severity=EnumInvariantSeverity.WARNING,
                    config={"fields": ["exists"]},
                ),
                ModelInvariant(
                    name="Second Critical Fail",
                    type=EnumInvariantType.FIELD_PRESENCE,
                    severity=EnumInvariantSeverity.CRITICAL,
                    config={"fields": ["missing"]},
                ),
                ModelInvariant(
                    name="Third Never Evaluated",
                    type=EnumInvariantType.FIELD_PRESENCE,
                    severity=EnumInvariantSeverity.WARNING,
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
        assert summary.critical_failures == 0
        assert summary.overall_passed is True
        assert len(summary.results) == 0
