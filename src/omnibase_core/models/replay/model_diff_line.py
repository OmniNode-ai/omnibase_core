"""Model for a single line in diff output."""

from typing import Literal

from pydantic import BaseModel, ConfigDict


class ModelDiffLine(BaseModel):
    """Single line in diff output.

    Represents one line of a side-by-side comparison between
    baseline and replay execution outputs.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    line_number: int
    baseline_content: str | None
    replay_content: str | None
    change_type: Literal["unchanged", "modified", "added", "removed"]


__all__ = ["ModelDiffLine"]
