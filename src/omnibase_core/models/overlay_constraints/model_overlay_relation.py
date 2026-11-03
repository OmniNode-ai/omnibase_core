# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""One relation between overlay keys, as a contract declares it (OMN-22185)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ModelOverlayRelation(BaseModel):
    """A named comparison: ``<sum of keys or numbers> <operator> <sum of keys or numbers>``."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    relation_name: str = Field(
        min_length=1, description="Name a refusal cites, such as the plan's R1"
    )
    expression: str = Field(
        min_length=1,
        description=(
            "Two sums joined by one comparison operator; a term is an overlay key, "
            "a derived name or a number"
        ),
    )
