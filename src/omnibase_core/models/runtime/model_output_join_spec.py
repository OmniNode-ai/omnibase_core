# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Declared terminal-event/projection join target for a liveness surface.

OMN-15126 implementation of the OMN-14845 design (design §4).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["ModelOutputJoinSpec"]


class ModelOutputJoinSpec(BaseModel):
    """Declared terminal-event/projection join target for one surface (design §4)."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    terminal_topic: str = Field(..., min_length=1)
    projection_table: str = Field(..., min_length=1)
    projection_key_fields: tuple[str, ...] = Field(..., min_length=1)
    projection_key_canonicalization: str = Field(
        ...,
        min_length=1,
        description=(
            "Declared serialization for a composite key, e.g. 'json_sorted_keys', "
            "so a composite key has one unambiguous string form."
        ),
    )
    expected_value_predicate: str = Field(
        ...,
        min_length=1,
        description=(
            "Required, non-empty expression evaluated against the observed "
            "projection value, e.g. \"status == 'COMPLETED' and error_code is "
            'None" — this is what makes the join an actual proof, not a '
            "presence check."
        ),
    )
