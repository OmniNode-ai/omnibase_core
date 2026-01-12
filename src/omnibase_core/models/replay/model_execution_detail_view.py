"""Model for detailed view of a single execution comparison."""

from datetime import datetime
from typing import Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from omnibase_core.models.replay.model_input_snapshot import ModelInputSnapshot
from omnibase_core.models.replay.model_invariant_result_detail import (
    ModelInvariantResultDetail,
)
from omnibase_core.models.replay.model_output_snapshot import ModelOutputSnapshot
from omnibase_core.models.replay.model_side_by_side_comparison import (
    ModelSideBySideComparison,
)
from omnibase_core.models.replay.model_timing_breakdown import ModelTimingBreakdown
from omnibase_core.utils.util_hash_validation import (
    validate_hash_format as _validate_hash_format,
)


class ModelExecutionDetailView(BaseModel):
    """Detailed view of a single execution comparison for drill-down.

    This is the "deep dive" view when someone clicks on a specific
    execution in the replay report. It provides complete context
    including inputs, outputs, diffs, invariant results, and timing.

    Thread Safety:
        This model is immutable (frozen=True) and safe for concurrent access.

    Validation:
        - input_display: This is a convenience field for UI display purposes.
          It is independent of original_input.raw and may contain a truncated
          or formatted representation of the input. For the canonical input data,
          always use original_input.raw. The input_display field supports Unicode
          characters and can contain very large strings if needed.
        - invariant_results: Can be an empty list, which is valid for executions
          where no invariant checks are configured. When empty, invariants_all_passed
          should typically be True (vacuously true - no invariants means none failed).
        - input_hash: Must be formatted as "algorithm:hexdigest"
          (e.g., "sha256:a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2").
          Algorithm must be alphanumeric, digest must be hexadecimal.
          Common algorithms: sha256 (64 hex chars), sha512 (128 hex chars), md5 (32 hex chars).
        - outputs_match and output_diff_display: These fields must be consistent:
          * When outputs_match=True, output_diff_display must be None (no diff needed)
          * When outputs_match=False, output_diff_display must NOT be None (diff exists)
        - All nested models (ModelInputSnapshot, ModelOutputSnapshot, etc.) perform
          their own validation; see their respective docstrings for details.

    Attributes:
        comparison_id: Unique identifier for this comparison.
        baseline_execution_id: ID of the baseline execution.
        replay_execution_id: ID of the replay execution.
        original_input: Snapshot of the execution input (canonical input data).
        input_hash: Hash identifier of the input for deduplication. Must be
            formatted as "algorithm:hexdigest"
            (e.g., "sha256:a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2").
            Algorithm must be alphanumeric, digest must be hexadecimal.
            Common algorithms: sha256 (64 hex chars), sha512 (128 hex chars), md5 (32 hex chars).
        input_display: JSON-formatted input string for display (may be truncated
            for large inputs to maintain UI responsiveness). This is independent
            of original_input.raw and serves as a pre-formatted display value.
        baseline_output: Snapshot of baseline execution output.
        replay_output: Snapshot of replay execution output.
        output_diff_display: Unified diff format showing differences between
            baseline and replay outputs (None if outputs match exactly).
        outputs_match: Whether baseline and replay outputs are identical.
        side_by_side: Side-by-side comparison view.
        invariant_results: Results of all invariant checks. Can be empty if no
            invariants are configured for this execution.
        invariants_all_passed: Whether all invariants passed. True when
            invariant_results is empty (vacuously true).
        timing_breakdown: Detailed timing comparison.
        execution_timestamp: When the execution occurred. Must be timezone-aware;
            UTC is recommended for consistency across distributed systems.
        corpus_entry_id: ID of the corpus entry this execution belongs to.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    # Identification
    comparison_id: UUID
    baseline_execution_id: UUID
    replay_execution_id: UUID

    # Input Context
    original_input: ModelInputSnapshot
    input_hash: str = Field(
        min_length=1,
        description=(
            "Hash identifier of the input for deduplication. "
            "Must be formatted as 'algorithm:hexdigest' "
            "(e.g., 'sha256:a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2'). "
            "Algorithm must be alphanumeric, digest must be hexadecimal. "
            "Common algorithms: sha256 (64 hex chars), sha512 (128 hex chars), md5 (32 hex chars)."
        ),
    )
    input_display: str

    @field_validator("input_hash")
    @classmethod
    def validate_hash_format(cls, v: str) -> str:
        """Validate that input_hash follows the 'algorithm:hexdigest' format.

        Args:
            v: The hash string to validate.

        Returns:
            The validated hash string.

        Raises:
            ValueError: If the hash format is invalid or too long.
        """
        return _validate_hash_format(v)

    # Output Comparison
    baseline_output: ModelOutputSnapshot
    replay_output: ModelOutputSnapshot
    output_diff_display: str | None = None
    outputs_match: bool

    # Side-by-Side View
    side_by_side: ModelSideBySideComparison

    # Invariant Results
    invariant_results: list[ModelInvariantResultDetail]
    invariants_all_passed: bool

    # Timing Breakdown
    timing_breakdown: ModelTimingBreakdown

    # Metadata
    execution_timestamp: datetime = Field(
        description=(
            "When the execution occurred. Must be timezone-aware; "
            "UTC is recommended for consistency across distributed systems."
        ),
    )
    corpus_entry_id: UUID

    @field_validator("execution_timestamp")
    @classmethod
    def validate_timezone_aware(cls, v: datetime) -> datetime:
        """Validate that execution_timestamp is timezone-aware.

        Args:
            v: The datetime to validate.

        Returns:
            The validated datetime.

        Raises:
            ValueError: If the datetime is naive (lacks timezone info).
        """
        if v.tzinfo is None or v.tzinfo.utcoffset(v) is None:
            raise ValueError(
                "execution_timestamp must be timezone-aware. "
                "Use datetime with tzinfo (e.g., datetime.now(timezone.utc) "
                "or datetime(..., tzinfo=timezone.utc))."
            )
        return v

    @model_validator(mode="after")
    def validate_outputs_consistency(self) -> Self:
        """Validate consistency between outputs_match and output_diff_display.

        Ensures that:
        - When outputs_match=True, output_diff_display should be None (no diff needed)
        - When outputs_match=False, output_diff_display should NOT be None (diff exists)

        Returns:
            The validated model instance.

        Raises:
            ValueError: If the consistency check fails.
        """
        if self.outputs_match and self.output_diff_display is not None:
            raise ValueError(
                "When outputs_match=True, output_diff_display should be None "
                "(no diff needed when outputs are identical)"
            )
        if not self.outputs_match and self.output_diff_display is None:
            raise ValueError(
                "When outputs_match=False, output_diff_display should contain "
                "the diff (differences must be displayed when outputs differ)"
            )
        return self


__all__ = ["ModelExecutionDetailView"]
