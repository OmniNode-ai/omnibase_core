# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
from __future__ import annotations

"""Exact recorded event-ledger position, without a write-order claim."""

from pydantic import BaseModel, ConfigDict, Field


class ModelExecutionGraphSourceRef(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    topic: str = Field(min_length=1)
    partition: int = Field(ge=0)
    kafka_offset: int = Field(ge=0)
