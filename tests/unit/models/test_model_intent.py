"""
Tests for ModelIntent.

This module tests the intent model for side effect declarations from pure Reducer FSM.
"""

from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from omnibase_core.models.reducer.model_intent import ModelIntent


class TestModelIntentInstantiation:
    """Test ModelIntent instantiation."""

    def test_create_intent_with_required_fields(self):
        """Test creating a ModelIntent with only required fields."""
        intent = ModelIntent(intent_type="log", target="metrics_service")

        assert intent is not None
        assert isinstance(intent, ModelIntent)
        assert intent.intent_type == "log"
        assert intent.target == "metrics_service"
        assert isinstance(intent.intent_id, UUID)
        assert intent.payload == {}
        assert intent.priority == 1
        assert intent.lease_id is None
        assert intent.epoch is None

    def test_create_intent_with_all_fields(self):
        """Test creating a ModelIntent with all fields."""
        test_intent_id = uuid4()
        test_lease_id = uuid4()
        test_payload = {"metric": "cpu_usage", "value": 85.5}

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
        intent1 = ModelIntent(intent_type="log", target="service")
        intent2 = ModelIntent(intent_type="log", target="service")

        assert isinstance(intent1.intent_id, UUID)
        assert isinstance(intent2.intent_id, UUID)
        assert intent1.intent_id != intent2.intent_id


class TestModelIntentFieldValidation:
    """Test ModelIntent field validation."""

    def test_intent_type_validation(self):
        """Test intent_type field validation."""
        # Valid intent_type
        intent = ModelIntent(intent_type="log", target="service")
        assert intent.intent_type == "log"

        # Test min_length validation - empty string should fail
        with pytest.raises(ValidationError) as exc_info:
            ModelIntent(intent_type="", target="service")
        assert "String should have at least 1 character" in str(exc_info.value)

        # Test max_length validation - 101 chars should fail
        with pytest.raises(ValidationError) as exc_info:
            ModelIntent(intent_type="x" * 101, target="service")
        assert "String should have at most 100 characters" in str(exc_info.value)

    def test_target_validation(self):
        """Test target field validation."""
        # Valid target
        intent = ModelIntent(intent_type="log", target="metrics_service")
        assert intent.target == "metrics_service"

        # Test min_length validation - empty string should fail
        with pytest.raises(ValidationError) as exc_info:
            ModelIntent(intent_type="log", target="")
        assert "String should have at least 1 character" in str(exc_info.value)

        # Test max_length validation - 201 chars should fail
        with pytest.raises(ValidationError) as exc_info:
            ModelIntent(intent_type="log", target="x" * 201)
        assert "String should have at most 200 characters" in str(exc_info.value)

    def test_priority_validation(self):
        """Test priority field validation and boundaries."""
        # Valid priorities (1-10)
        for priority in range(1, 11):
            intent = ModelIntent(intent_type="log", target="service", priority=priority)
            assert intent.priority == priority

        # Test lower boundary - 0 should fail
        with pytest.raises(ValidationError) as exc_info:
            ModelIntent(intent_type="log", target="service", priority=0)
        assert "greater than or equal to 1" in str(exc_info.value)

        # Test upper boundary - 11 should fail
        with pytest.raises(ValidationError) as exc_info:
            ModelIntent(intent_type="log", target="service", priority=11)
        assert "less than or equal to 10" in str(exc_info.value)

    def test_priority_default_value(self):
        """Test priority default value is 1."""
        intent = ModelIntent(intent_type="log", target="service")
        assert intent.priority == 1

    def test_payload_default_value(self):
        """Test payload default value is empty dict."""
        intent = ModelIntent(intent_type="log", target="service")
        assert intent.payload == {}
        assert isinstance(intent.payload, dict)

    def test_payload_with_data(self):
        """Test payload with various data types."""
        test_payload = {
            "string": "value",
            "int": 42,
            "float": 3.14,
            "bool": True,
            "list": [1, 2, 3],
            "nested": {"key": "value"},
        }

        intent = ModelIntent(
            intent_type="write",
            target="database",
            payload=test_payload,
        )

        assert intent.payload == test_payload
        assert intent.payload["string"] == "value"
        assert intent.payload["int"] == 42
        assert intent.payload["nested"]["key"] == "value"

    def test_epoch_validation(self):
        """Test epoch field validation."""
        # Valid epochs (>= 0)
        for epoch in [0, 1, 10, 100, 1000]:
            intent = ModelIntent(intent_type="log", target="service", epoch=epoch)
            assert intent.epoch == epoch

        # Test lower boundary - negative should fail
        with pytest.raises(ValidationError) as exc_info:
            ModelIntent(intent_type="log", target="service", epoch=-1)
        assert "greater than or equal to 0" in str(exc_info.value)

    def test_epoch_default_value(self):
        """Test epoch default value is None."""
        intent = ModelIntent(intent_type="log", target="service")
        assert intent.epoch is None

    def test_lease_id_validation(self):
        """Test lease_id UUID validation."""
        test_lease_id = uuid4()
        intent = ModelIntent(
            intent_type="log",
            target="service",
            lease_id=test_lease_id,
        )

        assert intent.lease_id == test_lease_id
        assert isinstance(intent.lease_id, UUID)

    def test_lease_id_default_value(self):
        """Test lease_id default value is None."""
        intent = ModelIntent(intent_type="log", target="service")
        assert intent.lease_id is None


class TestModelIntentSerialization:
    """Test ModelIntent serialization."""

    def test_model_dump(self):
        """Test serializing intent to dictionary."""
        test_intent_id = uuid4()
        test_lease_id = uuid4()

        intent = ModelIntent(
            intent_id=test_intent_id,
            intent_type="emit_event",
            target="kafka_topic",
            payload={"key": "value"},
            priority=7,
            lease_id=test_lease_id,
            epoch=2,
        )

        data = intent.model_dump()

        assert isinstance(data, dict)
        assert data["intent_id"] == test_intent_id
        assert data["intent_type"] == "emit_event"
        assert data["target"] == "kafka_topic"
        assert data["payload"] == {"key": "value"}
        assert data["priority"] == 7
        assert data["lease_id"] == test_lease_id
        assert data["epoch"] == 2

    def test_model_dump_json(self):
        """Test serializing intent to JSON string."""
        intent = ModelIntent(
            intent_type="log",
            target="service",
            payload={"metric": "cpu"},
        )

        json_str = intent.model_dump_json()

        assert isinstance(json_str, str)
        assert "intent_id" in json_str
        assert "intent_type" in json_str
        assert "log" in json_str
        assert "target" in json_str
        assert "service" in json_str
        assert "payload" in json_str
        assert "metric" in json_str

    def test_kafka_message_format_serialization(self):
        """Test serialization matches Kafka message format expectations."""
        test_payload = {
            "event_type": "METRICS_RECORDED",
            "timestamp": "2025-10-23T12:00:00Z",
            "data": {"cpu": 85.5, "memory": 2048},
        }

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
        assert kafka_data["payload"]["event_type"] == "METRICS_RECORDED"
        assert kafka_data["priority"] == 5


class TestModelIntentDeserialization:
    """Test ModelIntent deserialization."""

    def test_model_validate(self):
        """Test deserializing from dictionary."""
        test_intent_id = uuid4()
        test_lease_id = uuid4()

        data = {
            "intent_id": str(test_intent_id),
            "intent_type": "notify",
            "target": "slack_channel",
            "payload": {"message": "Deployment complete"},
            "priority": 3,
            "lease_id": str(test_lease_id),
            "epoch": 5,
        }

        intent = ModelIntent.model_validate(data)

        assert isinstance(intent, ModelIntent)
        assert intent.intent_id == test_intent_id
        assert intent.intent_type == "notify"
        assert intent.target == "slack_channel"
        assert intent.payload == {"message": "Deployment complete"}
        assert intent.priority == 3
        assert intent.lease_id == test_lease_id
        assert intent.epoch == 5

    def test_model_validate_json(self):
        """Test deserializing from JSON string."""
        test_intent_id = uuid4()

        json_str = f"""{{
            "intent_id": "{test_intent_id}",
            "intent_type": "write",
            "target": "database",
            "payload": {{"key": "value"}},
            "priority": 8
        }}"""

        intent = ModelIntent.model_validate_json(json_str)

        assert isinstance(intent, ModelIntent)
        assert intent.intent_id == test_intent_id
        assert intent.intent_type == "write"
        assert intent.target == "database"
        assert intent.payload == {"key": "value"}
        assert intent.priority == 8

    def test_kafka_message_deserialization(self):
        """Test deserializing from Kafka message format."""
        # Simulate Kafka message data
        kafka_message = {
            "intent_id": str(uuid4()),
            "intent_type": "emit_event",
            "target": "dev.omninode.metrics.v1",
            "payload": {
                "event_type": "NODE_GENERATION_COMPLETED",
                "correlation_id": str(uuid4()),
                "timestamp": "2025-10-23T12:00:00Z",
                "data": {"node_name": "NodeMetricsCollector"},
            },
            "priority": 6,
        }

        intent = ModelIntent.model_validate(kafka_message)

        assert isinstance(intent, ModelIntent)
        assert intent.intent_type == "emit_event"
        assert intent.target == "dev.omninode.metrics.v1"
        assert intent.payload["event_type"] == "NODE_GENERATION_COMPLETED"
        assert intent.priority == 6

    def test_roundtrip_serialization(self):
        """Test serialization and deserialization roundtrip."""
        original_intent = ModelIntent(
            intent_type="log",
            target="metrics_service",
            payload={"metric": "latency", "value": 125.3},
            priority=4,
            epoch=1,
        )

        # Serialize
        data = original_intent.model_dump()

        # Deserialize
        restored_intent = ModelIntent.model_validate(data)

        # Verify they are equivalent
        assert restored_intent.intent_id == original_intent.intent_id
        assert restored_intent.intent_type == original_intent.intent_type
        assert restored_intent.target == original_intent.target
        assert restored_intent.payload == original_intent.payload
        assert restored_intent.priority == original_intent.priority
        assert restored_intent.epoch == original_intent.epoch


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
            ModelIntent(intent_type="log")
        assert "target" in str(exc_info.value)

    def test_intent_type_boundary_values(self):
        """Test intent_type at exact boundaries."""
        # Exactly 1 character (minimum)
        intent = ModelIntent(intent_type="x", target="service")
        assert intent.intent_type == "x"

        # Exactly 100 characters (maximum)
        intent = ModelIntent(intent_type="x" * 100, target="service")
        assert intent.intent_type == "x" * 100

    def test_target_boundary_values(self):
        """Test target at exact boundaries."""
        # Exactly 1 character (minimum)
        intent = ModelIntent(intent_type="log", target="s")
        assert intent.target == "s"

        # Exactly 200 characters (maximum)
        intent = ModelIntent(intent_type="log", target="s" * 200)
        assert intent.target == "s" * 200

    def test_priority_boundary_values(self):
        """Test priority at exact boundaries."""
        # Exactly 1 (minimum)
        intent = ModelIntent(intent_type="log", target="service", priority=1)
        assert intent.priority == 1

        # Exactly 10 (maximum)
        intent = ModelIntent(intent_type="log", target="service", priority=10)
        assert intent.priority == 10

    def test_epoch_boundary_value(self):
        """Test epoch at boundary (0)."""
        intent = ModelIntent(intent_type="log", target="service", epoch=0)
        assert intent.epoch == 0

    def test_invalid_uuid_format(self):
        """Test that invalid UUID format raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ModelIntent(
                intent_type="log",
                target="service",
                intent_id="not-a-uuid",
            )
        assert "UUID" in str(exc_info.value) or "uuid" in str(exc_info.value).lower()

    def test_extra_fields_behavior(self):
        """Test behavior with extra fields (should be ignored)."""
        data = {
            "intent_type": "log",
            "target": "service",
            "extra_field": "should_be_ignored",
            "another_field": 123,
        }

        intent = ModelIntent.model_validate(data)

        # Should create successfully
        assert intent.intent_type == "log"
        assert intent.target == "service"

        # Extra fields should be ignored
        assert not hasattr(intent, "extra_field")
        assert not hasattr(intent, "another_field")


class TestModelIntentModelConfig:
    """Test ModelIntent model configuration."""

    def test_model_config_extra_ignore(self):
        """Test that model_config has extra='ignore'."""
        assert ModelIntent.model_config["extra"] == "ignore"

    def test_model_config_validate_assignment(self):
        """Test that model_config has validate_assignment=True."""
        assert ModelIntent.model_config["validate_assignment"] is True

    def test_assignment_validation(self):
        """Test that assignment validation works."""
        intent = ModelIntent(intent_type="log", target="service", priority=5)

        # Valid assignment
        intent.priority = 8
        assert intent.priority == 8

        # Invalid assignment should raise ValidationError
        with pytest.raises(ValidationError):
            intent.priority = 11  # Out of range

    def test_model_config_use_enum_values(self):
        """Test that model_config has use_enum_values=False."""
        assert ModelIntent.model_config["use_enum_values"] is False


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
        assert "Intent declaration" in ModelIntent.__doc__

    def test_model_class_name(self):
        """Test ModelIntent class name."""
        assert ModelIntent.__name__ == "ModelIntent"

    def test_model_module(self):
        """Test ModelIntent module."""
        assert ModelIntent.__module__ == "omnibase_core.models.reducer.model_intent"

    def test_model_inheritance(self):
        """Test that ModelIntent inherits from BaseModel."""
        from pydantic import BaseModel

        intent = ModelIntent(intent_type="log", target="service")
        assert isinstance(intent, BaseModel)


class TestModelIntentComparison:
    """Test ModelIntent comparison operations."""

    def test_equality_same_values(self):
        """Test equality with same field values."""
        test_id = uuid4()
        test_lease_id = uuid4()

        intent1 = ModelIntent(
            intent_id=test_id,
            intent_type="log",
            target="service",
            payload={"key": "value"},
            priority=5,
            lease_id=test_lease_id,
            epoch=2,
        )

        intent2 = ModelIntent(
            intent_id=test_id,
            intent_type="log",
            target="service",
            payload={"key": "value"},
            priority=5,
            lease_id=test_lease_id,
            epoch=2,
        )

        assert intent1 == intent2

    def test_inequality_different_values(self):
        """Test inequality with different field values."""
        intent1 = ModelIntent(intent_type="log", target="service1")
        intent2 = ModelIntent(intent_type="log", target="service2")

        assert intent1 != intent2

    def test_model_copy(self):
        """Test creating a copy of ModelIntent."""
        original = ModelIntent(
            intent_type="emit_event",
            target="kafka_topic",
            payload={"data": "test"},
            priority=7,
        )

        copied = original.model_copy()

        assert copied == original
        assert copied is not original
        assert copied.intent_id == original.intent_id
        assert copied.intent_type == original.intent_type

    def test_model_copy_deep(self):
        """Test deep copy of ModelIntent with nested payload."""
        original = ModelIntent(
            intent_type="write",
            target="database",
            payload={"nested": {"key": "value"}},
        )

        copied = original.model_copy(deep=True)

        # Modify nested payload in copy
        copied.payload["nested"]["key"] = "modified"

        # Original should be unchanged
        assert original.payload["nested"]["key"] == "value"
        assert copied.payload["nested"]["key"] == "modified"


class TestModelIntentStringRepresentation:
    """Test ModelIntent string representation."""

    def test_str_representation(self):
        """Test string representation of ModelIntent."""
        intent = ModelIntent(intent_type="log", target="service")

        str_repr = str(intent)
        assert isinstance(str_repr, str)
        assert "intent_type" in str_repr or "log" in str_repr

    def test_repr_representation(self):
        """Test repr representation of ModelIntent."""
        intent = ModelIntent(intent_type="log", target="service")

        repr_str = repr(intent)
        assert isinstance(repr_str, str)
        assert "ModelIntent" in repr_str
