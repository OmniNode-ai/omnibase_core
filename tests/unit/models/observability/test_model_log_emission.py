# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for ModelLogEmission."""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from omnibase_core.enums.enum_severity import EnumSeverity
from omnibase_core.models.observability.model_log_emission import ModelLogEmission


class TestModelLogEmission:
    """Tests for ModelLogEmission model."""

    def test_create_with_defaults(self) -> None:
        """Test creating log emission with default level."""
        log = ModelLogEmission(message="Test message")
        assert log.message == "Test message"
        assert log.level == EnumSeverity.INFO
        assert log.context == {}
        assert log.timestamp is not None

    def test_create_with_all_fields(self) -> None:
        """Test creating log emission with all fields."""
        ts = datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC)
        log = ModelLogEmission(
            level=EnumSeverity.ERROR,
            message="Connection failed",
            context={"host": "db.example.com", "port": "5432"},
            timestamp=ts,
        )
        assert log.level == EnumSeverity.ERROR
        assert log.message == "Connection failed"
        assert log.context == {"host": "db.example.com", "port": "5432"}
        assert log.timestamp == ts

    def test_all_severity_levels(self) -> None:
        """Test all severity levels are accepted."""
        for level in EnumSeverity:
            log = ModelLogEmission(level=level, message="test")
            assert log.level == level

    def test_message_required(self) -> None:
        """Test that message is required."""
        with pytest.raises(ValidationError) as exc_info:
            ModelLogEmission()  # type: ignore[call-arg]
        assert "message" in str(exc_info.value)

    def test_message_min_length(self) -> None:
        """Test message minimum length validation."""
        with pytest.raises(ValidationError) as exc_info:
            ModelLogEmission(message="")
        assert "string_too_short" in str(exc_info.value)

    def test_message_max_length(self) -> None:
        """Test message maximum length validation."""
        with pytest.raises(ValidationError) as exc_info:
            ModelLogEmission(message="x" * 8193)
        assert "string_too_long" in str(exc_info.value)

    def test_timestamp_defaults_to_now(self) -> None:
        """Test that timestamp defaults to current time."""
        before = datetime.now(UTC)
        log = ModelLogEmission(message="test")
        after = datetime.now(UTC)
        assert before <= log.timestamp <= after

    def test_model_is_frozen(self) -> None:
        """Test that model is immutable."""
        log = ModelLogEmission(message="test")
        with pytest.raises(ValidationError):
            log.message = "changed"  # type: ignore[misc]

    def test_extra_fields_forbidden(self) -> None:
        """Test that extra fields are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelLogEmission(message="test", extra="value")  # type: ignore[call-arg]
        assert "extra" in str(exc_info.value).lower()
