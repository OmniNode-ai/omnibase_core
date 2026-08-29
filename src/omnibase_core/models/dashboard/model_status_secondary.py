# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""The number a status tile shows next to its verdict (OMN-16884, Phase C3).

"DLQ critical" and "DLQ critical — depth 41,902" are different operational
facts, and only the second one tells an operator whether to page. The kind is
declared (``count`` / ``depth`` / ``rate``) so a renderer formats the number
without pattern-matching on a label.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_status_secondary_kind import EnumStatusSecondaryKind

__all__ = ["ModelStatusSecondary"]


class ModelStatusSecondary(BaseModel):
    """A numeric secondary displayed alongside a tile's status."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        from_attributes=True,
        allow_inf_nan=False,
    )

    kind: EnumStatusSecondaryKind = Field(
        ...,
        description="What the number measures: count, depth, or rate",
    )
    value: float = Field(
        ...,
        description="The measured value as delivered by the upstream projection",
    )
    label: str = Field(
        ...,
        description="Short human-readable label for the number (e.g. 'DLQ depth')",
        min_length=1,
    )
    unit: str | None = Field(
        default=None,
        description=(
            "Unit or per-interval suffix (e.g. 'msg/min'). None where the "
            "number is dimensionless, which a count usually is."
        ),
        min_length=1,
    )
