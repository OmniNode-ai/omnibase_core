# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Wire consumer declaration model."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ModelWireConsumer(BaseModel):
    """Consumer declaration in a wire schema contract."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    repo: str = Field(..., description="Repository containing the consumer")
    file: str = Field(..., description="Path to consumer code")
    model: str = Field(..., description="Pydantic model class name")
    ingest_shim: str | None = Field(
        default=None, description="Ingest shim model name if active"
    )
    ingest_shim_retirement_ticket: str | None = Field(
        default=None, description="Ticket for shim retirement"
    )
