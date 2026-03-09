# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for ModelOnexEnvelope.chunking field extension."""

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from omnibase_core.models.chunking.model_chunk_metadata import ModelChunkMetadata
from omnibase_core.models.core.model_onex_envelope import ModelOnexEnvelope
from omnibase_core.models.primitives.model_semver import ModelSemVer

FIXED_SERIES_ID = UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")
DEFAULT_VERSION = ModelSemVer(major=1, minor=0, patch=0)


def _make_envelope(**kwargs: object) -> ModelOnexEnvelope:
    return ModelOnexEnvelope(
        envelope_id=uuid4(),
        envelope_version=DEFAULT_VERSION,
        correlation_id=uuid4(),
        source_node="test_node",
        operation="TEST_OP",
        payload={"key": "value"},
        timestamp=datetime.now(UTC),
        **kwargs,
    )


@pytest.mark.unit
class TestModelOnexEnvelopeChunkingField:
    def test_chunking_defaults_to_none(self) -> None:
        env = _make_envelope()
        assert env.chunking is None

    def test_chunking_field_accepts_metadata(self) -> None:
        meta = ModelChunkMetadata(
            chunk_series_id=FIXED_SERIES_ID,
            chunk_index=0,
            chunk_count=2,
            chunk_size=512,
            total_size=1024,
            payload_checksum="sha256:abc",
            chunk_checksum="sha256:def",
            reassembly_strategy="strict_order",
        )
        env = _make_envelope(chunking=meta)
        assert env.chunking is not None
        assert env.chunking.chunk_index == 0

    def test_json_round_trip_with_chunking(self) -> None:
        meta = ModelChunkMetadata(
            chunk_series_id=FIXED_SERIES_ID,
            chunk_index=1,
            chunk_count=2,
            chunk_size=512,
            total_size=1024,
            payload_checksum="sha256:abc",
            chunk_checksum="sha256:ghi",
            reassembly_strategy="any_order",
        )
        env = _make_envelope(chunking=meta)
        restored = ModelOnexEnvelope.model_validate_json(env.model_dump_json())
        assert restored.chunking == meta

    def test_json_round_trip_without_chunking(self) -> None:
        env = _make_envelope()
        restored = ModelOnexEnvelope.model_validate_json(env.model_dump_json())
        assert restored.chunking is None
