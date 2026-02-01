"""Stability calculation utilities for baseline health assessment.

This module provides functions to calculate system stability scores
based on invariant pass rates, error rates, latency metrics, and corpus size.

Design Philosophy
-----------------
The stability calculation uses a weighted multi-factor approach to provide
a holistic view of system health. The weights reflect the relative importance
of each factor in determining operational stability:

- **Invariants (40%)**: Correctness checks are the most critical factor.
  A system that produces incorrect results is fundamentally broken,
  regardless of performance characteristics.

- **Error Rate (30%)**: Production error rates directly impact user
  experience and system reliability. High error rates indicate systemic
  issues that must be addressed.

- **Latency Consistency (20%)**: Consistent response times indicate
  predictable system behavior. High variance (p99 >> avg) suggests
  intermittent issues like resource contention or external dependencies.

- **Corpus Size (10%)**: Statistical significance of the assessment.
  Larger sample sizes provide more confidence but are secondary to
  actual quality metrics.

Stability Status Logic
----------------------
The function implements a **fail-fast on invariants** policy: any failing
invariant immediately results in "unstable" status. This is intentional
because invariants represent critical correctness checks. A system may
have excellent performance metrics but still be fundamentally broken
if it violates invariants.

The "degraded" status is reserved for systems where:

- All invariants pass (correctness is maintained)
- But performance metrics indicate suboptimal operation

Confidence Calculation
----------------------
Confidence reflects how much trust we can place in the stability assessment
itself. A high stability score with low confidence suggests we need more
data before making decisions based on the report. Factors include:

- Corpus size (50%): Primary determinant of statistical confidence
- Input diversity (30%): Coverage of the input space
- Invariant count (20%): Thoroughness of validation checks
"""

from typing import TYPE_CHECKING, Literal

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors import ModelOnexError

if TYPE_CHECKING:
    from omnibase_core.models.health.model_invariant_status import ModelInvariantStatus
    from omnibase_core.models.health.model_performance_metrics import (
        ModelPerformanceMetrics,
    )


# =============================================================================
# Stability Status Thresholds
# =============================================================================
# These thresholds determine the categorical status based on the weighted score.
# They are configurable via function parameters for flexibility in different
# deployment contexts (e.g., stricter thresholds for production vs. staging).

DEFAULT_STABLE_THRESHOLD = 0.8
"""Minimum score (0-1) required for "stable" status.

Rationale: 0.8 allows for minor degradation (e.g., slightly elevated error
rates or latency variance) while still indicating a healthy system. This
aligns with common SLA targets of 99%+ availability with acceptable performance.
"""

DEFAULT_DEGRADED_THRESHOLD = 0.5
"""Minimum score (0-1) required for "degraded" status (below this = unstable).

Rationale: 0.5 represents a system that is still functional but has significant
issues that need attention. Below this threshold, the system is considered
operationally compromised.
"""

# =============================================================================
# Corpus Size Thresholds
# =============================================================================
# These control the confidence calculation based on sample size.

DEFAULT_MIN_CORPUS_SIZE = 100
"""Minimum corpus size for meaningful statistical analysis.

Rationale: With fewer than 100 samples, statistical measures like percentiles
become unreliable. This threshold ensures basic statistical validity while
remaining achievable for low-traffic systems.
"""

DEFAULT_TARGET_CORPUS_SIZE = 1000
"""Target corpus size for full confidence score.

Rationale: At 1000 samples, percentile calculations (p95, p99) are statistically
robust, and rare error conditions have likely been observed. This is a balance
between statistical rigor and practical data collection.
"""

DEFAULT_FULL_INVARIANT_COUNT = 10
"""Number of invariants required for full invariant coverage score.

Rationale: Most well-designed systems have 5-15 core invariants covering:

- Input validation (1-2 invariants)
- Output format correctness (1-2 invariants)
- Business logic rules (3-5 invariants)
- Resource constraints (1-2 invariants)
- Data consistency (1-2 invariants)

Ten invariants represents comprehensive coverage without penalizing
simpler systems that legitimately have fewer constraints.
"""

# =============================================================================
# Stability Factor Thresholds
# =============================================================================
# These define the boundaries for individual stability factors.

ERROR_RATE_THRESHOLD = 0.10
"""Error rate (0-1) at which the error score becomes zero.

Rationale: A 10% error rate is considered catastrophic for most production
systems. At this level, 1 in 10 requests fails, which typically violates
SLAs and causes significant user impact. The linear interpolation from
0% (score=1.0) to 10% (score=0.0) provides a smooth degradation curve.
"""

MAX_LATENCY_RATIO = 6.0
"""Maximum acceptable ratio of p99 latency to average latency.

Rationale: A p99/avg ratio of 6x indicates severe latency variance, suggesting
issues like:

- Garbage collection pauses
- Database connection pool exhaustion
- External service timeouts
- Resource contention under load

Healthy systems typically show p99/avg ratios between 2x-4x. Beyond 6x,
the system is too unpredictable for reliable operation.
"""

# =============================================================================
# Stability Factor Weights (must sum to 1.0)
# =============================================================================
# These weights determine the relative importance of each factor in the
# overall stability score.

WEIGHT_INVARIANTS = 0.4
"""Weight for invariant pass rate in stability score.

Rationale: Invariants are the most critical factor because they represent
correctness. A system that passes all performance checks but violates
invariants is fundamentally broken.
"""

WEIGHT_ERROR_RATE = 0.3
"""Weight for error rate score in stability score.

Rationale: Error rates directly impact user experience and are often
the primary SLA metric.
"""

WEIGHT_LATENCY = 0.2
"""Weight for latency consistency score in stability score.

Rationale: Latency variance indicates system predictability. While less
critical than correctness or error rates, high variance degrades user
experience and may indicate underlying issues.
"""

WEIGHT_CORPUS = 0.1
"""Weight for corpus size score in stability score.

Rationale: Corpus size affects confidence in the assessment but not the
actual system quality. Smaller weight keeps focus on quality metrics.
"""

# =============================================================================
# Confidence Factor Weights (must sum to 1.0)
# =============================================================================
# These weights determine how confidence is calculated from corpus size,
# diversity, and invariant coverage.

WEIGHT_CONFIDENCE_CORPUS = 0.5
"""Weight for corpus size in confidence calculation.

Rationale: Sample size is the primary determinant of statistical confidence.
"""

WEIGHT_CONFIDENCE_DIVERSITY = 0.3
"""Weight for input diversity in confidence calculation.

Rationale: A large corpus of similar inputs may miss edge cases. Diversity
ensures the corpus covers the input space representatively.
"""

WEIGHT_CONFIDENCE_INVARIANTS = 0.2
"""Weight for invariant coverage in confidence calculation.

Rationale: More invariants provide more thorough validation, but this is
secondary to having sufficient, diverse data.
"""

# =============================================================================
# Confidence Reasoning Thresholds
# =============================================================================
# These thresholds determine the qualitative descriptions in confidence reasoning.

DIVERSITY_LOW_THRESHOLD = 0.5
"""Diversity score (0-1) below which diversity is considered "low".

Rationale: Below 0.5, less than half the input space is represented,
indicating significant gaps in test coverage that may hide issues.
"""

DIVERSITY_HIGH_THRESHOLD = 0.8
"""Diversity score (0-1) above which diversity is considered "high".

Rationale: Above 0.8, the corpus covers most of the relevant input space,
providing strong confidence that edge cases have been exercised.
"""

FEW_INVARIANTS_THRESHOLD = 5
"""Invariant count below which coverage is noted as limited.

Rationale: Fewer than 5 invariants suggests minimal validation coverage.
While some simple systems may legitimately have few invariants, this
threshold flags potential gaps in correctness checking.
"""


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
        ModelOnexError: If invariants list is empty, avg_latency_ms is zero,
            or target_corpus_size is not greater than 0.

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
            error_code=EnumCoreErrorCode.INVALID_PARAMETER,
        )

    if metrics.avg_latency_ms == 0:
        raise ModelOnexError(
            message="avg_latency_ms must be greater than 0 (current: 0.0, expected: > 0.0)",
            error_code=EnumCoreErrorCode.INVALID_PARAMETER,
        )

    if target_corpus_size <= 0:
        raise ModelOnexError(
            message="target_corpus_size must be greater than 0",
            error_code=EnumCoreErrorCode.INVALID_PARAMETER,
            context={"target_corpus_size": target_corpus_size},
        )

    factors: list[tuple[str, float, float]] = []

    # Factor 1: Invariant pass rate
    # Correctness is paramount - see WEIGHT_INVARIANTS docstring for rationale
    pass_rate = sum(1 for i in invariants if i.passed) / len(invariants)
    factors.append(("invariants", pass_rate, WEIGHT_INVARIANTS))

    # Factor 2: Error rate
    # Linear interpolation: 0% error -> score 1.0, ERROR_RATE_THRESHOLD -> score 0.0
    error_score = max(0.0, 1.0 - (metrics.error_rate / ERROR_RATE_THRESHOLD))
    factors.append(("errors", error_score, WEIGHT_ERROR_RATE))

    # Factor 3: Latency consistency
    # Measures variance via p99/avg ratio. Ratio of 1.0 -> score 1.0,
    # ratio >= MAX_LATENCY_RATIO -> score 0.0
    latency_ratio = metrics.p99_latency_ms / metrics.avg_latency_ms
    latency_score = max(0.0, 1.0 - (latency_ratio - 1) / (MAX_LATENCY_RATIO - 1))
    factors.append(("latency", latency_score, WEIGHT_LATENCY))

    # Factor 4: Corpus size
    # Linear scale from 0 to target_corpus_size, capped at 1.0
    corpus_score = min(1.0, corpus_size / target_corpus_size)
    factors.append(("corpus", corpus_score, WEIGHT_CORPUS))

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
    full_invariant_count: int = DEFAULT_FULL_INVARIANT_COUNT,
    diversity_low_threshold: float = DIVERSITY_LOW_THRESHOLD,
    diversity_high_threshold: float = DIVERSITY_HIGH_THRESHOLD,
    few_invariants_threshold: int = FEW_INVARIANTS_THRESHOLD,
) -> tuple[float, str]:
    """Calculate confidence level in the baseline assessment.

    Confidence reflects how much trust we can place in the stability assessment.
    A high stability score with low confidence suggests we need more data before
    making decisions based on the report.

    Confidence is based on three weighted factors:

    - **Corpus size (50%)**: Sample size is the primary determinant of statistical
      confidence. Larger samples provide more reliable percentile and error rate
      measurements.

    - **Input diversity (30%)**: A large corpus of similar inputs may miss edge
      cases. Diversity ensures the corpus covers the input space representatively.

    - **Invariant coverage (20%)**: More invariants provide more thorough validation,
      but this is secondary to having sufficient, diverse data.

    Args:
        corpus_size: Number of samples in the execution corpus.
        input_diversity_score: Diversity score of inputs (0-1).
        invariant_count: Number of invariants checked.
        min_corpus_size: Minimum corpus size for meaningful statistical analysis
            (default: 100). Below this threshold, confidence is proportionally reduced.
        target_corpus_size: Target corpus size for full confidence score
            (default: 1000). At or above this size, corpus factor is 1.0.
        full_invariant_count: Number of invariants for full coverage score
            (default: 10). See DEFAULT_FULL_INVARIANT_COUNT for rationale.
        diversity_low_threshold: Diversity score below which diversity is noted
            as "low" in reasoning (default: 0.5).
        diversity_high_threshold: Diversity score above which diversity is noted
            as "high" in reasoning (default: 0.8).
        few_invariants_threshold: Invariant count below which coverage is noted
            as limited in reasoning (default: 5).

    Returns:
        Tuple of (confidence_level, reasoning) where:

        - confidence_level: Float between 0 and 1
        - reasoning: String explaining the confidence level

    Raises:
        ModelOnexError: If corpus_size or invariant_count is negative, if
            input_diversity_score is not between 0.0 and 1.0, or if
            min_corpus_size, target_corpus_size, or full_invariant_count is not
            greater than 0.

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
    if min_corpus_size <= 0:
        raise ModelOnexError(
            message="min_corpus_size must be greater than 0",
            error_code=EnumCoreErrorCode.INVALID_PARAMETER,
            context={"min_corpus_size": min_corpus_size},
        )
    if target_corpus_size <= 0:
        raise ModelOnexError(
            message="target_corpus_size must be greater than 0",
            error_code=EnumCoreErrorCode.INVALID_PARAMETER,
            context={"target_corpus_size": target_corpus_size},
        )
    if full_invariant_count <= 0:
        raise ModelOnexError(
            message="full_invariant_count must be greater than 0",
            error_code=EnumCoreErrorCode.INVALID_PARAMETER,
            context={"full_invariant_count": full_invariant_count},
        )

    factors = []

    # Factor 1: Corpus size
    # Ensures continuity at min_corpus_size boundary: both branches produce identical
    # values at exactly min_corpus_size. Below min, we scale linearly from 0 to the
    # value that would be produced at min_corpus_size (min_corpus_size/target_corpus_size).
    if corpus_size < min_corpus_size:
        # min_factor is the corpus_factor value at exactly min_corpus_size
        min_factor = min(1.0, min_corpus_size / target_corpus_size)
        corpus_factor = (corpus_size / min_corpus_size) * min_factor
    else:
        corpus_factor = min(1.0, corpus_size / target_corpus_size)
    factors.append(("corpus_size", corpus_factor, WEIGHT_CONFIDENCE_CORPUS))

    # Factor 2: Input diversity
    # Directly uses the provided diversity score as the factor value
    factors.append(("diversity", input_diversity_score, WEIGHT_CONFIDENCE_DIVERSITY))

    # Factor 3: Invariant coverage
    # Scales linearly from 0 invariants (factor=0) to full_invariant_count (factor=1.0)
    # See DEFAULT_FULL_INVARIANT_COUNT docstring for rationale on the default threshold
    invariant_factor = min(1.0, invariant_count / full_invariant_count)
    factors.append(("invariants", invariant_factor, WEIGHT_CONFIDENCE_INVARIANTS))

    # Calculate weighted confidence
    confidence = sum(factor_score * weight for _, factor_score, weight in factors)

    # Generate reasoning using configurable thresholds
    # This provides human-readable explanations of each contributing factor
    reasons = []
    if corpus_size < min_corpus_size:
        reasons.append(f"corpus below minimum ({corpus_size}/{min_corpus_size})")
    elif corpus_size < target_corpus_size:
        reasons.append(f"corpus at {corpus_size}/{target_corpus_size} target")
    else:
        reasons.append("corpus size is adequate")

    if input_diversity_score < diversity_low_threshold:
        reasons.append("low input diversity")
    elif input_diversity_score >= diversity_high_threshold:
        reasons.append("high input diversity")

    if invariant_count < few_invariants_threshold:
        reasons.append(f"only {invariant_count} invariants checked")
    elif invariant_count >= full_invariant_count:
        reasons.append("comprehensive invariant coverage")

    reasoning = "; ".join(reasons) if reasons else "all factors nominal"

    return confidence, reasoning
