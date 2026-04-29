# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Wire field constraints model."""

from __future__ import annotations

from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ModelWireFieldConstraints(BaseModel):
    """Optional constraints on a wire schema field."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    ge: float | None = Field(default=None, description="Greater than or equal to")
    le: float | None = Field(default=None, description="Less than or equal to")
    min_length: int | None = Field(default=None, description="Minimum string length")
    max_length: int | None = Field(default=None, description="Maximum string length")
    enum: list[str] | None = Field(default=None, description="Allowed enum values")

    @model_validator(mode="after")
    def validate_constraint_ranges(self) -> Self:
        """Reject contradictory numeric and length constraints."""
        if self.ge is not None and self.le is not None and self.ge > self.le:
            msg = "ge must be less than or equal to le"
            raise ValueError(msg)
        if (
            self.min_length is not None
            and self.max_length is not None
            and self.min_length > self.max_length
        ):
            msg = "min_length must be less than or equal to max_length"
            raise ValueError(msg)
        return self
