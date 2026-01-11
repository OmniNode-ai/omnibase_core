"""Model for side-by-side formatted comparison."""

from pydantic import BaseModel, ConfigDict

from omnibase_core.models.replay.model_diff_line import ModelDiffLine


class ModelSideBySideComparison(BaseModel):
    """Side-by-side formatted comparison.

    Provides a formatted view of baseline vs replay outputs,
    with pretty-printed JSON and line-by-line diff.

    Thread Safety:
        This model is immutable (frozen=True) and safe for concurrent access.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    baseline_formatted: str  # Pretty-printed JSON
    replay_formatted: str  # Pretty-printed JSON
    diff_lines: list[ModelDiffLine]  # Line-by-line diff


__all__ = ["ModelSideBySideComparison"]
