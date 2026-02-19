# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

#
# SPDX-License-Identifier: Apache-2.0
"""
Unit tests for ModelCorpusTimeRange - Time Range Model for Execution Corpus.

Tests cover:
- Model immutability (frozen)
- Time range validation (min_time <= max_time)
- Duration property calculation
- Edge cases (equal times)

.. versionadded:: 0.4.0
    Added as part of Replay Infrastructure (OMN-1116)
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from omnibase_core.errors import ModelOnexError
from omnibase_core.models.replay.model_corpus_time_range import ModelCorpusTimeRange


class TestModelCorpusTimeRangeValidation:
    """Tests for ModelCorpusTimeRange time ordering validation."""

    def test_valid_time_range_min_less_than_max(self) -> None:
        """Test that valid time range (min < max) works."""
        min_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
        max_time = datetime(2024, 1, 1, 13, 0, 0, tzinfo=UTC)

        time_range = ModelCorpusTimeRange(
            min_time=min_time,
            max_time=max_time,
        )

        assert time_range.min_time == min_time
        assert time_range.max_time == max_time

    def test_valid_time_range_equal_times(self) -> None:
        """Test that equal times (min == max) works."""
        same_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)

        time_range = ModelCorpusTimeRange(
            min_time=same_time,
            max_time=same_time,
        )

        assert time_range.min_time == same_time
        assert time_range.max_time == same_time
        assert time_range.duration == timedelta(0)

    def test_invalid_time_range_min_greater_than_max_raises_error(self) -> None:
        """Test that invalid time range (min > max) raises ModelOnexError."""
        min_time = datetime(2024, 1, 1, 14, 0, 0, tzinfo=UTC)  # Later time
        max_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)  # Earlier time

        with pytest.raises(ModelOnexError) as exc_info:
            ModelCorpusTimeRange(
                min_time=min_time,
                max_time=max_time,
            )

        assert "min_time must be <= max_time" in str(exc_info.value)


class TestModelCorpusTimeRangeDuration:
    """Tests for ModelCorpusTimeRange duration property."""

    def test_duration_calculation(self) -> None:
        """Test that duration is correctly calculated."""
        min_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
        max_time = datetime(2024, 1, 1, 13, 30, 0, tzinfo=UTC)

        time_range = ModelCorpusTimeRange(
            min_time=min_time,
            max_time=max_time,
        )

        assert time_range.duration == timedelta(hours=1, minutes=30)

    def test_duration_zero_for_equal_times(self) -> None:
        """Test that duration is zero when min == max."""
        same_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)

        time_range = ModelCorpusTimeRange(
            min_time=same_time,
            max_time=same_time,
        )

        assert time_range.duration == timedelta(0)


class TestModelCorpusTimeRangeImmutability:
    """Tests for ModelCorpusTimeRange immutability (frozen)."""

    def test_model_is_frozen(self) -> None:
        """Test that model is immutable after creation."""
        time_range = ModelCorpusTimeRange(
            min_time=datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC),
            max_time=datetime(2024, 1, 1, 13, 0, 0, tzinfo=UTC),
        )

        with pytest.raises(Exception):  # Pydantic raises ValidationError for frozen
            time_range.min_time = datetime(2024, 1, 1, 11, 0, 0, tzinfo=UTC)  # type: ignore[misc]
