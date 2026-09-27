# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Inclusive ledger ingest-watermark bound for one selected partition."""

from pydantic import BaseModel, ConfigDict, Field


class ModelExecutionGraphSourceCursor(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    topic: str = Field(min_length=1)
    partition: int = Field(ge=0)
    max_ingest_watermark: int = Field(ge=1)
