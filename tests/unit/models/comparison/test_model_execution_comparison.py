"""Tests for ModelExecutionComparison.

Comprehensive test suite for the execution comparison model,
covering creation, validation, diff detection, invariant pairing,
and metric calculations.
"""

import json
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

import pytest
from pydantic import ValidationError

from omnibase_core.enums.enum_invariant_severity import EnumInvariantSeverity
from omnibase_core.models.comparison import (
    ModelExecutionComparison,
    ModelInvariantComparisonSummary,
    ModelOutputDiff,
    ModelValueChange,
)
from omnibase_core.models.invariant import ModelInvariantResult

# Import centralized test UUIDs from conftest
from .conftest import (
    TEST_BASELINE_ID,
    TEST_COMPARISON_ID,
    TEST_INVARIANT_ID_1,
    TEST_INVARIANT_ID_2,
    TEST_REPLAY_ID,
)

# ============================================================================
# Helper Fixtures for ModelExecutionComparison Tests
# ============================================================================


@pytest.fixture
def sample_invariant_result_passed() -> ModelInvariantResult:
    """Create a sample passing invariant result."""
    return ModelInvariantResult(
        invariant_id=TEST_INVARIANT_ID_1,
        invariant_name="latency_check",
        passed=True,
        severity=EnumInvariantSeverity.WARNING,
        actual_value=150.0,
        expected_value=500.0,
        message="Latency within acceptable range",
    )


@pytest.fixture
def sample_invariant_result_failed() -> ModelInvariantResult:
    """Create a sample failing invariant result."""
    return ModelInvariantResult(
        invariant_id=TEST_INVARIANT_ID_2,
        invariant_name="cost_check",
        passed=False,
        severity=EnumInvariantSeverity.CRITICAL,
        actual_value=0.15,
        expected_value=0.10,
        message="Cost exceeded maximum threshold",
    )


@pytest.fixture
def sample_no_regression_summary() -> ModelInvariantComparisonSummary:
    """Create sample invariant comparison summary with no regression."""
    return ModelInvariantComparisonSummary(
        total_invariants=5,
        both_passed=4,
        both_failed=0,
        new_violations=0,
        fixed_violations=1,
    )


@pytest.fixture
def sample_regression_summary() -> ModelInvariantComparisonSummary:
    """Create sample invariant comparison summary with regression detected."""
    return ModelInvariantComparisonSummary(
        total_invariants=5,
        both_passed=3,
        both_failed=0,
        new_violations=2,
        fixed_violations=0,
    )


@pytest.fixture
def minimal_comparison_data(
    sample_input_hash: str,
    sample_matching_output_hashes: tuple[str, str],
    sample_no_regression_summary: ModelInvariantComparisonSummary,
    sample_invariant_result_passed: ModelInvariantResult,
) -> dict[str, Any]:
    """Create minimal valid data for ModelExecutionComparison."""
    baseline_hash, replay_hash = sample_matching_output_hashes
    return {
        "baseline_execution_id": TEST_BASELINE_ID,
        "replay_execution_id": TEST_REPLAY_ID,
        "input_hash": sample_input_hash,
        "input_hash_match": True,
        "baseline_output_hash": baseline_hash,
        "replay_output_hash": replay_hash,
        "output_match": True,
        "baseline_latency_ms": 150.0,
        "replay_latency_ms": 160.0,
        "latency_delta_ms": 10.0,  # 160 - 150
        "latency_delta_percent": 6.67,  # (10 / 150) * 100
        "baseline_invariant_results": [sample_invariant_result_passed],
        "replay_invariant_results": [sample_invariant_result_passed],
        "invariant_comparison": sample_no_regression_summary,
    }


@pytest.fixture
def comparison_with_diff_data(
    sample_input_hash: str,
    sample_different_output_hashes: tuple[str, str],
    sample_output_diff: ModelOutputDiff,
    sample_regression_summary: ModelInvariantComparisonSummary,
    sample_invariant_result_passed: ModelInvariantResult,
    sample_invariant_result_failed: ModelInvariantResult,
) -> dict[str, Any]:
    """Create comparison data with output differences."""
    baseline_hash, replay_hash = sample_different_output_hashes
    return {
        "baseline_execution_id": TEST_BASELINE_ID,
        "replay_execution_id": TEST_REPLAY_ID,
        "input_hash": sample_input_hash,
        "input_hash_match": True,
        "baseline_output_hash": baseline_hash,
        "replay_output_hash": replay_hash,
        "output_match": False,
        "output_diff": sample_output_diff,
        "baseline_latency_ms": 150.0,
        "replay_latency_ms": 200.0,
        "latency_delta_ms": 50.0,
        "latency_delta_percent": 33.33,
        "baseline_cost": 0.05,
        "replay_cost": 0.08,
        "cost_delta": 0.03,
        "cost_delta_percent": 60.0,
        "baseline_invariant_results": [sample_invariant_result_passed],
        "replay_invariant_results": [sample_invariant_result_failed],
        "invariant_comparison": sample_regression_summary,
    }


# ============================================================================
# Test Classes
# ============================================================================


@pytest.mark.unit
class TestModelExecutionComparisonCreation:
    """Test ModelExecutionComparison creation and validation."""

    def test_create_comparison_with_matching_outputs(
        self,
        minimal_comparison_data: dict[str, Any],
    ) -> None:
        """Comparison correctly identifies matching outputs."""
        comparison = ModelExecutionComparison(**minimal_comparison_data)

        assert comparison.baseline_execution_id == TEST_BASELINE_ID
        assert comparison.replay_execution_id == TEST_REPLAY_ID
        assert comparison.output_match is True
        assert comparison.output_diff is None

    def test_create_comparison_with_differing_outputs(
        self,
        comparison_with_diff_data: dict[str, Any],
    ) -> None:
        """Comparison detects and structures output differences."""
        comparison = ModelExecutionComparison(**comparison_with_diff_data)

        assert comparison.output_match is False
        assert comparison.output_diff is not None
        assert isinstance(comparison.output_diff, ModelOutputDiff)
        assert comparison.output_diff.has_differences is True
        assert comparison.baseline_output_hash != comparison.replay_output_hash

    def test_input_hash_mismatch_flagged(
        self,
        sample_no_regression_summary: ModelInvariantComparisonSummary,
        sample_invariant_result_passed: ModelInvariantResult,
    ) -> None:
        """Input hash mismatch is clearly flagged as invalid comparison."""
        data = {
            "baseline_execution_id": TEST_BASELINE_ID,
            "replay_execution_id": TEST_REPLAY_ID,
            "input_hash": "sha256:different_hash_1234567890123456789012345678901234567890",
            "input_hash_match": False,  # Flag indicating mismatch
            "baseline_output_hash": "sha256:output1234567890123456789012345678901234567890123",
            "replay_output_hash": "sha256:output1234567890123456789012345678901234567890123",
            "output_match": True,
            "baseline_latency_ms": 100.0,
            "replay_latency_ms": 100.0,
            "latency_delta_ms": 0.0,
            "latency_delta_percent": 0.0,
            "baseline_invariant_results": [sample_invariant_result_passed],
            "replay_invariant_results": [sample_invariant_result_passed],
            "invariant_comparison": sample_no_regression_summary,
        }
        comparison = ModelExecutionComparison(**data)

        # The comparison should flag input hash mismatch
        assert comparison.input_hash_match is False

    def test_comparison_requires_both_executions(
        self,
        sample_input_hash: str,
        sample_matching_output_hashes: tuple[str, str],
        sample_no_regression_summary: ModelInvariantComparisonSummary,
        sample_invariant_result_passed: ModelInvariantResult,
    ) -> None:
        """Validation fails if either execution reference is missing."""
        baseline_hash, replay_hash = sample_matching_output_hashes
        common_data = {
            "input_hash": sample_input_hash,
            "input_hash_match": True,
            "baseline_output_hash": baseline_hash,
            "replay_output_hash": replay_hash,
            "output_match": True,
            "baseline_latency_ms": 100.0,
            "replay_latency_ms": 100.0,
            "latency_delta_ms": 0.0,
            "latency_delta_percent": 0.0,
            "baseline_invariant_results": [sample_invariant_result_passed],
            "replay_invariant_results": [sample_invariant_result_passed],
            "invariant_comparison": sample_no_regression_summary,
        }

        # Missing baseline_execution_id
        with pytest.raises(ValidationError) as exc_info:
            ModelExecutionComparison(
                replay_execution_id=TEST_REPLAY_ID,
                **common_data,
            )
        assert "baseline_execution_id" in str(exc_info.value)

        # Missing replay_execution_id
        with pytest.raises(ValidationError) as exc_info:
            ModelExecutionComparison(
                baseline_execution_id=TEST_BASELINE_ID,
                **common_data,
            )
        assert "replay_execution_id" in str(exc_info.value)

    def test_comparison_generates_unique_id(
        self,
        minimal_comparison_data: dict[str, Any],
    ) -> None:
        """Each comparison gets a unique comparison_id by default."""
        comparison1 = ModelExecutionComparison(**minimal_comparison_data)
        comparison2 = ModelExecutionComparison(**minimal_comparison_data)

        assert comparison1.comparison_id is not None
        assert comparison2.comparison_id is not None
        assert isinstance(comparison1.comparison_id, UUID)
        assert isinstance(comparison2.comparison_id, UUID)
        assert comparison1.comparison_id != comparison2.comparison_id

    def test_comparison_is_frozen(
        self,
        minimal_comparison_data: dict[str, Any],
    ) -> None:
        """Comparison is immutable after creation."""
        comparison = ModelExecutionComparison(**minimal_comparison_data)

        with pytest.raises((AttributeError, ValidationError)):
            comparison.output_match = False  # type: ignore[misc]


@pytest.mark.unit
class TestModelExecutionComparisonDiffDetection:
    """Test output difference detection in ModelExecutionComparison."""

    def test_detect_value_change(
        self,
        sample_input_hash: str,
        sample_different_output_hashes: tuple[str, str],
        sample_no_regression_summary: ModelInvariantComparisonSummary,
        sample_invariant_result_passed: ModelInvariantResult,
    ) -> None:
        """Detects when output values change."""
        baseline_hash, replay_hash = sample_different_output_hashes
        output_diff = ModelOutputDiff(
            values_changed={
                "root['response']['text']": ModelValueChange(
                    old_value="Original text",
                    new_value="Changed text",
                )
            },
        )

        comparison = ModelExecutionComparison(
            baseline_execution_id=TEST_BASELINE_ID,
            replay_execution_id=TEST_REPLAY_ID,
            input_hash=sample_input_hash,
            input_hash_match=True,
            baseline_output_hash=baseline_hash,
            replay_output_hash=replay_hash,
            output_match=False,
            output_diff=output_diff,
            baseline_latency_ms=100.0,
            replay_latency_ms=100.0,
            latency_delta_ms=0.0,
            latency_delta_percent=0.0,
            baseline_invariant_results=[sample_invariant_result_passed],
            replay_invariant_results=[sample_invariant_result_passed],
            invariant_comparison=sample_no_regression_summary,
        )

        assert comparison.output_diff is not None
        assert len(comparison.output_diff.values_changed) > 0

    def test_detect_structural_change(
        self,
        sample_input_hash: str,
        sample_different_output_hashes: tuple[str, str],
        sample_no_regression_summary: ModelInvariantComparisonSummary,
        sample_invariant_result_passed: ModelInvariantResult,
    ) -> None:
        """Detects when output structure changes (added/removed fields)."""
        baseline_hash, replay_hash = sample_different_output_hashes
        output_diff = ModelOutputDiff(
            items_added=["root['new_field']"],
            items_removed=["root['old_field']"],
        )

        comparison = ModelExecutionComparison(
            baseline_execution_id=TEST_BASELINE_ID,
            replay_execution_id=TEST_REPLAY_ID,
            input_hash=sample_input_hash,
            input_hash_match=True,
            baseline_output_hash=baseline_hash,
            replay_output_hash=replay_hash,
            output_match=False,
            output_diff=output_diff,
            baseline_latency_ms=100.0,
            replay_latency_ms=100.0,
            latency_delta_ms=0.0,
            latency_delta_percent=0.0,
            baseline_invariant_results=[sample_invariant_result_passed],
            replay_invariant_results=[sample_invariant_result_passed],
            invariant_comparison=sample_no_regression_summary,
        )

        assert comparison.output_diff is not None
        assert len(comparison.output_diff.items_added) > 0
        assert len(comparison.output_diff.items_removed) > 0

    def test_no_diff_for_identical_outputs(
        self,
        minimal_comparison_data: dict[str, Any],
    ) -> None:
        """output_diff is None when outputs match."""
        comparison = ModelExecutionComparison(**minimal_comparison_data)

        assert comparison.output_match is True
        assert comparison.output_diff is None

    def test_output_match_true_when_hashes_equal(
        self,
        sample_input_hash: str,
        sample_matching_output_hashes: tuple[str, str],
        sample_no_regression_summary: ModelInvariantComparisonSummary,
        sample_invariant_result_passed: ModelInvariantResult,
    ) -> None:
        """output_match is True when baseline and replay hashes are equal."""
        baseline_hash, replay_hash = sample_matching_output_hashes
        assert baseline_hash == replay_hash

        comparison = ModelExecutionComparison(
            baseline_execution_id=TEST_BASELINE_ID,
            replay_execution_id=TEST_REPLAY_ID,
            input_hash=sample_input_hash,
            input_hash_match=True,
            baseline_output_hash=baseline_hash,
            replay_output_hash=replay_hash,
            output_match=True,
            baseline_latency_ms=100.0,
            replay_latency_ms=100.0,
            latency_delta_ms=0.0,
            latency_delta_percent=0.0,
            baseline_invariant_results=[sample_invariant_result_passed],
            replay_invariant_results=[sample_invariant_result_passed],
            invariant_comparison=sample_no_regression_summary,
        )

        assert comparison.output_match is True
        assert comparison.baseline_output_hash == comparison.replay_output_hash

    def test_output_match_false_when_hashes_differ(
        self,
        sample_input_hash: str,
        sample_different_output_hashes: tuple[str, str],
        sample_no_regression_summary: ModelInvariantComparisonSummary,
        sample_invariant_result_passed: ModelInvariantResult,
    ) -> None:
        """output_match is False when baseline and replay hashes differ."""
        baseline_hash, replay_hash = sample_different_output_hashes
        assert baseline_hash != replay_hash

        comparison = ModelExecutionComparison(
            baseline_execution_id=TEST_BASELINE_ID,
            replay_execution_id=TEST_REPLAY_ID,
            input_hash=sample_input_hash,
            input_hash_match=True,
            baseline_output_hash=baseline_hash,
            replay_output_hash=replay_hash,
            output_match=False,
            output_diff=ModelOutputDiff(),
            baseline_latency_ms=100.0,
            replay_latency_ms=100.0,
            latency_delta_ms=0.0,
            latency_delta_percent=0.0,
            baseline_invariant_results=[sample_invariant_result_passed],
            replay_invariant_results=[sample_invariant_result_passed],
            invariant_comparison=sample_no_regression_summary,
        )

        assert comparison.output_match is False
        assert comparison.baseline_output_hash != comparison.replay_output_hash


@pytest.mark.unit
class TestModelExecutionComparisonInvariantPairing:
    """Test pairing of invariant results between baseline and replay executions."""

    def test_stores_baseline_invariant_results(
        self,
        minimal_comparison_data: dict[str, Any],
        sample_invariant_result_passed: ModelInvariantResult,
        sample_invariant_result_failed: ModelInvariantResult,
    ) -> None:
        """Baseline invariant results are stored correctly."""
        baseline_results = [
            sample_invariant_result_passed,
            sample_invariant_result_failed,
        ]

        data = {
            **minimal_comparison_data,
            "baseline_invariant_results": baseline_results,
        }
        comparison = ModelExecutionComparison(**data)

        assert comparison.baseline_invariant_results is not None
        assert len(comparison.baseline_invariant_results) == 2
        assert (
            comparison.baseline_invariant_results[0].invariant_name == "latency_check"
        )
        assert comparison.baseline_invariant_results[1].invariant_name == "cost_check"

    def test_stores_replay_invariant_results(
        self,
        minimal_comparison_data: dict[str, Any],
        sample_invariant_result_passed: ModelInvariantResult,
    ) -> None:
        """Replay invariant results are stored correctly."""
        replay_results = [sample_invariant_result_passed]

        data = {
            **minimal_comparison_data,
            "replay_invariant_results": replay_results,
        }
        comparison = ModelExecutionComparison(**data)

        assert comparison.replay_invariant_results is not None
        assert len(comparison.replay_invariant_results) == 1
        assert comparison.replay_invariant_results[0].passed is True

    def test_invariant_comparison_summary_included(
        self,
        minimal_comparison_data: dict[str, Any],
    ) -> None:
        """Invariant comparison summary is included and valid."""
        comparison = ModelExecutionComparison(**minimal_comparison_data)

        assert comparison.invariant_comparison is not None
        assert isinstance(
            comparison.invariant_comparison, ModelInvariantComparisonSummary
        )
        assert comparison.invariant_comparison.total_invariants == 5
        assert comparison.invariant_comparison.both_passed == 4

    def test_regression_detection_from_summary(
        self,
        comparison_with_diff_data: dict[str, Any],
    ) -> None:
        """Can detect regressions via invariant_comparison.regression_detected."""
        comparison = ModelExecutionComparison(**comparison_with_diff_data)

        assert comparison.invariant_comparison.regression_detected is True
        assert comparison.invariant_comparison.new_violations == 2


@pytest.mark.unit
class TestModelExecutionComparisonMetrics:
    """Test latency and cost metric calculations in ModelExecutionComparison."""

    def test_latency_delta_calculation(
        self,
        sample_input_hash: str,
        sample_matching_output_hashes: tuple[str, str],
        sample_no_regression_summary: ModelInvariantComparisonSummary,
        sample_invariant_result_passed: ModelInvariantResult,
    ) -> None:
        """Latency delta calculated correctly (replay - baseline)."""
        baseline_hash, replay_hash = sample_matching_output_hashes

        comparison = ModelExecutionComparison(
            baseline_execution_id=TEST_BASELINE_ID,
            replay_execution_id=TEST_REPLAY_ID,
            input_hash=sample_input_hash,
            input_hash_match=True,
            baseline_output_hash=baseline_hash,
            replay_output_hash=replay_hash,
            output_match=True,
            baseline_latency_ms=150.0,
            replay_latency_ms=180.0,
            latency_delta_ms=30.0,  # replay - baseline = 180 - 150
            latency_delta_percent=20.0,  # (30 / 150) * 100
            baseline_invariant_results=[sample_invariant_result_passed],
            replay_invariant_results=[sample_invariant_result_passed],
            invariant_comparison=sample_no_regression_summary,
        )

        # latency_delta_ms = replay - baseline = 180 - 150 = 30
        assert comparison.latency_delta_ms == 30.0

    def test_latency_delta_percent_positive(
        self,
        sample_input_hash: str,
        sample_matching_output_hashes: tuple[str, str],
        sample_no_regression_summary: ModelInvariantComparisonSummary,
        sample_invariant_result_passed: ModelInvariantResult,
    ) -> None:
        """Positive percent means replay was slower."""
        baseline_hash, replay_hash = sample_matching_output_hashes

        comparison = ModelExecutionComparison(
            baseline_execution_id=TEST_BASELINE_ID,
            replay_execution_id=TEST_REPLAY_ID,
            input_hash=sample_input_hash,
            input_hash_match=True,
            baseline_output_hash=baseline_hash,
            replay_output_hash=replay_hash,
            output_match=True,
            baseline_latency_ms=100.0,
            replay_latency_ms=120.0,  # 20% slower
            latency_delta_ms=20.0,
            latency_delta_percent=20.0,  # Positive = slower
            baseline_invariant_results=[sample_invariant_result_passed],
            replay_invariant_results=[sample_invariant_result_passed],
            invariant_comparison=sample_no_regression_summary,
        )

        # latency_delta_percent = (120 - 100) / 100 * 100 = 20%
        assert comparison.latency_delta_percent == pytest.approx(20.0)
        assert comparison.latency_delta_percent > 0  # Positive = slower

    def test_latency_delta_percent_negative(
        self,
        sample_input_hash: str,
        sample_matching_output_hashes: tuple[str, str],
        sample_no_regression_summary: ModelInvariantComparisonSummary,
        sample_invariant_result_passed: ModelInvariantResult,
    ) -> None:
        """Negative percent means replay was faster."""
        baseline_hash, replay_hash = sample_matching_output_hashes

        comparison = ModelExecutionComparison(
            baseline_execution_id=TEST_BASELINE_ID,
            replay_execution_id=TEST_REPLAY_ID,
            input_hash=sample_input_hash,
            input_hash_match=True,
            baseline_output_hash=baseline_hash,
            replay_output_hash=replay_hash,
            output_match=True,
            baseline_latency_ms=100.0,
            replay_latency_ms=80.0,  # 20% faster
            latency_delta_ms=-20.0,
            latency_delta_percent=-20.0,  # Negative = faster
            baseline_invariant_results=[sample_invariant_result_passed],
            replay_invariant_results=[sample_invariant_result_passed],
            invariant_comparison=sample_no_regression_summary,
        )

        # latency_delta_percent = (80 - 100) / 100 * 100 = -20%
        assert comparison.latency_delta_percent == pytest.approx(-20.0)
        assert comparison.latency_delta_percent < 0  # Negative = faster

    def test_latency_delta_percent_with_zero_baseline(
        self,
        sample_input_hash: str,
        sample_matching_output_hashes: tuple[str, str],
        sample_no_regression_summary: ModelInvariantComparisonSummary,
        sample_invariant_result_passed: ModelInvariantResult,
    ) -> None:
        """Model accepts zero baseline latency with pre-computed delta percent.

        When baseline_latency_ms is 0, calculating percent change would cause
        division by zero. Since ModelExecutionComparison stores pre-computed
        delta_percent values (not computed at runtime), the producer of this
        data is responsible for handling the edge case.

        Convention: When baseline is 0, latency_delta_percent is set to 0.0
        (alternatively could be infinity or undefined, but 0.0 is a safe default).
        This test verifies the model accepts valid data for this edge case.
        """
        baseline_hash, replay_hash = sample_matching_output_hashes

        comparison = ModelExecutionComparison(
            baseline_execution_id=TEST_BASELINE_ID,
            replay_execution_id=TEST_REPLAY_ID,
            input_hash=sample_input_hash,
            input_hash_match=True,
            baseline_output_hash=baseline_hash,
            replay_output_hash=replay_hash,
            output_match=True,
            baseline_latency_ms=0.0,  # Zero baseline (edge case)
            replay_latency_ms=100.0,  # Non-zero replay
            latency_delta_ms=100.0,  # replay - baseline = 100 - 0
            latency_delta_percent=0.0,  # Convention: 0% when baseline is 0
            baseline_invariant_results=[sample_invariant_result_passed],
            replay_invariant_results=[sample_invariant_result_passed],
            invariant_comparison=sample_no_regression_summary,
        )

        # Verify the model accepts zero baseline latency
        assert comparison.baseline_latency_ms == 0.0
        assert comparison.replay_latency_ms == 100.0
        assert comparison.latency_delta_ms == 100.0
        # Delta percent is 0.0 by convention when baseline is 0
        # (avoids division by zero in percent calculation)
        assert comparison.latency_delta_percent == 0.0

    def test_cost_delta_with_missing_values(
        self,
        minimal_comparison_data: dict[str, Any],
    ) -> None:
        """Cost delta is None if either cost is missing."""
        # minimal_comparison_data does not include cost values
        comparison = ModelExecutionComparison(**minimal_comparison_data)

        assert comparison.baseline_cost is None
        assert comparison.replay_cost is None
        assert comparison.cost_delta is None

    def test_cost_delta_calculation(
        self,
        comparison_with_diff_data: dict[str, Any],
    ) -> None:
        """Cost delta calculated correctly when both present."""
        comparison = ModelExecutionComparison(**comparison_with_diff_data)

        # From fixture: baseline_cost=0.05, replay_cost=0.08
        # cost_delta = replay_cost - baseline_cost = 0.08 - 0.05 = 0.03
        assert comparison.baseline_cost == 0.05
        assert comparison.replay_cost == 0.08
        assert comparison.cost_delta == pytest.approx(0.03)

    def test_latency_must_be_non_negative(
        self,
        sample_input_hash: str,
        sample_matching_output_hashes: tuple[str, str],
        sample_no_regression_summary: ModelInvariantComparisonSummary,
        sample_invariant_result_passed: ModelInvariantResult,
    ) -> None:
        """Latency values must be >= 0."""
        baseline_hash, replay_hash = sample_matching_output_hashes
        common_data = {
            "input_hash": sample_input_hash,
            "input_hash_match": True,
            "baseline_output_hash": baseline_hash,
            "replay_output_hash": replay_hash,
            "output_match": True,
            "latency_delta_ms": 0.0,
            "latency_delta_percent": 0.0,
            "baseline_invariant_results": [sample_invariant_result_passed],
            "replay_invariant_results": [sample_invariant_result_passed],
            "invariant_comparison": sample_no_regression_summary,
        }

        with pytest.raises(ValidationError) as exc_info:
            ModelExecutionComparison(
                baseline_execution_id=TEST_BASELINE_ID,
                replay_execution_id=TEST_REPLAY_ID,
                baseline_latency_ms=-10.0,  # Invalid negative latency
                replay_latency_ms=100.0,
                **common_data,
            )
        assert (
            "baseline_latency_ms" in str(exc_info.value)
            or "greater" in str(exc_info.value).lower()
        )

        with pytest.raises(ValidationError) as exc_info:
            ModelExecutionComparison(
                baseline_execution_id=TEST_BASELINE_ID,
                replay_execution_id=TEST_REPLAY_ID,
                baseline_latency_ms=100.0,
                replay_latency_ms=-5.0,  # Invalid negative latency
                **common_data,
            )
        assert (
            "replay_latency_ms" in str(exc_info.value)
            or "greater" in str(exc_info.value).lower()
        )


@pytest.mark.unit
class TestModelExecutionComparisonSerialization:
    """Test serialization to dict and JSON for ModelExecutionComparison."""

    def test_serializes_to_dict(
        self,
        minimal_comparison_data: dict[str, Any],
    ) -> None:
        """Comparison can be serialized to dictionary."""
        comparison = ModelExecutionComparison(**minimal_comparison_data)
        serialized = comparison.model_dump()

        assert isinstance(serialized, dict)
        assert "baseline_execution_id" in serialized
        assert "replay_execution_id" in serialized
        assert "output_match" in serialized
        assert "invariant_comparison" in serialized
        assert serialized["output_match"] is True

    def test_serializes_to_json(
        self,
        minimal_comparison_data: dict[str, Any],
    ) -> None:
        """Comparison can be serialized to JSON string."""
        comparison = ModelExecutionComparison(**minimal_comparison_data)
        json_str = comparison.model_dump_json()

        assert isinstance(json_str, str)
        parsed = json.loads(json_str)
        assert parsed["output_match"] is True
        assert "baseline_execution_id" in parsed
        assert "invariant_comparison" in parsed

    def test_compared_at_defaults_to_now(
        self,
        minimal_comparison_data: dict[str, Any],
    ) -> None:
        """compared_at field defaults to current UTC time."""
        before = datetime.now(UTC)
        comparison = ModelExecutionComparison(**minimal_comparison_data)
        after = datetime.now(UTC)

        assert comparison.compared_at is not None
        assert isinstance(comparison.compared_at, datetime)
        # Allow 1 second tolerance for test execution
        assert (
            before - timedelta(seconds=1)
            <= comparison.compared_at
            <= after + timedelta(seconds=1)
        )


@pytest.mark.unit
class TestModelExecutionComparisonEdgeCases:
    """Test edge cases and boundary conditions for ModelExecutionComparison."""

    def test_comparison_with_zero_latency(
        self,
        sample_input_hash: str,
        sample_matching_output_hashes: tuple[str, str],
        sample_no_regression_summary: ModelInvariantComparisonSummary,
        sample_invariant_result_passed: ModelInvariantResult,
    ) -> None:
        """Comparison handles zero latency correctly."""
        baseline_hash, replay_hash = sample_matching_output_hashes

        comparison = ModelExecutionComparison(
            baseline_execution_id=TEST_BASELINE_ID,
            replay_execution_id=TEST_REPLAY_ID,
            input_hash=sample_input_hash,
            input_hash_match=True,
            baseline_output_hash=baseline_hash,
            replay_output_hash=replay_hash,
            output_match=True,
            baseline_latency_ms=0.0,
            replay_latency_ms=0.0,
            latency_delta_ms=0.0,
            latency_delta_percent=0.0,
            baseline_invariant_results=[sample_invariant_result_passed],
            replay_invariant_results=[sample_invariant_result_passed],
            invariant_comparison=sample_no_regression_summary,
        )

        assert comparison.baseline_latency_ms == 0.0
        assert comparison.replay_latency_ms == 0.0
        assert comparison.latency_delta_ms == 0.0

    def test_comparison_with_empty_invariant_results(
        self,
        sample_input_hash: str,
        sample_matching_output_hashes: tuple[str, str],
        sample_no_regression_summary: ModelInvariantComparisonSummary,
    ) -> None:
        """Comparison handles empty invariant result lists."""
        baseline_hash, replay_hash = sample_matching_output_hashes

        comparison = ModelExecutionComparison(
            baseline_execution_id=TEST_BASELINE_ID,
            replay_execution_id=TEST_REPLAY_ID,
            input_hash=sample_input_hash,
            input_hash_match=True,
            baseline_output_hash=baseline_hash,
            replay_output_hash=replay_hash,
            output_match=True,
            baseline_latency_ms=100.0,
            replay_latency_ms=100.0,
            latency_delta_ms=0.0,
            latency_delta_percent=0.0,
            baseline_invariant_results=[],
            replay_invariant_results=[],
            invariant_comparison=sample_no_regression_summary,
        )

        assert comparison.baseline_invariant_results == []
        assert comparison.replay_invariant_results == []

    def test_comparison_with_custom_id(
        self,
        minimal_comparison_data: dict[str, Any],
    ) -> None:
        """Comparison accepts custom comparison_id."""
        data = {
            **minimal_comparison_data,
            "comparison_id": TEST_COMPARISON_ID,
        }
        comparison = ModelExecutionComparison(**data)

        assert comparison.comparison_id == TEST_COMPARISON_ID

    def test_comparison_with_very_large_latency(
        self,
        sample_input_hash: str,
        sample_matching_output_hashes: tuple[str, str],
        sample_no_regression_summary: ModelInvariantComparisonSummary,
        sample_invariant_result_passed: ModelInvariantResult,
    ) -> None:
        """Comparison handles very large latency values."""
        baseline_hash, replay_hash = sample_matching_output_hashes

        comparison = ModelExecutionComparison(
            baseline_execution_id=TEST_BASELINE_ID,
            replay_execution_id=TEST_REPLAY_ID,
            input_hash=sample_input_hash,
            input_hash_match=True,
            baseline_output_hash=baseline_hash,
            replay_output_hash=replay_hash,
            output_match=True,
            baseline_latency_ms=999999999.0,
            replay_latency_ms=999999999.0,
            latency_delta_ms=0.0,
            latency_delta_percent=0.0,
            baseline_invariant_results=[sample_invariant_result_passed],
            replay_invariant_results=[sample_invariant_result_passed],
            invariant_comparison=sample_no_regression_summary,
        )

        assert comparison.baseline_latency_ms == 999999999.0
        assert comparison.latency_delta_ms == 0.0

    def test_comparison_with_fractional_cost(
        self,
        sample_input_hash: str,
        sample_matching_output_hashes: tuple[str, str],
        sample_no_regression_summary: ModelInvariantComparisonSummary,
        sample_invariant_result_passed: ModelInvariantResult,
    ) -> None:
        """Comparison handles fractional cost values accurately."""
        baseline_hash, replay_hash = sample_matching_output_hashes

        comparison = ModelExecutionComparison(
            baseline_execution_id=TEST_BASELINE_ID,
            replay_execution_id=TEST_REPLAY_ID,
            input_hash=sample_input_hash,
            input_hash_match=True,
            baseline_output_hash=baseline_hash,
            replay_output_hash=replay_hash,
            output_match=True,
            baseline_latency_ms=100.0,
            replay_latency_ms=100.0,
            latency_delta_ms=0.0,
            latency_delta_percent=0.0,
            baseline_cost=0.00001,
            replay_cost=0.00002,
            cost_delta=0.00001,
            cost_delta_percent=100.0,
            baseline_invariant_results=[sample_invariant_result_passed],
            replay_invariant_results=[sample_invariant_result_passed],
            invariant_comparison=sample_no_regression_summary,
        )

        assert comparison.baseline_cost == pytest.approx(0.00001)
        assert comparison.replay_cost == pytest.approx(0.00002)
        assert comparison.cost_delta == pytest.approx(0.00001)

    def test_output_match_true_consistent_with_equal_hashes(
        self,
        sample_input_hash: str,
        sample_matching_output_hashes: tuple[str, str],
        sample_no_regression_summary: ModelInvariantComparisonSummary,
        sample_invariant_result_passed: ModelInvariantResult,
    ) -> None:
        """Validate that output_match=True is consistent when hashes are equal.

        This test documents the expected usage pattern: when baseline_output_hash
        and replay_output_hash are equal, the caller should set output_match=True.

        Note:
            The model stores user-provided consistency flags (not auto-computed).
            The caller is responsible for computing hash equality and setting
            output_match accordingly. This test validates that the expected
            consistent state is accepted by the model.
        """
        baseline_hash, replay_hash = sample_matching_output_hashes
        # Verify precondition: hashes are equal
        assert baseline_hash == replay_hash, "Fixture should provide equal hashes"

        comparison = ModelExecutionComparison(
            baseline_execution_id=TEST_BASELINE_ID,
            replay_execution_id=TEST_REPLAY_ID,
            input_hash=sample_input_hash,
            input_hash_match=True,
            baseline_output_hash=baseline_hash,
            replay_output_hash=replay_hash,
            output_match=True,  # Consistent with equal hashes
            baseline_latency_ms=100.0,
            replay_latency_ms=100.0,
            latency_delta_ms=0.0,
            latency_delta_percent=0.0,
            baseline_invariant_results=[sample_invariant_result_passed],
            replay_invariant_results=[sample_invariant_result_passed],
            invariant_comparison=sample_no_regression_summary,
        )

        # Verify the consistent state is stored correctly
        assert comparison.output_match is True
        assert comparison.baseline_output_hash == comparison.replay_output_hash
        # No diff should be provided for matching outputs
        assert comparison.output_diff is None

    def test_output_match_false_consistent_with_different_hashes(
        self,
        sample_input_hash: str,
        sample_different_output_hashes: tuple[str, str],
        sample_no_regression_summary: ModelInvariantComparisonSummary,
        sample_invariant_result_passed: ModelInvariantResult,
    ) -> None:
        """Validate that output_match=False is consistent when hashes differ.

        This test documents the expected usage pattern: when baseline_output_hash
        and replay_output_hash are different, the caller should set output_match=False.

        Note:
            The model stores user-provided consistency flags (not auto-computed).
            The caller is responsible for computing hash equality and setting
            output_match accordingly. This test validates that the expected
            consistent state is accepted by the model.
        """
        baseline_hash, replay_hash = sample_different_output_hashes
        # Verify precondition: hashes are different
        assert baseline_hash != replay_hash, "Fixture should provide different hashes"

        comparison = ModelExecutionComparison(
            baseline_execution_id=TEST_BASELINE_ID,
            replay_execution_id=TEST_REPLAY_ID,
            input_hash=sample_input_hash,
            input_hash_match=True,
            baseline_output_hash=baseline_hash,
            replay_output_hash=replay_hash,
            output_match=False,  # Consistent with different hashes
            output_diff=ModelOutputDiff(
                values_changed={
                    "root['response']": ModelValueChange(
                        old_value="baseline response",
                        new_value="replay response",
                    )
                }
            ),
            baseline_latency_ms=100.0,
            replay_latency_ms=100.0,
            latency_delta_ms=0.0,
            latency_delta_percent=0.0,
            baseline_invariant_results=[sample_invariant_result_passed],
            replay_invariant_results=[sample_invariant_result_passed],
            invariant_comparison=sample_no_regression_summary,
        )

        # Verify the consistent state is stored correctly
        assert comparison.output_match is False
        assert comparison.baseline_output_hash != comparison.replay_output_hash
        # Diff should be provided for non-matching outputs
        assert comparison.output_diff is not None
        assert comparison.output_diff.has_differences is True


@pytest.mark.unit
class TestModelExecutionComparisonExtraFields:
    """Test ModelExecutionComparison behavior with additional metadata fields.

    Note: These tests verify the model's behavior with extra fields.
    Since the model has `extra="ignore"`, additional metadata fields
    not defined in the model schema will be silently ignored.
    """

    def test_extra_fields_ignored(
        self,
        minimal_comparison_data: dict[str, Any],
    ) -> None:
        """Extra fields are ignored per model configuration."""
        data = {
            **minimal_comparison_data,
            "node_id": "node_llm_call_gpt4",
            "node_version": "1.0.0",
            "baseline_environment": "staging",
            "replay_environment": "production",
        }
        comparison = ModelExecutionComparison(**data)

        # The model should be created successfully even with extra fields
        assert comparison.baseline_execution_id == TEST_BASELINE_ID

        # Extra fields are not accessible (model ignores them)
        assert not hasattr(comparison, "node_id")
        assert not hasattr(comparison, "node_version")

    def test_core_fields_preserved(
        self,
        minimal_comparison_data: dict[str, Any],
    ) -> None:
        """Core model fields are preserved correctly."""
        comparison = ModelExecutionComparison(**minimal_comparison_data)

        assert comparison.baseline_execution_id == TEST_BASELINE_ID
        assert comparison.replay_execution_id == TEST_REPLAY_ID
        assert comparison.output_match is True
        assert comparison.input_hash_match is True
        assert len(comparison.baseline_invariant_results) >= 1
        assert len(comparison.replay_invariant_results) >= 1


@pytest.mark.unit
class TestModelExecutionComparisonCostDelta:
    """Test cost delta and percentage calculations in ModelExecutionComparison."""

    def test_cost_delta_percent_with_values(
        self,
        sample_input_hash: str,
        sample_matching_output_hashes: tuple[str, str],
        sample_no_regression_summary: ModelInvariantComparisonSummary,
        sample_invariant_result_passed: ModelInvariantResult,
    ) -> None:
        """Cost delta percent is calculated when costs are present."""
        baseline_hash, replay_hash = sample_matching_output_hashes

        comparison = ModelExecutionComparison(
            baseline_execution_id=TEST_BASELINE_ID,
            replay_execution_id=TEST_REPLAY_ID,
            input_hash=sample_input_hash,
            input_hash_match=True,
            baseline_output_hash=baseline_hash,
            replay_output_hash=replay_hash,
            output_match=True,
            baseline_latency_ms=100.0,
            replay_latency_ms=100.0,
            latency_delta_ms=0.0,
            latency_delta_percent=0.0,
            baseline_cost=0.10,
            replay_cost=0.15,
            cost_delta=0.05,
            cost_delta_percent=50.0,  # (0.05 / 0.10) * 100
            baseline_invariant_results=[sample_invariant_result_passed],
            replay_invariant_results=[sample_invariant_result_passed],
            invariant_comparison=sample_no_regression_summary,
        )

        assert comparison.cost_delta_percent == pytest.approx(50.0)

    def test_cost_delta_percent_none_without_costs(
        self,
        minimal_comparison_data: dict[str, Any],
    ) -> None:
        """Cost delta percent is None when costs are not provided."""
        comparison = ModelExecutionComparison(**minimal_comparison_data)

        assert comparison.cost_delta_percent is None


@pytest.mark.unit
class TestModelExecutionComparisonCostDeltaEdgeCases:
    """Test edge cases for cost delta calculations.

    These tests verify the model handles various cost scenarios correctly,
    including division by zero protection and partial cost data.
    """

    def test_edge_cost_delta_percent_with_zero_baseline_cost(
        self,
        sample_input_hash: str,
        sample_matching_output_hashes: tuple[str, str],
        sample_no_regression_summary: ModelInvariantComparisonSummary,
        sample_invariant_result_passed: ModelInvariantResult,
    ) -> None:
        """Model accepts zero baseline_cost with pre-computed delta percent.

        When baseline_cost is 0, calculating percent change would cause
        division by zero. Since ModelExecutionComparison stores pre-computed
        delta_percent values (not computed at runtime), the producer of this
        data is responsible for handling the edge case.

        Convention: When baseline_cost is 0, cost_delta_percent should be set
        to 0.0 (alternatively could be infinity or undefined, but 0.0 is a
        safe default that avoids representing undefined percentage).
        """
        baseline_hash, replay_hash = sample_matching_output_hashes

        comparison = ModelExecutionComparison(
            baseline_execution_id=TEST_BASELINE_ID,
            replay_execution_id=TEST_REPLAY_ID,
            input_hash=sample_input_hash,
            input_hash_match=True,
            baseline_output_hash=baseline_hash,
            replay_output_hash=replay_hash,
            output_match=True,
            baseline_latency_ms=100.0,
            replay_latency_ms=100.0,
            latency_delta_ms=0.0,
            latency_delta_percent=0.0,
            baseline_cost=0.0,  # Zero baseline (division by zero edge case)
            replay_cost=0.05,  # Non-zero replay
            cost_delta=0.05,  # replay - baseline = 0.05 - 0
            cost_delta_percent=0.0,  # Convention: 0% when baseline is 0
            baseline_invariant_results=[sample_invariant_result_passed],
            replay_invariant_results=[sample_invariant_result_passed],
            invariant_comparison=sample_no_regression_summary,
        )

        # Verify the model accepts zero baseline_cost
        assert comparison.baseline_cost == 0.0
        assert comparison.replay_cost == 0.05
        assert comparison.cost_delta == 0.05
        # Delta percent is 0.0 by convention when baseline is 0
        # (avoids division by zero in percent calculation)
        assert comparison.cost_delta_percent == 0.0

    def test_edge_cost_delta_when_both_costs_none(
        self,
        sample_input_hash: str,
        sample_matching_output_hashes: tuple[str, str],
        sample_no_regression_summary: ModelInvariantComparisonSummary,
        sample_invariant_result_passed: ModelInvariantResult,
    ) -> None:
        """Model accepts None for all cost fields when costs unavailable.

        When cost data is not available for either execution, all cost
        fields should be None, indicating no cost comparison is possible.
        """
        baseline_hash, replay_hash = sample_matching_output_hashes

        comparison = ModelExecutionComparison(
            baseline_execution_id=TEST_BASELINE_ID,
            replay_execution_id=TEST_REPLAY_ID,
            input_hash=sample_input_hash,
            input_hash_match=True,
            baseline_output_hash=baseline_hash,
            replay_output_hash=replay_hash,
            output_match=True,
            baseline_latency_ms=100.0,
            replay_latency_ms=100.0,
            latency_delta_ms=0.0,
            latency_delta_percent=0.0,
            baseline_cost=None,  # No cost data
            replay_cost=None,  # No cost data
            cost_delta=None,  # Cannot compute delta
            cost_delta_percent=None,  # Cannot compute percent
            baseline_invariant_results=[sample_invariant_result_passed],
            replay_invariant_results=[sample_invariant_result_passed],
            invariant_comparison=sample_no_regression_summary,
        )

        assert comparison.baseline_cost is None
        assert comparison.replay_cost is None
        assert comparison.cost_delta is None
        assert comparison.cost_delta_percent is None

    def test_edge_cost_delta_when_both_costs_zero(
        self,
        sample_input_hash: str,
        sample_matching_output_hashes: tuple[str, str],
        sample_no_regression_summary: ModelInvariantComparisonSummary,
        sample_invariant_result_passed: ModelInvariantResult,
    ) -> None:
        """Model accepts zero for both costs (e.g., free tier executions).

        When both executions have zero cost (e.g., free tier, cached responses),
        delta should be 0.0 and delta_percent should be 0.0 (no change).
        """
        baseline_hash, replay_hash = sample_matching_output_hashes

        comparison = ModelExecutionComparison(
            baseline_execution_id=TEST_BASELINE_ID,
            replay_execution_id=TEST_REPLAY_ID,
            input_hash=sample_input_hash,
            input_hash_match=True,
            baseline_output_hash=baseline_hash,
            replay_output_hash=replay_hash,
            output_match=True,
            baseline_latency_ms=100.0,
            replay_latency_ms=100.0,
            latency_delta_ms=0.0,
            latency_delta_percent=0.0,
            baseline_cost=0.0,  # Free execution
            replay_cost=0.0,  # Free execution
            cost_delta=0.0,  # No difference
            cost_delta_percent=0.0,  # 0% change (0/0 convention)
            baseline_invariant_results=[sample_invariant_result_passed],
            replay_invariant_results=[sample_invariant_result_passed],
            invariant_comparison=sample_no_regression_summary,
        )

        assert comparison.baseline_cost == 0.0
        assert comparison.replay_cost == 0.0
        assert comparison.cost_delta == 0.0
        assert comparison.cost_delta_percent == 0.0

    def test_edge_cost_delta_when_only_baseline_cost_provided(
        self,
        sample_input_hash: str,
        sample_matching_output_hashes: tuple[str, str],
        sample_no_regression_summary: ModelInvariantComparisonSummary,
        sample_invariant_result_passed: ModelInvariantResult,
    ) -> None:
        """Model accepts partial cost data (only baseline_cost available).

        When only baseline_cost is available (replay cost unknown),
        delta and delta_percent should typically be None since comparison
        is not meaningful.
        """
        baseline_hash, replay_hash = sample_matching_output_hashes

        comparison = ModelExecutionComparison(
            baseline_execution_id=TEST_BASELINE_ID,
            replay_execution_id=TEST_REPLAY_ID,
            input_hash=sample_input_hash,
            input_hash_match=True,
            baseline_output_hash=baseline_hash,
            replay_output_hash=replay_hash,
            output_match=True,
            baseline_latency_ms=100.0,
            replay_latency_ms=100.0,
            latency_delta_ms=0.0,
            latency_delta_percent=0.0,
            baseline_cost=0.10,  # Baseline cost known
            replay_cost=None,  # Replay cost unknown
            cost_delta=None,  # Cannot compute without replay_cost
            cost_delta_percent=None,  # Cannot compute percent
            baseline_invariant_results=[sample_invariant_result_passed],
            replay_invariant_results=[sample_invariant_result_passed],
            invariant_comparison=sample_no_regression_summary,
        )

        assert comparison.baseline_cost == 0.10
        assert comparison.replay_cost is None
        assert comparison.cost_delta is None
        assert comparison.cost_delta_percent is None

    def test_edge_cost_delta_when_only_replay_cost_provided(
        self,
        sample_input_hash: str,
        sample_matching_output_hashes: tuple[str, str],
        sample_no_regression_summary: ModelInvariantComparisonSummary,
        sample_invariant_result_passed: ModelInvariantResult,
    ) -> None:
        """Model accepts partial cost data (only replay_cost available).

        When only replay_cost is available (baseline cost unknown),
        delta and delta_percent should typically be None since comparison
        is not meaningful.
        """
        baseline_hash, replay_hash = sample_matching_output_hashes

        comparison = ModelExecutionComparison(
            baseline_execution_id=TEST_BASELINE_ID,
            replay_execution_id=TEST_REPLAY_ID,
            input_hash=sample_input_hash,
            input_hash_match=True,
            baseline_output_hash=baseline_hash,
            replay_output_hash=replay_hash,
            output_match=True,
            baseline_latency_ms=100.0,
            replay_latency_ms=100.0,
            latency_delta_ms=0.0,
            latency_delta_percent=0.0,
            baseline_cost=None,  # Baseline cost unknown
            replay_cost=0.08,  # Replay cost known
            cost_delta=None,  # Cannot compute without baseline_cost
            cost_delta_percent=None,  # Cannot compute percent
            baseline_invariant_results=[sample_invariant_result_passed],
            replay_invariant_results=[sample_invariant_result_passed],
            invariant_comparison=sample_no_regression_summary,
        )

        assert comparison.baseline_cost is None
        assert comparison.replay_cost == 0.08
        assert comparison.cost_delta is None
        assert comparison.cost_delta_percent is None

    def test_edge_cost_delta_negative_when_replay_cheaper(
        self,
        sample_input_hash: str,
        sample_matching_output_hashes: tuple[str, str],
        sample_no_regression_summary: ModelInvariantComparisonSummary,
        sample_invariant_result_passed: ModelInvariantResult,
    ) -> None:
        """Model accepts negative cost_delta when replay is cheaper.

        A negative cost_delta indicates a cost reduction (improvement).
        """
        baseline_hash, replay_hash = sample_matching_output_hashes

        comparison = ModelExecutionComparison(
            baseline_execution_id=TEST_BASELINE_ID,
            replay_execution_id=TEST_REPLAY_ID,
            input_hash=sample_input_hash,
            input_hash_match=True,
            baseline_output_hash=baseline_hash,
            replay_output_hash=replay_hash,
            output_match=True,
            baseline_latency_ms=100.0,
            replay_latency_ms=100.0,
            latency_delta_ms=0.0,
            latency_delta_percent=0.0,
            baseline_cost=0.10,  # Baseline cost
            replay_cost=0.06,  # Replay cheaper (40% reduction)
            cost_delta=-0.04,  # Negative = cost reduction
            cost_delta_percent=-40.0,  # Negative = improvement
            baseline_invariant_results=[sample_invariant_result_passed],
            replay_invariant_results=[sample_invariant_result_passed],
            invariant_comparison=sample_no_regression_summary,
        )

        assert comparison.baseline_cost == 0.10
        assert comparison.replay_cost == 0.06
        assert comparison.cost_delta == pytest.approx(-0.04)
        assert comparison.cost_delta_percent == pytest.approx(-40.0)
        # Negative delta = cost reduction (improvement)
        assert comparison.cost_delta < 0


@pytest.mark.unit
class TestModelExecutionComparisonInputHashMismatchEdgeCases:
    """Test edge cases for input hash mismatch handling.

    These tests verify that input_hash_match=False is properly handled
    and documents expected behavior for invalid comparison scenarios.
    """

    def test_edge_input_hash_mismatch_with_matching_outputs(
        self,
        sample_no_regression_summary: ModelInvariantComparisonSummary,
        sample_invariant_result_passed: ModelInvariantResult,
    ) -> None:
        """Input hash mismatch is flagged even when outputs match.

        This is an important edge case: outputs might coincidentally match
        even with different inputs, but the comparison is still invalid
        because we're comparing apples to oranges.
        """
        comparison = ModelExecutionComparison(
            baseline_execution_id=TEST_BASELINE_ID,
            replay_execution_id=TEST_REPLAY_ID,
            input_hash="sha256:input_hash_value_for_invalid_comparison_test_123",
            input_hash_match=False,  # CRITICAL: Inputs were different!
            baseline_output_hash="sha256:same_output_hash_coincidentally_matches_12345678",
            replay_output_hash="sha256:same_output_hash_coincidentally_matches_12345678",
            output_match=True,  # Outputs match, but comparison is invalid
            baseline_latency_ms=100.0,
            replay_latency_ms=100.0,
            latency_delta_ms=0.0,
            latency_delta_percent=0.0,
            baseline_invariant_results=[sample_invariant_result_passed],
            replay_invariant_results=[sample_invariant_result_passed],
            invariant_comparison=sample_no_regression_summary,
        )

        # Key assertion: input_hash_match is False, flagging invalid comparison
        assert comparison.input_hash_match is False
        # Even though outputs match, comparison is invalid due to input mismatch
        assert comparison.output_match is True

    def test_edge_input_hash_mismatch_with_different_outputs(
        self,
        sample_different_output_hashes: tuple[str, str],
        sample_output_diff: ModelOutputDiff,
        sample_regression_summary: ModelInvariantComparisonSummary,
        sample_invariant_result_passed: ModelInvariantResult,
        sample_invariant_result_failed: ModelInvariantResult,
    ) -> None:
        """Input hash mismatch with different outputs is clearly invalid.

        When inputs differ and outputs differ, the comparison is meaningless.
        The input_hash_match flag allows consumers to filter out such cases.
        """
        baseline_hash, replay_hash = sample_different_output_hashes

        comparison = ModelExecutionComparison(
            baseline_execution_id=TEST_BASELINE_ID,
            replay_execution_id=TEST_REPLAY_ID,
            input_hash="sha256:mismatched_input_hash_for_test_case_123456789",
            input_hash_match=False,  # Invalid comparison
            baseline_output_hash=baseline_hash,
            replay_output_hash=replay_hash,
            output_match=False,
            output_diff=sample_output_diff,
            baseline_latency_ms=100.0,
            replay_latency_ms=150.0,
            latency_delta_ms=50.0,
            latency_delta_percent=50.0,
            baseline_invariant_results=[sample_invariant_result_passed],
            replay_invariant_results=[sample_invariant_result_failed],
            invariant_comparison=sample_regression_summary,
        )

        # Both flags indicate problems, but input_hash_match is primary
        assert comparison.input_hash_match is False
        assert comparison.output_match is False
        # Output diff and regression are recorded but should be ignored
        # when input_hash_match is False
        assert comparison.output_diff is not None
        assert comparison.invariant_comparison.regression_detected is True

    def test_edge_input_hash_mismatch_documentation_pattern(
        self,
        sample_no_regression_summary: ModelInvariantComparisonSummary,
        sample_invariant_result_passed: ModelInvariantResult,
    ) -> None:
        """Document the expected consumer pattern for input hash mismatch.

        Consumers should ALWAYS check input_hash_match first before
        interpreting other comparison results. This test documents the
        recommended validation pattern.
        """
        comparison = ModelExecutionComparison(
            baseline_execution_id=TEST_BASELINE_ID,
            replay_execution_id=TEST_REPLAY_ID,
            input_hash="sha256:some_input_hash_value_that_differs_from_replay_1234",
            input_hash_match=False,
            baseline_output_hash="sha256:baseline_output_hash_123456789012345678901234",
            replay_output_hash="sha256:replay_output_hash_9876543210987654321098765",
            output_match=False,
            baseline_latency_ms=100.0,
            replay_latency_ms=200.0,
            latency_delta_ms=100.0,
            latency_delta_percent=100.0,
            baseline_invariant_results=[sample_invariant_result_passed],
            replay_invariant_results=[sample_invariant_result_passed],
            invariant_comparison=sample_no_regression_summary,
        )

        # Recommended consumer validation pattern:
        def is_valid_comparison(c: ModelExecutionComparison) -> bool:
            """Check if comparison is valid (same inputs were used)."""
            return c.input_hash_match is True

        # This comparison should be rejected
        assert is_valid_comparison(comparison) is False

        # If input_hash_match is False, other comparisons are meaningless
        # (output_match, latency_delta, invariant_comparison, etc.)


@pytest.mark.unit
class TestModelExecutionComparisonIdField:
    """Test comparison_id field generation and validation."""

    def test_comparison_id_is_uuid(
        self,
        minimal_comparison_data: dict[str, Any],
    ) -> None:
        """Generated comparison_id is a valid UUID."""
        comparison = ModelExecutionComparison(**minimal_comparison_data)

        # Should be a UUID instance
        assert isinstance(comparison.comparison_id, UUID)

    def test_accepts_custom_uuid(
        self,
        minimal_comparison_data: dict[str, Any],
    ) -> None:
        """Accepts custom UUID as comparison_id."""
        custom_id = UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")
        data = {
            **minimal_comparison_data,
            "comparison_id": custom_id,
        }
        comparison = ModelExecutionComparison(**data)

        assert comparison.comparison_id == custom_id


@pytest.mark.unit
class TestModelExecutionComparisonLatencyDeltaValidation:
    """Test latency delta validation in ModelExecutionComparison.

    These tests verify the model_validator that ensures latency delta
    fields are consistent with their source values (baseline and replay latencies).
    """

    def test_validation_accepts_consistent_latency_delta_ms(
        self,
        sample_input_hash: str,
        sample_matching_output_hashes: tuple[str, str],
        sample_no_regression_summary: ModelInvariantComparisonSummary,
        sample_invariant_result_passed: ModelInvariantResult,
    ) -> None:
        """Validator accepts correct latency_delta_ms calculation."""
        baseline_hash, replay_hash = sample_matching_output_hashes

        # Correct: delta = 180 - 150 = 30
        comparison = ModelExecutionComparison(
            baseline_execution_id=TEST_BASELINE_ID,
            replay_execution_id=TEST_REPLAY_ID,
            input_hash=sample_input_hash,
            input_hash_match=True,
            baseline_output_hash=baseline_hash,
            replay_output_hash=replay_hash,
            output_match=True,
            baseline_latency_ms=150.0,
            replay_latency_ms=180.0,
            latency_delta_ms=30.0,  # Correct: 180 - 150
            latency_delta_percent=20.0,  # Correct: (30 / 150) * 100
            baseline_invariant_results=[sample_invariant_result_passed],
            replay_invariant_results=[sample_invariant_result_passed],
            invariant_comparison=sample_no_regression_summary,
        )

        assert comparison.latency_delta_ms == 30.0
        assert comparison.latency_delta_percent == 20.0

    def test_validation_rejects_inconsistent_latency_delta_ms(
        self,
        sample_input_hash: str,
        sample_matching_output_hashes: tuple[str, str],
        sample_no_regression_summary: ModelInvariantComparisonSummary,
        sample_invariant_result_passed: ModelInvariantResult,
    ) -> None:
        """Validator rejects incorrect latency_delta_ms."""
        baseline_hash, replay_hash = sample_matching_output_hashes

        # Incorrect: delta should be 30 (180 - 150), not 50
        with pytest.raises(ValidationError) as exc_info:
            ModelExecutionComparison(
                baseline_execution_id=TEST_BASELINE_ID,
                replay_execution_id=TEST_REPLAY_ID,
                input_hash=sample_input_hash,
                input_hash_match=True,
                baseline_output_hash=baseline_hash,
                replay_output_hash=replay_hash,
                output_match=True,
                baseline_latency_ms=150.0,
                replay_latency_ms=180.0,
                latency_delta_ms=50.0,  # Wrong! Should be 30
                latency_delta_percent=20.0,
                baseline_invariant_results=[sample_invariant_result_passed],
                replay_invariant_results=[sample_invariant_result_passed],
                invariant_comparison=sample_no_regression_summary,
            )

        assert "latency_delta_ms is inconsistent" in str(exc_info.value)
        assert "got 50.0" in str(exc_info.value)
        assert "expected 30.0" in str(exc_info.value)

    def test_validation_rejects_inconsistent_latency_delta_percent(
        self,
        sample_input_hash: str,
        sample_matching_output_hashes: tuple[str, str],
        sample_no_regression_summary: ModelInvariantComparisonSummary,
        sample_invariant_result_passed: ModelInvariantResult,
    ) -> None:
        """Validator rejects incorrect latency_delta_percent."""
        baseline_hash, replay_hash = sample_matching_output_hashes

        # delta_ms is correct (30), but percent is wrong
        # Should be (30 / 150) * 100 = 20%, not 50%
        with pytest.raises(ValidationError) as exc_info:
            ModelExecutionComparison(
                baseline_execution_id=TEST_BASELINE_ID,
                replay_execution_id=TEST_REPLAY_ID,
                input_hash=sample_input_hash,
                input_hash_match=True,
                baseline_output_hash=baseline_hash,
                replay_output_hash=replay_hash,
                output_match=True,
                baseline_latency_ms=150.0,
                replay_latency_ms=180.0,
                latency_delta_ms=30.0,  # Correct
                latency_delta_percent=50.0,  # Wrong! Should be 20%
                baseline_invariant_results=[sample_invariant_result_passed],
                replay_invariant_results=[sample_invariant_result_passed],
                invariant_comparison=sample_no_regression_summary,
            )

        assert "latency_delta_percent is inconsistent" in str(exc_info.value)
        assert "got 50.0" in str(exc_info.value)
        assert "expected 20.00" in str(exc_info.value)

    def test_validation_accepts_zero_baseline_with_zero_percent(
        self,
        sample_input_hash: str,
        sample_matching_output_hashes: tuple[str, str],
        sample_no_regression_summary: ModelInvariantComparisonSummary,
        sample_invariant_result_passed: ModelInvariantResult,
    ) -> None:
        """Validator accepts 0.0 percent when baseline is 0 (convention)."""
        baseline_hash, replay_hash = sample_matching_output_hashes

        # When baseline is 0, delta_percent must be 0.0 (convention)
        comparison = ModelExecutionComparison(
            baseline_execution_id=TEST_BASELINE_ID,
            replay_execution_id=TEST_REPLAY_ID,
            input_hash=sample_input_hash,
            input_hash_match=True,
            baseline_output_hash=baseline_hash,
            replay_output_hash=replay_hash,
            output_match=True,
            baseline_latency_ms=0.0,
            replay_latency_ms=100.0,
            latency_delta_ms=100.0,  # Correct: 100 - 0
            latency_delta_percent=0.0,  # Convention: 0% when baseline is 0
            baseline_invariant_results=[sample_invariant_result_passed],
            replay_invariant_results=[sample_invariant_result_passed],
            invariant_comparison=sample_no_regression_summary,
        )

        assert comparison.baseline_latency_ms == 0.0
        assert comparison.latency_delta_percent == 0.0

    def test_validation_rejects_zero_baseline_with_nonzero_percent(
        self,
        sample_input_hash: str,
        sample_matching_output_hashes: tuple[str, str],
        sample_no_regression_summary: ModelInvariantComparisonSummary,
        sample_invariant_result_passed: ModelInvariantResult,
    ) -> None:
        """Validator rejects non-zero percent when baseline is 0."""
        baseline_hash, replay_hash = sample_matching_output_hashes

        # When baseline is 0, delta_percent must be 0.0 (not inf or any other value)
        with pytest.raises(ValidationError) as exc_info:
            ModelExecutionComparison(
                baseline_execution_id=TEST_BASELINE_ID,
                replay_execution_id=TEST_REPLAY_ID,
                input_hash=sample_input_hash,
                input_hash_match=True,
                baseline_output_hash=baseline_hash,
                replay_output_hash=replay_hash,
                output_match=True,
                baseline_latency_ms=0.0,
                replay_latency_ms=100.0,
                latency_delta_ms=100.0,  # Correct
                latency_delta_percent=100.0,  # Wrong! Must be 0.0 when baseline is 0
                baseline_invariant_results=[sample_invariant_result_passed],
                replay_invariant_results=[sample_invariant_result_passed],
                invariant_comparison=sample_no_regression_summary,
            )

        assert "latency_delta_percent must be 0.0 when baseline_latency_ms is 0" in str(
            exc_info.value
        )

    def test_validation_accepts_negative_delta_ms(
        self,
        sample_input_hash: str,
        sample_matching_output_hashes: tuple[str, str],
        sample_no_regression_summary: ModelInvariantComparisonSummary,
        sample_invariant_result_passed: ModelInvariantResult,
    ) -> None:
        """Validator accepts negative latency_delta_ms (replay faster)."""
        baseline_hash, replay_hash = sample_matching_output_hashes

        # Replay is faster: 80 - 100 = -20 (-20%)
        comparison = ModelExecutionComparison(
            baseline_execution_id=TEST_BASELINE_ID,
            replay_execution_id=TEST_REPLAY_ID,
            input_hash=sample_input_hash,
            input_hash_match=True,
            baseline_output_hash=baseline_hash,
            replay_output_hash=replay_hash,
            output_match=True,
            baseline_latency_ms=100.0,
            replay_latency_ms=80.0,
            latency_delta_ms=-20.0,  # Correct: 80 - 100
            latency_delta_percent=-20.0,  # Correct: (-20 / 100) * 100
            baseline_invariant_results=[sample_invariant_result_passed],
            replay_invariant_results=[sample_invariant_result_passed],
            invariant_comparison=sample_no_regression_summary,
        )

        assert comparison.latency_delta_ms == -20.0
        assert comparison.latency_delta_percent == -20.0

    def test_validation_tolerance_for_floating_point(
        self,
        sample_input_hash: str,
        sample_matching_output_hashes: tuple[str, str],
        sample_no_regression_summary: ModelInvariantComparisonSummary,
        sample_invariant_result_passed: ModelInvariantResult,
    ) -> None:
        """Validator allows small floating point tolerance (0.01)."""
        baseline_hash, replay_hash = sample_matching_output_hashes

        # Values within 0.01 tolerance should be accepted
        # Expected delta_ms = 30.0, expected percent = 20.0
        # Using 30.005 and 19.995 (within tolerance)
        comparison = ModelExecutionComparison(
            baseline_execution_id=TEST_BASELINE_ID,
            replay_execution_id=TEST_REPLAY_ID,
            input_hash=sample_input_hash,
            input_hash_match=True,
            baseline_output_hash=baseline_hash,
            replay_output_hash=replay_hash,
            output_match=True,
            baseline_latency_ms=150.0,
            replay_latency_ms=180.0,
            latency_delta_ms=30.005,  # Within 0.01 of 30.0
            latency_delta_percent=19.995,  # Within 0.01 of 20.0
            baseline_invariant_results=[sample_invariant_result_passed],
            replay_invariant_results=[sample_invariant_result_passed],
            invariant_comparison=sample_no_regression_summary,
        )

        assert comparison.latency_delta_ms == 30.005

    def test_validation_both_zero_latencies(
        self,
        sample_input_hash: str,
        sample_matching_output_hashes: tuple[str, str],
        sample_no_regression_summary: ModelInvariantComparisonSummary,
        sample_invariant_result_passed: ModelInvariantResult,
    ) -> None:
        """Validator accepts zero for all latency fields."""
        baseline_hash, replay_hash = sample_matching_output_hashes

        comparison = ModelExecutionComparison(
            baseline_execution_id=TEST_BASELINE_ID,
            replay_execution_id=TEST_REPLAY_ID,
            input_hash=sample_input_hash,
            input_hash_match=True,
            baseline_output_hash=baseline_hash,
            replay_output_hash=replay_hash,
            output_match=True,
            baseline_latency_ms=0.0,
            replay_latency_ms=0.0,
            latency_delta_ms=0.0,  # Correct: 0 - 0
            latency_delta_percent=0.0,  # Convention: 0% when baseline is 0
            baseline_invariant_results=[sample_invariant_result_passed],
            replay_invariant_results=[sample_invariant_result_passed],
            invariant_comparison=sample_no_regression_summary,
        )

        assert comparison.baseline_latency_ms == 0.0
        assert comparison.replay_latency_ms == 0.0
        assert comparison.latency_delta_ms == 0.0
        assert comparison.latency_delta_percent == 0.0


@pytest.mark.unit
class TestModelExecutionComparisonCostDeltaValidation:
    """Test cost delta validation in ModelExecutionComparison.

    These tests verify the model_validator that ensures cost delta
    fields are consistent with their source values (baseline and replay costs).

    Validation rules:
        - When both baseline_cost and replay_cost are provided:
            - cost_delta must match (replay_cost - baseline_cost) within tolerance
            - cost_delta_percent must match (cost_delta / baseline_cost) * 100
              when baseline_cost > 0
        - When baseline_cost is 0 and replay_cost is provided:
            - cost_delta_percent must be 0.0 (documented convention)
        - When either cost is None:
            - Both cost_delta and cost_delta_percent must be None
        - Partial cost data is allowed:
            - One cost provided with deltas as None is valid
    """

    def test_validation_accepts_consistent_cost_delta(
        self,
        sample_input_hash: str,
        sample_matching_output_hashes: tuple[str, str],
        sample_no_regression_summary: ModelInvariantComparisonSummary,
        sample_invariant_result_passed: ModelInvariantResult,
    ) -> None:
        """Validator accepts correct cost_delta calculation."""
        baseline_hash, replay_hash = sample_matching_output_hashes

        # Correct: delta = 0.08 - 0.05 = 0.03, percent = (0.03 / 0.05) * 100 = 60%
        comparison = ModelExecutionComparison(
            baseline_execution_id=TEST_BASELINE_ID,
            replay_execution_id=TEST_REPLAY_ID,
            input_hash=sample_input_hash,
            input_hash_match=True,
            baseline_output_hash=baseline_hash,
            replay_output_hash=replay_hash,
            output_match=True,
            baseline_latency_ms=100.0,
            replay_latency_ms=100.0,
            latency_delta_ms=0.0,
            latency_delta_percent=0.0,
            baseline_cost=0.05,
            replay_cost=0.08,
            cost_delta=0.03,  # Correct: 0.08 - 0.05
            cost_delta_percent=60.0,  # Correct: (0.03 / 0.05) * 100
            baseline_invariant_results=[sample_invariant_result_passed],
            replay_invariant_results=[sample_invariant_result_passed],
            invariant_comparison=sample_no_regression_summary,
        )

        assert comparison.cost_delta == pytest.approx(0.03)
        assert comparison.cost_delta_percent == pytest.approx(60.0)

    def test_validation_rejects_inconsistent_cost_delta(
        self,
        sample_input_hash: str,
        sample_matching_output_hashes: tuple[str, str],
        sample_no_regression_summary: ModelInvariantComparisonSummary,
        sample_invariant_result_passed: ModelInvariantResult,
    ) -> None:
        """Validator rejects incorrect cost_delta value."""
        baseline_hash, replay_hash = sample_matching_output_hashes

        # Incorrect: delta should be 0.03 (0.08 - 0.05), not 999.0
        with pytest.raises(ValidationError) as exc_info:
            ModelExecutionComparison(
                baseline_execution_id=TEST_BASELINE_ID,
                replay_execution_id=TEST_REPLAY_ID,
                input_hash=sample_input_hash,
                input_hash_match=True,
                baseline_output_hash=baseline_hash,
                replay_output_hash=replay_hash,
                output_match=True,
                baseline_latency_ms=100.0,
                replay_latency_ms=100.0,
                latency_delta_ms=0.0,
                latency_delta_percent=0.0,
                baseline_cost=0.05,
                replay_cost=0.08,
                cost_delta=999.0,  # Wrong! Should be 0.03
                cost_delta_percent=60.0,
                baseline_invariant_results=[sample_invariant_result_passed],
                replay_invariant_results=[sample_invariant_result_passed],
                invariant_comparison=sample_no_regression_summary,
            )

        assert "cost_delta is inconsistent" in str(exc_info.value)
        assert "got 999.0" in str(exc_info.value)

    def test_validation_rejects_inconsistent_cost_delta_percent(
        self,
        sample_input_hash: str,
        sample_matching_output_hashes: tuple[str, str],
        sample_no_regression_summary: ModelInvariantComparisonSummary,
        sample_invariant_result_passed: ModelInvariantResult,
    ) -> None:
        """Validator rejects incorrect cost_delta_percent value."""
        baseline_hash, replay_hash = sample_matching_output_hashes

        # cost_delta is correct (0.03), but percent is wrong
        # Should be (0.03 / 0.05) * 100 = 60%, not 50%
        with pytest.raises(ValidationError) as exc_info:
            ModelExecutionComparison(
                baseline_execution_id=TEST_BASELINE_ID,
                replay_execution_id=TEST_REPLAY_ID,
                input_hash=sample_input_hash,
                input_hash_match=True,
                baseline_output_hash=baseline_hash,
                replay_output_hash=replay_hash,
                output_match=True,
                baseline_latency_ms=100.0,
                replay_latency_ms=100.0,
                latency_delta_ms=0.0,
                latency_delta_percent=0.0,
                baseline_cost=0.05,
                replay_cost=0.08,
                cost_delta=0.03,  # Correct
                cost_delta_percent=50.0,  # Wrong! Should be 60%
                baseline_invariant_results=[sample_invariant_result_passed],
                replay_invariant_results=[sample_invariant_result_passed],
                invariant_comparison=sample_no_regression_summary,
            )

        assert "cost_delta_percent is inconsistent" in str(exc_info.value)
        assert "got 50.0" in str(exc_info.value)
        assert "expected 60.00" in str(exc_info.value)

    def test_validation_accepts_zero_baseline_cost_with_zero_percent(
        self,
        sample_input_hash: str,
        sample_matching_output_hashes: tuple[str, str],
        sample_no_regression_summary: ModelInvariantComparisonSummary,
        sample_invariant_result_passed: ModelInvariantResult,
    ) -> None:
        """Validator accepts 0.0 percent when baseline_cost is 0 (convention)."""
        baseline_hash, replay_hash = sample_matching_output_hashes

        # When baseline_cost is 0, cost_delta_percent must be 0.0 (convention)
        comparison = ModelExecutionComparison(
            baseline_execution_id=TEST_BASELINE_ID,
            replay_execution_id=TEST_REPLAY_ID,
            input_hash=sample_input_hash,
            input_hash_match=True,
            baseline_output_hash=baseline_hash,
            replay_output_hash=replay_hash,
            output_match=True,
            baseline_latency_ms=100.0,
            replay_latency_ms=100.0,
            latency_delta_ms=0.0,
            latency_delta_percent=0.0,
            baseline_cost=0.0,  # Zero baseline (division by zero edge case)
            replay_cost=0.05,
            cost_delta=0.05,  # Correct: 0.05 - 0
            cost_delta_percent=0.0,  # Convention: 0% when baseline is 0
            baseline_invariant_results=[sample_invariant_result_passed],
            replay_invariant_results=[sample_invariant_result_passed],
            invariant_comparison=sample_no_regression_summary,
        )

        assert comparison.baseline_cost == 0.0
        assert comparison.cost_delta_percent == 0.0

    def test_validation_rejects_zero_baseline_cost_with_nonzero_percent(
        self,
        sample_input_hash: str,
        sample_matching_output_hashes: tuple[str, str],
        sample_no_regression_summary: ModelInvariantComparisonSummary,
        sample_invariant_result_passed: ModelInvariantResult,
    ) -> None:
        """Validator rejects non-zero percent when baseline_cost is 0."""
        baseline_hash, replay_hash = sample_matching_output_hashes

        # When baseline_cost is 0, cost_delta_percent must be 0.0
        with pytest.raises(ValidationError) as exc_info:
            ModelExecutionComparison(
                baseline_execution_id=TEST_BASELINE_ID,
                replay_execution_id=TEST_REPLAY_ID,
                input_hash=sample_input_hash,
                input_hash_match=True,
                baseline_output_hash=baseline_hash,
                replay_output_hash=replay_hash,
                output_match=True,
                baseline_latency_ms=100.0,
                replay_latency_ms=100.0,
                latency_delta_ms=0.0,
                latency_delta_percent=0.0,
                baseline_cost=0.0,
                replay_cost=0.05,
                cost_delta=0.05,  # Correct
                cost_delta_percent=100.0,  # Wrong! Must be 0.0 when baseline is 0
                baseline_invariant_results=[sample_invariant_result_passed],
                replay_invariant_results=[sample_invariant_result_passed],
                invariant_comparison=sample_no_regression_summary,
            )

        assert "cost_delta_percent must be 0.0 when baseline_cost is 0" in str(
            exc_info.value
        )

    def test_validation_rejects_cost_delta_when_both_costs_none(
        self,
        sample_input_hash: str,
        sample_matching_output_hashes: tuple[str, str],
        sample_no_regression_summary: ModelInvariantComparisonSummary,
        sample_invariant_result_passed: ModelInvariantResult,
    ) -> None:
        """Validator rejects cost_delta when both costs are None."""
        baseline_hash, replay_hash = sample_matching_output_hashes

        # cost_delta should be None when both costs are None
        with pytest.raises(ValidationError) as exc_info:
            ModelExecutionComparison(
                baseline_execution_id=TEST_BASELINE_ID,
                replay_execution_id=TEST_REPLAY_ID,
                input_hash=sample_input_hash,
                input_hash_match=True,
                baseline_output_hash=baseline_hash,
                replay_output_hash=replay_hash,
                output_match=True,
                baseline_latency_ms=100.0,
                replay_latency_ms=100.0,
                latency_delta_ms=0.0,
                latency_delta_percent=0.0,
                baseline_cost=None,
                replay_cost=None,
                cost_delta=0.05,  # Wrong! Should be None when both costs are None
                cost_delta_percent=None,
                baseline_invariant_results=[sample_invariant_result_passed],
                replay_invariant_results=[sample_invariant_result_passed],
                invariant_comparison=sample_no_regression_summary,
            )

        assert (
            "cost_delta must be None when both baseline_cost and replay_cost are None"
            in str(exc_info.value)
        )

    def test_validation_rejects_cost_delta_percent_when_both_costs_none(
        self,
        sample_input_hash: str,
        sample_matching_output_hashes: tuple[str, str],
        sample_no_regression_summary: ModelInvariantComparisonSummary,
        sample_invariant_result_passed: ModelInvariantResult,
    ) -> None:
        """Validator rejects cost_delta_percent when both costs are None."""
        baseline_hash, replay_hash = sample_matching_output_hashes

        with pytest.raises(ValidationError) as exc_info:
            ModelExecutionComparison(
                baseline_execution_id=TEST_BASELINE_ID,
                replay_execution_id=TEST_REPLAY_ID,
                input_hash=sample_input_hash,
                input_hash_match=True,
                baseline_output_hash=baseline_hash,
                replay_output_hash=replay_hash,
                output_match=True,
                baseline_latency_ms=100.0,
                replay_latency_ms=100.0,
                latency_delta_ms=0.0,
                latency_delta_percent=0.0,
                baseline_cost=None,
                replay_cost=None,
                cost_delta=None,
                cost_delta_percent=50.0,  # Wrong! Should be None when both costs are None
                baseline_invariant_results=[sample_invariant_result_passed],
                replay_invariant_results=[sample_invariant_result_passed],
                invariant_comparison=sample_no_regression_summary,
            )

        assert (
            "cost_delta_percent must be None when both baseline_cost and replay_cost are None"
            in str(exc_info.value)
        )

    def test_validation_rejects_cost_delta_when_partial_data_baseline_only(
        self,
        sample_input_hash: str,
        sample_matching_output_hashes: tuple[str, str],
        sample_no_regression_summary: ModelInvariantComparisonSummary,
        sample_invariant_result_passed: ModelInvariantResult,
    ) -> None:
        """Validator rejects cost_delta when only baseline_cost is provided."""
        baseline_hash, replay_hash = sample_matching_output_hashes

        with pytest.raises(ValidationError) as exc_info:
            ModelExecutionComparison(
                baseline_execution_id=TEST_BASELINE_ID,
                replay_execution_id=TEST_REPLAY_ID,
                input_hash=sample_input_hash,
                input_hash_match=True,
                baseline_output_hash=baseline_hash,
                replay_output_hash=replay_hash,
                output_match=True,
                baseline_latency_ms=100.0,
                replay_latency_ms=100.0,
                latency_delta_ms=0.0,
                latency_delta_percent=0.0,
                baseline_cost=0.10,  # Baseline provided
                replay_cost=None,  # Replay missing
                cost_delta=0.05,  # Wrong! Should be None with partial data
                cost_delta_percent=None,
                baseline_invariant_results=[sample_invariant_result_passed],
                replay_invariant_results=[sample_invariant_result_passed],
                invariant_comparison=sample_no_regression_summary,
            )

        assert "cost_delta must be None when cost data is partial" in str(
            exc_info.value
        )

    def test_validation_rejects_cost_delta_when_partial_data_replay_only(
        self,
        sample_input_hash: str,
        sample_matching_output_hashes: tuple[str, str],
        sample_no_regression_summary: ModelInvariantComparisonSummary,
        sample_invariant_result_passed: ModelInvariantResult,
    ) -> None:
        """Validator rejects cost_delta when only replay_cost is provided."""
        baseline_hash, replay_hash = sample_matching_output_hashes

        with pytest.raises(ValidationError) as exc_info:
            ModelExecutionComparison(
                baseline_execution_id=TEST_BASELINE_ID,
                replay_execution_id=TEST_REPLAY_ID,
                input_hash=sample_input_hash,
                input_hash_match=True,
                baseline_output_hash=baseline_hash,
                replay_output_hash=replay_hash,
                output_match=True,
                baseline_latency_ms=100.0,
                replay_latency_ms=100.0,
                latency_delta_ms=0.0,
                latency_delta_percent=0.0,
                baseline_cost=None,  # Baseline missing
                replay_cost=0.08,  # Replay provided
                cost_delta=0.08,  # Wrong! Should be None with partial data
                cost_delta_percent=None,
                baseline_invariant_results=[sample_invariant_result_passed],
                replay_invariant_results=[sample_invariant_result_passed],
                invariant_comparison=sample_no_regression_summary,
            )

        assert "cost_delta must be None when cost data is partial" in str(
            exc_info.value
        )

    def test_validation_accepts_partial_data_with_none_deltas(
        self,
        sample_input_hash: str,
        sample_matching_output_hashes: tuple[str, str],
        sample_no_regression_summary: ModelInvariantComparisonSummary,
        sample_invariant_result_passed: ModelInvariantResult,
    ) -> None:
        """Validator accepts partial cost data when deltas are None."""
        baseline_hash, replay_hash = sample_matching_output_hashes

        # Partial data is valid when deltas are None
        comparison = ModelExecutionComparison(
            baseline_execution_id=TEST_BASELINE_ID,
            replay_execution_id=TEST_REPLAY_ID,
            input_hash=sample_input_hash,
            input_hash_match=True,
            baseline_output_hash=baseline_hash,
            replay_output_hash=replay_hash,
            output_match=True,
            baseline_latency_ms=100.0,
            replay_latency_ms=100.0,
            latency_delta_ms=0.0,
            latency_delta_percent=0.0,
            baseline_cost=0.10,  # Baseline known
            replay_cost=None,  # Replay unknown
            cost_delta=None,  # Correctly None for partial data
            cost_delta_percent=None,  # Correctly None for partial data
            baseline_invariant_results=[sample_invariant_result_passed],
            replay_invariant_results=[sample_invariant_result_passed],
            invariant_comparison=sample_no_regression_summary,
        )

        assert comparison.baseline_cost == 0.10
        assert comparison.replay_cost is None
        assert comparison.cost_delta is None
        assert comparison.cost_delta_percent is None

    def test_validation_accepts_both_costs_with_none_deltas(
        self,
        sample_input_hash: str,
        sample_matching_output_hashes: tuple[str, str],
        sample_no_regression_summary: ModelInvariantComparisonSummary,
        sample_invariant_result_passed: ModelInvariantResult,
    ) -> None:
        """Validator accepts both costs with None deltas (not computed)."""
        baseline_hash, replay_hash = sample_matching_output_hashes

        # Both costs provided but deltas not computed is valid
        comparison = ModelExecutionComparison(
            baseline_execution_id=TEST_BASELINE_ID,
            replay_execution_id=TEST_REPLAY_ID,
            input_hash=sample_input_hash,
            input_hash_match=True,
            baseline_output_hash=baseline_hash,
            replay_output_hash=replay_hash,
            output_match=True,
            baseline_latency_ms=100.0,
            replay_latency_ms=100.0,
            latency_delta_ms=0.0,
            latency_delta_percent=0.0,
            baseline_cost=0.05,
            replay_cost=0.08,
            cost_delta=None,  # Not computed
            cost_delta_percent=None,  # Not computed
            baseline_invariant_results=[sample_invariant_result_passed],
            replay_invariant_results=[sample_invariant_result_passed],
            invariant_comparison=sample_no_regression_summary,
        )

        assert comparison.baseline_cost == 0.05
        assert comparison.replay_cost == 0.08
        assert comparison.cost_delta is None
        assert comparison.cost_delta_percent is None

    def test_validation_accepts_negative_cost_delta_when_replay_cheaper(
        self,
        sample_input_hash: str,
        sample_matching_output_hashes: tuple[str, str],
        sample_no_regression_summary: ModelInvariantComparisonSummary,
        sample_invariant_result_passed: ModelInvariantResult,
    ) -> None:
        """Validator accepts negative cost_delta when replay is cheaper."""
        baseline_hash, replay_hash = sample_matching_output_hashes

        # Replay is cheaper: 0.06 - 0.10 = -0.04 (-40%)
        comparison = ModelExecutionComparison(
            baseline_execution_id=TEST_BASELINE_ID,
            replay_execution_id=TEST_REPLAY_ID,
            input_hash=sample_input_hash,
            input_hash_match=True,
            baseline_output_hash=baseline_hash,
            replay_output_hash=replay_hash,
            output_match=True,
            baseline_latency_ms=100.0,
            replay_latency_ms=100.0,
            latency_delta_ms=0.0,
            latency_delta_percent=0.0,
            baseline_cost=0.10,
            replay_cost=0.06,  # Cheaper
            cost_delta=-0.04,  # Correct: 0.06 - 0.10
            cost_delta_percent=-40.0,  # Correct: (-0.04 / 0.10) * 100
            baseline_invariant_results=[sample_invariant_result_passed],
            replay_invariant_results=[sample_invariant_result_passed],
            invariant_comparison=sample_no_regression_summary,
        )

        assert comparison.cost_delta == pytest.approx(-0.04)
        assert comparison.cost_delta_percent == pytest.approx(-40.0)

    def test_validation_tolerance_for_cost_floating_point(
        self,
        sample_input_hash: str,
        sample_matching_output_hashes: tuple[str, str],
        sample_no_regression_summary: ModelInvariantComparisonSummary,
        sample_invariant_result_passed: ModelInvariantResult,
    ) -> None:
        """Validator allows small floating point tolerance (0.001) for cost fields."""
        baseline_hash, replay_hash = sample_matching_output_hashes

        # Values within 0.001 tolerance should be accepted
        # Expected delta = 0.03, expected percent = 60.0
        # Using 0.0305 (within 0.001 of 0.03) and 60.999 (within 0.001 of 61.0)
        # Note: 0.0305/0.05*100 = 61.0, so we use 60.999 which is within tolerance
        comparison = ModelExecutionComparison(
            baseline_execution_id=TEST_BASELINE_ID,
            replay_execution_id=TEST_REPLAY_ID,
            input_hash=sample_input_hash,
            input_hash_match=True,
            baseline_output_hash=baseline_hash,
            replay_output_hash=replay_hash,
            output_match=True,
            baseline_latency_ms=100.0,
            replay_latency_ms=100.0,
            latency_delta_ms=0.0,
            latency_delta_percent=0.0,
            baseline_cost=0.05,
            replay_cost=0.08,
            cost_delta=0.0305,  # Within 0.001 of expected 0.03
            cost_delta_percent=60.999,  # Within 0.001 of expected 61.0 for 0.0305/0.05*100
            baseline_invariant_results=[sample_invariant_result_passed],
            replay_invariant_results=[sample_invariant_result_passed],
            invariant_comparison=sample_no_regression_summary,
        )

        assert comparison.cost_delta == pytest.approx(0.0305)

    def test_validation_accepts_both_costs_zero(
        self,
        sample_input_hash: str,
        sample_matching_output_hashes: tuple[str, str],
        sample_no_regression_summary: ModelInvariantComparisonSummary,
        sample_invariant_result_passed: ModelInvariantResult,
    ) -> None:
        """Validator accepts zero for both costs with zero deltas."""
        baseline_hash, replay_hash = sample_matching_output_hashes

        # Both zero (e.g., free tier executions)
        comparison = ModelExecutionComparison(
            baseline_execution_id=TEST_BASELINE_ID,
            replay_execution_id=TEST_REPLAY_ID,
            input_hash=sample_input_hash,
            input_hash_match=True,
            baseline_output_hash=baseline_hash,
            replay_output_hash=replay_hash,
            output_match=True,
            baseline_latency_ms=100.0,
            replay_latency_ms=100.0,
            latency_delta_ms=0.0,
            latency_delta_percent=0.0,
            baseline_cost=0.0,
            replay_cost=0.0,
            cost_delta=0.0,  # Correct: 0 - 0
            cost_delta_percent=0.0,  # Convention: 0% when baseline is 0
            baseline_invariant_results=[sample_invariant_result_passed],
            replay_invariant_results=[sample_invariant_result_passed],
            invariant_comparison=sample_no_regression_summary,
        )

        assert comparison.baseline_cost == 0.0
        assert comparison.replay_cost == 0.0
        assert comparison.cost_delta == 0.0
        assert comparison.cost_delta_percent == 0.0

    def test_validation_accepts_cost_delta_percent_only_with_consistent_value(
        self,
        sample_input_hash: str,
        sample_matching_output_hashes: tuple[str, str],
        sample_no_regression_summary: ModelInvariantComparisonSummary,
        sample_invariant_result_passed: ModelInvariantResult,
    ) -> None:
        """Validator accepts cost_delta_percent when cost_delta is None.

        When cost_delta is None but cost_delta_percent is provided,
        the validator computes the expected delta from source costs
        and uses that to validate the percent.
        """
        baseline_hash, replay_hash = sample_matching_output_hashes

        # cost_delta is None but percent is computed from source costs
        comparison = ModelExecutionComparison(
            baseline_execution_id=TEST_BASELINE_ID,
            replay_execution_id=TEST_REPLAY_ID,
            input_hash=sample_input_hash,
            input_hash_match=True,
            baseline_output_hash=baseline_hash,
            replay_output_hash=replay_hash,
            output_match=True,
            baseline_latency_ms=100.0,
            replay_latency_ms=100.0,
            latency_delta_ms=0.0,
            latency_delta_percent=0.0,
            baseline_cost=0.05,
            replay_cost=0.08,
            cost_delta=None,  # Not provided
            cost_delta_percent=60.0,  # Correct: ((0.08 - 0.05) / 0.05) * 100
            baseline_invariant_results=[sample_invariant_result_passed],
            replay_invariant_results=[sample_invariant_result_passed],
            invariant_comparison=sample_no_regression_summary,
        )

        assert comparison.cost_delta is None
        assert comparison.cost_delta_percent == pytest.approx(60.0)

    def test_validation_rejects_example_from_task(
        self,
        sample_input_hash: str,
        sample_matching_output_hashes: tuple[str, str],
        sample_no_regression_summary: ModelInvariantComparisonSummary,
        sample_invariant_result_passed: ModelInvariantResult,
    ) -> None:
        """Validator rejects the exact inconsistent example from the task description.

        This test documents that the example from the task description is now
        correctly rejected by the validator:
            ModelExecutionComparison(
                baseline_cost=0.05,
                replay_cost=0.08,
                cost_delta=999.0,  # Wrong! Should be 0.03
                cost_delta_percent=50.0,  # Wrong! Should be 60.0
            )
        """
        baseline_hash, replay_hash = sample_matching_output_hashes

        # This was the exact problematic example from the task
        with pytest.raises(ValidationError) as exc_info:
            ModelExecutionComparison(
                baseline_execution_id=TEST_BASELINE_ID,
                replay_execution_id=TEST_REPLAY_ID,
                input_hash=sample_input_hash,
                input_hash_match=True,
                baseline_output_hash=baseline_hash,
                replay_output_hash=replay_hash,
                output_match=True,
                baseline_latency_ms=100.0,
                replay_latency_ms=100.0,
                latency_delta_ms=0.0,
                latency_delta_percent=0.0,
                baseline_cost=0.05,
                replay_cost=0.08,
                cost_delta=999.0,  # Wrong! Should be 0.03
                cost_delta_percent=50.0,  # Wrong! Should be 60.0
                baseline_invariant_results=[sample_invariant_result_passed],
                replay_invariant_results=[sample_invariant_result_passed],
                invariant_comparison=sample_no_regression_summary,
            )

        # The cost_delta validation should trigger first
        assert "cost_delta is inconsistent" in str(exc_info.value)
