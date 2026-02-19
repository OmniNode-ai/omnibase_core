# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

#
# SPDX-License-Identifier: Apache-2.0

"""
Tests for ModelPayloadLogEvent.

This module tests the ModelPayloadLogEvent model for log event emission intents, verifying:
1. Field validation (level, message, context)
2. Discriminator value
3. Serialization/deserialization
4. Immutability
5. Default values
"""

import pytest
from pydantic import ValidationError

from omnibase_core.models.reducer.payloads import ModelPayloadLogEvent


@pytest.mark.unit
class TestModelPayloadLogEventInstantiation:
    """Test ModelPayloadLogEvent instantiation."""

    def test_create_with_required_fields(self) -> None:
        """Test creating payload with required fields only."""
        payload = ModelPayloadLogEvent(level="INFO", message="Test message")
        assert payload.level == "INFO"
        assert payload.message == "Test message"
        assert payload.intent_type == "log_event"

    def test_create_with_all_fields(self) -> None:
        """Test creating payload with all fields."""
        payload = ModelPayloadLogEvent(
            level="ERROR",
            message="Error occurred",
            context={"user_id": "123", "action": "login"},
        )
        assert payload.level == "ERROR"
        assert payload.message == "Error occurred"
        assert payload.context == {"user_id": "123", "action": "login"}


@pytest.mark.unit
class TestModelPayloadLogEventDiscriminator:
    """Test discriminator field."""

    def test_intent_type_value(self) -> None:
        """Test that intent_type is 'log_event'."""
        payload = ModelPayloadLogEvent(level="INFO", message="Test")
        assert payload.intent_type == "log_event"

    def test_intent_type_in_serialization(self) -> None:
        """Test that intent_type is included in serialization."""
        payload = ModelPayloadLogEvent(level="INFO", message="Test")
        data = payload.model_dump()
        assert data["intent_type"] == "log_event"


@pytest.mark.unit
class TestModelPayloadLogEventLevelValidation:
    """Test level field validation."""

    def test_valid_level_debug(self) -> None:
        """Test valid DEBUG level."""
        payload = ModelPayloadLogEvent(level="DEBUG", message="Debug message")
        assert payload.level == "DEBUG"

    def test_valid_level_info(self) -> None:
        """Test valid INFO level."""
        payload = ModelPayloadLogEvent(level="INFO", message="Info message")
        assert payload.level == "INFO"

    def test_valid_level_warning(self) -> None:
        """Test valid WARNING level."""
        payload = ModelPayloadLogEvent(level="WARNING", message="Warning message")
        assert payload.level == "WARNING"

    def test_valid_level_error(self) -> None:
        """Test valid ERROR level."""
        payload = ModelPayloadLogEvent(level="ERROR", message="Error message")
        assert payload.level == "ERROR"

    def test_invalid_level_rejected(self) -> None:
        """Test that invalid level is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelPayloadLogEvent(level="CRITICAL", message="Test")  # type: ignore[arg-type]
        assert "level" in str(exc_info.value)

    def test_lowercase_level_rejected(self) -> None:
        """Test that lowercase level is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelPayloadLogEvent(level="info", message="Test")  # type: ignore[arg-type]
        assert "level" in str(exc_info.value)


@pytest.mark.unit
class TestModelPayloadLogEventMessageValidation:
    """Test message field validation."""

    def test_message_required(self) -> None:
        """Test that message is required."""
        with pytest.raises(ValidationError) as exc_info:
            ModelPayloadLogEvent(level="INFO")  # type: ignore[call-arg]
        assert "message" in str(exc_info.value)

    def test_message_min_length(self) -> None:
        """Test message minimum length validation."""
        with pytest.raises(ValidationError) as exc_info:
            ModelPayloadLogEvent(level="INFO", message="")
        assert "message" in str(exc_info.value)

    def test_message_max_length(self) -> None:
        """Test message maximum length validation."""
        long_message = "a" * 4097
        with pytest.raises(ValidationError) as exc_info:
            ModelPayloadLogEvent(level="INFO", message=long_message)
        assert "message" in str(exc_info.value)


@pytest.mark.unit
class TestModelPayloadLogEventDefaultValues:
    """Test default values."""

    def test_default_context(self) -> None:
        """Test default context is empty dict."""
        payload = ModelPayloadLogEvent(level="INFO", message="Test")
        assert payload.context == {}


@pytest.mark.unit
class TestModelPayloadLogEventImmutability:
    """Test frozen/immutability."""

    def test_cannot_modify_level(self) -> None:
        """Test that level cannot be modified after creation."""
        payload = ModelPayloadLogEvent(level="INFO", message="Test")
        with pytest.raises(ValidationError):
            payload.level = "ERROR"  # type: ignore[misc]

    def test_cannot_modify_message(self) -> None:
        """Test that message cannot be modified after creation."""
        payload = ModelPayloadLogEvent(level="INFO", message="Test")
        with pytest.raises(ValidationError):
            payload.message = "New message"  # type: ignore[misc]


@pytest.mark.unit
class TestModelPayloadLogEventSerialization:
    """Test serialization/deserialization."""

    def test_roundtrip_serialization(self) -> None:
        """Test roundtrip serialization."""
        original = ModelPayloadLogEvent(
            level="WARNING",
            message="Warning message",
            context={"source": "test"},
        )
        data = original.model_dump()
        restored = ModelPayloadLogEvent.model_validate(data)
        assert restored == original

    def test_json_roundtrip(self) -> None:
        """Test JSON roundtrip serialization."""
        original = ModelPayloadLogEvent(level="INFO", message="Test")
        json_str = original.model_dump_json()
        restored = ModelPayloadLogEvent.model_validate_json(json_str)
        assert restored == original

    def test_serialization_includes_all_fields(self) -> None:
        """Test that serialization includes all fields."""
        payload = ModelPayloadLogEvent(level="INFO", message="Test")
        data = payload.model_dump()
        expected_keys = {"intent_type", "level", "message", "context"}
        assert set(data.keys()) == expected_keys


@pytest.mark.unit
class TestModelPayloadLogEventExtraFieldsRejected:
    """Test that extra fields are rejected."""

    def test_reject_extra_field(self) -> None:
        """Test that extra fields are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelPayloadLogEvent(
                level="INFO",
                message="Test",
                unknown_field="value",  # type: ignore[call-arg]
            )
        assert "extra_forbidden" in str(exc_info.value)


@pytest.mark.unit
class TestModelPayloadLogEventContextTypes:
    """Test context field with various value types."""

    def test_context_with_string_values(self) -> None:
        """Test context with string values."""
        payload = ModelPayloadLogEvent(
            level="INFO", message="Test", context={"key": "value"}
        )
        assert payload.context["key"] == "value"

    def test_context_with_numeric_values(self) -> None:
        """Test context with numeric values."""
        payload = ModelPayloadLogEvent(
            level="INFO", message="Test", context={"count": 42, "ratio": 0.5}
        )
        assert payload.context["count"] == 42
        assert payload.context["ratio"] == 0.5

    def test_context_with_nested_dict(self) -> None:
        """Test context with nested dictionary."""
        payload = ModelPayloadLogEvent(
            level="INFO",
            message="Test",
            context={"nested": {"inner": "value"}},
        )
        assert payload.context["nested"] == {"inner": "value"}

    def test_context_with_list_values(self) -> None:
        """Test context with list values."""
        payload = ModelPayloadLogEvent(
            level="INFO",
            message="Test",
            context={"items": [1, 2, 3]},
        )
        assert payload.context["items"] == [1, 2, 3]
