"""Model for a single line in diff output."""

from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ModelDiffLine(BaseModel):
    """Single line in diff output.

    Represents one line of a side-by-side comparison between
    baseline and replay execution outputs.

    Attributes:
        line_number: The line number in the comparison.
        baseline_content: Content from baseline output (None if line was added).
        replay_content: Content from replay output (None if line was removed).
        change_type: Type of change for this line.

    Validation:
        The model enforces semantic consistency between change_type and content fields:

        - ``change_type="added"``: baseline_content MUST be None (line only exists in replay)
        - ``change_type="removed"``: replay_content MUST be None (line only exists in baseline)
        - ``change_type="unchanged"``: both contents must be equal (if both present)
        - ``change_type="modified"``: both must be present AND different

    Thread Safety:
        This model is immutable (frozen=True) and safe for concurrent access.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    line_number: int = Field(ge=1, description="Line number (1-indexed, must be >= 1)")
    baseline_content: str | None
    replay_content: str | None
    change_type: Literal["unchanged", "modified", "added", "removed"]

    @model_validator(mode="after")
    def validate_change_type_consistency(self) -> Self:
        """Validate semantic consistency between change_type and content fields.

        Raises:
            ValueError: If change_type is inconsistent with content field values.

        Returns:
            Self: The validated model instance.
        """
        if self.change_type == "added":
            if self.baseline_content is not None:
                raise ValueError(
                    "change_type='added' requires baseline_content to be None "
                    "(added lines only exist in replay output)"
                )
        elif self.change_type == "removed":
            if self.replay_content is not None:
                raise ValueError(
                    "change_type='removed' requires replay_content to be None "
                    "(removed lines only exist in baseline output)"
                )
        elif self.change_type == "unchanged":
            if (
                self.baseline_content is not None
                and self.replay_content is not None
                and self.baseline_content != self.replay_content
            ):
                raise ValueError(
                    "change_type='unchanged' requires baseline_content and replay_content "
                    "to be equal when both are present"
                )
        elif self.change_type == "modified":
            if self.baseline_content is None:
                raise ValueError(
                    "change_type='modified' requires baseline_content to be present"
                )
            if self.replay_content is None:
                raise ValueError(
                    "change_type='modified' requires replay_content to be present"
                )
            if self.baseline_content == self.replay_content:
                raise ValueError(
                    "change_type='modified' requires baseline_content and replay_content "
                    "to be different (use 'unchanged' for identical content)"
                )
        return self


__all__ = ["ModelDiffLine"]
