# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ProtocolChunkableEnvelope — minimal serialization contract for chunkable envelopes."""

from typing import Protocol, runtime_checkable


@runtime_checkable
class ProtocolChunkableEnvelope(Protocol):
    """Serialization protocol that domain envelopes implement to support chunking.

    Domain envelopes do NOT need to know about chunking. They only need to be
    serializable to/from bytes so the ChunkingGateway can slice them.

    The ChunkingGateway uses this protocol; domain code never calls it directly.
    """

    def to_bytes(self) -> bytes:
        """Serialize the logical envelope to a byte representation.

        Returns:
            bytes: Deterministic serialization of the full envelope. The
                ChunkingGateway will slice these bytes into chunks.
        """
        ...

    @classmethod
    def from_bytes(cls, data: bytes) -> "ProtocolChunkableEnvelope":
        """Deserialize a logical envelope from bytes.

        Args:
            data: Full byte representation (concatenation of all chunk payloads).

        Returns:
            Reconstructed logical envelope.

        Raises:
            ValueError: If data cannot be deserialized into a valid envelope.
        """
        ...
