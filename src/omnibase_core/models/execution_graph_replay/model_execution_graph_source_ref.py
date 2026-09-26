# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
from __future__ import annotations

"""Exact location of an ingested event-ledger record."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ModelExecutionGraphSourceRef(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    topic: str = Field(min_length=1)
    partition: int = Field(ge=0)
    kafka_offset: int = Field(ge=0)
    ingest_epoch: Literal[1] | None = None
    ingest_seq: int | None = Field(default=None, ge=1)

    @model_validator(mode="after")
    def validate_watermark_presence_pair(self) -> ModelExecutionGraphSourceRef:
        if (self.ingest_epoch is None) != (self.ingest_seq is None):
            raise ValueError(
                "ingest_epoch and ingest_seq must both be set or both null"
            )
        return self
