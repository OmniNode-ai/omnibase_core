# SPDX-FileCopyrightText: 2025 OmniNode Team
#
# SPDX-License-Identifier: Apache-2.0

"""
Tests for ModelIntentPayloadUnion discriminated union.

This module tests the discriminated union type alias, verifying:
1. Automatic type resolution based on 'intent_type' discriminator
2. All discriminator values map correctly
3. Invalid discriminator values are rejected
4. Serialization/deserialization through the union
5. Type adapter behavior for validation
"""

from typing import get_args
from uuid import uuid4

import pytest
from pydantic import TypeAdapter, ValidationError

from omnibase_core.models.reducer.payloads import (
    ModelIntentPayloadUnion,
    PayloadEmitEvent,
    PayloadExtension,
    PayloadFSMCompleted,
    PayloadFSMStateAction,
    PayloadFSMTransitionAction,
    PayloadHTTP,
    PayloadLogEvent,
    PayloadMetric,
    PayloadNotify,
    PayloadPersistResult,
    PayloadPersistState,
    PayloadWrite,
)

# TypeAdapter for validating the union type
IntentPayloadAdapter = TypeAdapter(ModelIntentPayloadUnion)


@pytest.mark.unit
class TestModelIntentPayloadUnionDiscriminator:
    """Test discriminator resolution for all payload types."""

    def test_resolve_log_event(self) -> None:
        """Test discriminator resolution for log_event."""
        data = {
            "intent_type": "log_event",
            "level": "INFO",
            "message": "Test message",
        }
        payload = IntentPayloadAdapter.validate_python(data)

        assert isinstance(payload, PayloadLogEvent)
        assert payload.intent_type == "log_event"

    def test_resolve_record_metric(self) -> None:
        """Test discriminator resolution for record_metric."""
        data = {
            "intent_type": "record_metric",
            "name": "test.metric",
            "value": 42.0,
        }
        payload = IntentPayloadAdapter.validate_python(data)

        assert isinstance(payload, PayloadMetric)
        assert payload.intent_type == "record_metric"

    def test_resolve_persist_state(self) -> None:
        """Test discriminator resolution for persist_state."""
        data = {
            "intent_type": "persist_state",
            "state_key": "fsm:test:state",
            "state_data": {"status": "active"},
        }
        payload = IntentPayloadAdapter.validate_python(data)

        assert isinstance(payload, PayloadPersistState)
        assert payload.intent_type == "persist_state"

    def test_resolve_persist_result(self) -> None:
        """Test discriminator resolution for persist_result."""
        data = {
            "intent_type": "persist_result",
            "result_key": "compute:test:result",
            "result_data": {"value": 100},
        }
        payload = IntentPayloadAdapter.validate_python(data)

        assert isinstance(payload, PayloadPersistResult)
        assert payload.intent_type == "persist_result"

    def test_resolve_write(self) -> None:
        """Test discriminator resolution for write."""
        data = {
            "intent_type": "write",
            "path": "/test/path",
            "content": "test content",
        }
        payload = IntentPayloadAdapter.validate_python(data)

        assert isinstance(payload, PayloadWrite)
        assert payload.intent_type == "write"

    def test_resolve_http_request(self) -> None:
        """Test discriminator resolution for http_request."""
        data = {
            "intent_type": "http_request",
            "url": "https://example.com/api",
        }
        payload = IntentPayloadAdapter.validate_python(data)

        assert isinstance(payload, PayloadHTTP)
        assert payload.intent_type == "http_request"

    def test_resolve_emit_event(self) -> None:
        """Test discriminator resolution for emit_event."""
        data = {
            "intent_type": "emit_event",
            "event_type": "order.created",
            "event_data": {"order_id": "123"},
            "topic": "orders",
        }
        payload = IntentPayloadAdapter.validate_python(data)

        assert isinstance(payload, PayloadEmitEvent)
        assert payload.intent_type == "emit_event"

    def test_resolve_notify(self) -> None:
        """Test discriminator resolution for notify."""
        data = {
            "intent_type": "notify",
            "channel": "email",
            "recipients": ["test@example.com"],
            "subject": "Test Subject",
            "body": "Test Body",
        }
        payload = IntentPayloadAdapter.validate_python(data)

        assert isinstance(payload, PayloadNotify)
        assert payload.intent_type == "notify"

    def test_resolve_extension(self) -> None:
        """Test discriminator resolution for extension."""
        data = {
            "intent_type": "extension",
            "extension_type": "plugin.transform",
            "plugin_name": "test-plugin",
        }
        payload = IntentPayloadAdapter.validate_python(data)

        assert isinstance(payload, PayloadExtension)
        assert payload.intent_type == "extension"

    def test_resolve_fsm_state_action(self) -> None:
        """Test discriminator resolution for fsm_state_action."""
        data = {
            "intent_type": "fsm_state_action",
            "state_name": "authenticated",
            "action_type": "on_enter",
            "action_name": "log_session",
        }
        payload = IntentPayloadAdapter.validate_python(data)

        assert isinstance(payload, PayloadFSMStateAction)
        assert payload.intent_type == "fsm_state_action"

    def test_resolve_fsm_transition_action(self) -> None:
        """Test discriminator resolution for fsm_transition_action."""
        data = {
            "intent_type": "fsm_transition_action",
            "from_state": "cart",
            "to_state": "checkout",
            "trigger": "proceed",
            "action_name": "calculate_total",
        }
        payload = IntentPayloadAdapter.validate_python(data)

        assert isinstance(payload, PayloadFSMTransitionAction)
        assert payload.intent_type == "fsm_transition_action"

    def test_resolve_fsm_completed(self) -> None:
        """Test discriminator resolution for fsm_completed."""
        fsm_id = uuid4()
        data = {
            "intent_type": "fsm_completed",
            "fsm_id": str(fsm_id),
            "final_state": "completed",
            "completion_status": "success",
        }
        payload = IntentPayloadAdapter.validate_python(data)

        assert isinstance(payload, PayloadFSMCompleted)
        assert payload.intent_type == "fsm_completed"


@pytest.mark.unit
class TestModelIntentPayloadUnionInvalidDiscriminator:
    """Test invalid discriminator handling."""

    def test_unknown_intent_type_rejected(self) -> None:
        """Test that unknown intent_type values are rejected."""
        data = {
            "intent_type": "unknown_type",
        }
        with pytest.raises(ValidationError) as exc_info:
            IntentPayloadAdapter.validate_python(data)
        # Should indicate discriminator issue
        assert "intent_type" in str(exc_info.value) or "discriminator" in str(
            exc_info.value
        )

    def test_missing_intent_type_rejected(self) -> None:
        """Test that missing intent_type field is rejected."""
        data = {
            "level": "INFO",
            "message": "Test",
        }
        with pytest.raises(ValidationError) as exc_info:
            IntentPayloadAdapter.validate_python(data)
        assert "intent_type" in str(exc_info.value) or "discriminator" in str(
            exc_info.value
        )

    def test_empty_intent_type_rejected(self) -> None:
        """Test that empty string intent_type is rejected."""
        data = {
            "intent_type": "",
            "level": "INFO",
            "message": "Test",
        }
        with pytest.raises(ValidationError):
            IntentPayloadAdapter.validate_python(data)


@pytest.mark.unit
class TestModelIntentPayloadUnionFromInstances:
    """Test union handling of already-instantiated payloads."""

    def test_log_event_instance(self) -> None:
        """Test validating PayloadLogEvent instance."""
        instance = PayloadLogEvent(level="INFO", message="Test")
        validated = IntentPayloadAdapter.validate_python(instance)
        assert isinstance(validated, PayloadLogEvent)

    def test_metric_instance(self) -> None:
        """Test validating PayloadMetric instance."""
        instance = PayloadMetric(name="test.metric", value=42.0)
        validated = IntentPayloadAdapter.validate_python(instance)
        assert isinstance(validated, PayloadMetric)

    def test_write_instance(self) -> None:
        """Test validating PayloadWrite instance."""
        instance = PayloadWrite(path="/test", content="data")
        validated = IntentPayloadAdapter.validate_python(instance)
        assert isinstance(validated, PayloadWrite)

    def test_http_instance(self) -> None:
        """Test validating PayloadHTTP instance."""
        instance = PayloadHTTP(url="https://example.com")
        validated = IntentPayloadAdapter.validate_python(instance)
        assert isinstance(validated, PayloadHTTP)

    def test_emit_event_instance(self) -> None:
        """Test validating PayloadEmitEvent instance."""
        instance = PayloadEmitEvent(
            event_type="test.event", event_data={"key": "value"}, topic="test-topic"
        )
        validated = IntentPayloadAdapter.validate_python(instance)
        assert isinstance(validated, PayloadEmitEvent)


@pytest.mark.unit
class TestModelIntentPayloadUnionSerialization:
    """Test serialization through the union type."""

    def test_serialize_log_event_via_union(self) -> None:
        """Test serialization of log_event through union."""
        data = {
            "intent_type": "log_event",
            "level": "INFO",
            "message": "Test message",
            "context": {"key": "value"},
        }
        payload = IntentPayloadAdapter.validate_python(data)
        serialized = payload.model_dump()

        assert serialized["intent_type"] == "log_event"
        assert serialized["level"] == "INFO"
        assert serialized["message"] == "Test message"

    def test_serialize_write_via_union(self) -> None:
        """Test serialization of write through union."""
        data = {
            "intent_type": "write",
            "path": "/test/path",
            "content": "test content",
            "content_type": "application/json",
        }
        payload = IntentPayloadAdapter.validate_python(data)
        serialized = payload.model_dump()

        assert serialized["intent_type"] == "write"
        assert serialized["path"] == "/test/path"
        assert serialized["content"] == "test content"

    def test_roundtrip_all_types(self) -> None:
        """Test roundtrip serialization for all payload types."""
        payloads = [
            PayloadLogEvent(level="INFO", message="Test"),
            PayloadMetric(name="test.metric", value=42.0),
            PayloadWrite(path="/test", content="data"),
            PayloadHTTP(url="https://example.com"),
            PayloadPersistState(state_key="key", state_data={"status": "active"}),
            PayloadPersistResult(result_key="key", result_data={"value": 1}),
            PayloadEmitEvent(
                event_type="test.event", event_data={}, topic="test-topic"
            ),
            PayloadNotify(
                channel="email",
                recipients=["test@example.com"],
                subject="Test",
                body="Test body",
            ),
            PayloadExtension(extension_type="plugin.test", plugin_name="test"),
        ]

        for original in payloads:
            serialized = original.model_dump()
            restored = IntentPayloadAdapter.validate_python(serialized)
            assert type(restored) is type(original)
            assert restored.intent_type == original.intent_type


@pytest.mark.unit
class TestModelIntentPayloadUnionValidation:
    """Test validation through the union type."""

    def test_validate_with_missing_required_field(self) -> None:
        """Test validation fails when required field missing."""
        data = {
            "intent_type": "log_event",
            # Missing level and message
        }
        with pytest.raises(ValidationError) as exc_info:
            IntentPayloadAdapter.validate_python(data)
        assert "level" in str(exc_info.value) or "message" in str(exc_info.value)

    def test_validate_with_invalid_field_value(self) -> None:
        """Test validation fails with invalid field value."""
        data = {
            "intent_type": "log_event",
            "level": "INVALID_LEVEL",  # Not a valid level
            "message": "Test",
        }
        with pytest.raises(ValidationError) as exc_info:
            IntentPayloadAdapter.validate_python(data)
        assert "level" in str(exc_info.value)

    def test_validate_with_extra_field(self) -> None:
        """Test validation fails with extra field."""
        data = {
            "intent_type": "log_event",
            "level": "INFO",
            "message": "Test",
            "unknown_field": "value",
        }
        with pytest.raises(ValidationError) as exc_info:
            IntentPayloadAdapter.validate_python(data)
        assert "extra_forbidden" in str(exc_info.value)


@pytest.mark.unit
class TestModelIntentPayloadUnionTypeArgs:
    """Test union type composition."""

    def test_union_contains_all_payload_types(self) -> None:
        """Test that union contains all expected payload types."""
        # Get the union args (the types in the union)
        # Note: get_args on Annotated returns (Union[...], Field(...))
        args = get_args(ModelIntentPayloadUnion)
        # First arg should be the union
        union_types = get_args(args[0]) if args else []

        expected_types = {
            PayloadLogEvent,
            PayloadMetric,
            PayloadPersistState,
            PayloadPersistResult,
            PayloadFSMStateAction,
            PayloadFSMTransitionAction,
            PayloadFSMCompleted,
            PayloadEmitEvent,
            PayloadWrite,
            PayloadHTTP,
            PayloadNotify,
            PayloadExtension,
        }

        assert set(union_types) == expected_types


@pytest.mark.unit
class TestModelIntentPayloadUnionEdgeCases:
    """Test edge cases for union type."""

    def test_null_payload_rejected(self) -> None:
        """Test that None/null is rejected."""
        with pytest.raises(ValidationError):
            IntentPayloadAdapter.validate_python(None)

    def test_empty_dict_rejected(self) -> None:
        """Test that empty dict is rejected."""
        with pytest.raises(ValidationError):
            IntentPayloadAdapter.validate_python({})

    def test_string_rejected(self) -> None:
        """Test that string is rejected."""
        with pytest.raises(ValidationError):
            IntentPayloadAdapter.validate_python("log_event")

    def test_list_rejected(self) -> None:
        """Test that list is rejected."""
        with pytest.raises(ValidationError):
            IntentPayloadAdapter.validate_python([{"intent_type": "log_event"}])

    def test_case_sensitive_discriminator(self) -> None:
        """Test that discriminator is case-sensitive."""
        data = {
            "intent_type": "LOG_EVENT",  # Wrong case
            "level": "INFO",
            "message": "Test",
        }
        with pytest.raises(ValidationError):
            IntentPayloadAdapter.validate_python(data)


@pytest.mark.unit
class TestModelIntentPayloadUnionJSONValidation:
    """Test JSON string validation."""

    def test_validate_json_log_event(self) -> None:
        """Test validation from JSON string."""
        json_str = '{"intent_type": "log_event", "level": "INFO", "message": "Test"}'
        payload = IntentPayloadAdapter.validate_json(json_str)

        assert isinstance(payload, PayloadLogEvent)
        assert payload.intent_type == "log_event"

    def test_validate_json_write(self) -> None:
        """Test validation from JSON string for write."""
        json_str = '{"intent_type": "write", "path": "/test", "content": "data"}'
        payload = IntentPayloadAdapter.validate_json(json_str)

        assert isinstance(payload, PayloadWrite)
        assert payload.path == "/test"

    def test_validate_json_invalid_intent_type(self) -> None:
        """Test JSON validation fails with invalid intent_type."""
        json_str = '{"intent_type": "invalid_type"}'
        with pytest.raises(ValidationError):
            IntentPayloadAdapter.validate_json(json_str)

    def test_validate_json_malformed(self) -> None:
        """Test JSON validation fails with malformed JSON."""
        json_str = '{intent_type: "log_event"}'  # Invalid JSON
        with pytest.raises(ValidationError):
            IntentPayloadAdapter.validate_json(json_str)
