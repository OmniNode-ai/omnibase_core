"""Execution comparison model for baseline vs replay evaluation.

Captures all comparison data between a baseline execution and a replay,
including input verification, output differences, invariant results,
and performance/cost metrics.

Thread Safety:
    ModelExecutionComparison is immutable (frozen=True) after creation,
    making it thread-safe for concurrent read access.
"""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.comparison.model_invariant_comparison_summary import (
    ModelInvariantComparisonSummary,
)
from omnibase_core.models.comparison.model_output_diff import ModelOutputDiff
from omnibase_core.models.invariant.model_invariant_result import ModelInvariantResult


class ModelExecutionComparison(BaseModel):
    """Comparison between baseline and replay execution.

    Captures all comparison data between a baseline execution and a replay,
    including input verification, output differences, invariant results,
    and performance/cost metrics.

    Attributes:
        baseline_execution_id: Unique identifier for the baseline execution.
        replay_execution_id: Unique identifier for the replay execution.
        comparison_id: Unique identifier for this comparison.
        input_hash: Hash of the input used (should match between baseline and replay).
        input_hash_match: True if the same input was used for both executions.
        baseline_output_hash: Hash of the baseline execution output.
        replay_output_hash: Hash of the replay execution output.
        output_match: True if outputs are identical between baseline and replay.
        output_diff: Structured diff of outputs if they differ, None if identical.
        baseline_invariant_results: Individual invariant results from baseline.
        replay_invariant_results: Individual invariant results from replay.
        invariant_comparison: Summary of invariant comparison between executions.
        baseline_latency_ms: Execution time of baseline in milliseconds.
        replay_latency_ms: Execution time of replay in milliseconds.
        latency_delta_ms: Difference in latency (replay - baseline).
        latency_delta_percent: Percentage change in latency from baseline.
        baseline_cost: Cost of baseline execution (optional).
        replay_cost: Cost of replay execution (optional).
        cost_delta: Difference in cost (replay - baseline) (optional).
        cost_delta_percent: Percentage change in cost from baseline (optional).
        compared_at: Timestamp when the comparison was performed.

    Thread Safety:
        This model is immutable (frozen=True) after creation, making it
        thread-safe for concurrent read access.
    """

    model_config = ConfigDict(frozen=True, extra="ignore", from_attributes=True)

    # Execution References
    baseline_execution_id: UUID = Field(
        ...,
        description="Unique identifier for the baseline execution",
    )
    replay_execution_id: UUID = Field(
        ...,
        description="Unique identifier for the replay execution",
    )
    comparison_id: UUID = Field(
        default_factory=uuid4,
        description="Unique identifier for this comparison",
    )

    # Input Verification
    input_hash: str = Field(
        ...,
        description="Hash of the input used (should match between baseline and replay)",
    )
    input_hash_match: bool = Field(
        ...,
        description="True if the same input was used for both executions",
    )

    # Output Comparison
    baseline_output_hash: str = Field(
        ...,
        description="Hash of the baseline execution output",
    )
    replay_output_hash: str = Field(
        ...,
        description="Hash of the replay execution output",
    )
    output_match: bool = Field(
        ...,
        description="True if outputs are identical between baseline and replay",
    )
    output_diff: ModelOutputDiff | None = Field(
        default=None,
        description="Structured diff of outputs if they differ, None if identical",
    )

    # Invariant Results
    baseline_invariant_results: list[ModelInvariantResult] = Field(
        ...,
        description="Individual invariant results from baseline execution",
    )
    replay_invariant_results: list[ModelInvariantResult] = Field(
        ...,
        description="Individual invariant results from replay execution",
    )
    invariant_comparison: ModelInvariantComparisonSummary = Field(
        ...,
        description="Summary of invariant comparison between executions",
    )

    # Performance Metrics
    baseline_latency_ms: float = Field(
        ...,
        ge=0,
        description="Execution time of baseline in milliseconds",
    )
    replay_latency_ms: float = Field(
        ...,
        ge=0,
        description="Execution time of replay in milliseconds",
    )
    latency_delta_ms: float = Field(
        ...,
        description="Difference in latency (replay - baseline) in milliseconds",
    )
    latency_delta_percent: float = Field(
        ...,
        description="Percentage change in latency from baseline",
    )

    # Cost Metrics (optional)
    baseline_cost: float | None = Field(
        default=None,
        ge=0,
        description="Cost of baseline execution (optional)",
    )
    replay_cost: float | None = Field(
        default=None,
        ge=0,
        description="Cost of replay execution (optional)",
    )
    cost_delta: float | None = Field(
        default=None,
        description="Difference in cost (replay - baseline) (optional)",
    )
    cost_delta_percent: float | None = Field(
        default=None,
        description="Percentage change in cost from baseline (optional)",
    )

    # Metadata
    compared_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Timestamp when the comparison was performed",
    )


__all__ = ["ModelExecutionComparison"]
