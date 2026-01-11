"""Stability calculation utilities for baseline health assessment.

This module provides functions to calculate system stability scores
based on invariant pass rates, error rates, latency metrics, and corpus size.
"""

from typing import TYPE_CHECKING, Literal

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors import ModelOnexError

if TYPE_CHECKING:
    from omnibase_core.models.health.model_invariant_status import ModelInvariantStatus
    from omnibase_core.models.health.model_performance_metrics import (
        ModelPerformanceMetrics,
    )


# Stability thresholds (configurable defaults)
DEFAULT_STABLE_THRESHOLD = 0.8
DEFAULT_DEGRADED_THRESHOLD = 0.5
DEFAULT_MIN_CORPUS_SIZE = 100
DEFAULT_TARGET_CORPUS_SIZE = 1000

# Stability calculation thresholds
ERROR_RATE_THRESHOLD = 0.10  # 10% error rate = 0 stability score
MAX_LATENCY_RATIO = 6.0  # p99 = 6x avg latency = 0 stability score


def calculate_stability(
    invariants: list["ModelInvariantStatus"],
    metrics: "ModelPerformanceMetrics",
    corpus_size: int,
    *,
    stable_threshold: float = DEFAULT_STABLE_THRESHOLD,
    degraded_threshold: float = DEFAULT_DEGRADED_THRESHOLD,
    target_corpus_size: int = DEFAULT_TARGET_CORPUS_SIZE,
) -> tuple[float, Literal["stable", "unstable", "degraded"], str]:
    """Calculate stability score and status.

    The stability score is a weighted combination of:
    - Invariant pass rate (40% weight)
    - Error rate score (30% weight)
    - Latency consistency (20% weight)
    - Corpus size score (10% weight)

    Args:
        invariants: List of invariant check results.
        metrics: Performance metrics to evaluate.
        corpus_size: Number of samples in the execution corpus.
        stable_threshold: Score threshold for "stable" status (default: 0.8).
        degraded_threshold: Score threshold for "degraded" status (default: 0.5).
        target_corpus_size: Target corpus size for full score (default: 1000).

    Returns:
        Tuple of (score, status, details) where:
        - score: Float between 0 and 1
        - status: One of "stable", "unstable", "degraded"
        - details: String describing the score breakdown

    Note:
        Any failing invariant immediately results in "unstable" status,
        regardless of the overall stability score. This is intentional:
        invariants represent critical correctness checks that must ALL pass
        for the system to be considered operationally healthy. The "degraded"
        status is reserved for cases where all invariants pass but performance
        metrics (error rate, latency, corpus size) indicate suboptimal operation.

    Raises:
        ModelOnexError: If invariants list is empty or avg_latency_ms is zero.

    Example:
        >>> from uuid import uuid4
        >>> from omnibase_core.models.health.model_invariant_status import (
        ...     ModelInvariantStatus,
        ... )
        >>> from omnibase_core.models.health.model_performance_metrics import (
        ...     ModelPerformanceMetrics,
        ... )
        >>> invariants = [
        ...     ModelInvariantStatus(invariant_id=uuid4(), name="test", passed=True)
        ... ]
        >>> metrics = ModelPerformanceMetrics(
        ...     avg_latency_ms=100, p95_latency_ms=200, p99_latency_ms=300,
        ...     avg_cost_per_call=0.01, total_calls=1000, error_rate=0.01
        ... )
        >>> score, status, details = calculate_stability(invariants, metrics, 500)
        >>> status
        'stable'
    """
    if not invariants:
        raise ModelOnexError(
            message="invariants list cannot be empty",
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
        )

    if metrics.avg_latency_ms == 0:
        raise ModelOnexError(
            message="avg_latency_ms must be greater than 0 (current: 0.0, expected: > 0.0)",
            error_code=EnumCoreErrorCode.INVALID_PARAMETER,
        )

    factors: list[tuple[str, float, float]] = []

    # Factor 1: Invariant pass rate (40% weight)
    pass_rate = sum(1 for i in invariants if i.passed) / len(invariants)
    factors.append(("invariants", pass_rate, 0.4))

    # Factor 2: Error rate (30% weight)
    # 10% error rate = 0 score, 0% error rate = 1 score
    error_score = max(0.0, 1.0 - (metrics.error_rate / ERROR_RATE_THRESHOLD))
    factors.append(("errors", error_score, 0.3))

    # Factor 3: Latency consistency (20% weight)
    # p99 = 6x avg = 0 score, p99 = avg = 1 score
    latency_ratio = metrics.p99_latency_ms / metrics.avg_latency_ms
    latency_score = max(0.0, 1.0 - (latency_ratio - 1) / (MAX_LATENCY_RATIO - 1))
    factors.append(("latency", latency_score, 0.2))

    # Factor 4: Corpus size (10% weight)
    # target_corpus_size+ samples = full score
    corpus_score = min(1.0, corpus_size / target_corpus_size)
    factors.append(("corpus", corpus_score, 0.1))

    # Calculate weighted score
    score = sum(factor_score * weight for _, factor_score, weight in factors)

    # Determine status
    # NOTE: Any failing invariant immediately results in "unstable" status,
    # regardless of overall score. This is intentional - invariants are critical
    # correctness checks that must ALL pass for the system to be considered
    # stable. The "degraded" status is reserved for when all invariants pass
    # but performance metrics indicate suboptimal operation.
    if pass_rate < 1.0:
        status: Literal["stable", "unstable", "degraded"] = "unstable"
    elif score >= stable_threshold:
        status = "stable"
    elif score >= degraded_threshold:
        status = "degraded"
    else:
        status = "unstable"

    # Format details
    factor_details = ", ".join(
        f"{name}={factor_score:.2f}*{weight}" for name, factor_score, weight in factors
    )
    details = f"Score breakdown: [{factor_details}] = {score:.3f}"

    return score, status, details


def calculate_confidence(
    corpus_size: int,
    input_diversity_score: float,
    invariant_count: int,
    *,
    min_corpus_size: int = DEFAULT_MIN_CORPUS_SIZE,
    target_corpus_size: int = DEFAULT_TARGET_CORPUS_SIZE,
) -> tuple[float, str]:
    """Calculate confidence level in the baseline assessment.

    Confidence is based on:
    - Corpus size (larger = more confidence)
    - Input diversity (more diverse = more confidence)
    - Number of invariants checked (more = more confidence)

    Args:
        corpus_size: Number of samples in the execution corpus.
        input_diversity_score: Diversity score of inputs (0-1).
        invariant_count: Number of invariants checked.
        min_corpus_size: Minimum corpus size for any confidence.
        target_corpus_size: Target corpus size for full confidence.

    Returns:
        Tuple of (confidence_level, reasoning) where:
        - confidence_level: Float between 0 and 1
        - reasoning: String explaining the confidence level

    Raises:
        ModelOnexError: If corpus_size or invariant_count is negative, or if
            input_diversity_score is not between 0.0 and 1.0.

    Example:
        >>> confidence, reasoning = calculate_confidence(
        ...     corpus_size=500,
        ...     input_diversity_score=0.8,
        ...     invariant_count=10
        ... )
        >>> confidence > 0.5
        True
    """
    # Input validation
    if corpus_size < 0:
        raise ModelOnexError(
            message="corpus_size must be non-negative",
            error_code=EnumCoreErrorCode.INVALID_PARAMETER,
            context={"corpus_size": corpus_size},
        )
    if not (0.0 <= input_diversity_score <= 1.0):
        raise ModelOnexError(
            message="input_diversity_score must be between 0.0 and 1.0",
            error_code=EnumCoreErrorCode.INVALID_PARAMETER,
            context={"input_diversity_score": input_diversity_score},
        )
    if invariant_count < 0:
        raise ModelOnexError(
            message="invariant_count must be non-negative",
            error_code=EnumCoreErrorCode.INVALID_PARAMETER,
            context={"invariant_count": invariant_count},
        )

    factors = []

    # Factor 1: Corpus size (50% weight)
    if corpus_size < min_corpus_size:
        corpus_factor = corpus_size / min_corpus_size * 0.5  # Cap at 0.5 if below min
    else:
        corpus_factor = min(1.0, corpus_size / target_corpus_size)
    factors.append(("corpus_size", corpus_factor, 0.5))

    # Factor 2: Input diversity (30% weight)
    factors.append(("diversity", input_diversity_score, 0.3))

    # Factor 3: Invariant coverage (20% weight)
    # 10+ invariants = full score
    invariant_factor = min(1.0, invariant_count / 10)
    factors.append(("invariants", invariant_factor, 0.2))

    # Calculate weighted confidence
    confidence = sum(factor_score * weight for _, factor_score, weight in factors)

    # Generate reasoning
    reasons = []
    if corpus_size < min_corpus_size:
        reasons.append(f"corpus below minimum ({corpus_size}/{min_corpus_size})")
    elif corpus_size < target_corpus_size:
        reasons.append(f"corpus at {corpus_size}/{target_corpus_size} target")
    else:
        reasons.append("corpus size is adequate")

    if input_diversity_score < 0.5:
        reasons.append("low input diversity")
    elif input_diversity_score >= 0.8:
        reasons.append("high input diversity")

    if invariant_count < 5:
        reasons.append(f"only {invariant_count} invariants checked")

    reasoning = "; ".join(reasons) if reasons else "all factors nominal"

    return confidence, reasoning
