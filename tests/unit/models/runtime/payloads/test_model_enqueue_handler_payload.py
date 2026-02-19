# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

#
# SPDX-License-Identifier: Apache-2.0

"""
Tests for ModelEnqueueHandlerPayload.

This module tests the ENQUEUE_HANDLER directive payload, verifying:
1. Discriminator field (kind="enqueue_handler")
2. Priority bounds validation (1-10)
3. Default values for all fields
4. Integration with ModelSchemaValue
5. Serialization/deserialization roundtrip
"""

import pytest
from pydantic import ValidationError

from omnibase_core.models.common.model_schema_value import ModelSchemaValue
from omnibase_core.models.runtime.payloads import ModelEnqueueHandlerPayload


@pytest.mark.unit
class TestModelEnqueueHandlerPayloadDiscriminator:
    """Test discriminator field behavior."""

    def test_kind_is_literal_enqueue_handler(self) -> None:
        """Test that kind field is always 'enqueue_handler'."""
        payload = ModelEnqueueHandlerPayload()
        assert payload.kind == "enqueue_handler"

    def test_kind_cannot_be_changed(self) -> None:
        """Test that kind field cannot be set to different value."""
        with pytest.raises(ValidationError):
            ModelEnqueueHandlerPayload(kind="other_kind")  # type: ignore[arg-type]

    def test_kind_default_value(self) -> None:
        """Test that kind has correct default value."""
        payload = ModelEnqueueHandlerPayload()
        assert payload.kind == "enqueue_handler"


@pytest.mark.unit
class TestModelEnqueueHandlerPayloadDefaults:
    """Test default values."""

    def test_all_defaults(self) -> None:
        """Test that all fields have correct defaults."""
        payload = ModelEnqueueHandlerPayload()

        assert payload.kind == "enqueue_handler"
        assert payload.handler_args is not None
        assert payload.handler_args.value_type == "object"
        assert payload.priority == 1
        assert payload.queue_name is None

    def test_handler_args_default_is_empty_object(self) -> None:
        """Test that handler_args defaults to empty object."""
        payload = ModelEnqueueHandlerPayload()
        assert payload.handler_args.object_value == {}


@pytest.mark.unit
class TestModelEnqueueHandlerPayloadPriorityValidation:
    """Test priority field validation."""

    def test_priority_valid_minimum(self) -> None:
        """Test priority at minimum value (1)."""
        payload = ModelEnqueueHandlerPayload(priority=1)
        assert payload.priority == 1

    def test_priority_valid_maximum(self) -> None:
        """Test priority at maximum value (10)."""
        payload = ModelEnqueueHandlerPayload(priority=10)
        assert payload.priority == 10

    def test_priority_valid_middle(self) -> None:
        """Test priority at middle value."""
        payload = ModelEnqueueHandlerPayload(priority=5)
        assert payload.priority == 5

    def test_priority_below_minimum(self) -> None:
        """Test priority below minimum (0)."""
        with pytest.raises(ValidationError) as exc_info:
            ModelEnqueueHandlerPayload(priority=0)
        assert "priority" in str(exc_info.value)

    def test_priority_above_maximum(self) -> None:
        """Test priority above maximum (11)."""
        with pytest.raises(ValidationError) as exc_info:
            ModelEnqueueHandlerPayload(priority=11)
        assert "priority" in str(exc_info.value)

    def test_priority_negative(self) -> None:
        """Test negative priority."""
        with pytest.raises(ValidationError) as exc_info:
            ModelEnqueueHandlerPayload(priority=-1)
        assert "priority" in str(exc_info.value)


@pytest.mark.unit
class TestModelEnqueueHandlerPayloadHandlerArgs:
    """Test handler_args field."""

    def test_handler_args_with_object(self) -> None:
        """Test handler_args with object value."""
        args = ModelSchemaValue.create_object({"task_id": "123", "retry": True})
        payload = ModelEnqueueHandlerPayload(handler_args=args)

        assert payload.handler_args.value_type == "object"
        assert "task_id" in payload.handler_args.object_value

    def test_handler_args_with_array(self) -> None:
        """Test handler_args with array value."""
        args = ModelSchemaValue.create_array([1, 2, 3])
        payload = ModelEnqueueHandlerPayload(handler_args=args)

        assert payload.handler_args.value_type == "array"

    def test_handler_args_with_string(self) -> None:
        """Test handler_args with string value."""
        args = ModelSchemaValue.create_string("simple_arg")
        payload = ModelEnqueueHandlerPayload(handler_args=args)

        assert payload.handler_args.value_type == "string"
        assert payload.handler_args.string_value == "simple_arg"


@pytest.mark.unit
class TestModelEnqueueHandlerPayloadQueueName:
    """Test queue_name field."""

    def test_queue_name_none(self) -> None:
        """Test queue_name defaults to None."""
        payload = ModelEnqueueHandlerPayload()
        assert payload.queue_name is None

    def test_queue_name_with_value(self) -> None:
        """Test queue_name with specific value."""
        payload = ModelEnqueueHandlerPayload(queue_name="high-priority")
        assert payload.queue_name == "high-priority"

    def test_queue_name_empty_string(self) -> None:
        """Test queue_name with empty string (should be allowed)."""
        payload = ModelEnqueueHandlerPayload(queue_name="")
        assert payload.queue_name == ""


@pytest.mark.unit
class TestModelEnqueueHandlerPayloadSerialization:
    """Test serialization/deserialization."""

    def test_serialization_defaults(self) -> None:
        """Test serialization with default values."""
        payload = ModelEnqueueHandlerPayload()
        data = payload.model_dump()

        assert data["kind"] == "enqueue_handler"
        assert data["priority"] == 1
        assert data["queue_name"] is None

    def test_serialization_all_fields(self) -> None:
        """Test serialization with all fields set."""
        args = ModelSchemaValue.create_object({"task_id": "123"})
        payload = ModelEnqueueHandlerPayload(
            handler_args=args,
            priority=5,
            queue_name="test-queue",
        )
        data = payload.model_dump()

        assert data["priority"] == 5
        assert data["queue_name"] == "test-queue"

    def test_roundtrip_serialization(self) -> None:
        """Test roundtrip serialization."""
        args = ModelSchemaValue.create_object({"key": "value"})
        original = ModelEnqueueHandlerPayload(
            handler_args=args,
            priority=7,
            queue_name="my-queue",
        )
        data = original.model_dump()
        restored = ModelEnqueueHandlerPayload.model_validate(data)

        assert restored.kind == original.kind
        assert restored.priority == original.priority
        assert restored.queue_name == original.queue_name

    def test_json_serialization(self) -> None:
        """Test JSON serialization."""
        payload = ModelEnqueueHandlerPayload(priority=5)
        json_str = payload.model_dump_json()

        assert '"kind":"enqueue_handler"' in json_str
        assert '"priority":5' in json_str


@pytest.mark.unit
class TestModelEnqueueHandlerPayloadImmutability:
    """Test immutability (frozen model)."""

    def test_cannot_modify_priority(self) -> None:
        """Test that priority cannot be modified."""
        payload = ModelEnqueueHandlerPayload(priority=5)
        with pytest.raises(ValidationError):
            payload.priority = 10  # type: ignore[misc]

    def test_cannot_modify_queue_name(self) -> None:
        """Test that queue_name cannot be modified."""
        payload = ModelEnqueueHandlerPayload(queue_name="original")
        with pytest.raises(ValidationError):
            payload.queue_name = "modified"  # type: ignore[misc]


@pytest.mark.unit
class TestModelEnqueueHandlerPayloadExtraFieldsRejected:
    """Test extra fields rejection."""

    def test_reject_extra_fields(self) -> None:
        """Test that extra fields are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelEnqueueHandlerPayload(unknown_field="value")  # type: ignore[call-arg]
        assert "extra_forbidden" in str(exc_info.value)


@pytest.mark.unit
class TestModelEnqueueHandlerPayloadEdgeCases:
    """Test edge cases."""

    def test_all_priority_values(self) -> None:
        """Test all valid priority values 1-10."""
        for priority in range(1, 11):
            payload = ModelEnqueueHandlerPayload(priority=priority)
            assert payload.priority == priority

    def test_queue_name_with_special_characters(self) -> None:
        """Test queue_name with special characters."""
        payload = ModelEnqueueHandlerPayload(queue_name="queue-name_v2.0")
        assert payload.queue_name == "queue-name_v2.0"

    def test_handler_args_complex_nested(self) -> None:
        """Test handler_args with complex nested structure."""
        args = ModelSchemaValue.create_object(
            {
                "config": {
                    "retries": 3,
                    "timeout": 30,
                    "options": ["a", "b", "c"],
                },
                "metadata": {
                    "created_by": "system",
                },
            }
        )
        payload = ModelEnqueueHandlerPayload(handler_args=args)
        assert payload.handler_args.value_type == "object"
