# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Diagnostic event emitted when a chunk series cannot be reassembled."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_chunk_failure_reason import EnumChunkFailureReason

__all__ = ["EnumChunkFailureReason", "ModelChunkSeriesFailed"]


class ModelChunkSeriesFailed(BaseModel):
    """Diagnostic event emitted when a chunk series cannot be reassembled.

    Published to a dead-letter or diagnostics topic when the ReassemblyGateway
    gives up on a chunk series. No partial results are ever passed to domain code;
    this event is the failure signal.
    """

    chunk_series_id: UUID = Field(
        description="UUID of the chunk series that failed.",
    )
    reason: EnumChunkFailureReason = Field(
        description="Categorized failure reason.",
    )
    received_chunk_count: int = Field(
        ge=0,
        description="Number of chunks actually received before abandonment.",
    )
    expected_chunk_count: int = Field(
        ge=1,
        description="Total number of chunks expected in this series.",
    )
    failed_at: datetime = Field(
        description="UTC timestamp when the series was abandoned.",
    )
    detail: str | None = Field(
        default=None,
        description="Optional human-readable detail (e.g., checksum values).",
    )

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        from_attributes=True,
    )
