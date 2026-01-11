"""Model for detailed view of a single execution comparison."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

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

    Attributes:
        comparison_id: Unique identifier for this comparison.
        baseline_execution_id: ID of the baseline execution.
        replay_execution_id: ID of the replay execution.
        original_input: Snapshot of the execution input.
        input_hash: Hash of the input for deduplication.
        input_display: Formatted input for human reading (may be truncated).
        baseline_output: Snapshot of baseline execution output.
        replay_output: Snapshot of replay execution output.
        output_diff_display: Human-readable diff (None if outputs match).
        outputs_match: Whether baseline and replay outputs are identical.
        side_by_side: Side-by-side comparison view.
        invariant_results: Results of all invariant checks.
        invariants_all_passed: Whether all invariants passed.
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
    input_hash: str
    input_display: str

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
