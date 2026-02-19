# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

#
# SPDX-License-Identifier: Apache-2.0

"""
Tests for ModelDirectivePayload discriminated union.

This module tests the discriminated union type alias, verifying:
1. Automatic type resolution based on 'kind' discriminator
2. All discriminator values map correctly
3. Invalid discriminator values are rejected
4. Serialization/deserialization through the union
5. Type adapter behavior for validation
"""

from datetime import UTC, datetime
from typing import get_args
from uuid import uuid4

import pytest
from pydantic import TypeAdapter, ValidationError

from omnibase_core.models.common.model_schema_value import ModelSchemaValue
from omnibase_core.models.runtime.payloads import (
    ModelCancelExecutionPayload,
    ModelDelayUntilPayload,
    ModelDirectivePayload,
    ModelEnqueueHandlerPayload,
    ModelRetryWithBackoffPayload,
    ModelScheduleEffectPayload,
)

# TypeAdapter for validating the union type
DirectivePayloadAdapter = TypeAdapter(ModelDirectivePayload)


@pytest.mark.unit
class TestModelDirectivePayloadUnionDiscriminator:
    """Test discriminator resolution for all payload types."""

    def test_resolve_schedule_effect(self) -> None:
        """Test discriminator resolution for schedule_effect."""
        data = {
            "kind": "schedule_effect",
            "effect_node_type": "http_request",
        }
        payload = DirectivePayloadAdapter.validate_python(data)

        assert isinstance(payload, ModelScheduleEffectPayload)
        assert payload.kind == "schedule_effect"

    def test_resolve_enqueue_handler(self) -> None:
        """Test discriminator resolution for enqueue_handler."""
        data = {
            "kind": "enqueue_handler",
            "priority": 5,
        }
        payload = DirectivePayloadAdapter.validate_python(data)

        assert isinstance(payload, ModelEnqueueHandlerPayload)
        assert payload.kind == "enqueue_handler"

    def test_resolve_retry_with_backoff(self) -> None:
        """Test discriminator resolution for retry_with_backoff."""
        op_id = uuid4()
        data = {
            "kind": "retry_with_backoff",
            "operation_id": str(op_id),
        }
        payload = DirectivePayloadAdapter.validate_python(data)

        assert isinstance(payload, ModelRetryWithBackoffPayload)
        assert payload.kind == "retry_with_backoff"

    def test_resolve_delay_until(self) -> None:
        """Test discriminator resolution for delay_until."""
        op_id = uuid4()
        exec_at = datetime.now(UTC)
        data = {
            "kind": "delay_until",
            "operation_id": str(op_id),
            "execute_at": exec_at.isoformat(),
        }
        payload = DirectivePayloadAdapter.validate_python(data)

        assert isinstance(payload, ModelDelayUntilPayload)
        assert payload.kind == "delay_until"

    def test_resolve_cancel_execution(self) -> None:
        """Test discriminator resolution for cancel_execution."""
        exec_id = uuid4()
        data = {
            "kind": "cancel_execution",
            "execution_id": str(exec_id),
        }
        payload = DirectivePayloadAdapter.validate_python(data)

        assert isinstance(payload, ModelCancelExecutionPayload)
        assert payload.kind == "cancel_execution"


@pytest.mark.unit
class TestModelDirectivePayloadUnionInvalidDiscriminator:
    """Test invalid discriminator handling."""

    def test_unknown_kind_rejected(self) -> None:
        """Test that unknown kind values are rejected."""
        data = {
            "kind": "unknown_type",
        }
        with pytest.raises(ValidationError) as exc_info:
            DirectivePayloadAdapter.validate_python(data)
        # Should indicate discriminator issue
        assert "kind" in str(exc_info.value) or "discriminator" in str(exc_info.value)

    def test_missing_kind_rejected(self) -> None:
        """Test that missing kind field is rejected."""
        data = {
            "effect_node_type": "http_request",
        }
        with pytest.raises(ValidationError) as exc_info:
            DirectivePayloadAdapter.validate_python(data)
        assert "kind" in str(exc_info.value) or "discriminator" in str(exc_info.value)

    def test_empty_kind_rejected(self) -> None:
        """Test that empty string kind is rejected."""
        data = {
            "kind": "",
            "effect_node_type": "test",
        }
        with pytest.raises(ValidationError):
            DirectivePayloadAdapter.validate_python(data)


@pytest.mark.unit
class TestModelDirectivePayloadUnionFromInstances:
    """Test union handling of already-instantiated payloads."""

    def test_schedule_effect_instance(self) -> None:
        """Test validating ModelScheduleEffectPayload instance."""
        instance = ModelScheduleEffectPayload(effect_node_type="test")
        # Validation should pass and return the same type
        validated = DirectivePayloadAdapter.validate_python(instance)
        assert isinstance(validated, ModelScheduleEffectPayload)

    def test_enqueue_handler_instance(self) -> None:
        """Test validating ModelEnqueueHandlerPayload instance."""
        instance = ModelEnqueueHandlerPayload(priority=3)
        validated = DirectivePayloadAdapter.validate_python(instance)
        assert isinstance(validated, ModelEnqueueHandlerPayload)

    def test_retry_with_backoff_instance(self) -> None:
        """Test validating ModelRetryWithBackoffPayload instance."""
        instance = ModelRetryWithBackoffPayload(operation_id=uuid4())
        validated = DirectivePayloadAdapter.validate_python(instance)
        assert isinstance(validated, ModelRetryWithBackoffPayload)

    def test_delay_until_instance(self) -> None:
        """Test validating ModelDelayUntilPayload instance."""
        instance = ModelDelayUntilPayload(
            execute_at=datetime.now(UTC),
            operation_id=uuid4(),
        )
        validated = DirectivePayloadAdapter.validate_python(instance)
        assert isinstance(validated, ModelDelayUntilPayload)

    def test_cancel_execution_instance(self) -> None:
        """Test validating ModelCancelExecutionPayload instance."""
        instance = ModelCancelExecutionPayload(execution_id=uuid4())
        validated = DirectivePayloadAdapter.validate_python(instance)
        assert isinstance(validated, ModelCancelExecutionPayload)


@pytest.mark.unit
class TestModelDirectivePayloadUnionSerialization:
    """Test serialization through the union type."""

    def test_serialize_schedule_effect_via_union(self) -> None:
        """Test serialization of schedule_effect through union."""
        data = {
            "kind": "schedule_effect",
            "effect_node_type": "http_request",
            "effect_input": ModelSchemaValue.create_object(
                {"url": "test"}
            ).model_dump(),
        }
        payload = DirectivePayloadAdapter.validate_python(data)
        serialized = payload.model_dump()

        assert serialized["kind"] == "schedule_effect"
        assert serialized["effect_node_type"] == "http_request"

    def test_serialize_enqueue_handler_via_union(self) -> None:
        """Test serialization of enqueue_handler through union."""
        data = {
            "kind": "enqueue_handler",
            "priority": 7,
            "queue_name": "high-priority",
        }
        payload = DirectivePayloadAdapter.validate_python(data)
        serialized = payload.model_dump()

        assert serialized["kind"] == "enqueue_handler"
        assert serialized["priority"] == 7
        assert serialized["queue_name"] == "high-priority"

    def test_roundtrip_all_types(self) -> None:
        """Test roundtrip serialization for all payload types."""
        payloads = [
            ModelScheduleEffectPayload(effect_node_type="test"),
            ModelEnqueueHandlerPayload(priority=5),
            ModelRetryWithBackoffPayload(operation_id=uuid4()),
            ModelDelayUntilPayload(
                execute_at=datetime.now(UTC),
                operation_id=uuid4(),
            ),
            ModelCancelExecutionPayload(execution_id=uuid4()),
        ]

        for original in payloads:
            serialized = original.model_dump()
            restored = DirectivePayloadAdapter.validate_python(serialized)
            assert type(restored) is type(original)
            assert restored.kind == original.kind


@pytest.mark.unit
class TestModelDirectivePayloadUnionValidation:
    """Test validation through the union type."""

    def test_validate_with_missing_required_field(self) -> None:
        """Test validation fails when required field missing."""
        data = {
            "kind": "schedule_effect",
            # Missing effect_node_type
        }
        with pytest.raises(ValidationError) as exc_info:
            DirectivePayloadAdapter.validate_python(data)
        assert "effect_node_type" in str(exc_info.value)

    def test_validate_with_invalid_field_value(self) -> None:
        """Test validation fails with invalid field value."""
        data = {
            "kind": "enqueue_handler",
            "priority": 100,  # Above max (10)
        }
        with pytest.raises(ValidationError) as exc_info:
            DirectivePayloadAdapter.validate_python(data)
        assert "priority" in str(exc_info.value)

    def test_validate_with_extra_field(self) -> None:
        """Test validation fails with extra field."""
        data = {
            "kind": "schedule_effect",
            "effect_node_type": "test",
            "unknown_field": "value",
        }
        with pytest.raises(ValidationError) as exc_info:
            DirectivePayloadAdapter.validate_python(data)
        assert "extra_forbidden" in str(exc_info.value)


@pytest.mark.unit
class TestModelDirectivePayloadUnionTypeArgs:
    """Test union type composition."""

    def test_union_contains_all_payload_types(self) -> None:
        """Test that union contains all expected payload types."""
        # Get the union args (the types in the union)
        # Note: get_args on Annotated returns (Union[...], Field(...))
        args = get_args(ModelDirectivePayload)
        # First arg should be the union
        union_types = get_args(args[0]) if args else []

        expected_types = {
            ModelScheduleEffectPayload,
            ModelEnqueueHandlerPayload,
            ModelRetryWithBackoffPayload,
            ModelDelayUntilPayload,
            ModelCancelExecutionPayload,
        }

        assert set(union_types) == expected_types


@pytest.mark.unit
class TestModelDirectivePayloadUnionEdgeCases:
    """Test edge cases for union type."""

    def test_null_payload_rejected(self) -> None:
        """Test that None/null is rejected."""
        with pytest.raises(ValidationError):
            DirectivePayloadAdapter.validate_python(None)

    def test_empty_dict_rejected(self) -> None:
        """Test that empty dict is rejected."""
        with pytest.raises(ValidationError):
            DirectivePayloadAdapter.validate_python({})

    def test_string_rejected(self) -> None:
        """Test that string is rejected."""
        with pytest.raises(ValidationError):
            DirectivePayloadAdapter.validate_python("schedule_effect")

    def test_list_rejected(self) -> None:
        """Test that list is rejected."""
        with pytest.raises(ValidationError):
            DirectivePayloadAdapter.validate_python([{"kind": "schedule_effect"}])

    def test_case_sensitive_discriminator(self) -> None:
        """Test that discriminator is case-sensitive."""
        data = {
            "kind": "SCHEDULE_EFFECT",  # Wrong case
            "effect_node_type": "test",
        }
        with pytest.raises(ValidationError):
            DirectivePayloadAdapter.validate_python(data)


@pytest.mark.unit
class TestModelDirectivePayloadUnionJSONValidation:
    """Test JSON string validation."""

    def test_validate_json_schedule_effect(self) -> None:
        """Test validation from JSON string."""
        json_str = '{"kind": "schedule_effect", "effect_node_type": "test"}'
        payload = DirectivePayloadAdapter.validate_json(json_str)

        assert isinstance(payload, ModelScheduleEffectPayload)
        assert payload.kind == "schedule_effect"

    def test_validate_json_enqueue_handler(self) -> None:
        """Test validation from JSON string for enqueue_handler."""
        json_str = '{"kind": "enqueue_handler", "priority": 5}'
        payload = DirectivePayloadAdapter.validate_json(json_str)

        assert isinstance(payload, ModelEnqueueHandlerPayload)
        assert payload.priority == 5

    def test_validate_json_invalid_kind(self) -> None:
        """Test JSON validation fails with invalid kind."""
        json_str = '{"kind": "invalid_type"}'
        with pytest.raises(ValidationError):
            DirectivePayloadAdapter.validate_json(json_str)

    def test_validate_json_malformed(self) -> None:
        """Test JSON validation fails with malformed JSON."""
        json_str = '{kind: "schedule_effect"}'  # Invalid JSON
        with pytest.raises(ValidationError):
            DirectivePayloadAdapter.validate_json(json_str)
