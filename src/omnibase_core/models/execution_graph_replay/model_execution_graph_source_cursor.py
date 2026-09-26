# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Inclusive transactional ingest watermark for one Kafka partition."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ModelExecutionGraphSourceCursor(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    topic: str = Field(min_length=1)
    partition: int = Field(ge=0)
    ingest_epoch: Literal[1]
    max_ingest_seq: int = Field(ge=0)
