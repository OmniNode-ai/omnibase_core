"""Tests for Claude Code hook event models.

Validates ModelClaudeCodeHookEvent and ModelClaudeCodeHookEventPayload including
construction, immutability, validation, helper methods, and serialization.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from omnibase_core.enums.hooks.claude_code.enum_claude_code_hook_event_type import (
    EnumClaudeCodeHookEventType,
)
from omnibase_core.models.hooks.claude_code.model_claude_code_hook_event import (
    ModelClaudeCodeHookEvent,
)
from omnibase_core.models.hooks.claude_code.model_claude_code_hook_event_payload import (
    ModelClaudeCodeHookEventPayload,
)


@pytest.mark.unit
class TestModelClaudeCodeHookEvent:
    """Test ModelClaudeCodeHookEvent functionality."""

    def test_valid_construction_required_fields(self) -> None:
        """Test valid construction with all required fields."""
        timestamp = datetime.now(UTC)
        payload = ModelClaudeCodeHookEventPayload()

        event = ModelClaudeCodeHookEvent(
            event_type=EnumClaudeCodeHookEventType.USER_PROMPT_SUBMIT,
            session_id="session-abc123",
            timestamp_utc=timestamp,
            payload=payload,
        )

        assert event.event_type == EnumClaudeCodeHookEventType.USER_PROMPT_SUBMIT
        assert event.session_id == "session-abc123"
        assert event.timestamp_utc == timestamp
        assert event.payload == payload
        assert event.correlation_id is None

    def test_valid_construction_with_correlation_id(self) -> None:
        """Test valid construction with optional correlation_id."""
        timestamp = datetime.now(UTC)
        correlation_id = uuid4()

        event = ModelClaudeCodeHookEvent(
            event_type=EnumClaudeCodeHookEventType.SESSION_START,
            session_id="session-xyz789",
            correlation_id=correlation_id,
            timestamp_utc=timestamp,
            payload=ModelClaudeCodeHookEventPayload(),
        )

        assert event.correlation_id == correlation_id

    def test_model_is_frozen_immutable(self) -> None:
        """Test that model is frozen and rejects attribute assignment."""
        event = ModelClaudeCodeHookEvent(
            event_type=EnumClaudeCodeHookEventType.USER_PROMPT_SUBMIT,
            session_id="session-123",
            timestamp_utc=datetime.now(UTC),
            payload=ModelClaudeCodeHookEventPayload(),
        )

        with pytest.raises(ValidationError) as exc_info:
            event.session_id = "modified-session"  # type: ignore[misc]

        assert (
            "frozen" in str(exc_info.value).lower()
            or "instance is immutable" in str(exc_info.value).lower()
        )

    def test_extra_forbid_rejects_unknown_fields(self) -> None:
        """Test that extra='forbid' rejects unknown fields."""
        timestamp = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            ModelClaudeCodeHookEvent(
                event_type=EnumClaudeCodeHookEventType.USER_PROMPT_SUBMIT,
                session_id="session-123",
                timestamp_utc=timestamp,
                payload=ModelClaudeCodeHookEventPayload(),
                unknown_field="should_fail",  # type: ignore[call-arg]
            )

        assert "extra" in str(exc_info.value).lower() or "unknown_field" in str(
            exc_info.value
        )

    def test_missing_required_field_raises_error(self) -> None:
        """Test that missing required fields raise ValidationError."""
        with pytest.raises(ValidationError):
            ModelClaudeCodeHookEvent(
                event_type=EnumClaudeCodeHookEventType.USER_PROMPT_SUBMIT,
                # Missing session_id, timestamp_utc, payload
            )  # type: ignore[call-arg]

    def test_session_id_is_string_not_uuid(self) -> None:
        """Test that session_id accepts strings per Claude Code API contract."""
        event = ModelClaudeCodeHookEvent(
            event_type=EnumClaudeCodeHookEventType.SESSION_START,
            session_id="not-a-uuid-just-a-string",
            timestamp_utc=datetime.now(UTC),
            payload=ModelClaudeCodeHookEventPayload(),
        )

        assert event.session_id == "not-a-uuid-just-a-string"
        assert isinstance(event.session_id, str)

    def test_naive_datetime_raises_validation_error(self) -> None:
        """Test that naive datetime (no timezone) raises ValidationError."""
        naive_timestamp = datetime(2024, 1, 15, 12, 30, 45)  # No tzinfo

        with pytest.raises(ValidationError) as exc_info:
            ModelClaudeCodeHookEvent(
                event_type=EnumClaudeCodeHookEventType.USER_PROMPT_SUBMIT,
                session_id="session-123",
                timestamp_utc=naive_timestamp,
                payload=ModelClaudeCodeHookEventPayload(),
            )

        assert "timezone-aware" in str(exc_info.value)


@pytest.mark.unit
class TestModelClaudeCodeHookEventHelperMethods:
    """Test helper methods on ModelClaudeCodeHookEvent."""

    def _create_event(
        self, event_type: EnumClaudeCodeHookEventType
    ) -> ModelClaudeCodeHookEvent:
        """Create a test event with the specified type."""
        return ModelClaudeCodeHookEvent(
            event_type=event_type,
            session_id="test-session",
            timestamp_utc=datetime.now(UTC),
            payload=ModelClaudeCodeHookEventPayload(),
        )

    def test_is_agentic_event_returns_true_for_agentic_types(self) -> None:
        """Test is_agentic_event returns True for agentic loop events."""
        agentic_types = [
            EnumClaudeCodeHookEventType.PRE_TOOL_USE,
            EnumClaudeCodeHookEventType.PERMISSION_REQUEST,
            EnumClaudeCodeHookEventType.POST_TOOL_USE,
            EnumClaudeCodeHookEventType.POST_TOOL_USE_FAILURE,
            EnumClaudeCodeHookEventType.SUBAGENT_START,
            EnumClaudeCodeHookEventType.SUBAGENT_STOP,
        ]

        for event_type in agentic_types:
            event = self._create_event(event_type)
            assert event.is_agentic_event() is True, (
                f"Expected {event_type} to be agentic"
            )

    def test_is_agentic_event_returns_false_for_non_agentic_types(self) -> None:
        """Test is_agentic_event returns False for non-agentic events."""
        non_agentic_types = [
            EnumClaudeCodeHookEventType.SESSION_START,
            EnumClaudeCodeHookEventType.SESSION_END,
            EnumClaudeCodeHookEventType.USER_PROMPT_SUBMIT,
            EnumClaudeCodeHookEventType.NOTIFICATION,
            EnumClaudeCodeHookEventType.STOP,
            EnumClaudeCodeHookEventType.PRE_COMPACT,
        ]

        for event_type in non_agentic_types:
            event = self._create_event(event_type)
            assert event.is_agentic_event() is False, (
                f"Expected {event_type} to NOT be agentic"
            )

    def test_is_session_event_returns_true_for_session_types(self) -> None:
        """Test is_session_event returns True for session lifecycle events."""
        session_types = [
            EnumClaudeCodeHookEventType.SESSION_START,
            EnumClaudeCodeHookEventType.SESSION_END,
            EnumClaudeCodeHookEventType.STOP,
            EnumClaudeCodeHookEventType.PRE_COMPACT,
        ]

        for event_type in session_types:
            event = self._create_event(event_type)
            assert event.is_session_event() is True, (
                f"Expected {event_type} to be session event"
            )

    def test_is_session_event_returns_false_for_non_session_types(self) -> None:
        """Test is_session_event returns False for non-session events."""
        non_session_types = [
            EnumClaudeCodeHookEventType.USER_PROMPT_SUBMIT,
            EnumClaudeCodeHookEventType.PRE_TOOL_USE,
            EnumClaudeCodeHookEventType.PERMISSION_REQUEST,
            EnumClaudeCodeHookEventType.POST_TOOL_USE,
            EnumClaudeCodeHookEventType.POST_TOOL_USE_FAILURE,
            EnumClaudeCodeHookEventType.SUBAGENT_START,
            EnumClaudeCodeHookEventType.SUBAGENT_STOP,
            EnumClaudeCodeHookEventType.NOTIFICATION,
        ]

        for event_type in non_session_types:
            event = self._create_event(event_type)
            assert event.is_session_event() is False, (
                f"Expected {event_type} to NOT be session event"
            )


@pytest.mark.unit
class TestModelClaudeCodeHookEventSerialization:
    """Test serialization and deserialization of ModelClaudeCodeHookEvent."""

    def test_json_serialization(self) -> None:
        """Test JSON serialization produces valid output."""
        timestamp = datetime(2024, 1, 15, 12, 30, 45, tzinfo=UTC)
        correlation_id = UUID("12345678-1234-5678-1234-567812345678")

        event = ModelClaudeCodeHookEvent(
            event_type=EnumClaudeCodeHookEventType.USER_PROMPT_SUBMIT,
            session_id="test-session-001",
            correlation_id=correlation_id,
            timestamp_utc=timestamp,
            payload=ModelClaudeCodeHookEventPayload(),
        )

        json_data = event.model_dump(mode="json")

        assert json_data["event_type"] == "UserPromptSubmit"
        assert json_data["session_id"] == "test-session-001"
        assert json_data["correlation_id"] == "12345678-1234-5678-1234-567812345678"
        assert "2024-01-15" in json_data["timestamp_utc"]
        assert json_data["payload"] == {}

    def test_json_deserialization(self) -> None:
        """Test JSON deserialization produces valid model."""
        json_data = {
            "event_type": "SessionStart",
            "session_id": "deserialized-session",
            "correlation_id": "abcd1234-abcd-1234-abcd-1234abcd5678",
            "timestamp_utc": "2024-06-20T10:00:00+00:00",
            "payload": {},
        }

        event = ModelClaudeCodeHookEvent.model_validate(json_data)

        assert event.event_type == EnumClaudeCodeHookEventType.SESSION_START
        assert event.session_id == "deserialized-session"
        assert event.correlation_id == UUID("abcd1234-abcd-1234-abcd-1234abcd5678")
        assert isinstance(event.payload, ModelClaudeCodeHookEventPayload)

    def test_round_trip_serialization(self) -> None:
        """Test full round-trip serialization preserves data."""
        timestamp = datetime.now(UTC)
        correlation_id = uuid4()

        original = ModelClaudeCodeHookEvent(
            event_type=EnumClaudeCodeHookEventType.PRE_TOOL_USE,
            session_id="roundtrip-session",
            correlation_id=correlation_id,
            timestamp_utc=timestamp,
            payload=ModelClaudeCodeHookEventPayload(),
        )

        # Serialize to JSON string
        json_str = original.model_dump_json()

        # Deserialize back
        json_data = json.loads(json_str)
        deserialized = ModelClaudeCodeHookEvent.model_validate(json_data)

        assert deserialized.event_type == original.event_type
        assert deserialized.session_id == original.session_id
        assert deserialized.correlation_id == original.correlation_id
        # Timestamps may have microsecond differences in serialization
        assert deserialized.timestamp_utc.date() == original.timestamp_utc.date()

    def test_deserialization_without_optional_fields(self) -> None:
        """Test deserialization works without optional correlation_id."""
        json_data = {
            "event_type": "Notification",
            "session_id": "minimal-session",
            "timestamp_utc": "2024-01-01T00:00:00+00:00",
            "payload": {},
        }

        event = ModelClaudeCodeHookEvent.model_validate(json_data)

        assert event.event_type == EnumClaudeCodeHookEventType.NOTIFICATION
        assert event.correlation_id is None


@pytest.mark.unit
class TestModelClaudeCodeHookEventPayload:
    """Test ModelClaudeCodeHookEventPayload base class."""

    def test_base_class_instantiation(self) -> None:
        """Test base class can be instantiated with no fields."""
        payload = ModelClaudeCodeHookEventPayload()

        assert payload is not None
        assert isinstance(payload, ModelClaudeCodeHookEventPayload)

    def test_model_is_frozen_immutable(self) -> None:
        """Test that payload model is frozen."""
        payload = ModelClaudeCodeHookEventPayload()

        # Attempting to add a new attribute should fail on frozen model
        with pytest.raises((ValidationError, TypeError, AttributeError)):
            payload.new_field = "value"  # type: ignore[attr-defined]

    def test_extra_allow_accepts_unknown_fields(self) -> None:
        """Test that extra='allow' accepts unknown fields for forward compatibility."""
        # Create payload with arbitrary extra fields
        payload = ModelClaudeCodeHookEventPayload.model_validate(
            {"future_field": "value", "another_field": 123, "nested": {"key": "val"}}
        )

        assert payload is not None
        # Extra fields should be accessible
        assert payload.model_extra is not None
        assert payload.model_extra.get("future_field") == "value"
        assert payload.model_extra.get("another_field") == 123

    def test_subclass_with_additional_fields(self) -> None:
        """Test that payload can be subclassed with additional fields."""

        class PromptSubmitPayload(ModelClaudeCodeHookEventPayload):
            """Custom payload for prompt submission."""

            prompt: str
            prompt_length: int

        payload = PromptSubmitPayload(prompt="Hello, Claude!", prompt_length=14)

        assert payload.prompt == "Hello, Claude!"
        assert payload.prompt_length == 14
        assert isinstance(payload, ModelClaudeCodeHookEventPayload)

    def test_subclass_inherits_frozen_behavior(self) -> None:
        """Test that subclasses inherit frozen behavior."""

        class CustomPayload(ModelClaudeCodeHookEventPayload):
            """Custom frozen payload."""

            value: str

        payload = CustomPayload(value="test")

        with pytest.raises((ValidationError, TypeError, AttributeError)):
            payload.value = "modified"  # type: ignore[misc]

    def test_subclass_with_extra_allow(self) -> None:
        """Test that subclasses still allow extra fields."""

        class ExtensiblePayload(ModelClaudeCodeHookEventPayload):
            """Payload that should still accept extras."""

            known_field: str

        payload = ExtensiblePayload.model_validate(
            {"known_field": "known", "unknown_field": "accepted"}
        )

        assert payload.known_field == "known"
        assert payload.model_extra is not None
        assert payload.model_extra.get("unknown_field") == "accepted"

    def test_empty_payload_serialization(self) -> None:
        """Test that empty payload serializes correctly."""
        payload = ModelClaudeCodeHookEventPayload()
        json_data = payload.model_dump()

        assert json_data == {}

    def test_payload_with_extras_serialization(self) -> None:
        """Test that payload with extra fields serializes correctly."""
        payload = ModelClaudeCodeHookEventPayload.model_validate(
            {"extra_key": "extra_value"}
        )

        json_data = payload.model_dump()
        assert json_data.get("extra_key") == "extra_value"


@pytest.mark.unit
class TestModelClaudeCodeHookEventIntegration:
    """Test integration scenarios between event and payload."""

    def test_event_with_custom_payload_subclass(self) -> None:
        """Test event can hold custom payload subclass."""

        class ToolUsePayload(ModelClaudeCodeHookEventPayload):
            """Payload for tool use events."""

            tool_name: str
            tool_input: dict[str, str]

        payload = ToolUsePayload(tool_name="read_file", tool_input={"path": "/test.py"})

        event = ModelClaudeCodeHookEvent(
            event_type=EnumClaudeCodeHookEventType.PRE_TOOL_USE,
            session_id="tool-session",
            timestamp_utc=datetime.now(UTC),
            payload=payload,
        )

        assert isinstance(event.payload, ToolUsePayload)
        assert event.payload.tool_name == "read_file"  # type: ignore[attr-defined]

    def test_from_attributes_compatibility(self) -> None:
        """Test from_attributes=True enables attribute-based construction."""

        # Create a simple namespace object with the required attributes
        class MockEventData:
            event_type = EnumClaudeCodeHookEventType.SESSION_END
            session_id = "mock-session"
            correlation_id = None
            timestamp_utc = datetime.now(UTC)
            payload = ModelClaudeCodeHookEventPayload()

        mock_data = MockEventData()
        event = ModelClaudeCodeHookEvent.model_validate(mock_data)

        assert event.event_type == EnumClaudeCodeHookEventType.SESSION_END
        assert event.session_id == "mock-session"

    def test_all_event_types_constructable(self) -> None:
        """Test that all event types can be used to construct events."""
        for event_type in EnumClaudeCodeHookEventType:
            event = ModelClaudeCodeHookEvent(
                event_type=event_type,
                session_id=f"session-{event_type.value}",
                timestamp_utc=datetime.now(UTC),
                payload=ModelClaudeCodeHookEventPayload(),
            )

            assert event.event_type == event_type
            assert event_type.value in event.session_id
