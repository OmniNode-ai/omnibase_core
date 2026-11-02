# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Field source: a constant (OMN-21997)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

__all__ = ["ModelViewFieldSourceConstant"]

#: Markers of a template or formula. A constant is data, not code.
_EXPRESSION_MARKERS = ("{{", "${", "{%")


class ModelViewFieldSourceConstant(BaseModel):
    """Use a fixed text value for every row."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    source_kind: Literal["constant"] = Field(
        default="constant", description="Discriminator for the field source union"
    )
    value: str = Field(..., description="The constant, taken literally")

    @field_validator("value")
    @classmethod
    def validate_value_is_not_an_expression(cls, value: str) -> str:
        """Refuse a value that is a formula or template rather than a constant.

        Raises:
            ValueError: If the value starts with ``=`` or holds a template marker.
        """
        if value.startswith("=") or any(m in value for m in _EXPRESSION_MARKERS):
            raise ValueError(
                f"constant '{value}' looks like an expression; a field map "
                f"takes columns, constants and references only"
            )
        return value
