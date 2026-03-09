# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelChunkedEnvelope — wire format transmitted by transport when chunking is active."""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.chunking.model_chunk_metadata import ModelChunkMetadata


class ModelChunkedEnvelope(BaseModel):
    """Wire-format model for a single chunk transmitted over transport.

    The transport publishes N of these (one per chunk) for a single
    logical ModelOnexEnvelope. The ReassemblyGateway buffers them by
    chunk_series_id, verifies checksums, and hands the reassembled
    logical envelope to the runtime.

    Fields:
        envelope_headers: Key/value headers extracted from the logical envelope
            (source_node, operation, correlation_id, etc.) so the transport
            can route without parsing the binary payload.
        chunk_metadata: Full chunk descriptor including series ID, index,
            checksums, and reassembly strategy.
        chunk_payload: Raw bytes of this chunk's slice of the serialized
            original envelope payload.
    """

    envelope_headers: dict[str, str] = Field(
        description="Routing headers extracted from the logical envelope.",
    )
    chunk_metadata: ModelChunkMetadata = Field(
        description="Chunk descriptor including series identity and checksums.",
    )
    chunk_payload: bytes = Field(
        description="Raw bytes slice of the serialized original envelope payload.",
    )

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        from_attributes=True,
    )
