# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Exact Kafka event coordinates for a demand-aware liveness join.

OMN-15126 implementation of the OMN-14845 design (design §5).
"""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["ModelEventRef"]


class ModelEventRef(BaseModel):
    """Exact coordinates of one observed Kafka event (design §5)."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    topic: str = Field(..., min_length=1)
    partition: int = Field(..., ge=0)
    offset: int = Field(..., ge=0)
    event_id: UUID
