"""Tests for ModelEnvelopePayload.

This module tests the typed envelope payload model including:
- Basic creation and field access
- Round-trip serialization (to_dict/from_dict)
- Warning behavior for data loss scenarios
- Reserved key collision handling
- Immutable update methods
"""

from __future__ import annotations

import warnings
from datetime import UTC, datetime

import pytest

from omnibase_core.errors import ModelOnexError
from omnibase_core.models.common.model_envelope_payload import (
    ModelEnvelopePayload,
    PayloadDataValue,
)


class TestModelEnvelopePayloadBasic:
    """Test basic ModelEnvelopePayload functionality."""

    def test_create_with_all_fields(self) -> None:
        """Test creating payload with all typed fields."""
        payload = ModelEnvelopePayload(
            event_type="user.created",
            source="auth-service",
            timestamp="2024-01-15T10:30:00Z",
            correlation_id="abc-123",
            data={"user_id": "12345"},
        )
        assert payload.event_type == "user.created"
        assert payload.source == "auth-service"
        assert payload.timestamp == "2024-01-15T10:30:00Z"
        assert payload.correlation_id == "abc-123"
        assert payload.data == {"user_id": "12345"}

    def test_create_with_minimal_fields(self) -> None:
        """Test creating payload with no fields."""
        payload = ModelEnvelopePayload()
        assert payload.event_type is None
        assert payload.source is None
        assert payload.timestamp is None
        assert payload.correlation_id is None
        assert payload.data == {}

    def test_data_field_types(self) -> None:
        """Test that data field accepts all PayloadDataValue types."""
        payload = ModelEnvelopePayload(
            data={
                "string_val": "hello",
                "int_val": 42,
                "float_val": 3.14,
                "bool_val": True,
                "list_val": ["a", "b", "c"],
                "none_val": None,
            }
        )
        assert payload.data["string_val"] == "hello"
        assert payload.data["int_val"] == 42
        assert payload.data["float_val"] == 3.14
        assert payload.data["bool_val"] is True
        assert payload.data["list_val"] == ["a", "b", "c"]
        assert payload.data["none_val"] is None

    def test_max_data_entries_validation(self) -> None:
        """Test that data dict size is validated."""
        large_data = {f"key_{i}": f"value_{i}" for i in range(101)}
        with pytest.raises(ModelOnexError) as exc_info:
            ModelEnvelopePayload(data=large_data)
        assert "exceeds maximum size" in str(exc_info.value)


class TestModelEnvelopePayloadRoundTrip:
    """Test round-trip serialization."""

    def test_to_dict_from_dict_roundtrip(self) -> None:
        """Test that to_dict/from_dict round-trip preserves data."""
        original = ModelEnvelopePayload(
            event_type="user.created",
            source="auth-service",
            timestamp="2024-01-15T10:30:00Z",
            correlation_id="abc-123",
            data={"user_id": "12345", "active": True},
        )

        # Round-trip
        dict_repr = original.to_dict()
        restored = ModelEnvelopePayload.from_dict(dict_repr)

        assert restored == original

    def test_to_dict_from_dict_roundtrip_empty(self) -> None:
        """Test round-trip with empty payload."""
        original = ModelEnvelopePayload()
        dict_repr = original.to_dict()
        restored = ModelEnvelopePayload.from_dict(dict_repr)
        assert restored == original

    def test_to_dict_from_dict_roundtrip_data_only(self) -> None:
        """Test round-trip with data field only."""
        original = ModelEnvelopePayload(
            data={"key1": "value1", "key2": 42, "key3": True}
        )
        dict_repr = original.to_dict()
        restored = ModelEnvelopePayload.from_dict(dict_repr)
        assert restored == original

    def test_to_dict_output_format(self) -> None:
        """Test to_dict output format with nested data."""
        payload = ModelEnvelopePayload(
            event_type="test",
            data={"foo": "bar"},
        )
        result = payload.to_dict()
        assert "event_type" in result
        assert "data" in result
        assert isinstance(result["data"], dict)
        assert result["data"]["foo"] == "bar"

    def test_from_dict_flat_format(self) -> None:
        """Test from_dict with flat format (unknown keys go to data)."""
        input_dict: dict[str, PayloadDataValue] = {
            "event_type": "user.created",
            "source": "auth-service",
            "custom_field": "custom_value",
            "another_field": 42,
        }
        payload = ModelEnvelopePayload.from_dict(input_dict)
        assert payload.event_type == "user.created"
        assert payload.source == "auth-service"
        assert payload.data["custom_field"] == "custom_value"
        assert payload.data["another_field"] == 42


class TestModelEnvelopePayloadWarnings:
    """Test warning behavior for edge cases."""

    def test_from_dict_warns_on_nested_dict_values(self) -> None:
        """Test that from_dict warns when dict values are skipped."""
        input_dict = {
            "event_type": "test",
            "nested_obj": {"foo": "bar"},  # This should trigger warning
            "valid_field": "value",
        }

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            payload = ModelEnvelopePayload.from_dict(input_dict)

            # Should have one warning about skipped dict
            assert len(w) == 1
            assert "skipped" in str(w[0].message).lower()
            assert "nested_obj" in str(w[0].message)

        # Verify the dict value was indeed skipped
        assert "nested_obj" not in payload.data
        assert payload.data["valid_field"] == "value"

    def test_from_dict_warns_on_nested_dict_in_data(self) -> None:
        """Test warning for nested dict inside data dict."""
        input_dict = {
            "event_type": "test",
            "data": {
                "valid_key": "value",
                "nested_dict": {"inner": "value"},  # type: ignore[dict-item]
            },
        }

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            payload = ModelEnvelopePayload.from_dict(input_dict)

            assert len(w) == 1
            assert "data.nested_dict" in str(w[0].message)

        assert "nested_dict" not in payload.data
        assert payload.data["valid_key"] == "value"

    def test_to_string_dict_warns_on_reserved_key(self) -> None:
        """Test that to_string_dict warns when prefixing reserved keys."""
        payload = ModelEnvelopePayload(
            event_type="typed_event_type",
            data={"event_type": "data_event_type"},  # Reserved key in data
        )

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = payload.to_string_dict()

            # Should warn about prefixed key
            assert len(w) == 1
            assert "prefixed" in str(w[0].message).lower()
            assert "event_type" in str(w[0].message)

        # Verify the key was prefixed
        assert result["event_type"] == "typed_event_type"
        assert result["data_event_type"] == "data_event_type"

    def test_to_string_dict_warns_on_collision(self) -> None:
        """Test warning when prefixed key collides with existing data key."""
        payload = ModelEnvelopePayload(
            event_type="typed_value",
            data={
                "event_type": "from_reserved",
                "data_event_type": "from_original",
            },
        )

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = payload.to_string_dict()

            # Should have two warnings: prefixed and collision
            assert len(w) == 2
            warning_messages = [str(warning.message) for warning in w]
            assert any("prefixed" in msg.lower() for msg in warning_messages)
            assert any("collision" in msg.lower() for msg in warning_messages)

        # One value will overwrite the other (data loss)
        assert "event_type" in result
        assert "data_event_type" in result


class TestModelEnvelopePayloadStringDict:
    """Test to_string_dict and from_string_dict conversion."""

    def test_to_string_dict_basic(self) -> None:
        """Test basic to_string_dict conversion."""
        payload = ModelEnvelopePayload(
            event_type="test",
            source="service",
            data={"key": "value"},
        )
        result = payload.to_string_dict()
        assert result["event_type"] == "test"
        assert result["source"] == "service"
        assert result["key"] == "value"

    def test_to_string_dict_bool_conversion(self) -> None:
        """Test that booleans are converted to lowercase strings."""
        payload = ModelEnvelopePayload(data={"is_active": True, "is_deleted": False})
        result = payload.to_string_dict()
        assert result["is_active"] == "true"
        assert result["is_deleted"] == "false"

    def test_to_string_dict_list_conversion(self) -> None:
        """Test that lists are converted to comma-separated strings."""
        payload = ModelEnvelopePayload(data={"tags": ["a", "b", "c"]})
        result = payload.to_string_dict()
        assert result["tags"] == "a,b,c"

    def test_to_string_dict_numeric_conversion(self) -> None:
        """Test that numbers are converted to strings."""
        payload = ModelEnvelopePayload(data={"count": 42, "rate": 3.14})
        result = payload.to_string_dict()
        assert result["count"] == "42"
        assert result["rate"] == "3.14"

    def test_from_string_dict(self) -> None:
        """Test from_string_dict conversion."""
        input_dict = {
            "event_type": "test",
            "source": "service",
            "custom_key": "custom_value",
        }
        payload = ModelEnvelopePayload.from_string_dict(input_dict)
        assert payload.event_type == "test"
        assert payload.source == "service"
        assert payload.data["custom_key"] == "custom_value"


class TestModelEnvelopePayloadImmutableUpdates:
    """Test immutable update methods."""

    def test_set_data_returns_new_instance(self) -> None:
        """Test that set_data returns a new instance."""
        original = ModelEnvelopePayload(event_type="test")
        updated = original.set_data("key", "value")

        assert original is not updated
        assert "key" not in original.data
        assert updated.data["key"] == "value"
        assert updated.event_type == "test"

    def test_with_timestamp_sets_current_time(self) -> None:
        """Test that with_timestamp sets current UTC time."""
        original = ModelEnvelopePayload(event_type="test")
        before = datetime.now(UTC)
        updated = original.with_timestamp()
        after = datetime.now(UTC)

        assert original is not updated
        assert original.timestamp is None
        assert updated.timestamp is not None

        # Parse the ISO timestamp
        ts = datetime.fromisoformat(updated.timestamp.replace("Z", "+00:00"))
        assert before <= ts <= after

    def test_with_timestamp_custom_time(self) -> None:
        """Test with_timestamp with custom datetime."""
        original = ModelEnvelopePayload()
        custom_time = datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC)
        updated = original.with_timestamp(custom_time)

        assert updated.timestamp == custom_time.isoformat()


class TestModelEnvelopePayloadAccessors:
    """Test accessor methods."""

    def test_get_typed_field(self) -> None:
        """Test get() for typed fields."""
        payload = ModelEnvelopePayload(
            event_type="test",
            source="service",
        )
        assert payload.get("event_type") == "test"
        assert payload.get("source") == "service"
        assert payload.get("timestamp") is None
        assert payload.get("timestamp", "default") == "default"

    def test_get_data_field(self) -> None:
        """Test get() for data fields."""
        payload = ModelEnvelopePayload(data={"key": "value"})
        assert payload.get("key") == "value"
        assert payload.get("missing") is None
        assert payload.get("missing", "default") == "default"

    def test_get_data_method(self) -> None:
        """Test get_data() for data-only access."""
        payload = ModelEnvelopePayload(
            event_type="test",
            data={"key": "value"},
        )
        assert payload.get_data("key") == "value"
        assert payload.get_data("event_type") is None  # Not in data dict

    def test_has_typed_field(self) -> None:
        """Test has() for typed fields."""
        payload = ModelEnvelopePayload(event_type="test")
        assert payload.has("event_type") is True
        assert payload.has("source") is False

    def test_has_data_field(self) -> None:
        """Test has() for data fields."""
        payload = ModelEnvelopePayload(data={"key": "value"})
        assert payload.has("key") is True
        assert payload.has("missing") is False

    def test_contains_dunder(self) -> None:
        """Test __contains__ implementation."""
        payload = ModelEnvelopePayload(
            event_type="test",
            data={"key": "value"},
        )
        assert "event_type" in payload
        assert "key" in payload
        assert "missing" not in payload


class TestModelEnvelopePayloadLenBool:
    """Test __len__ and __bool__ implementations."""

    def test_len_empty(self) -> None:
        """Test len() of empty payload."""
        payload = ModelEnvelopePayload()
        assert len(payload) == 0

    def test_len_typed_fields(self) -> None:
        """Test len() counts typed fields."""
        payload = ModelEnvelopePayload(
            event_type="test",
            source="service",
        )
        assert len(payload) == 2

    def test_len_data_fields(self) -> None:
        """Test len() counts data fields."""
        payload = ModelEnvelopePayload(data={"key1": "val1", "key2": "val2"})
        assert len(payload) == 2

    def test_len_combined(self) -> None:
        """Test len() counts both typed and data fields."""
        payload = ModelEnvelopePayload(
            event_type="test",
            data={"key": "value"},
        )
        assert len(payload) == 2

    def test_bool_empty(self) -> None:
        """Test bool() of empty payload."""
        payload = ModelEnvelopePayload()
        assert bool(payload) is False

    def test_bool_with_typed_field(self) -> None:
        """Test bool() with typed field."""
        payload = ModelEnvelopePayload(event_type="test")
        assert bool(payload) is True

    def test_bool_with_data(self) -> None:
        """Test bool() with data field."""
        payload = ModelEnvelopePayload(data={"key": "value"})
        assert bool(payload) is True
