# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelAntipatternExample — good or bad code snippet for an antipattern (OMN-11910)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ModelAntipatternExample(BaseModel):
    """A good or bad code snippet illustrating an antipattern."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    kind: Literal["good", "bad"] = Field(
        description="Whether this is a good or bad example"
    )
    code: str = Field(description="Code snippet")
    label: str = Field(description="Short label for the example")


__all__ = ["ModelAntipatternExample"]
