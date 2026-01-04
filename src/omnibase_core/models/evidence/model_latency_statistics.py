# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""Latency comparison statistics between baseline and replay executions.

This model provides comprehensive latency metrics including averages and
percentiles (P50, P95) for comparing baseline vs replay execution performance.
"""

import math
import statistics

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors import ModelOnexError


class ModelLatencyStatistics(BaseModel):
    """Latency comparison statistics between baseline and replay.

    This model captures latency metrics for both baseline and replay executions,
    along with computed deltas showing performance differences. Positive delta
    percentages indicate regression (replay slower), negative indicate improvement.

    All values are in milliseconds (ms).

    Attributes:
        baseline_avg_ms: Average latency across baseline executions
        baseline_p50_ms: 50th percentile (median) of baseline latencies
        baseline_p95_ms: 95th percentile of baseline latencies
        replay_avg_ms: Average latency across replay executions
        replay_p50_ms: 50th percentile (median) of replay latencies
        replay_p95_ms: 95th percentile of replay latencies
        delta_avg_ms: Absolute difference in average latency (replay - baseline)
        delta_avg_percent: Percentage change in average latency
        delta_p50_percent: Percentage change in P50 latency
        delta_p95_percent: Percentage change in P95 latency
    """

    model_config = ConfigDict(
        frozen=True,  # Immutable after creation
        extra="forbid",  # No extra fields allowed
        from_attributes=True,  # pytest-xdist compatibility
    )

    # Baseline metrics
    baseline_avg_ms: float = Field(
        description="Average latency across baseline executions (ms)"
    )
    baseline_p50_ms: float = Field(
        description="50th percentile (median) of baseline latencies (ms)"
    )
    baseline_p95_ms: float = Field(
        description="95th percentile of baseline latencies (ms)"
    )

    # Replay metrics
    replay_avg_ms: float = Field(
        description="Average latency across replay executions (ms)"
    )
    replay_p50_ms: float = Field(
        description="50th percentile (median) of replay latencies (ms)"
    )
    replay_p95_ms: float = Field(description="95th percentile of replay latencies (ms)")

    # Computed deltas
    delta_avg_ms: float = Field(
        description="Absolute difference in average latency: replay - baseline (ms)"
    )
    delta_avg_percent: float = Field(
        description="Percentage change in average latency. Positive = regression."
    )
    delta_p50_percent: float = Field(
        description="Percentage change in P50 latency. Positive = regression."
    )
    delta_p95_percent: float = Field(
        description="Percentage change in P95 latency. Positive = regression."
    )

    @classmethod
    def from_latency_values(
        cls,
        baseline_values: list[float],
        replay_values: list[float],
    ) -> "ModelLatencyStatistics":
        """Compute statistics from raw latency measurements.

        Args:
            baseline_values: List of baseline latency measurements (ms).
                Must not be empty.
            replay_values: List of replay latency measurements (ms).
                Must not be empty.

        Returns:
            ModelLatencyStatistics with computed metrics.

        Raises:
            ModelOnexError: If either list is empty or lists have different lengths.
        """
        if not baseline_values:
            raise ModelOnexError(
                message="baseline_values cannot be empty",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                context={"parameter": "baseline_values"},
            )
        if not replay_values:
            raise ModelOnexError(
                message="replay_values cannot be empty",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                context={"parameter": "replay_values"},
            )
        if len(baseline_values) != len(replay_values):
            raise ModelOnexError(
                message="baseline_values and replay_values must have the same length",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                context={
                    "baseline_count": len(baseline_values),
                    "replay_count": len(replay_values),
                },
            )

        # Compute baseline statistics
        baseline_avg = statistics.mean(baseline_values)
        baseline_p50 = cls._compute_percentile(baseline_values, 50)
        baseline_p95 = cls._compute_percentile(baseline_values, 95)

        # Compute replay statistics
        replay_avg = statistics.mean(replay_values)
        replay_p50 = cls._compute_percentile(replay_values, 50)
        replay_p95 = cls._compute_percentile(replay_values, 95)

        # Compute deltas
        delta_avg_ms = replay_avg - baseline_avg
        delta_avg_percent = cls._compute_delta_percent(baseline_avg, replay_avg)
        delta_p50_percent = cls._compute_delta_percent(baseline_p50, replay_p50)
        delta_p95_percent = cls._compute_delta_percent(baseline_p95, replay_p95)

        return cls(
            baseline_avg_ms=baseline_avg,
            baseline_p50_ms=baseline_p50,
            baseline_p95_ms=baseline_p95,
            replay_avg_ms=replay_avg,
            replay_p50_ms=replay_p50,
            replay_p95_ms=replay_p95,
            delta_avg_ms=delta_avg_ms,
            delta_avg_percent=delta_avg_percent,
            delta_p50_percent=delta_p50_percent,
            delta_p95_percent=delta_p95_percent,
        )

    @staticmethod
    def _compute_percentile(values: list[float], percentile: int) -> float:
        """Compute percentile using stdlib (no numpy).

        Uses the nearest-rank method for P95 and median for P50.

        Args:
            values: List of values (must not be empty).
            percentile: Percentile to compute (0-100).

        Returns:
            The computed percentile value.
        """
        if len(values) == 1:
            return values[0]

        sorted_values = sorted(values)
        n = len(sorted_values)

        if percentile == 50:
            # Use statistics.median for P50 (handles even/odd correctly)
            return statistics.median(sorted_values)

        # Nearest-rank method for other percentiles
        # Index = ceil(percentile/100 * n) - 1
        rank = math.ceil(percentile / 100.0 * n) - 1
        # Clamp to valid range
        rank = max(0, min(rank, n - 1))
        return sorted_values[rank]

    @staticmethod
    def _compute_delta_percent(baseline: float, replay: float) -> float:
        """Compute percentage change from baseline to replay.

        Args:
            baseline: Baseline value.
            replay: Replay value.

        Returns:
            Percentage change. Returns 0.0 if baseline is zero to avoid
            division by zero.
        """
        if baseline == 0.0:
            return 0.0
        return ((replay - baseline) / baseline) * 100.0


__all__ = ["ModelLatencyStatistics"]
