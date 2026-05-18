# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""ModelCursorContract — describes the cursor mechanism for a projection (OMN-11192)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ModelCursorContract(BaseModel):
    """Describes the cursor type and replay capability for a projection."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        from_attributes=True,
    )

    cursor_type: Literal["kafka_offset", "timestamp", "sequence"] = Field(
        ...,
        description="The mechanism used to track projection position.",
    )

    supports_replay: bool = Field(
        ...,
        description="Whether this projection can be rebuilt from its cursor position.",
    )
