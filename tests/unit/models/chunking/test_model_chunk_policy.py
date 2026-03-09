# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for ModelChunkPolicy."""

import pytest
from pydantic import ValidationError

from omnibase_core.models.chunking.model_chunk_policy import ModelChunkPolicy


@pytest.mark.unit
class TestModelChunkPolicy:
    def test_default_values(self) -> None:
        p = ModelChunkPolicy()
        assert p.max_payload_size_bytes == 900_000
        assert p.chunk_target_size_bytes == 256_000
        assert p.max_chunk_count == 100
        assert p.enabled is True
        assert p.reassembly_timeout_seconds == 60

    def test_custom_values(self) -> None:
        p = ModelChunkPolicy(
            max_payload_size_bytes=500_000,
            chunk_target_size_bytes=100_000,
            max_chunk_count=10,
            enabled=False,
        )
        assert not p.enabled
        assert p.max_chunk_count == 10

    def test_chunk_target_must_be_positive(self) -> None:
        with pytest.raises(ValidationError):
            ModelChunkPolicy(chunk_target_size_bytes=0)

    def test_max_chunk_count_must_be_positive(self) -> None:
        with pytest.raises(ValidationError):
            ModelChunkPolicy(max_chunk_count=0)

    def test_json_round_trip(self) -> None:
        p = ModelChunkPolicy(max_payload_size_bytes=1_000_000)
        restored = ModelChunkPolicy.model_validate_json(p.model_dump_json())
        assert restored == p
