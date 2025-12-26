"""Tests for ModelDeliveryResult."""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from omnibase_core.models.event_bus.model_delivery_result import ModelDeliveryResult


@pytest.mark.unit
class TestModelDeliveryResult:
    """Test suite for ModelDeliveryResult."""

    def test_initialization_with_required_fields(self):
        """Test initialization with required fields only."""
        result = ModelDeliveryResult(
            success=True,
            topic="test-topic",
        )

        assert result.success is True
        assert result.topic == "test-topic"
        assert result.partition is None
        assert result.offset is None
        assert result.timestamp is None
        assert result.error_message is None

    def test_initialization_with_all_fields(self):
        """Test initialization with all fields."""
        now = datetime.now(UTC)
        result = ModelDeliveryResult(
            success=True,
            topic="test-topic",
            partition=0,
            offset=12345,
            timestamp=now,
            error_message=None,
        )

        assert result.success is True
        assert result.topic == "test-topic"
        assert result.partition == 0
        assert result.offset == 12345
        assert result.timestamp == now
        assert result.error_message is None

    def test_initialization_failure(self):
        """Test initialization for failed delivery."""
        result = ModelDeliveryResult(
            success=False,
            topic="test-topic",
            error_message="Connection timeout",
        )

        assert result.success is False
        assert result.topic == "test-topic"
        assert result.error_message == "Connection timeout"
        assert result.offset is None

    def test_immutability(self):
        """Test that model is immutable (frozen)."""
        result = ModelDeliveryResult(
            success=True,
            topic="test-topic",
        )

        with pytest.raises(ValidationError):
            result.success = False

    def test_extra_forbid(self):
        """Test that extra fields are forbidden."""
        with pytest.raises(ValidationError):
            ModelDeliveryResult(
                success=True,
                topic="test-topic",
                extra_field="not allowed",
            )

    def test_topic_validation_empty(self):
        """Test topic validation rejects empty string."""
        with pytest.raises(ValidationError):
            ModelDeliveryResult(success=True, topic="")

    def test_topic_validation_whitespace(self):
        """Test topic validation strips and rejects whitespace-only."""
        with pytest.raises(ValidationError):
            ModelDeliveryResult(success=True, topic="   ")

    def test_partition_validation_negative(self):
        """Test partition validation rejects negative values."""
        with pytest.raises(ValidationError):
            ModelDeliveryResult(success=True, topic="test", partition=-1)

    def test_offset_validation_negative(self):
        """Test offset validation rejects negative values."""
        with pytest.raises(ValidationError):
            ModelDeliveryResult(success=True, topic="test", offset=-1)

    def test_error_message_strips_whitespace(self):
        """Test error_message strips whitespace."""
        result = ModelDeliveryResult(
            success=False,
            topic="test-topic",
            error_message="  Error message  ",
        )
        assert result.error_message == "Error message"

    def test_error_message_empty_becomes_none(self):
        """Test empty error_message becomes None."""
        result = ModelDeliveryResult(
            success=False,
            topic="test-topic",
            error_message="   ",
        )
        assert result.error_message is None

    def test_is_successful(self):
        """Test is_successful method."""
        success = ModelDeliveryResult(success=True, topic="test")
        failure = ModelDeliveryResult(success=False, topic="test")

        assert success.is_successful() is True
        assert failure.is_successful() is False

    def test_is_failed(self):
        """Test is_failed method."""
        success = ModelDeliveryResult(success=True, topic="test")
        failure = ModelDeliveryResult(success=False, topic="test")

        assert success.is_failed() is False
        assert failure.is_failed() is True

    def test_has_offset(self):
        """Test has_offset method."""
        with_offset = ModelDeliveryResult(success=True, topic="test", offset=0)
        without_offset = ModelDeliveryResult(success=True, topic="test")

        assert with_offset.has_offset() is True
        assert without_offset.has_offset() is False

    def test_has_timestamp(self):
        """Test has_timestamp method."""
        now = datetime.now(UTC)
        with_timestamp = ModelDeliveryResult(success=True, topic="test", timestamp=now)
        without_timestamp = ModelDeliveryResult(success=True, topic="test")

        assert with_timestamp.has_timestamp() is True
        assert without_timestamp.has_timestamp() is False

    def test_has_error(self):
        """Test has_error method."""
        with_error = ModelDeliveryResult(
            success=False, topic="test", error_message="Error"
        )
        without_error = ModelDeliveryResult(success=True, topic="test")

        assert with_error.has_error() is True
        assert without_error.has_error() is False

    def test_get_partition_offset(self):
        """Test get_partition_offset method."""
        result = ModelDeliveryResult(
            success=True,
            topic="test",
            partition=1,
            offset=100,
        )
        assert result.get_partition_offset() == "1:100"

        # Without partition/offset
        result_no_offset = ModelDeliveryResult(success=True, topic="test")
        assert result_no_offset.get_partition_offset() == "unknown"

    def test_get_timestamp_iso(self):
        """Test get_timestamp_iso method."""
        now = datetime.now(UTC)
        result = ModelDeliveryResult(success=True, topic="test", timestamp=now)

        iso_str = result.get_timestamp_iso()
        assert iso_str is not None
        assert now.isoformat() == iso_str

        # Without timestamp
        result_no_ts = ModelDeliveryResult(success=True, topic="test")
        assert result_no_ts.get_timestamp_iso() is None

    def test_get_summary_success(self):
        """Test get_summary for successful delivery."""
        result = ModelDeliveryResult(
            success=True,
            topic="test-topic",
            partition=0,
            offset=100,
        )

        summary = result.get_summary()
        assert "Delivered to test-topic" in summary
        assert "0:100" in summary

    def test_get_summary_failure(self):
        """Test get_summary for failed delivery."""
        result = ModelDeliveryResult(
            success=False,
            topic="test-topic",
            error_message="Connection refused",
        )

        summary = result.get_summary()
        assert "Failed to deliver" in summary
        assert "test-topic" in summary
        assert "Connection refused" in summary

    def test_create_success_factory(self):
        """Test create_success factory method."""
        result = ModelDeliveryResult.create_success(
            topic="test-topic",
            partition=0,
            offset=100,
        )

        assert result.success is True
        assert result.topic == "test-topic"
        assert result.partition == 0
        assert result.offset == 100
        assert result.timestamp is not None

    def test_create_success_with_timestamp(self):
        """Test create_success with custom timestamp."""
        now = datetime.now(UTC)
        result = ModelDeliveryResult.create_success(
            topic="test-topic",
            partition=0,
            offset=100,
            timestamp=now,
        )

        assert result.timestamp == now

    def test_create_failure_factory(self):
        """Test create_failure factory method."""
        result = ModelDeliveryResult.create_failure(
            topic="test-topic",
            error_message="Connection timeout",
        )

        assert result.success is False
        assert result.topic == "test-topic"
        assert result.error_message == "Connection timeout"
        assert result.offset is None
        assert result.timestamp is None

    def test_create_failure_with_partition(self):
        """Test create_failure with partition."""
        result = ModelDeliveryResult.create_failure(
            topic="test-topic",
            error_message="Write failed",
            partition=2,
        )

        assert result.partition == 2

    def test_serialization(self):
        """Test model serialization."""
        now = datetime.now(UTC)
        result = ModelDeliveryResult(
            success=True,
            topic="test-topic",
            partition=0,
            offset=100,
            timestamp=now,
        )

        data = result.model_dump()

        assert data["success"] is True
        assert data["topic"] == "test-topic"
        assert data["partition"] == 0
        assert data["offset"] == 100
        assert data["timestamp"] == now

    def test_deserialization(self):
        """Test model deserialization from dict."""
        now = datetime.now(UTC)
        data = {
            "success": True,
            "topic": "test-topic",
            "partition": 1,
            "offset": 50,
            "timestamp": now,
        }

        result = ModelDeliveryResult(**data)

        assert result.success is True
        assert result.topic == "test-topic"
        assert result.partition == 1
        assert result.offset == 50
        assert result.timestamp == now
