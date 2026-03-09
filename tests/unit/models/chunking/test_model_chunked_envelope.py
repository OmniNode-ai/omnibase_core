# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for ModelChunkedEnvelope wire model."""

from uuid import UUID

import pytest

from omnibase_core.models.chunking.model_chunk_metadata import ModelChunkMetadata
from omnibase_core.models.chunking.model_chunked_envelope import ModelChunkedEnvelope

FIXED_SERIES_ID = UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")


def _make_metadata(index: int = 0, count: int = 2) -> ModelChunkMetadata:
    payload = b"x" * 256
    return ModelChunkMetadata(
        chunk_series_id=FIXED_SERIES_ID,
        chunk_index=index,
        chunk_count=count,
        chunk_size=len(payload),
        total_size=len(payload) * count,
        payload_checksum="sha256:whole",
        chunk_checksum=f"sha256:chunk{index}",
        reassembly_strategy="strict_order",
    )


@pytest.mark.unit
class TestModelChunkedEnvelope:
    def test_basic_construction(self) -> None:
        meta = _make_metadata()
        env = ModelChunkedEnvelope(
            envelope_headers={"source_node": "test", "operation": "OP"},
            chunk_metadata=meta,
            chunk_payload=b"hello world",
        )
        assert env.chunk_payload == b"hello world"
        assert env.chunk_metadata.chunk_index == 0

    def test_empty_headers_allowed(self) -> None:
        meta = _make_metadata()
        env = ModelChunkedEnvelope(
            envelope_headers={},
            chunk_metadata=meta,
            chunk_payload=b"data",
        )
        assert env.envelope_headers == {}

    def test_json_round_trip(self) -> None:
        meta = _make_metadata(index=1)
        env = ModelChunkedEnvelope(
            envelope_headers={"op": "TEST"},
            chunk_metadata=meta,
            chunk_payload=b"\x00\x01\x02\x03",
        )
        restored = ModelChunkedEnvelope.model_validate_json(env.model_dump_json())
        assert restored.chunk_payload == env.chunk_payload
        assert restored.chunk_metadata == meta

    def test_frozen(self) -> None:
        meta = _make_metadata()
        env = ModelChunkedEnvelope(
            envelope_headers={},
            chunk_metadata=meta,
            chunk_payload=b"x",
        )
        with pytest.raises(Exception):
            env.chunk_payload = b"y"  # type: ignore[misc]
