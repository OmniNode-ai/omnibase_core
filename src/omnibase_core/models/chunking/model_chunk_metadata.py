# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelChunkMetadata — transport-level chunk descriptor for ONEX envelope chunking."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ModelChunkMetadata(BaseModel):
    """Immutable descriptor for a single chunk in a chunked envelope series.

    Chunking is transport-level only. Domain code constructs normal logical
    envelopes; the ChunkingGateway slices them and attaches ChunkMetadata.
    Nodes never see this model directly.

    Fields:
        chunk_series_id: UUID identifying all chunks of the same logical message.
        chunk_index: Zero-based position of this chunk in the series.
        chunk_count: Total number of expected chunks in the series.
        chunk_size: Size in bytes of this chunk's payload.
        total_size: Size in bytes of the original un-split payload.
        payload_checksum: Checksum of the full original payload (hex digest).
        chunk_checksum: Checksum of this individual chunk payload (hex digest).
        reassembly_strategy: How the consumer should reassemble chunks.
        expiry_timestamp: Optional UTC deadline after which this series is abandoned.
        priority: Scheduling hint for the reassembly buffer.
    """

    chunk_series_id: UUID = Field(
        description="UUID identifying all chunks belonging to the same logical message.",
    )
    chunk_index: int = Field(
        ge=0,
        description="Zero-based position of this chunk in the ordered series.",
    )
    chunk_count: int = Field(
        ge=1,
        description="Total number of chunks expected for this series.",
    )
    chunk_size: int = Field(
        ge=0,
        description="Size in bytes of this chunk's payload.",
    )
    total_size: int = Field(
        ge=0,
        description="Size in bytes of the full original payload before chunking.",
    )
    payload_checksum: str = Field(
        description="Checksum of the complete original payload (algorithm:hex format).",
    )
    chunk_checksum: str = Field(
        description="Checksum of this individual chunk payload (algorithm:hex format).",
    )
    reassembly_strategy: Literal["strict_order", "any_order"] = Field(
        description=(
            "Reassembly strategy: 'strict_order' requires sequential delivery; "
            "'any_order' tolerates out-of-order arrival."
        ),
    )
    expiry_timestamp: datetime | None = Field(
        default=None,
        description="Optional UTC timestamp after which this chunk series is abandoned.",
    )
    priority: Literal["low", "normal", "high"] = Field(
        default="normal",
        description="Scheduling priority hint for the reassembly buffer.",
    )

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        from_attributes=True,
    )
