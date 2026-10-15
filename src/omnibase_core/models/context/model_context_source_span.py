# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelContextSourceSpan — a line or character range inside a source (OMN-18531 / TC.1)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.enums.enum_context_span_unit import EnumContextSpanUnit

__all__ = ["ModelContextSourceSpan"]


class ModelContextSourceSpan(BaseModel):
    """Half-open range [start, end) of an entry's text within its source_ref."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    unit: EnumContextSpanUnit
    start: int = Field(ge=0)
    end: int = Field(ge=0)

    @model_validator(mode="after")
    def _end_not_before_start(self) -> ModelContextSourceSpan:
        if self.end < self.start:
            raise ValueError(f"span end {self.end} is before start {self.start}")
        return self
