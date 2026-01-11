"""Model for a single line in diff output."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ModelDiffLine(BaseModel):
    """Single line in diff output.

    Represents one line of a side-by-side comparison between
    baseline and replay execution outputs.

    Attributes:
        line_number: The line number in the comparison.
        baseline_content: Content from baseline output (None if line was added).
        replay_content: Content from replay output (None if line was removed).
        change_type: Type of change for this line.

    Thread Safety:
        This model is immutable (frozen=True) and safe for concurrent access.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    line_number: int = Field(ge=1, description="Line number (1-indexed, must be >= 1)")
    baseline_content: str | None
    replay_content: str | None
    change_type: Literal["unchanged", "modified", "added", "removed"]


__all__ = ["ModelDiffLine"]
