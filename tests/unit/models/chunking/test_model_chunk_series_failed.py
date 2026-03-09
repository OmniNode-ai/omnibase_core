# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for ModelChunkSeriesFailed diagnostic event."""

from datetime import UTC, datetime
from uuid import UUID

import pytest

from omnibase_core.models.chunking.model_chunk_series_failed import (
    EnumChunkFailureReason,
    ModelChunkSeriesFailed,
)

FIXED_SERIES_ID = UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")


@pytest.mark.unit
class TestModelChunkSeriesFailed:
    def test_timeout_failure(self) -> None:
        event = ModelChunkSeriesFailed(
            chunk_series_id=FIXED_SERIES_ID,
            reason=EnumChunkFailureReason.TIMEOUT,
            received_chunk_count=2,
            expected_chunk_count=5,
            failed_at=datetime.now(UTC),
        )
        assert event.reason == EnumChunkFailureReason.TIMEOUT
        assert event.received_chunk_count == 2

    def test_checksum_failure(self) -> None:
        event = ModelChunkSeriesFailed(
            chunk_series_id=FIXED_SERIES_ID,
            reason=EnumChunkFailureReason.CHECKSUM_MISMATCH,
            received_chunk_count=5,
            expected_chunk_count=5,
            failed_at=datetime.now(UTC),
            detail="Expected sha256:abc, got sha256:bad",
        )
        assert event.reason == EnumChunkFailureReason.CHECKSUM_MISMATCH
        assert event.detail is not None

    def test_json_round_trip(self) -> None:
        event = ModelChunkSeriesFailed(
            chunk_series_id=FIXED_SERIES_ID,
            reason=EnumChunkFailureReason.DUPLICATE_CHUNK,
            received_chunk_count=3,
            expected_chunk_count=3,
            failed_at=datetime.now(UTC),
        )
        restored = ModelChunkSeriesFailed.model_validate_json(event.model_dump_json())
        assert restored.chunk_series_id == FIXED_SERIES_ID
