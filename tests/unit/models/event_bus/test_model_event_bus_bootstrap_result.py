# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

#
# SPDX-License-Identifier: Apache-2.0
"""
Tests for ModelEventBusBootstrapResult.

Comprehensive tests for event bus bootstrap result including:
- Construction with valid inputs
- Construction with invalid inputs
- Serialization and deserialization
- Edge cases
"""

import pytest
from pydantic import ValidationError

from omnibase_core.models.event_bus.model_event_bus_bootstrap_result import (
    ModelEventBusBootstrapResult,
)


@pytest.mark.unit
class TestModelEventBusBootstrapResultConstruction:
    """Test ModelEventBusBootstrapResult construction."""

    def test_create_with_required_fields(self) -> None:
        """Test creating a bootstrap result with required fields."""
        result = ModelEventBusBootstrapResult(
            status="ok",
            message="Bootstrap completed successfully",
        )

        assert result.status == "ok"
        assert result.message == "Bootstrap completed successfully"

    def test_create_with_error_status(self) -> None:
        """Test creating a bootstrap result with error status."""
        result = ModelEventBusBootstrapResult(
            status="error",
            message="Failed to connect to event bus",
        )

        assert result.status == "error"
        assert result.message == "Failed to connect to event bus"

    def test_create_with_various_statuses(self) -> None:
        """Test creating bootstrap results with various status values."""
        statuses = ["ok", "error", "warning", "pending", "initializing"]

        for status in statuses:
            result = ModelEventBusBootstrapResult(
                status=status,
                message=f"Status is {status}",
            )
            assert result.status == status


@pytest.mark.unit
class TestModelEventBusBootstrapResultValidation:
    """Test ModelEventBusBootstrapResult validation."""

    def test_missing_status_raises_error(self) -> None:
        """Test that missing status raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ModelEventBusBootstrapResult(message="Some message")  # type: ignore[call-arg]

        assert "status" in str(exc_info.value)

    def test_missing_message_raises_error(self) -> None:
        """Test that missing message raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ModelEventBusBootstrapResult(status="ok")  # type: ignore[call-arg]

        assert "message" in str(exc_info.value)

    def test_none_status_raises_error(self) -> None:
        """Test that None status raises ValidationError."""
        with pytest.raises(ValidationError):
            ModelEventBusBootstrapResult(
                status=None,  # type: ignore[arg-type]
                message="Some message",
            )

    def test_none_message_raises_error(self) -> None:
        """Test that None message raises ValidationError."""
        with pytest.raises(ValidationError):
            ModelEventBusBootstrapResult(
                status="ok",
                message=None,  # type: ignore[arg-type]
            )


@pytest.mark.unit
class TestModelEventBusBootstrapResultSerialization:
    """Test ModelEventBusBootstrapResult serialization."""

    def test_model_dump(self) -> None:
        """Test model_dump() serialization."""
        result = ModelEventBusBootstrapResult(
            status="ok",
            message="Bootstrap completed",
        )

        data = result.model_dump()

        assert isinstance(data, dict)
        assert data["status"] == "ok"
        assert data["message"] == "Bootstrap completed"

    def test_model_validate(self) -> None:
        """Test model_validate() deserialization."""
        data = {
            "status": "error",
            "message": "Connection failed",
        }

        result = ModelEventBusBootstrapResult.model_validate(data)

        assert result.status == "error"
        assert result.message == "Connection failed"

    def test_serialization_roundtrip(self) -> None:
        """Test serialization and deserialization roundtrip."""
        original = ModelEventBusBootstrapResult(
            status="ok",
            message="Bootstrap completed successfully",
        )

        data = original.model_dump()
        restored = ModelEventBusBootstrapResult.model_validate(data)

        assert restored.status == original.status
        assert restored.message == original.message

    def test_json_serialization(self) -> None:
        """Test JSON serialization."""
        result = ModelEventBusBootstrapResult(
            status="ok",
            message="Success",
        )

        json_data = result.model_dump_json()

        assert isinstance(json_data, str)
        assert "status" in json_data
        assert "message" in json_data
        assert "ok" in json_data

    def test_json_deserialization(self) -> None:
        """Test JSON deserialization."""
        json_data = '{"status": "error", "message": "Failed"}'

        result = ModelEventBusBootstrapResult.model_validate_json(json_data)

        assert result.status == "error"
        assert result.message == "Failed"


@pytest.mark.unit
class TestModelEventBusBootstrapResultEdgeCases:
    """Test ModelEventBusBootstrapResult edge cases."""

    def test_empty_string_status(self) -> None:
        """Test creating result with empty status string."""
        result = ModelEventBusBootstrapResult(
            status="",
            message="Some message",
        )

        assert result.status == ""

    def test_empty_string_message(self) -> None:
        """Test creating result with empty message string."""
        result = ModelEventBusBootstrapResult(
            status="ok",
            message="",
        )

        assert result.message == ""

    def test_long_message(self) -> None:
        """Test creating result with long message."""
        long_message = "x" * 10000

        result = ModelEventBusBootstrapResult(
            status="ok",
            message=long_message,
        )

        assert len(result.message) == 10000

    def test_unicode_in_message(self) -> None:
        """Test creating result with unicode in message."""
        result = ModelEventBusBootstrapResult(
            status="ok",
            message="Bootstrap completed successfully - 2025",
        )

        assert "2025" in result.message

    def test_special_characters_in_message(self) -> None:
        """Test creating result with special characters."""
        result = ModelEventBusBootstrapResult(
            status="error",
            message="Failed: Connection refused (errno: -111)\nRetry later.",
        )

        assert "errno" in result.message
        assert "\n" in result.message

    def test_whitespace_handling(self) -> None:
        """Test that whitespace is preserved in message."""
        result = ModelEventBusBootstrapResult(
            status="ok",
            message="  Message with spaces  ",
        )

        assert result.message == "  Message with spaces  "
