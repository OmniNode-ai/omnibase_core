# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Inclusive Kafka offset bound for one explicitly selected partition.

This is deliberately not a write-order cursor.  The watermark follow-up
ticket owns that stronger contract; Phase 2 records offset-bound append
invariance as pending rather than claiming it here.
"""

from pydantic import BaseModel, ConfigDict, Field


class ModelExecutionGraphSourceCursor(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    topic: str = Field(min_length=1)
    partition: int = Field(ge=0)
    max_kafka_offset: int = Field(ge=0)
