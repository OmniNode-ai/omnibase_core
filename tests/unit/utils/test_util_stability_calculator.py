# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for stability calculator utility.

This module tests the stability calculation functions that determine system health
based on invariant pass rates, error rates, latency metrics, and corpus size.

Test Coverage:
    - TestStabilityDetection: Core stability detection logic
    - TestStabilityEdgeCases: Edge cases and error handling
    - TestConfidenceCalculation: Confidence level calculation
    - TestConfidenceInputValidation: Input validation for confidence function

Design Rationale:
    The tests verify the weighted multi-factor approach to stability assessment:

    - Invariants (40%): Correctness checks are most critical
    - Error Rate (30%): Production error rates impact user experience
    - Latency Consistency (20%): Predictable response times indicate health
    - Corpus Size (10%): Statistical significance of the assessment

    Key invariant: Any failing invariant immediately results in "unstable" status,
    regardless of other metrics. This fail-fast behavior ensures correctness
    is never sacrificed for performance.
"""

from uuid import uuid4

import pytest
from pydantic import ValidationError

pytestmark = pytest.mark.unit

from omnibase_core.errors import ModelOnexError
from omnibase_core.models.health.model_invariant_status import ModelInvariantStatus
from omnibase_core.models.health.model_performance_metrics import (
    ModelPerformanceMetrics,
)
from omnibase_core.utils.util_stability_calculator import (
    DEFAULT_STABLE_THRESHOLD,
    calculate_confidence,
    calculate_stability,
)

# Test constants for magic number clarity
MINIMUM_CONFIDENCE_THRESHOLD = 0.8
BOUNDARY_CORPUS_SIZE = 50

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def all_passing_invariants() -> list[ModelInvariantStatus]:
    """Create a list of all passing invariants."""
    return [
        ModelInvariantStatus(
            invariant_id=uuid4(),
            name=f"invariant_{i}",
            passed=True,
        )
        for i in range(5)
    ]


@pytest.fixture
def one_failing_invariant() -> list[ModelInvariantStatus]:
    """Create a list with one failing invariant."""
    invariants = [
        ModelInvariantStatus(
            invariant_id=uuid4(),
            name=f"invariant_{i}",
            passed=True,
        )
        for i in range(4)
    ]
    invariants.append(
        ModelInvariantStatus(
            invariant_id=uuid4(),
            name="failing_invariant",
            passed=False,
            details="This invariant failed",
        )
    )
    return invariants


@pytest.fixture
def healthy_metrics() -> ModelPerformanceMetrics:
    """Create healthy performance metrics."""
    return ModelPerformanceMetrics(
        avg_latency_ms=100.0,
        p95_latency_ms=150.0,
        p99_latency_ms=200.0,  # 2x avg = acceptable
        avg_cost_per_call=0.002,
        total_calls=10000,
        error_rate=0.005,  # 0.5% error rate
    )


@pytest.fixture
def high_error_metrics() -> ModelPerformanceMetrics:
    """Create metrics with high error rate (>7%)."""
    return ModelPerformanceMetrics(
        avg_latency_ms=100.0,
        p95_latency_ms=150.0,
        p99_latency_ms=200.0,
        avg_cost_per_call=0.002,
        total_calls=10000,
        error_rate=0.08,  # 8% error rate - pushes score below stable threshold
    )


@pytest.fixture
def inconsistent_latency_metrics() -> ModelPerformanceMetrics:
    """Create metrics with inconsistent latency (high variance)."""
    return ModelPerformanceMetrics(
        avg_latency_ms=100.0,
        p95_latency_ms=400.0,
        p99_latency_ms=600.0,  # 6x avg = very inconsistent
        avg_cost_per_call=0.002,
        total_calls=10000,
        error_rate=0.01,
    )


# ============================================================================
# Phase 2: Stability Detection Tests
# ============================================================================


class TestStabilityDetection:
    """Test stability detection logic in calculate_stability."""

    def test_stable_requires_all_invariants_passing(
        self,
        one_failing_invariant: list[ModelInvariantStatus],
        healthy_metrics: ModelPerformanceMetrics,
    ) -> None:
        """Cannot be stable with failing invariants."""
        _score, status, details = calculate_stability(
            invariants=one_failing_invariant,
            metrics=healthy_metrics,
            corpus_size=1000,
        )

        # Even with healthy metrics, failing invariant means unstable
        assert status == "unstable"
        assert "invariants" in details.lower()

    def test_stable_requires_low_error_rate(
        self,
        all_passing_invariants: list[ModelInvariantStatus],
        high_error_metrics: ModelPerformanceMetrics,
    ) -> None:
        """Error rate must be low for stable status."""
        score, status, _details = calculate_stability(
            invariants=all_passing_invariants,
            metrics=high_error_metrics,
            corpus_size=1000,
        )

        # High error rate should reduce score
        # With 8% error rate, error_score = 1 - (0.08 * 10) = 0.2
        # Weighted contribution: 0.2 * 0.3 = 0.06
        # Total: 0.4 (invariants) + 0.06 (errors) + 0.16 (latency) + 0.1 (corpus) = 0.72
        assert score < DEFAULT_STABLE_THRESHOLD
        assert status in ("degraded", "unstable")

    def test_degraded_when_metrics_inconsistent(
        self,
        all_passing_invariants: list[ModelInvariantStatus],
        inconsistent_latency_metrics: ModelPerformanceMetrics,
    ) -> None:
        """High variance in metrics = degraded status."""
        score, status, _details = calculate_stability(
            invariants=all_passing_invariants,
            metrics=inconsistent_latency_metrics,
            corpus_size=1000,
        )

        # Inconsistent latency (6x ratio) should give latency_score = 0
        # This reduces overall score
        assert score < DEFAULT_STABLE_THRESHOLD
        assert status in ("degraded", "unstable")

    def test_unstable_when_corpus_too_small(
        self,
        all_passing_invariants: list[ModelInvariantStatus],
        healthy_metrics: ModelPerformanceMetrics,
    ) -> None:
        """Small corpus (< 100 samples) affects stability score."""
        small_corpus = 50  # Below minimum

        score, _status, details = calculate_stability(
            invariants=all_passing_invariants,
            metrics=healthy_metrics,
            corpus_size=small_corpus,
        )

        # Small corpus affects the corpus factor (10% weight)
        # corpus_score = 50/1000 = 0.05
        # This reduces overall score, but may still be stable with other good factors
        assert "corpus" in details.lower()
        # Score should be lower than with full corpus
        full_score, _, _ = calculate_stability(
            invariants=all_passing_invariants,
            metrics=healthy_metrics,
            corpus_size=1000,
        )
        assert score < full_score

    def test_stability_score_calculation(
        self,
        all_passing_invariants: list[ModelInvariantStatus],
        healthy_metrics: ModelPerformanceMetrics,
    ) -> None:
        """Stability score combines all factors correctly."""
        score, status, details = calculate_stability(
            invariants=all_passing_invariants,
            metrics=healthy_metrics,
            corpus_size=1000,
        )

        # With all factors healthy:
        # - invariants: 1.0 * 0.4 = 0.4
        # - errors (0.5% rate): (1 - 0.05) * 0.3 = 0.285
        # - latency (2x ratio): (1 - (2-1)/5) * 0.2 = 0.16
        # - corpus (1000): 1.0 * 0.1 = 0.1
        # Total: ~0.945

        assert 0.8 <= score <= 1.0
        assert status == "stable"

        # Details should contain breakdown
        assert "invariants" in details.lower()
        assert "errors" in details.lower()
        assert "latency" in details.lower()
        assert "corpus" in details.lower()


class TestStabilityEdgeCases:
    """Test edge cases in stability calculation."""

    def test_empty_invariants_raises_error(
        self,
        healthy_metrics: ModelPerformanceMetrics,
    ) -> None:
        """Empty invariants list should raise ModelOnexError."""
        with pytest.raises(ModelOnexError, match="cannot be empty"):
            calculate_stability(
                invariants=[],
                metrics=healthy_metrics,
                corpus_size=1000,
            )

    def test_zero_latency_raises_error(
        self,
        all_passing_invariants: list[ModelInvariantStatus],
    ) -> None:
        """Zero average latency should raise ModelOnexError."""
        zero_latency_metrics = ModelPerformanceMetrics(
            avg_latency_ms=0.0,  # This would cause division by zero
            p95_latency_ms=0.0,
            p99_latency_ms=0.0,
            avg_cost_per_call=0.0,
            total_calls=0,
            error_rate=0.0,
        )

        with pytest.raises(ModelOnexError, match="must be greater than 0"):
            calculate_stability(
                invariants=all_passing_invariants,
                metrics=zero_latency_metrics,
                corpus_size=1000,
            )

    def test_configurable_thresholds(
        self,
        all_passing_invariants: list[ModelInvariantStatus],
        healthy_metrics: ModelPerformanceMetrics,
    ) -> None:
        """Thresholds should be configurable."""
        # With very high stable threshold, even healthy system is degraded
        _score, status, _ = calculate_stability(
            invariants=all_passing_invariants,
            metrics=healthy_metrics,
            corpus_size=1000,
            stable_threshold=0.99,  # Very high threshold
        )

        assert status in ("degraded", "unstable")

        # With very low thresholds, even marginal system is stable
        _score2, status2, _ = calculate_stability(
            invariants=all_passing_invariants,
            metrics=healthy_metrics,
            corpus_size=100,  # Small corpus
            stable_threshold=0.5,  # Low threshold
        )

        assert status2 == "stable"


class TestConfidenceCalculation:
    """Test confidence level calculation."""

    def test_high_confidence_with_large_diverse_corpus(self) -> None:
        """Large corpus with high diversity = high confidence."""
        confidence, reasoning = calculate_confidence(
            corpus_size=2000,
            input_diversity_score=0.9,
            invariant_count=15,
        )

        assert confidence >= MINIMUM_CONFIDENCE_THRESHOLD
        assert "adequate" in reasoning.lower() or "corpus" in reasoning.lower()

    def test_low_confidence_with_small_corpus(self) -> None:
        """Small corpus = low confidence."""
        confidence, reasoning = calculate_confidence(
            corpus_size=BOUNDARY_CORPUS_SIZE,
            input_diversity_score=0.9,
            invariant_count=15,
        )

        assert confidence < MINIMUM_CONFIDENCE_THRESHOLD
        assert "below minimum" in reasoning.lower() or "corpus" in reasoning.lower()

    def test_low_confidence_with_low_diversity(self) -> None:
        """Low input diversity = lower confidence."""
        high_diversity_conf, _ = calculate_confidence(
            corpus_size=1000,
            input_diversity_score=0.9,
            invariant_count=10,
        )

        low_diversity_conf, reasoning = calculate_confidence(
            corpus_size=1000,
            input_diversity_score=0.2,
            invariant_count=10,
        )

        assert low_diversity_conf < high_diversity_conf
        assert "diversity" in reasoning.lower()

    def test_few_invariants_noted_in_reasoning(self) -> None:
        """Few invariants should be noted in reasoning."""
        _confidence, reasoning = calculate_confidence(
            corpus_size=1000,
            input_diversity_score=0.8,
            invariant_count=2,
        )

        assert "invariant" in reasoning.lower()

    def test_confidence_increases_monotonically_with_corpus_size(self) -> None:
        """Verify confidence increases monotonically as corpus size grows."""
        # Test with fixed diversity and invariant count
        fixed_diversity = 0.8
        fixed_invariants = 10

        # Sample corpus sizes from 0 to 2000
        corpus_sizes = [0, 50, 100, 200, 500, 1000, 1500, 2000]
        confidences: list[float] = []

        for size in corpus_sizes:
            confidence, _ = calculate_confidence(
                corpus_size=size,
                input_diversity_score=fixed_diversity,
                invariant_count=fixed_invariants,
            )
            confidences.append(confidence)

        # Verify monotonically increasing (each value >= previous)
        for i in range(1, len(confidences)):
            assert confidences[i] >= confidences[i - 1], (
                f"Confidence should increase monotonically: "
                f"size {corpus_sizes[i - 1]}={confidences[i - 1]:.4f} > "
                f"size {corpus_sizes[i]}={confidences[i]:.4f}"
            )


class TestConfidenceInputValidation:
    """Test input validation in calculate_confidence."""

    def test_negative_corpus_size_raises_error(self) -> None:
        """Negative corpus_size should raise ModelOnexError."""
        with pytest.raises(ModelOnexError, match="corpus_size must be non-negative"):
            calculate_confidence(
                corpus_size=-1,
                input_diversity_score=0.5,
                invariant_count=10,
            )

    def test_diversity_score_below_zero_raises_error(self) -> None:
        """input_diversity_score below 0.0 should raise ModelOnexError."""
        with pytest.raises(
            ModelOnexError, match=r"input_diversity_score must be between 0\.0 and 1\.0"
        ):
            calculate_confidence(
                corpus_size=100,
                input_diversity_score=-0.1,
                invariant_count=10,
            )

    def test_diversity_score_above_one_raises_error(self) -> None:
        """input_diversity_score above 1.0 should raise ModelOnexError."""
        with pytest.raises(
            ModelOnexError, match=r"input_diversity_score must be between 0\.0 and 1\.0"
        ):
            calculate_confidence(
                corpus_size=100,
                input_diversity_score=1.5,
                invariant_count=10,
            )

    def test_negative_invariant_count_raises_error(self) -> None:
        """Negative invariant_count should raise ModelOnexError."""
        with pytest.raises(
            ModelOnexError, match="invariant_count must be non-negative"
        ):
            calculate_confidence(
                corpus_size=100,
                input_diversity_score=0.5,
                invariant_count=-5,
            )

    def test_boundary_values_are_valid(self) -> None:
        """Boundary values (0 corpus, 0.0/1.0 diversity, 0 invariants) are valid."""
        # Zero corpus_size is valid (though results in low confidence)
        confidence, _ = calculate_confidence(
            corpus_size=0,
            input_diversity_score=0.5,
            invariant_count=10,
        )
        assert confidence >= 0.0

        # Boundary diversity scores are valid
        confidence, _ = calculate_confidence(
            corpus_size=100,
            input_diversity_score=0.0,
            invariant_count=10,
        )
        assert confidence >= 0.0

        confidence, _ = calculate_confidence(
            corpus_size=100,
            input_diversity_score=1.0,
            invariant_count=10,
        )
        assert confidence >= 0.0

        # Zero invariant_count is valid
        confidence, _ = calculate_confidence(
            corpus_size=100,
            input_diversity_score=0.5,
            invariant_count=0,
        )
        assert confidence >= 0.0


class TestPydanticFieldValidation:
    """Test Pydantic field validation on models.

    These tests verify that Pydantic field constraints (ge=0.0, le=1.0, etc.)
    properly raise ValidationError when violated. This is distinct from the
    business logic validation in calculate_stability which raises ModelOnexError.
    """

    def test_negative_avg_latency_raises_validation_error(self) -> None:
        """Negative avg_latency_ms should raise Pydantic ValidationError."""
        with pytest.raises(ValidationError, match="avg_latency_ms"):
            ModelPerformanceMetrics(
                avg_latency_ms=-1.0,  # Invalid: must be >= 0
                p95_latency_ms=150.0,
                p99_latency_ms=200.0,
                avg_cost_per_call=0.002,
                total_calls=1000,
                error_rate=0.01,
            )

    def test_negative_p95_latency_raises_validation_error(self) -> None:
        """Negative p95_latency_ms should raise Pydantic ValidationError."""
        with pytest.raises(ValidationError, match="p95_latency_ms"):
            ModelPerformanceMetrics(
                avg_latency_ms=100.0,
                p95_latency_ms=-50.0,  # Invalid: must be >= 0
                p99_latency_ms=200.0,
                avg_cost_per_call=0.002,
                total_calls=1000,
                error_rate=0.01,
            )

    def test_negative_p99_latency_raises_validation_error(self) -> None:
        """Negative p99_latency_ms should raise Pydantic ValidationError."""
        with pytest.raises(ValidationError, match="p99_latency_ms"):
            ModelPerformanceMetrics(
                avg_latency_ms=100.0,
                p95_latency_ms=150.0,
                p99_latency_ms=-10.0,  # Invalid: must be >= 0
                avg_cost_per_call=0.002,
                total_calls=1000,
                error_rate=0.01,
            )

    def test_error_rate_above_one_raises_validation_error(self) -> None:
        """Error rate > 1.0 should raise Pydantic ValidationError."""
        with pytest.raises(ValidationError, match="error_rate"):
            ModelPerformanceMetrics(
                avg_latency_ms=100.0,
                p95_latency_ms=150.0,
                p99_latency_ms=200.0,
                avg_cost_per_call=0.002,
                total_calls=1000,
                error_rate=1.5,  # Invalid: must be <= 1.0
            )

    def test_error_rate_below_zero_raises_validation_error(self) -> None:
        """Error rate < 0.0 should raise Pydantic ValidationError."""
        with pytest.raises(ValidationError, match="error_rate"):
            ModelPerformanceMetrics(
                avg_latency_ms=100.0,
                p95_latency_ms=150.0,
                p99_latency_ms=200.0,
                avg_cost_per_call=0.002,
                total_calls=1000,
                error_rate=-0.1,  # Invalid: must be >= 0.0
            )

    def test_negative_total_calls_raises_validation_error(self) -> None:
        """Negative total_calls should raise Pydantic ValidationError."""
        with pytest.raises(ValidationError, match="total_calls"):
            ModelPerformanceMetrics(
                avg_latency_ms=100.0,
                p95_latency_ms=150.0,
                p99_latency_ms=200.0,
                avg_cost_per_call=0.002,
                total_calls=-100,  # Invalid: must be >= 0
                error_rate=0.01,
            )

    def test_negative_avg_cost_raises_validation_error(self) -> None:
        """Negative avg_cost_per_call should raise Pydantic ValidationError."""
        with pytest.raises(ValidationError, match="avg_cost_per_call"):
            ModelPerformanceMetrics(
                avg_latency_ms=100.0,
                p95_latency_ms=150.0,
                p99_latency_ms=200.0,
                avg_cost_per_call=-0.001,  # Invalid: must be >= 0
                total_calls=1000,
                error_rate=0.01,
            )

    def test_percentile_ordering_raises_model_onex_error(self) -> None:
        """Invalid percentile ordering raises ModelOnexError (not ValidationError).

        This is business logic validation via model_validator, not field-level
        Pydantic validation.
        """
        with pytest.raises(ModelOnexError, match="percentiles must be ordered"):
            ModelPerformanceMetrics(
                avg_latency_ms=200.0,  # avg > p95 violates ordering
                p95_latency_ms=100.0,
                p99_latency_ms=300.0,
                avg_cost_per_call=0.002,
                total_calls=1000,
                error_rate=0.01,
            )
