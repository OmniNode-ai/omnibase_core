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

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.models.invariant.model_invariant_result import ModelInvariantResult
from omnibase_core.models.replay.model_invariant_comparison_summary import (
    ModelInvariantComparisonSummary,
)
from omnibase_core.models.replay.model_output_diff import ModelOutputDiff


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

    @model_validator(mode="after")
    def _validate_latency_deltas(self) -> "ModelExecutionComparison":
        """Validate that latency delta fields are consistent with source values.

        Validates:
            - latency_delta_ms matches (replay_latency_ms - baseline_latency_ms)
            - latency_delta_percent matches (delta_ms / baseline_ms) * 100
              when baseline > 0
            - When baseline is 0, latency_delta_percent must be 0.0 (convention)

        Raises:
            ValueError: If latency delta values are inconsistent with source values.
        """
        # Tolerance for floating point comparison
        tolerance = 0.01

        # Validate latency_delta_ms
        expected_delta_ms = self.replay_latency_ms - self.baseline_latency_ms
        if abs(self.latency_delta_ms - expected_delta_ms) > tolerance:
            raise ValueError(
                f"latency_delta_ms is inconsistent: "
                f"got {self.latency_delta_ms}, "
                f"expected {expected_delta_ms} "
                f"(replay_latency_ms={self.replay_latency_ms} - "
                f"baseline_latency_ms={self.baseline_latency_ms})"
            )

        # Validate latency_delta_percent
        if self.baseline_latency_ms == 0.0:
            # Convention: when baseline is 0, delta_percent must be 0.0
            # (avoids division by zero, undefined percentage)
            if self.latency_delta_percent != 0.0:
                raise ValueError(
                    f"latency_delta_percent must be 0.0 when baseline_latency_ms is 0 "
                    f"(got {self.latency_delta_percent}). "
                    f"Convention: percentage change is undefined/0% for zero baseline."
                )
        else:
            expected_delta_percent = (
                self.latency_delta_ms / self.baseline_latency_ms
            ) * 100
            if abs(self.latency_delta_percent - expected_delta_percent) > tolerance:
                raise ValueError(
                    f"latency_delta_percent is inconsistent: "
                    f"got {self.latency_delta_percent}, "
                    f"expected {expected_delta_percent:.2f} "
                    f"((latency_delta_ms={self.latency_delta_ms} / "
                    f"baseline_latency_ms={self.baseline_latency_ms}) * 100)"
                )

        return self

    @model_validator(mode="after")
    def _validate_cost_deltas(self) -> "ModelExecutionComparison":
        """Validate that cost delta fields are consistent with source values.

        Validates consistency rules for cost metrics:
            - When both baseline_cost and replay_cost are provided:
                - cost_delta must match (replay_cost - baseline_cost) within tolerance
                - cost_delta_percent must match (cost_delta / baseline_cost) * 100
                  when baseline_cost > 0
            - When baseline_cost is 0 and replay_cost is provided:
                - cost_delta_percent must be 0.0 (documented convention to avoid
                  undefined percentage)
            - When either cost is None:
                - Both cost_delta and cost_delta_percent must be None
            - Partial cost data is allowed:
                - One cost provided with deltas as None is valid

        Raises:
            ValueError: If cost delta values are inconsistent with source values.
        """
        # Tolerance for floating point comparison
        tolerance = 0.001

        # Case 1: Both costs are None - deltas must also be None
        if self.baseline_cost is None and self.replay_cost is None:
            if self.cost_delta is not None:
                raise ValueError(
                    "cost_delta must be None when both baseline_cost and "
                    f"replay_cost are None (got cost_delta={self.cost_delta})"
                )
            if self.cost_delta_percent is not None:
                raise ValueError(
                    "cost_delta_percent must be None when both baseline_cost and "
                    f"replay_cost are None (got cost_delta_percent={self.cost_delta_percent})"
                )
            return self

        # Case 2: Only one cost is provided (partial data)
        if self.baseline_cost is None or self.replay_cost is None:
            # With partial cost data, deltas should be None
            # (cannot compute meaningful delta without both values)
            if self.cost_delta is not None:
                raise ValueError(
                    f"cost_delta must be None when cost data is partial: "
                    f"baseline_cost={self.baseline_cost}, replay_cost={self.replay_cost}, "
                    f"but cost_delta={self.cost_delta}"
                )
            if self.cost_delta_percent is not None:
                raise ValueError(
                    f"cost_delta_percent must be None when cost data is partial: "
                    f"baseline_cost={self.baseline_cost}, replay_cost={self.replay_cost}, "
                    f"but cost_delta_percent={self.cost_delta_percent}"
                )
            return self

        # Case 3: Both costs are provided - validate deltas if present
        # Deltas can be None (not computed) or must be consistent
        if self.cost_delta is None and self.cost_delta_percent is None:
            # Valid: costs provided but deltas not computed
            return self

        # If cost_delta is provided, validate it matches expected value
        if self.cost_delta is not None:
            expected_delta = self.replay_cost - self.baseline_cost
            if abs(self.cost_delta - expected_delta) > tolerance:
                raise ValueError(
                    f"cost_delta is inconsistent: "
                    f"got {self.cost_delta}, expected {expected_delta:.6f} "
                    f"(replay_cost={self.replay_cost} - baseline_cost={self.baseline_cost})"
                )

        # If cost_delta_percent is provided, validate it
        if self.cost_delta_percent is not None:
            if self.baseline_cost == 0.0:
                # Convention: when baseline is 0, delta_percent must be 0.0
                if self.cost_delta_percent != 0.0:
                    raise ValueError(
                        f"cost_delta_percent must be 0.0 when baseline_cost is 0 "
                        f"(got {self.cost_delta_percent}). "
                        f"Convention: percentage change is undefined/0% for zero baseline."
                    )
            else:
                # Calculate expected percent using the actual delta
                # (either provided or computed)
                actual_delta = (
                    self.cost_delta
                    if self.cost_delta is not None
                    else (self.replay_cost - self.baseline_cost)
                )
                expected_percent = (actual_delta / self.baseline_cost) * 100
                if abs(self.cost_delta_percent - expected_percent) > tolerance:
                    raise ValueError(
                        f"cost_delta_percent is inconsistent: "
                        f"got {self.cost_delta_percent}, expected {expected_percent:.2f} "
                        f"((cost_delta={actual_delta} / "
                        f"baseline_cost={self.baseline_cost}) * 100)"
                    )

        return self

    @model_validator(mode="after")
    def _validate_output_match_consistency(self) -> "ModelExecutionComparison":
        """Validate that output_match field is consistent with hash comparison.

        Validates data consistency between output_match flag and actual hash values:
            - When output_match is True:
                - baseline_output_hash must equal replay_output_hash
                - output_diff should be None (identical outputs have no diff)
            - When output_match is False:
                - baseline_output_hash must NOT equal replay_output_hash

        This ensures the output_match flag accurately reflects the actual
        comparison state and prevents data inconsistencies where the flag
        contradicts the underlying hash values.

        Raises:
            ValueError: If output_match value is inconsistent with hash comparison.
        """
        hashes_match = self.baseline_output_hash == self.replay_output_hash

        if self.output_match and not hashes_match:
            raise ValueError(
                f"output_match is True but hashes differ: "
                f"baseline_output_hash={self.baseline_output_hash!r}, "
                f"replay_output_hash={self.replay_output_hash!r}. "
                f"output_match must be False when hashes are different."
            )

        if not self.output_match and hashes_match:
            raise ValueError(
                f"output_match is False but hashes are identical: "
                f"baseline_output_hash={self.baseline_output_hash!r}, "
                f"replay_output_hash={self.replay_output_hash!r}. "
                f"output_match must be True when hashes match."
            )

        if self.output_match and self.output_diff is not None:
            raise ValueError(
                "output_match is True but output_diff is present. "
                "When outputs are identical, output_diff should be None."
            )

        return self


__all__ = ["ModelExecutionComparison"]
