# SPDX-FileCopyrightText: 2026 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""An individual gate as reported by a validation implementation."""

from pydantic import BaseModel, ConfigDict, Field


class ModelModelSwapValidationGate(BaseModel):
    """Preserve the gate identifier, pass flag and explanatory reason."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        from_attributes=True,
        populate_by_name=True,
        serialize_by_alias=True,
    )

    id: str = Field(min_length=1)
    passed: bool = Field(alias="pass")
    reason: str


__all__ = ["ModelModelSwapValidationGate"]
