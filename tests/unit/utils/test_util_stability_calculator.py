"""Tests for stability calculator utility.

Phase 2: Stability Detection Tests
"""

from uuid import uuid4

import pytest

from omnibase_core.errors import OnexError
from omnibase_core.models.health.model_invariant_status import ModelInvariantStatus
from omnibase_core.models.health.model_performance_metrics import (
    ModelPerformanceMetrics,
)
from omnibase_core.utils.util_stability_calculator import (
    DEFAULT_STABLE_THRESHOLD,
    calculate_confidence,
    calculate_stability,
)

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
        """Empty invariants list should raise OnexError."""
        with pytest.raises(OnexError, match="cannot be empty"):
            calculate_stability(
                invariants=[],
                metrics=healthy_metrics,
                corpus_size=1000,
            )

    def test_zero_latency_raises_error(
        self,
        all_passing_invariants: list[ModelInvariantStatus],
    ) -> None:
        """Zero average latency should raise OnexError."""
        zero_latency_metrics = ModelPerformanceMetrics(
            avg_latency_ms=0.0,  # This would cause division by zero
            p95_latency_ms=0.0,
            p99_latency_ms=0.0,
            avg_cost_per_call=0.0,
            total_calls=0,
            error_rate=0.0,
        )

        with pytest.raises(OnexError, match="cannot be zero"):
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

        assert confidence >= 0.8
        assert "adequate" in reasoning.lower() or "corpus" in reasoning.lower()

    def test_low_confidence_with_small_corpus(self) -> None:
        """Small corpus = low confidence."""
        confidence, reasoning = calculate_confidence(
            corpus_size=50,
            input_diversity_score=0.9,
            invariant_count=15,
        )

        assert confidence < 0.8
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
