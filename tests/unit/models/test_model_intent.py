"""
Tests for ModelIntent.

This module tests the intent model for side effect declarations from pure Reducer FSM.
"""

from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from omnibase_core.models.reducer.model_intent import ModelIntent
from omnibase_core.models.reducer.payloads import ModelPayloadLogEvent


@pytest.mark.unit
class TestModelIntentInstantiation:
    """Test ModelIntent instantiation."""

    def test_create_intent_with_required_fields(self):
        """Test creating a ModelIntent with only required fields."""
        intent = ModelIntent(
            intent_type="log_event",
            target="metrics_service",
            payload=ModelPayloadLogEvent(
                level="INFO",
                message="Test message",
            ),
        )

        assert intent is not None
        assert isinstance(intent, ModelIntent)
        assert intent.intent_type == "log_event"
        assert intent.target == "metrics_service"
        assert isinstance(intent.intent_id, UUID)
        assert intent.priority == 1
        assert intent.lease_id is None
        assert intent.epoch is None

    def test_create_intent_with_all_fields(self):
        """Test creating a ModelIntent with all fields."""
        test_intent_id = uuid4()
        test_lease_id = uuid4()
        test_payload = ModelPayloadLogEvent(
            level="INFO",
            message="Test message",
        )

        intent = ModelIntent(
            intent_id=test_intent_id,
            intent_type="emit_event",
            target="kafka_topic",
            payload=test_payload,
            priority=5,
            lease_id=test_lease_id,
            epoch=3,
        )

        assert intent.intent_id == test_intent_id
        assert intent.intent_type == "emit_event"
        assert intent.target == "kafka_topic"
        assert intent.payload == test_payload
        assert intent.priority == 5
        assert intent.lease_id == test_lease_id
        assert intent.epoch == 3

    def test_intent_id_auto_generation(self):
        """Test that intent_id is auto-generated when not provided."""
        intent1 = ModelIntent(
            intent_type="log_event",
            target="service",
            payload=ModelPayloadLogEvent(
                level="INFO",
                message="Test message",
            ),
        )
        intent2 = ModelIntent(
            intent_type="log_event",
            target="service",
            payload=ModelPayloadLogEvent(
                level="INFO",
                message="Test message",
            ),
        )

        assert isinstance(intent1.intent_id, UUID)
        assert isinstance(intent2.intent_id, UUID)
        assert intent1.intent_id != intent2.intent_id


@pytest.mark.unit
class TestModelIntentFieldValidation:
    """Test ModelIntent field validation."""

    def test_intent_type_validation(self):
        """Test intent_type field validation."""
        # Valid intent_type
        intent = ModelIntent(
            intent_type="log_event",
            target="service",
            payload=ModelPayloadLogEvent(
                level="INFO",
                message="Test message",
            ),
        )
        assert intent.intent_type == "log_event"

        # Test min_length validation - empty string should fail
        with pytest.raises(ValidationError) as exc_info:
            ModelIntent(
                intent_type="",
                target="service",
                payload=ModelPayloadLogEvent(
                    level="INFO",
                    message="Test message",
                ),
            )
        assert "String should have at least 1 character" in str(exc_info.value)

        # Test max_length validation - 101 chars should fail
        with pytest.raises(ValidationError) as exc_info:
            ModelIntent(
                intent_type="x" * 101,
                target="service",
                payload=ModelPayloadLogEvent(
                    level="INFO",
                    message="Test message",
                ),
            )
        assert "String should have at most 100 characters" in str(exc_info.value)

    def test_target_validation(self):
        """Test target field validation."""
        # Valid target
        intent = ModelIntent(
            intent_type="log_event",
            target="metrics_service",
            payload=ModelPayloadLogEvent(
                level="INFO",
                message="Test message",
            ),
        )
        assert intent.target == "metrics_service"

        # Test min_length validation - empty string should fail
        with pytest.raises(ValidationError) as exc_info:
            ModelIntent(
                intent_type="log_event",
                target="",
                payload=ModelPayloadLogEvent(
                    level="INFO",
                    message="Test message",
                ),
            )
        assert "String should have at least 1 character" in str(exc_info.value)

        # Test max_length validation - 201 chars should fail
        with pytest.raises(ValidationError) as exc_info:
            ModelIntent(
                intent_type="log_event",
                target="x" * 201,
                payload=ModelPayloadLogEvent(
                    level="INFO",
                    message="Test message",
                ),
            )
        assert "String should have at most 200 characters" in str(exc_info.value)

    def test_priority_validation(self):
        """Test priority field validation and boundaries."""
        # Valid priorities (1-10)
        for priority in range(1, 11):
            intent = ModelIntent(
                intent_type="log_event",
                target="service",
                payload=ModelPayloadLogEvent(
                    level="INFO",
                    message="Test message",
                ),
                priority=priority,
            )
            assert intent.priority == priority

        # Test lower boundary - 0 should fail
        with pytest.raises(ValidationError) as exc_info:
            ModelIntent(
                intent_type="log_event",
                target="service",
                payload=ModelPayloadLogEvent(
                    level="INFO",
                    message="Test message",
                ),
                priority=0,
            )
        assert "greater than or equal to 1" in str(exc_info.value)

        # Test upper boundary - 11 should fail
        with pytest.raises(ValidationError) as exc_info:
            ModelIntent(
                intent_type="log_event",
                target="service",
                payload=ModelPayloadLogEvent(
                    level="INFO",
                    message="Test message",
                ),
                priority=11,
            )
        assert "less than or equal to 10" in str(exc_info.value)

    def test_priority_default_value(self):
        """Test priority default value is 1."""
        intent = ModelIntent(
            intent_type="log_event",
            target="service",
            payload=ModelPayloadLogEvent(
                level="INFO",
                message="Test message",
            ),
        )
        assert intent.priority == 1

    def test_payload_with_data(self):
        """Test payload with typed data."""
        test_payload = ModelPayloadLogEvent(
            level="INFO",
            message="Test message with data",
        )

        intent = ModelIntent(
            intent_type="write",
            target="database",
            payload=test_payload,
        )

        assert intent.payload == test_payload
        assert intent.payload.level == "INFO"
        assert intent.payload.message == "Test message with data"

    def test_epoch_validation(self):
        """Test epoch field validation."""
        # Valid epochs (>= 0)
        for epoch in [0, 1, 10, 100, 1000]:
            intent = ModelIntent(
                intent_type="log_event",
                target="service",
                payload=ModelPayloadLogEvent(
                    level="INFO",
                    message="Test message",
                ),
                epoch=epoch,
            )
            assert intent.epoch == epoch

        # Test lower boundary - negative should fail
        with pytest.raises(ValidationError) as exc_info:
            ModelIntent(
                intent_type="log_event",
                target="service",
                payload=ModelPayloadLogEvent(
                    level="INFO",
                    message="Test message",
                ),
                epoch=-1,
            )
        assert "greater than or equal to 0" in str(exc_info.value)

    def test_epoch_default_value(self):
        """Test epoch default value is None."""
        intent = ModelIntent(
            intent_type="log_event",
            target="service",
            payload=ModelPayloadLogEvent(
                level="INFO",
                message="Test message",
            ),
        )
        assert intent.epoch is None

    def test_lease_id_validation(self):
        """Test lease_id UUID validation."""
        test_lease_id = uuid4()
        intent = ModelIntent(
            intent_type="log_event",
            target="service",
            payload=ModelPayloadLogEvent(
                level="INFO",
                message="Test message",
            ),
            lease_id=test_lease_id,
        )

        assert intent.lease_id == test_lease_id
        assert isinstance(intent.lease_id, UUID)

    def test_lease_id_default_value(self):
        """Test lease_id default value is None."""
        intent = ModelIntent(
            intent_type="log_event",
            target="service",
            payload=ModelPayloadLogEvent(
                level="INFO",
                message="Test message",
            ),
        )
        assert intent.lease_id is None


@pytest.mark.unit
class TestModelIntentSerialization:
    """Test ModelIntent serialization."""

    def test_model_dump(self):
        """Test serializing intent to dictionary."""
        test_intent_id = uuid4()
        test_lease_id = uuid4()
        test_payload = ModelPayloadLogEvent(
            level="INFO",
            message="Test message",
        )

        intent = ModelIntent(
            intent_id=test_intent_id,
            intent_type="emit_event",
            target="kafka_topic",
            payload=test_payload,
            priority=7,
            lease_id=test_lease_id,
            epoch=2,
        )

        data = intent.model_dump()

        assert isinstance(data, dict)
        assert data["intent_id"] == test_intent_id
        assert data["intent_type"] == "emit_event"
        assert data["target"] == "kafka_topic"
        assert "payload" in data
        assert data["priority"] == 7
        assert data["lease_id"] == test_lease_id
        assert data["epoch"] == 2

    def test_model_dump_json(self):
        """Test serializing intent to JSON string."""
        intent = ModelIntent(
            intent_type="log_event",
            target="service",
            payload=ModelPayloadLogEvent(
                level="INFO",
                message="CPU metric",
            ),
        )

        json_str = intent.model_dump_json()

        assert isinstance(json_str, str)
        assert "intent_id" in json_str
        assert "intent_type" in json_str
        assert "log" in json_str
        assert "target" in json_str
        assert "service" in json_str
        assert "payload" in json_str
        assert "level" in json_str

    def test_kafka_message_format_serialization(self):
        """Test serialization matches Kafka message format expectations."""
        test_payload = ModelPayloadLogEvent(
            level="INFO",
            message="Metrics recorded",
        )

        intent = ModelIntent(
            intent_type="emit_event",
            target="dev.omninode.metrics.v1",
            payload=test_payload,
            priority=5,
        )

        # Serialize for Kafka
        kafka_data = intent.model_dump(mode="json")

        assert isinstance(kafka_data, dict)
        assert "intent_id" in kafka_data
        assert "intent_type" in kafka_data
        assert "target" in kafka_data
        assert "payload" in kafka_data
        assert kafka_data["payload"]["level"] == "INFO"
        assert kafka_data["priority"] == 5


@pytest.mark.unit
class TestModelIntentDeserialization:
    """Test ModelIntent deserialization.

    Note: ModelIntent uses Protocol-based payload typing, which doesn't support
    automatic deserialization from dict. These tests verify proper handling
    of typed payloads in serialization/deserialization workflows.
    """

    def test_model_validate_with_typed_payload(self):
        """Test deserializing from dictionary with pre-constructed payload."""
        test_intent_id = uuid4()
        test_lease_id = uuid4()
        test_payload = ModelPayloadLogEvent(
            level="INFO",
            message="Deployment complete",
        )

        data = {
            "intent_id": str(test_intent_id),
            "intent_type": "log_event",
            "target": "slack_channel",
            "payload": test_payload,  # Use typed payload object
            "priority": 3,
            "lease_id": str(test_lease_id),
            "epoch": 5,
        }

        intent = ModelIntent.model_validate(data)

        assert isinstance(intent, ModelIntent)
        assert intent.intent_id == test_intent_id
        assert intent.intent_type == "log_event"
        assert intent.target == "slack_channel"
        assert intent.payload.message == "Deployment complete"
        assert intent.priority == 3
        assert intent.lease_id == test_lease_id
        assert intent.epoch == 5

    def test_serialization_produces_dict(self):
        """Test that serialization produces a dict with payload data."""
        test_intent_id = uuid4()
        test_payload = ModelPayloadLogEvent(
            level="INFO",
            message="Test value",
        )

        intent = ModelIntent(
            intent_id=test_intent_id,
            intent_type="log_event",
            target="database",
            payload=test_payload,
            priority=8,
        )

        # Serialize to dict
        data = intent.model_dump()

        assert isinstance(data, dict)
        assert data["intent_id"] == test_intent_id
        assert data["intent_type"] == "log_event"
        assert data["target"] == "database"
        assert data["payload"]["level"] == "INFO"
        assert data["payload"]["message"] == "Test value"
        assert data["priority"] == 8

    def test_kafka_message_format(self):
        """Test intent serialization matches Kafka message format."""
        test_payload = ModelPayloadLogEvent(
            level="INFO",
            message="Node generation completed",
        )

        intent = ModelIntent(
            intent_type="log_event",
            target="dev.omninode.metrics.v1",
            payload=test_payload,
            priority=6,
        )

        # Serialize for Kafka
        kafka_data = intent.model_dump(mode="json")

        assert isinstance(kafka_data, dict)
        assert kafka_data["intent_type"] == "log_event"
        assert kafka_data["target"] == "dev.omninode.metrics.v1"
        assert kafka_data["payload"]["level"] == "INFO"
        assert kafka_data["priority"] == 6

    def test_roundtrip_with_model_copy(self):
        """Test roundtrip using model_copy for immutable updates."""
        test_payload = ModelPayloadLogEvent(
            level="INFO",
            message="Latency metric",
        )
        original_intent = ModelIntent(
            intent_type="log_event",
            target="metrics_service",
            payload=test_payload,
            priority=4,
            epoch=1,
        )

        # Create a copy (immutable pattern for frozen models)
        copied_intent = original_intent.model_copy()

        # Verify they are equivalent
        assert copied_intent.intent_id == original_intent.intent_id
        assert copied_intent.intent_type == original_intent.intent_type
        assert copied_intent.target == original_intent.target
        assert copied_intent.payload == original_intent.payload
        assert copied_intent.priority == original_intent.priority
        assert copied_intent.epoch == original_intent.epoch


@pytest.mark.unit
class TestModelIntentEdgeCases:
    """Test ModelIntent edge cases and error conditions."""

    def test_missing_required_fields(self):
        """Test that missing required fields raise ValidationError."""
        # Missing intent_type
        with pytest.raises(ValidationError) as exc_info:
            ModelIntent(target="service")
        assert "intent_type" in str(exc_info.value)

        # Missing target
        with pytest.raises(ValidationError) as exc_info:
            ModelIntent(intent_type="log_event")
        assert "target" in str(exc_info.value)

    def test_intent_type_boundary_values(self):
        """Test intent_type at exact boundaries."""
        # Exactly 1 character (minimum)
        intent = ModelIntent(
            intent_type="x",
            target="service",
            payload=ModelPayloadLogEvent(
                level="INFO",
                message="Test message",
            ),
        )
        assert intent.intent_type == "x"

        # Exactly 100 characters (maximum)
        intent = ModelIntent(
            intent_type="x" * 100,
            target="service",
            payload=ModelPayloadLogEvent(
                level="INFO",
                message="Test message",
            ),
        )
        assert intent.intent_type == "x" * 100

    def test_target_boundary_values(self):
        """Test target at exact boundaries."""
        # Exactly 1 character (minimum)
        intent = ModelIntent(
            intent_type="log_event",
            target="s",
            payload=ModelPayloadLogEvent(
                level="INFO",
                message="Test message",
            ),
        )
        assert intent.target == "s"

        # Exactly 200 characters (maximum)
        intent = ModelIntent(
            intent_type="log_event",
            target="s" * 200,
            payload=ModelPayloadLogEvent(
                level="INFO",
                message="Test message",
            ),
        )
        assert intent.target == "s" * 200

    def test_priority_boundary_values(self):
        """Test priority at exact boundaries."""
        # Exactly 1 (minimum)
        intent = ModelIntent(
            intent_type="log_event",
            target="service",
            payload=ModelPayloadLogEvent(
                level="INFO",
                message="Test message",
            ),
            priority=1,
        )
        assert intent.priority == 1

        # Exactly 10 (maximum)
        intent = ModelIntent(
            intent_type="log_event",
            target="service",
            payload=ModelPayloadLogEvent(
                level="INFO",
                message="Test message",
            ),
            priority=10,
        )
        assert intent.priority == 10

    def test_epoch_boundary_value(self):
        """Test epoch at boundary (0)."""
        intent = ModelIntent(
            intent_type="log_event",
            target="service",
            payload=ModelPayloadLogEvent(
                level="INFO",
                message="Test message",
            ),
            epoch=0,
        )
        assert intent.epoch == 0

    def test_invalid_uuid_format(self):
        """Test that invalid UUID format raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ModelIntent(
                intent_type="log_event",
                target="service",
                intent_id="not-a-uuid",
            )
        assert "UUID" in str(exc_info.value) or "uuid" in str(exc_info.value).lower()

    def test_extra_fields_behavior(self):
        """Test behavior with extra fields (should be forbidden)."""
        data = {
            "intent_type": "log",
            "target": "service",
            "extra_field": "should_be_forbidden",
            "another_field": 123,
        }

        # Extra fields should raise ValidationError (extra="forbid")
        with pytest.raises(ValidationError) as exc_info:
            ModelIntent.model_validate(data)

        # Should mention the extra fields
        error_str = str(exc_info.value)
        assert "extra_field" in error_str or "Extra inputs" in error_str


@pytest.mark.unit
class TestModelIntentModelConfig:
    """Test ModelIntent model configuration."""

    def test_model_config_extra_forbid(self):
        """Test that model_config has extra='forbid'."""
        assert ModelIntent.model_config["extra"] == "forbid"

    def test_model_config_frozen(self):
        """Test that model_config has frozen=True."""
        assert ModelIntent.model_config["frozen"] is True

    def test_model_config_validate_assignment(self):
        """Test that model_config handles assignment validation appropriately.

        Note: For frozen models, validate_assignment is not required because
        frozen=True already prevents any attribute assignment. The frozen
        behavior is tested in test_frozen_model_prevents_assignment.
        """
        # Frozen models don't need validate_assignment - frozen=True handles it
        assert ModelIntent.model_config.get("frozen") is True
        # validate_assignment is optional for frozen models
        # If present, it should be True; if absent, frozen handles validation
        validate_assignment = ModelIntent.model_config.get("validate_assignment")
        assert validate_assignment is None or validate_assignment is True

    def test_frozen_model_prevents_assignment(self):
        """Test that frozen model prevents direct attribute assignment."""
        intent = ModelIntent(
            intent_type="log_event",
            target="service",
            payload=ModelPayloadLogEvent(
                level="INFO",
                message="Test message",
            ),
            priority=5,
        )

        # Direct assignment should raise ValidationError (frozen=True)
        with pytest.raises(ValidationError) as exc_info:
            intent.priority = 8
        assert "frozen" in str(exc_info.value).lower() or "Instance is frozen" in str(
            exc_info.value
        )

    def test_model_copy_with_valid_values(self):
        """Test that model_copy works for valid value updates."""
        intent = ModelIntent(
            intent_type="log_event",
            target="service",
            payload=ModelPayloadLogEvent(
                level="INFO",
                message="Test message",
            ),
            priority=5,
        )

        # Use model_copy for updates (frozen model pattern)
        new_intent = intent.model_copy(update={"priority": 8})
        assert new_intent.priority == 8
        assert intent.priority == 5  # Original unchanged

    def test_validated_copy_with_invalid_values(self):
        """Test that validated copies reject invalid values."""
        intent = ModelIntent(
            intent_type="log_event",
            target="service",
            payload=ModelPayloadLogEvent(
                level="INFO",
                message="Test message",
            ),
            priority=5,
        )

        # model_copy bypasses validation, but model_validate enforces constraints
        # For validated updates, combine model_dump with model_validate
        data = intent.model_dump()
        data["priority"] = 11  # Out of range

        with pytest.raises(ValidationError):
            ModelIntent.model_validate(data)

    def test_model_config_use_enum_values(self):
        """Test that model_config has use_enum_values=False."""
        assert ModelIntent.model_config["use_enum_values"] is False


@pytest.mark.unit
class TestModelIntentMetadata:
    """Test ModelIntent metadata and introspection."""

    def test_model_fields(self):
        """Test that model has correct field definitions."""
        fields = ModelIntent.model_fields

        assert "intent_id" in fields
        assert "intent_type" in fields
        assert "target" in fields
        assert "payload" in fields
        assert "priority" in fields
        assert "lease_id" in fields
        assert "epoch" in fields

    def test_model_docstring(self):
        """Test ModelIntent docstring."""
        assert ModelIntent.__doc__ is not None
        # ModelIntent is now for extension/plugin workflows
        assert "intent declaration" in ModelIntent.__doc__.lower()
        assert "extension" in ModelIntent.__doc__.lower()

    def test_model_class_name(self):
        """Test ModelIntent class name."""
        assert ModelIntent.__name__ == "ModelIntent"

    def test_model_module(self):
        """Test ModelIntent module."""
        assert ModelIntent.__module__ == "omnibase_core.models.reducer.model_intent"

    def test_model_inheritance(self):
        """Test that ModelIntent inherits from BaseModel."""
        from pydantic import BaseModel

        intent = ModelIntent(
            intent_type="log_event",
            target="service",
            payload=ModelPayloadLogEvent(
                level="INFO",
                message="Test message",
            ),
        )
        assert isinstance(intent, BaseModel)


@pytest.mark.unit
class TestModelIntentComparison:
    """Test ModelIntent comparison operations."""

    def test_equality_same_values(self):
        """Test equality with same field values."""
        test_id = uuid4()
        test_lease_id = uuid4()
        test_payload = ModelPayloadLogEvent(
            level="INFO",
            message="Test message",
        )

        intent1 = ModelIntent(
            intent_id=test_id,
            intent_type="log_event",
            target="service",
            payload=test_payload,
            priority=5,
            lease_id=test_lease_id,
            epoch=2,
        )

        intent2 = ModelIntent(
            intent_id=test_id,
            intent_type="log_event",
            target="service",
            payload=test_payload,
            priority=5,
            lease_id=test_lease_id,
            epoch=2,
        )

        assert intent1 == intent2

    def test_inequality_different_values(self):
        """Test inequality with different field values."""
        intent1 = ModelIntent(
            intent_type="log_event",
            target="service1",
            payload=ModelPayloadLogEvent(
                level="INFO",
                message="Test message",
            ),
        )
        intent2 = ModelIntent(
            intent_type="log_event",
            target="service2",
            payload=ModelPayloadLogEvent(
                level="INFO",
                message="Test message",
            ),
        )

        assert intent1 != intent2

    def test_model_copy(self):
        """Test creating a copy of ModelIntent."""
        original = ModelIntent(
            intent_type="emit_event",
            target="kafka_topic",
            payload=ModelPayloadLogEvent(
                level="INFO",
                message="Test data",
            ),
            priority=7,
        )

        copied = original.model_copy()

        assert copied == original
        assert copied is not original
        assert copied.intent_id == original.intent_id
        assert copied.intent_type == original.intent_type

    def test_model_copy_deep(self):
        """Test deep copy of ModelIntent with payload."""
        original = ModelIntent(
            intent_type="write",
            target="database",
            payload=ModelPayloadLogEvent(
                level="INFO",
                message="Original value",
            ),
        )

        copied = original.model_copy(deep=True)

        # Verify deep copy
        assert copied == original
        assert copied is not original
        assert copied.payload == original.payload
        assert copied.payload is not original.payload  # Different instances


@pytest.mark.unit
class TestModelIntentStringRepresentation:
    """Test ModelIntent string representation."""

    def test_str_representation(self):
        """Test string representation of ModelIntent."""
        intent = ModelIntent(
            intent_type="log_event",
            target="service",
            payload=ModelPayloadLogEvent(
                level="INFO",
                message="Test message",
            ),
        )

        str_repr = str(intent)
        assert isinstance(str_repr, str)
        assert "intent_type" in str_repr or "log" in str_repr

    def test_repr_representation(self):
        """Test repr representation of ModelIntent."""
        intent = ModelIntent(
            intent_type="log_event",
            target="service",
            payload=ModelPayloadLogEvent(
                level="INFO",
                message="Test message",
            ),
        )

        repr_str = repr(intent)
        assert isinstance(repr_str, str)
        assert "ModelIntent" in repr_str
