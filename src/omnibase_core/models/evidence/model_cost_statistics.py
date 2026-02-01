"""Cost comparison statistics between baseline and replay executions.

Thread Safety:
    ModelCostStatistics is immutable (frozen=True) after creation,
    making it thread-safe for concurrent read access.
"""

from typing import cast

from pydantic import BaseModel, ConfigDict


class ModelCostStatistics(BaseModel):
    """Cost comparison statistics between baseline and replay executions.

    This model holds aggregated cost metrics for comparing baseline and replay
    execution costs during corpus replay. All values are pre-computed and stored
    rather than calculated on access.

    Attributes:
        baseline_total: Total cost across all baseline executions.
        replay_total: Total cost across all replay executions.
        delta_total: Absolute difference (replay_total - baseline_total).
        delta_percent: Percentage change ((delta_total / baseline_total) * 100).
            Set to 0.0 when baseline_total is zero (undefined).
        baseline_avg_per_execution: Average cost per baseline execution.
        replay_avg_per_execution: Average cost per replay execution.

    Thread Safety:
        This model is immutable (frozen=True) after creation, making it
        thread-safe for concurrent read access.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    # Total costs
    baseline_total: float
    replay_total: float
    delta_total: float
    delta_percent: float

    # Per-execution averages
    baseline_avg_per_execution: float
    replay_avg_per_execution: float

    @classmethod
    def from_cost_values(
        cls,
        baseline_costs: list[float | None],
        replay_costs: list[float | None],
    ) -> "ModelCostStatistics | None":
        """Compute statistics from raw cost values.

        Calculates totals, averages, and delta statistics from lists of
        individual execution costs.

        Args:
            baseline_costs: List of cost values from baseline executions.
            replay_costs: List of cost values from replay executions.

        Returns:
            ModelCostStatistics instance with computed statistics, or None if:
            - Either list is empty (no data)
            - Any value in either list is None (incomplete data)
        """
        # Return None for empty lists (no data)
        if not baseline_costs or not replay_costs:
            return None

        # Return None if any value is None (incomplete data)
        if any(cost is None for cost in baseline_costs):
            return None
        if any(cost is None for cost in replay_costs):
            return None

        # At this point, all values are floats (not None) - type narrowing via cast
        # The None checks above guarantee this, so direct cast is safe
        baseline_values = cast(list[float], baseline_costs)
        replay_values = cast(list[float], replay_costs)

        # Compute totals
        baseline_total = sum(baseline_values)
        replay_total = sum(replay_values)

        # Compute averages
        baseline_avg = baseline_total / len(baseline_costs)
        replay_avg = replay_total / len(replay_costs)

        # Compute deltas
        delta_total = replay_total - baseline_total
        # delta_percent is undefined when baseline is zero
        if baseline_total == 0.0:
            delta_percent = 0.0
        else:
            delta_percent = (delta_total / baseline_total) * 100.0

        return cls(
            baseline_total=baseline_total,
            replay_total=replay_total,
            delta_total=delta_total,
            delta_percent=delta_percent,
            baseline_avg_per_execution=baseline_avg,
            replay_avg_per_execution=replay_avg,
        )


__all__ = ["ModelCostStatistics"]
