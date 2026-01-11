"""Model for detailed view of a single execution comparison."""

import re
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

# Pattern for validating hash format: "algorithm:hexdigest"
# - Algorithm: alphanumeric (allows uppercase for flexibility, e.g., "SHA256" or "sha256")
# - Separator: colon
# - Digest: hexadecimal characters (0-9, a-f, A-F)
HASH_FORMAT_PATTERN = re.compile(r"^[a-zA-Z0-9]+:[a-fA-F0-9]+$")

from omnibase_core.models.replay.model_input_snapshot import ModelInputSnapshot
from omnibase_core.models.replay.model_invariant_result_detail import (
    ModelInvariantResultDetail,
)
from omnibase_core.models.replay.model_output_snapshot import ModelOutputSnapshot
from omnibase_core.models.replay.model_side_by_side_comparison import (
    ModelSideBySideComparison,
)
from omnibase_core.models.replay.model_timing_breakdown import ModelTimingBreakdown


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
        - input_hash: Must be formatted as "algorithm:hexdigest" (e.g., "sha256:abc123").
          Algorithm must be alphanumeric, digest must be hexadecimal.
        - All nested models (ModelInputSnapshot, ModelOutputSnapshot, etc.) perform
          their own validation; see their respective docstrings for details.

    Attributes:
        comparison_id: Unique identifier for this comparison.
        baseline_execution_id: ID of the baseline execution.
        replay_execution_id: ID of the replay execution.
        original_input: Snapshot of the execution input (canonical input data).
        input_hash: Hash identifier of the input for deduplication. Must be
            formatted as "algorithm:hexdigest" (e.g., "sha256:abc123").
            Algorithm must be alphanumeric, digest must be hexadecimal.
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
        execution_timestamp: When the execution occurred.
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
            "Must be formatted as 'algorithm:hexdigest' (e.g., 'sha256:abc123'). "
            "Algorithm must be alphanumeric, digest must be hexadecimal."
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
            ValueError: If the hash format is invalid.
        """
        if not HASH_FORMAT_PATTERN.match(v):
            raise ValueError(
                f"Invalid hash format: '{v}'. "
                "Must be 'algorithm:hexdigest' format (e.g., 'sha256:abc123'). "
                "Algorithm must be alphanumeric, digest must be hexadecimal."
            )
        return v

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
    execution_timestamp: datetime
    corpus_entry_id: UUID


__all__ = ["ModelExecutionDetailView"]
