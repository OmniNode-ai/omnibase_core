# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelChunkPolicy — configuration governing when and how envelopes are chunked."""

from pydantic import BaseModel, ConfigDict, Field


class ModelChunkPolicy(BaseModel):
    """Policy controlling envelope chunking at the transport boundary.

    The ChunkingGateway evaluates this policy for each publish call.
    If chunking is disabled or the payload is below max_payload_size_bytes,
    the envelope is published as-is.

    All size values are in bytes. All timeout values are in seconds.
    """

    enabled: bool = Field(
        default=True,
        description="Whether chunking is active for this transport/tenant scope.",
    )
    max_payload_size_bytes: int = Field(
        default=900_000,
        ge=1,
        description=(
            "Payload size in bytes above which chunking is triggered. "
            "Kafka default max.message.bytes is ~1 MB; default is 900 KB."
        ),
    )
    chunk_target_size_bytes: int = Field(
        default=256_000,
        ge=1,
        description="Target size in bytes for each individual chunk.",
    )
    max_chunk_count: int = Field(
        default=100,
        ge=1,
        description="Maximum number of chunks allowed for a single logical message.",
    )
    reassembly_timeout_seconds: float = Field(
        default=60.0,
        gt=0,
        description=(
            "Seconds the ReassemblyGateway waits for all chunks before "
            "emitting a ChunkSeriesFailed event."
        ),
    )

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        from_attributes=True,
    )
