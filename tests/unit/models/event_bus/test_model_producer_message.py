# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for ModelProducerMessage."""

import pytest
from pydantic import ValidationError

from omnibase_core.models.event_bus.model_producer_message import ModelProducerMessage


@pytest.mark.unit
class TestModelProducerMessage:
    """Test suite for ModelProducerMessage."""

    def test_initialization_with_required_fields(self):
        """Test initialization with required fields only."""
        message = ModelProducerMessage(
            topic="test-topic",
            value=b"test message",
        )

        assert message.topic == "test-topic"
        assert message.value == b"test message"
        assert message.key is None
        assert message.headers is None
        assert message.partition is None

    def test_initialization_with_all_fields(self):
        """Test initialization with all fields."""
        headers = {"content-type": b"application/json"}
        message = ModelProducerMessage(
            topic="test-topic",
            value=b"test message",
            key=b"test-key",
            headers=headers,
            partition=0,
        )

        assert message.topic == "test-topic"
        assert message.value == b"test message"
        assert message.key == b"test-key"
        assert message.headers == headers
        assert message.partition == 0

    def test_immutability(self):
        """Test that model is immutable (frozen)."""
        message = ModelProducerMessage(
            topic="test-topic",
            value=b"test message",
        )

        with pytest.raises(ValidationError):
            message.topic = "new-topic"

    def test_extra_forbid(self):
        """Test that extra fields are forbidden."""
        with pytest.raises(ValidationError):
            ModelProducerMessage(
                topic="test-topic",
                value=b"test message",
                extra_field="not allowed",
            )

    def test_topic_validation_empty(self):
        """Test topic validation rejects empty string."""
        with pytest.raises(ValidationError):
            ModelProducerMessage(topic="", value=b"test")

    def test_topic_validation_whitespace(self):
        """Test topic validation rejects whitespace-only."""
        with pytest.raises(ValidationError):
            ModelProducerMessage(topic="   ", value=b"test")

    def test_topic_validation_invalid_chars(self):
        """Test topic validation rejects invalid characters."""
        with pytest.raises(ValidationError):
            ModelProducerMessage(topic="test/topic", value=b"test")

        with pytest.raises(ValidationError):
            ModelProducerMessage(topic="test topic", value=b"test")

    def test_topic_validation_valid_chars(self):
        """Test topic validation accepts valid characters."""
        # Alphanumeric
        msg = ModelProducerMessage(topic="test123", value=b"test")
        assert msg.topic == "test123"

        # With dots
        msg = ModelProducerMessage(topic="test.topic", value=b"test")
        assert msg.topic == "test.topic"

        # With underscores
        msg = ModelProducerMessage(topic="test_topic", value=b"test")
        assert msg.topic == "test_topic"

        # With hyphens
        msg = ModelProducerMessage(topic="test-topic", value=b"test")
        assert msg.topic == "test-topic"

    def test_value_validation_empty(self):
        """Test value validation rejects empty bytes."""
        with pytest.raises(ValidationError):
            ModelProducerMessage(topic="test-topic", value=b"")

    def test_partition_validation_negative(self):
        """Test partition validation rejects negative values."""
        with pytest.raises(ValidationError):
            ModelProducerMessage(topic="test-topic", value=b"test", partition=-1)

    def test_partition_validation_zero(self):
        """Test partition validation accepts zero."""
        message = ModelProducerMessage(topic="test-topic", value=b"test", partition=0)
        assert message.partition == 0

    def test_get_key_string(self):
        """Test get_key_string method."""
        message = ModelProducerMessage(
            topic="test-topic",
            value=b"test",
            key=b"my-key",
        )
        assert message.get_key_string() == "my-key"

        # Without key
        message_no_key = ModelProducerMessage(topic="test-topic", value=b"test")
        assert message_no_key.get_key_string() is None

    def test_get_value_string(self):
        """Test get_value_string method."""
        message = ModelProducerMessage(topic="test-topic", value=b"hello world")
        assert message.get_value_string() == "hello world"

    def test_get_headers_dict(self):
        """Test get_headers_dict method."""
        headers = {
            "content-type": b"application/json",
            "x-custom": b"value",
        }
        message = ModelProducerMessage(
            topic="test-topic",
            value=b"test",
            headers=headers,
        )

        result = message.get_headers_dict()
        assert result == {
            "content-type": "application/json",
            "x-custom": "value",
        }

        # Without headers
        message_no_headers = ModelProducerMessage(topic="test-topic", value=b"test")
        assert message_no_headers.get_headers_dict() == {}

    def test_has_key(self):
        """Test has_key method."""
        with_key = ModelProducerMessage(topic="test", value=b"test", key=b"key")
        without_key = ModelProducerMessage(topic="test", value=b"test")

        assert with_key.has_key() is True
        assert without_key.has_key() is False

    def test_has_headers(self):
        """Test has_headers method."""
        with_headers = ModelProducerMessage(
            topic="test", value=b"test", headers={"k": b"v"}
        )
        without_headers = ModelProducerMessage(topic="test", value=b"test")
        empty_headers = ModelProducerMessage(topic="test", value=b"test", headers={})

        assert with_headers.has_headers() is True
        assert without_headers.has_headers() is False
        assert empty_headers.has_headers() is False

    def test_has_partition(self):
        """Test has_partition method."""
        with_partition = ModelProducerMessage(topic="test", value=b"test", partition=0)
        without_partition = ModelProducerMessage(topic="test", value=b"test")

        assert with_partition.has_partition() is True
        assert without_partition.has_partition() is False

    def test_get_size_bytes(self):
        """Test get_size_bytes method."""
        message = ModelProducerMessage(
            topic="test",
            value=b"hello",  # 5 bytes
            key=b"key",  # 3 bytes
            headers={"h": b"v"},  # 1 + 1 = 2 bytes
        )

        assert message.get_size_bytes() == 10

    def test_create_simple(self):
        """Test create_simple factory method."""
        message = ModelProducerMessage.create_simple("test-topic", "hello world")

        assert message.topic == "test-topic"
        assert message.value == b"hello world"
        assert message.key is None
        assert message.headers is None

    def test_create_with_key(self):
        """Test create_with_key factory method."""
        message = ModelProducerMessage.create_with_key("test-topic", "hello", "my-key")

        assert message.topic == "test-topic"
        assert message.value == b"hello"
        assert message.key == b"my-key"

    def test_create_with_headers(self):
        """Test create_with_headers factory method."""
        headers = {"content-type": "application/json", "x-custom": "value"}
        message = ModelProducerMessage.create_with_headers(
            "test-topic", "hello", headers
        )

        assert message.topic == "test-topic"
        assert message.value == b"hello"
        assert message.headers == {
            "content-type": b"application/json",
            "x-custom": b"value",
        }

    def test_serialization(self):
        """Test model serialization."""
        message = ModelProducerMessage(
            topic="test-topic",
            value=b"test message",
            key=b"test-key",
            partition=1,
        )

        data = message.model_dump()

        assert data["topic"] == "test-topic"
        assert data["value"] == b"test message"
        assert data["key"] == b"test-key"
        assert data["partition"] == 1

    def test_deserialization(self):
        """Test model deserialization from dict."""
        data = {
            "topic": "test-topic",
            "value": b"test message",
            "key": b"test-key",
        }

        message = ModelProducerMessage(**data)

        assert message.topic == "test-topic"
        assert message.value == b"test message"
        assert message.key == b"test-key"
