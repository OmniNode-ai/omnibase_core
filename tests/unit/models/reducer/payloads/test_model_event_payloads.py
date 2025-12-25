# SPDX-FileCopyrightText: 2025 OmniNode Team
#
# SPDX-License-Identifier: Apache-2.0

"""
Tests for PayloadEmitEvent.

This module tests the PayloadEmitEvent model for event emission intents, verifying:
1. Field validation (event_type, event_data, topic, etc.)
2. Discriminator value
3. Serialization/deserialization
4. Immutability
5. Default values
"""

import pytest
from pydantic import ValidationError

from omnibase_core.models.reducer.payloads import PayloadEmitEvent


@pytest.mark.unit
class TestPayloadEmitEventInstantiation:
    """Test PayloadEmitEvent instantiation."""

    def test_create_with_required_fields(self) -> None:
        """Test creating payload with required fields only."""
        payload = PayloadEmitEvent(
            event_type="order.created",
            event_data={"order_id": "123"},
            topic="orders",
        )
        assert payload.event_type == "order.created"
        assert payload.event_data == {"order_id": "123"}
        assert payload.topic == "orders"
        assert payload.intent_type == "emit_event"

    def test_create_with_all_fields(self) -> None:
        """Test creating payload with all fields."""
        payload = PayloadEmitEvent(
            event_type="inventory.updated",
            event_data={"sku": "PROD-123", "quantity": 50},
            topic="inventory-events",
            correlation_id="req-xyz-789",
            partition_key="PROD-123",
            headers={"event-version": "1.0", "source": "inventory-service"},
        )
        assert payload.event_type == "inventory.updated"
        assert payload.event_data == {"sku": "PROD-123", "quantity": 50}
        assert payload.topic == "inventory-events"
        assert payload.correlation_id == "req-xyz-789"
        assert payload.partition_key == "PROD-123"
        assert payload.headers == {
            "event-version": "1.0",
            "source": "inventory-service",
        }


@pytest.mark.unit
class TestPayloadEmitEventDiscriminator:
    """Test discriminator field."""

    def test_intent_type_value(self) -> None:
        """Test that intent_type is 'emit_event'."""
        payload = PayloadEmitEvent(event_type="test.event", event_data={}, topic="test")
        assert payload.intent_type == "emit_event"

    def test_intent_type_in_serialization(self) -> None:
        """Test that intent_type is included in serialization."""
        payload = PayloadEmitEvent(event_type="test.event", event_data={}, topic="test")
        data = payload.model_dump()
        assert data["intent_type"] == "emit_event"


@pytest.mark.unit
class TestPayloadEmitEventTypeValidation:
    """Test event_type field validation."""

    def test_event_type_required(self) -> None:
        """Test that event_type is required."""
        with pytest.raises(ValidationError) as exc_info:
            PayloadEmitEvent(event_data={}, topic="test")  # type: ignore[call-arg]
        assert "event_type" in str(exc_info.value)

    def test_event_type_min_length(self) -> None:
        """Test event_type minimum length validation."""
        with pytest.raises(ValidationError) as exc_info:
            PayloadEmitEvent(event_type="", event_data={}, topic="test")
        assert "event_type" in str(exc_info.value)

    def test_event_type_max_length(self) -> None:
        """Test event_type maximum length validation."""
        long_type = "a" * 257
        with pytest.raises(ValidationError) as exc_info:
            PayloadEmitEvent(event_type=long_type, event_data={}, topic="test")
        assert "event_type" in str(exc_info.value)

    def test_event_type_valid_patterns(self) -> None:
        """Test valid event_type patterns."""
        valid_types = [
            "order.created",
            "user.registered",
            "payment_processed",
            "inventory-updated",
            "Event123",
        ]
        for event_type in valid_types:
            payload = PayloadEmitEvent(
                event_type=event_type, event_data={}, topic="test"
            )
            assert payload.event_type == event_type

    def test_event_type_invalid_start_with_number(self) -> None:
        """Test that event_type cannot start with number."""
        with pytest.raises(ValidationError) as exc_info:
            PayloadEmitEvent(event_type="123event", event_data={}, topic="test")
        assert "event_type" in str(exc_info.value)


@pytest.mark.unit
class TestPayloadEmitEventTopicValidation:
    """Test topic field validation."""

    def test_topic_required(self) -> None:
        """Test that topic is required."""
        with pytest.raises(ValidationError) as exc_info:
            PayloadEmitEvent(event_type="test", event_data={})  # type: ignore[call-arg]
        assert "topic" in str(exc_info.value)

    def test_topic_min_length(self) -> None:
        """Test topic minimum length validation."""
        with pytest.raises(ValidationError) as exc_info:
            PayloadEmitEvent(event_type="test", event_data={}, topic="")
        assert "topic" in str(exc_info.value)

    def test_topic_max_length(self) -> None:
        """Test topic maximum length validation."""
        long_topic = "a" * 257
        with pytest.raises(ValidationError) as exc_info:
            PayloadEmitEvent(event_type="test", event_data={}, topic=long_topic)
        assert "topic" in str(exc_info.value)


@pytest.mark.unit
class TestPayloadEmitEventDefaultValues:
    """Test default values."""

    def test_default_correlation_id(self) -> None:
        """Test default correlation_id is None."""
        payload = PayloadEmitEvent(event_type="test", event_data={}, topic="test")
        assert payload.correlation_id is None

    def test_default_partition_key(self) -> None:
        """Test default partition_key is None."""
        payload = PayloadEmitEvent(event_type="test", event_data={}, topic="test")
        assert payload.partition_key is None

    def test_default_headers(self) -> None:
        """Test default headers is empty dict."""
        payload = PayloadEmitEvent(event_type="test", event_data={}, topic="test")
        assert payload.headers == {}


@pytest.mark.unit
class TestPayloadEmitEventCorrelationIdValidation:
    """Test correlation_id field validation."""

    def test_correlation_id_max_length(self) -> None:
        """Test correlation_id maximum length validation."""
        long_id = "a" * 129
        with pytest.raises(ValidationError) as exc_info:
            PayloadEmitEvent(
                event_type="test",
                event_data={},
                topic="test",
                correlation_id=long_id,
            )
        assert "correlation_id" in str(exc_info.value)


@pytest.mark.unit
class TestPayloadEmitEventPartitionKeyValidation:
    """Test partition_key field validation."""

    def test_partition_key_max_length(self) -> None:
        """Test partition_key maximum length validation."""
        long_key = "a" * 257
        with pytest.raises(ValidationError) as exc_info:
            PayloadEmitEvent(
                event_type="test",
                event_data={},
                topic="test",
                partition_key=long_key,
            )
        assert "partition_key" in str(exc_info.value)


@pytest.mark.unit
class TestPayloadEmitEventImmutability:
    """Test frozen/immutability."""

    def test_cannot_modify_event_type(self) -> None:
        """Test that event_type cannot be modified after creation."""
        payload = PayloadEmitEvent(event_type="test", event_data={}, topic="test")
        with pytest.raises(ValidationError):
            payload.event_type = "new.type"  # type: ignore[misc]

    def test_cannot_modify_topic(self) -> None:
        """Test that topic cannot be modified after creation."""
        payload = PayloadEmitEvent(event_type="test", event_data={}, topic="test")
        with pytest.raises(ValidationError):
            payload.topic = "new-topic"  # type: ignore[misc]


@pytest.mark.unit
class TestPayloadEmitEventSerialization:
    """Test serialization/deserialization."""

    def test_roundtrip_serialization(self) -> None:
        """Test roundtrip serialization."""
        original = PayloadEmitEvent(
            event_type="order.created",
            event_data={"order_id": "123", "total": 99.99},
            topic="orders",
            correlation_id="req-abc-123",
            partition_key="order-123",
            headers={"version": "1.0"},
        )
        data = original.model_dump()
        restored = PayloadEmitEvent.model_validate(data)
        assert restored == original

    def test_json_roundtrip(self) -> None:
        """Test JSON roundtrip serialization."""
        original = PayloadEmitEvent(
            event_type="test", event_data={"key": "value"}, topic="test"
        )
        json_str = original.model_dump_json()
        restored = PayloadEmitEvent.model_validate_json(json_str)
        assert restored == original

    def test_serialization_includes_all_fields(self) -> None:
        """Test that serialization includes all fields."""
        payload = PayloadEmitEvent(event_type="test", event_data={}, topic="test")
        data = payload.model_dump()
        expected_keys = {
            "intent_type",
            "event_type",
            "event_data",
            "topic",
            "correlation_id",
            "partition_key",
            "headers",
        }
        assert set(data.keys()) == expected_keys


@pytest.mark.unit
class TestPayloadEmitEventExtraFieldsRejected:
    """Test that extra fields are rejected."""

    def test_reject_extra_field(self) -> None:
        """Test that extra fields are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            PayloadEmitEvent(
                event_type="test",
                event_data={},
                topic="test",
                unknown_field="value",  # type: ignore[call-arg]
            )
        assert "extra_forbidden" in str(exc_info.value)
