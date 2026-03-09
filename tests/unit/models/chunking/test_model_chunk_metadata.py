# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for ModelChunkMetadata."""

from datetime import UTC, datetime
from uuid import UUID

import pytest
from pydantic import ValidationError

from omnibase_core.models.chunking.model_chunk_metadata import ModelChunkMetadata

FIXED_SERIES_ID = UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")


@pytest.mark.unit
class TestModelChunkMetadataInstantiation:
    def test_required_fields_only(self) -> None:
        m = ModelChunkMetadata(
            chunk_series_id=FIXED_SERIES_ID,
            chunk_index=0,
            chunk_count=3,
            chunk_size=512,
            total_size=1400,
            payload_checksum="sha256:abc123",
            chunk_checksum="sha256:def456",
            reassembly_strategy="strict_order",
        )
        assert m.chunk_index == 0
        assert m.chunk_count == 3
        assert m.priority == "normal"
        assert m.expiry_timestamp is None

    def test_optional_fields(self) -> None:
        expiry = datetime(2030, 1, 1, tzinfo=UTC)
        m = ModelChunkMetadata(
            chunk_series_id=FIXED_SERIES_ID,
            chunk_index=1,
            chunk_count=2,
            chunk_size=256,
            total_size=512,
            payload_checksum="sha256:abc",
            chunk_checksum="sha256:def",
            reassembly_strategy="any_order",
            expiry_timestamp=expiry,
            priority="high",
        )
        assert m.priority == "high"
        assert m.expiry_timestamp == expiry

    def test_invalid_reassembly_strategy_raises(self) -> None:
        with pytest.raises(ValidationError):
            ModelChunkMetadata(
                chunk_series_id=FIXED_SERIES_ID,
                chunk_index=0,
                chunk_count=1,
                chunk_size=100,
                total_size=100,
                payload_checksum="sha256:x",
                chunk_checksum="sha256:x",
                reassembly_strategy="unknown_strategy",  # type: ignore[arg-type]
            )

    def test_invalid_priority_raises(self) -> None:
        with pytest.raises(ValidationError):
            ModelChunkMetadata(
                chunk_series_id=FIXED_SERIES_ID,
                chunk_index=0,
                chunk_count=1,
                chunk_size=100,
                total_size=100,
                payload_checksum="sha256:x",
                chunk_checksum="sha256:x",
                reassembly_strategy="strict_order",
                priority="critical",  # type: ignore[arg-type]
            )

    def test_negative_chunk_index_raises(self) -> None:
        with pytest.raises(ValidationError):
            ModelChunkMetadata(
                chunk_series_id=FIXED_SERIES_ID,
                chunk_index=-1,
                chunk_count=1,
                chunk_size=100,
                total_size=100,
                payload_checksum="sha256:x",
                chunk_checksum="sha256:x",
                reassembly_strategy="strict_order",
            )

    def test_frozen_immutability(self) -> None:
        m = ModelChunkMetadata(
            chunk_series_id=FIXED_SERIES_ID,
            chunk_index=0,
            chunk_count=1,
            chunk_size=100,
            total_size=100,
            payload_checksum="sha256:x",
            chunk_checksum="sha256:x",
            reassembly_strategy="strict_order",
        )
        with pytest.raises(Exception):
            m.chunk_index = 5  # type: ignore[misc]

    def test_json_round_trip(self) -> None:
        m = ModelChunkMetadata(
            chunk_series_id=FIXED_SERIES_ID,
            chunk_index=0,
            chunk_count=2,
            chunk_size=512,
            total_size=1024,
            payload_checksum="sha256:abc",
            chunk_checksum="sha256:def",
            reassembly_strategy="strict_order",
        )
        restored = ModelChunkMetadata.model_validate_json(m.model_dump_json())
        assert restored == m
