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
        regression_detected=False,
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
        regression_detected=True,
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
            has_differences=True,
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
            has_differences=True,
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
            output_diff=ModelOutputDiff(has_differences=True),
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
