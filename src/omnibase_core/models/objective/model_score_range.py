# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Score range model for objective spec bounds declaration.

Defines the declared min/max bounds for an objective's score output.
Part of the objective functions and reward architecture (OMN-2537).
"""

from pydantic import BaseModel, ConfigDict, Field, model_validator

__all__ = ["ModelScoreRange"]


class ModelScoreRange(BaseModel):
    """Declared score bounds for an ObjectiveSpec.

    The minimum and maximum values must be explicitly declared in the
    ObjectiveSpec. They are not inferred at runtime. Changing the range
    requires a version bump on the containing ObjectiveSpec.

    Attributes:
        min: The minimum score value (inclusive lower bound).
        max: The maximum score value (inclusive upper bound).
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
    )

    min: float = Field(description="Minimum score value (inclusive lower bound)")
    max: float = Field(description="Maximum score value (inclusive upper bound)")

    @model_validator(mode="after")
    def validate_range_order(self) -> "ModelScoreRange":
        """Ensure min is strictly less than max.

        Returns:
            Self after validation.

        Raises:
            ValueError: If min >= max.
        """
        if self.min >= self.max:
            raise ValueError(
                f"ModelScoreRange.min ({self.min}) must be strictly less than "
                f"ModelScoreRange.max ({self.max})"
            )
        return self
