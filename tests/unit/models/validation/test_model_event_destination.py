# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

#
# SPDX-License-Identifier: Apache-2.0
"""Unit tests for ModelEventDestination.

Tests cover:
- Factory methods (create_memory, create_file, create_kafka)
- Validation rules (file destination requires file_path, etc.)
- Default values
- Serialization and deserialization
- Property methods

Related:
    - OMN-1151: Event destination configuration for contract validation
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from omnibase_core.enums.enum_event_sink_type import EnumEventSinkType
from omnibase_core.models.validation.model_event_destination import (
    ModelEventDestination,
)

# =============================================================================
# Factory Method Tests
# =============================================================================


@pytest.mark.unit
class TestModelEventDestinationFactories:
    """Tests for factory methods."""

    def test_create_memory_with_defaults(self) -> None:
        """Test create_memory with default values."""
        dest = ModelEventDestination.create_memory()

        assert dest.destination_type == EnumEventSinkType.MEMORY
        assert dest.destination_name == "memory"
        assert dest.enabled is True
        assert dest.buffer_size == 100
        assert dest.file_path is None
        assert dest.topic is None
        assert dest.bootstrap_servers is None

    def test_create_memory_with_custom_name(self) -> None:
        """Test create_memory with custom name."""
        dest = ModelEventDestination.create_memory(name="custom-memory")

        assert dest.destination_name == "custom-memory"
        assert dest.destination_type == EnumEventSinkType.MEMORY

    def test_create_memory_with_custom_buffer_size(self) -> None:
        """Test create_memory with custom buffer_size."""
        dest = ModelEventDestination.create_memory(buffer_size=500)

        assert dest.buffer_size == 500

    def test_create_file_with_required_params(self) -> None:
        """Test create_file with required parameters."""
        dest = ModelEventDestination.create_file(
            name="events-file",
            file_path="/var/log/events.jsonl",
        )

        assert dest.destination_type == EnumEventSinkType.FILE
        assert dest.destination_name == "events-file"
        assert dest.file_path == "/var/log/events.jsonl"
        assert dest.enabled is True
        assert dest.buffer_size == 100
        assert dest.flush_interval_ms == 5000

    def test_create_file_with_custom_params(self) -> None:
        """Test create_file with all custom parameters."""
        dest = ModelEventDestination.create_file(
            name="custom-file",
            file_path="/tmp/custom.jsonl",
            buffer_size=50,
            flush_interval_ms=2000,
        )

        assert dest.destination_name == "custom-file"
        assert dest.file_path == "/tmp/custom.jsonl"
        assert dest.buffer_size == 50
        assert dest.flush_interval_ms == 2000

    def test_create_kafka_with_required_params(self) -> None:
        """Test create_kafka with required parameters."""
        dest = ModelEventDestination.create_kafka(
            name="kafka-events",
            topic="contract.validation.events",
            bootstrap_servers="192.168.86.200:29092",
        )

        assert dest.destination_type == EnumEventSinkType.KAFKA
        assert dest.destination_name == "kafka-events"
        assert dest.topic == "contract.validation.events"
        assert dest.bootstrap_servers == "192.168.86.200:29092"
        assert dest.buffer_size == 100
        assert dest.flush_interval_ms == 1000  # Kafka default is lower

    def test_create_kafka_with_custom_params(self) -> None:
        """Test create_kafka with all custom parameters."""
        dest = ModelEventDestination.create_kafka(
            name="custom-kafka",
            topic="custom.topic",
            bootstrap_servers="localhost:9092,localhost:9093",
            buffer_size=200,
            flush_interval_ms=500,
        )

        assert dest.destination_name == "custom-kafka"
        assert dest.topic == "custom.topic"
        assert dest.bootstrap_servers == "localhost:9092,localhost:9093"
        assert dest.buffer_size == 200
        assert dest.flush_interval_ms == 500


# =============================================================================
# Validation Tests
# =============================================================================


@pytest.mark.unit
class TestModelEventDestinationValidation:
    """Tests for validation rules."""

    def test_file_destination_requires_file_path(self) -> None:
        """Test that FILE destination type requires file_path."""
        with pytest.raises(ValidationError) as exc_info:
            ModelEventDestination(
                destination_type=EnumEventSinkType.FILE,
                destination_name="file-no-path",
                # file_path is None
            )

        error_str = str(exc_info.value)
        assert "file_path" in error_str.lower()

    def test_kafka_destination_requires_topic(self) -> None:
        """Test that KAFKA destination type requires topic."""
        with pytest.raises(ValidationError) as exc_info:
            ModelEventDestination(
                destination_type=EnumEventSinkType.KAFKA,
                destination_name="kafka-no-topic",
                bootstrap_servers="localhost:9092",
                # topic is None
            )

        error_str = str(exc_info.value)
        assert "topic" in error_str.lower()

    def test_kafka_destination_requires_bootstrap_servers(self) -> None:
        """Test that KAFKA destination type requires bootstrap_servers."""
        with pytest.raises(ValidationError) as exc_info:
            ModelEventDestination(
                destination_type=EnumEventSinkType.KAFKA,
                destination_name="kafka-no-servers",
                topic="test.topic",
                # bootstrap_servers is None
            )

        error_str = str(exc_info.value)
        assert "bootstrap_servers" in error_str.lower()

    def test_memory_destination_does_not_require_file_path(self) -> None:
        """Test that MEMORY destination does not require file_path."""
        dest = ModelEventDestination(
            destination_type=EnumEventSinkType.MEMORY,
            destination_name="memory-test",
        )

        assert dest.file_path is None

    def test_destination_name_required(self) -> None:
        """Test that destination_name is required."""
        with pytest.raises(ValidationError) as exc_info:
            ModelEventDestination(
                destination_type=EnumEventSinkType.MEMORY,
                # destination_name missing
            )  # type: ignore[call-arg]

        error_str = str(exc_info.value)
        assert "destination_name" in error_str

    def test_destination_name_min_length(self) -> None:
        """Test that destination_name has min_length=1."""
        with pytest.raises(ValidationError) as exc_info:
            ModelEventDestination(
                destination_type=EnumEventSinkType.MEMORY,
                destination_name="",  # Empty string
            )

        error_str = str(exc_info.value)
        assert "destination_name" in error_str or "min_length" in error_str.lower()

    def test_destination_name_max_length(self) -> None:
        """Test that destination_name has max_length=255."""
        with pytest.raises(ValidationError) as exc_info:
            ModelEventDestination(
                destination_type=EnumEventSinkType.MEMORY,
                destination_name="a" * 256,  # Too long
            )

        error_str = str(exc_info.value)
        assert "destination_name" in error_str or "max_length" in error_str.lower()

    def test_buffer_size_min_value(self) -> None:
        """Test that buffer_size has minimum value of 1."""
        with pytest.raises(ValidationError) as exc_info:
            ModelEventDestination(
                destination_type=EnumEventSinkType.MEMORY,
                destination_name="test",
                buffer_size=0,  # Below minimum
            )

        error_str = str(exc_info.value)
        assert "buffer_size" in error_str or "greater" in error_str.lower()

    def test_buffer_size_max_value(self) -> None:
        """Test that buffer_size has maximum value of 10000."""
        with pytest.raises(ValidationError) as exc_info:
            ModelEventDestination(
                destination_type=EnumEventSinkType.MEMORY,
                destination_name="test",
                buffer_size=10001,  # Above maximum
            )

        error_str = str(exc_info.value)
        assert "buffer_size" in error_str or "less" in error_str.lower()

    def test_flush_interval_ms_min_value(self) -> None:
        """Test that flush_interval_ms has minimum value of 100."""
        with pytest.raises(ValidationError) as exc_info:
            ModelEventDestination(
                destination_type=EnumEventSinkType.MEMORY,
                destination_name="test",
                flush_interval_ms=50,  # Below minimum
            )

        error_str = str(exc_info.value)
        assert "flush_interval_ms" in error_str or "greater" in error_str.lower()

    def test_flush_interval_ms_max_value(self) -> None:
        """Test that flush_interval_ms has maximum value of 60000."""
        with pytest.raises(ValidationError) as exc_info:
            ModelEventDestination(
                destination_type=EnumEventSinkType.MEMORY,
                destination_name="test",
                flush_interval_ms=60001,  # Above maximum
            )

        error_str = str(exc_info.value)
        assert "flush_interval_ms" in error_str or "less" in error_str.lower()


# =============================================================================
# Default Value Tests
# =============================================================================


@pytest.mark.unit
class TestModelEventDestinationDefaults:
    """Tests for default values."""

    def test_enabled_defaults_to_true(self) -> None:
        """Test that enabled defaults to True."""
        dest = ModelEventDestination(
            destination_type=EnumEventSinkType.MEMORY,
            destination_name="test",
        )

        assert dest.enabled is True

    def test_buffer_size_defaults_to_100(self) -> None:
        """Test that buffer_size defaults to 100."""
        dest = ModelEventDestination(
            destination_type=EnumEventSinkType.MEMORY,
            destination_name="test",
        )

        assert dest.buffer_size == 100

    def test_flush_interval_ms_defaults_to_5000(self) -> None:
        """Test that flush_interval_ms defaults to 5000."""
        dest = ModelEventDestination(
            destination_type=EnumEventSinkType.MEMORY,
            destination_name="test",
        )

        assert dest.flush_interval_ms == 5000

    def test_file_path_defaults_to_none(self) -> None:
        """Test that file_path defaults to None."""
        dest = ModelEventDestination(
            destination_type=EnumEventSinkType.MEMORY,
            destination_name="test",
        )

        assert dest.file_path is None

    def test_topic_defaults_to_none(self) -> None:
        """Test that topic defaults to None."""
        dest = ModelEventDestination(
            destination_type=EnumEventSinkType.MEMORY,
            destination_name="test",
        )

        assert dest.topic is None

    def test_bootstrap_servers_defaults_to_none(self) -> None:
        """Test that bootstrap_servers defaults to None."""
        dest = ModelEventDestination(
            destination_type=EnumEventSinkType.MEMORY,
            destination_name="test",
        )

        assert dest.bootstrap_servers is None


# =============================================================================
# Property Method Tests
# =============================================================================


@pytest.mark.unit
class TestModelEventDestinationProperties:
    """Tests for property methods."""

    def test_is_persistent_memory(self) -> None:
        """Test that memory destination is not persistent."""
        dest = ModelEventDestination.create_memory()
        assert dest.is_persistent() is False

    def test_is_persistent_file(self) -> None:
        """Test that file destination is persistent."""
        dest = ModelEventDestination.create_file(
            name="file", file_path="/tmp/test.jsonl"
        )
        assert dest.is_persistent() is True

    def test_is_persistent_kafka(self) -> None:
        """Test that Kafka destination is persistent."""
        dest = ModelEventDestination.create_kafka(
            name="kafka",
            topic="test.topic",
            bootstrap_servers="localhost:9092",
        )
        assert dest.is_persistent() is True

    def test_requires_connection_memory(self) -> None:
        """Test that memory destination does not require connection."""
        dest = ModelEventDestination.create_memory()
        assert dest.requires_connection() is False

    def test_requires_connection_file(self) -> None:
        """Test that file destination does not require connection."""
        dest = ModelEventDestination.create_file(
            name="file", file_path="/tmp/test.jsonl"
        )
        assert dest.requires_connection() is False

    def test_requires_connection_kafka(self) -> None:
        """Test that Kafka destination requires connection."""
        dest = ModelEventDestination.create_kafka(
            name="kafka",
            topic="test.topic",
            bootstrap_servers="localhost:9092",
        )
        assert dest.requires_connection() is True


# =============================================================================
# Serialization Tests
# =============================================================================


@pytest.mark.unit
class TestModelEventDestinationSerialization:
    """Tests for serialization and deserialization."""

    def test_memory_destination_round_trip(self) -> None:
        """Test memory destination serialization round-trip."""
        original = ModelEventDestination.create_memory(
            name="memory-roundtrip",
            buffer_size=200,
        )

        json_str = original.model_dump_json()
        restored = ModelEventDestination.model_validate_json(json_str)

        assert restored.destination_type == original.destination_type
        assert restored.destination_name == original.destination_name
        assert restored.buffer_size == original.buffer_size
        assert restored.enabled == original.enabled

    def test_file_destination_round_trip(self) -> None:
        """Test file destination serialization round-trip."""
        original = ModelEventDestination.create_file(
            name="file-roundtrip",
            file_path="/var/log/events.jsonl",
            buffer_size=50,
            flush_interval_ms=2000,
        )

        json_str = original.model_dump_json()
        restored = ModelEventDestination.model_validate_json(json_str)

        assert restored.destination_type == original.destination_type
        assert restored.destination_name == original.destination_name
        assert restored.file_path == original.file_path
        assert restored.buffer_size == original.buffer_size
        assert restored.flush_interval_ms == original.flush_interval_ms

    def test_kafka_destination_round_trip(self) -> None:
        """Test Kafka destination serialization round-trip."""
        original = ModelEventDestination.create_kafka(
            name="kafka-roundtrip",
            topic="test.events",
            bootstrap_servers="host1:9092,host2:9092",
            buffer_size=150,
            flush_interval_ms=500,
        )

        json_str = original.model_dump_json()
        restored = ModelEventDestination.model_validate_json(json_str)

        assert restored.destination_type == original.destination_type
        assert restored.destination_name == original.destination_name
        assert restored.topic == original.topic
        assert restored.bootstrap_servers == original.bootstrap_servers
        assert restored.buffer_size == original.buffer_size
        assert restored.flush_interval_ms == original.flush_interval_ms

    def test_model_dump_dict(self) -> None:
        """Test model_dump produces correct dictionary."""
        dest = ModelEventDestination.create_file(
            name="dict-test",
            file_path="/tmp/test.jsonl",
        )

        data = dest.model_dump()

        assert data["destination_type"] == EnumEventSinkType.FILE
        assert data["destination_name"] == "dict-test"
        assert data["file_path"] == "/tmp/test.jsonl"
        assert data["enabled"] is True


# =============================================================================
# Immutability Tests
# =============================================================================


@pytest.mark.unit
class TestModelEventDestinationImmutability:
    """Tests for immutability (frozen model)."""

    def test_destination_is_frozen(self) -> None:
        """Test that destination is frozen (immutable)."""
        dest = ModelEventDestination.create_memory()

        with pytest.raises(ValidationError):
            dest.destination_name = "new-name"  # type: ignore[misc]

    def test_extra_fields_forbidden(self) -> None:
        """Test that extra fields are forbidden."""
        with pytest.raises(ValidationError) as exc_info:
            ModelEventDestination(
                destination_type=EnumEventSinkType.MEMORY,
                destination_name="test",
                unknown_field="value",  # type: ignore[call-arg]
            )

        error_str = str(exc_info.value)
        assert "unknown_field" in error_str or "extra" in error_str.lower()

    def test_model_config_is_frozen(self) -> None:
        """Test that model_config has frozen=True."""
        dest = ModelEventDestination.create_memory()
        assert dest.model_config.get("frozen") is True

    def test_model_config_forbids_extra(self) -> None:
        """Test that model_config has extra='forbid'."""
        dest = ModelEventDestination.create_memory()
        assert dest.model_config.get("extra") == "forbid"


# =============================================================================
# Edge Case Tests
# =============================================================================


@pytest.mark.unit
class TestModelEventDestinationEdgeCases:
    """Tests for edge cases."""

    def test_valid_boundary_buffer_size(self) -> None:
        """Test buffer_size at valid boundaries."""
        # Minimum valid value
        dest_min = ModelEventDestination(
            destination_type=EnumEventSinkType.MEMORY,
            destination_name="min-test",
            buffer_size=1,
        )
        assert dest_min.buffer_size == 1

        # Maximum valid value
        dest_max = ModelEventDestination(
            destination_type=EnumEventSinkType.MEMORY,
            destination_name="max-test",
            buffer_size=10000,
        )
        assert dest_max.buffer_size == 10000

    def test_valid_boundary_flush_interval(self) -> None:
        """Test flush_interval_ms at valid boundaries."""
        # Minimum valid value
        dest_min = ModelEventDestination(
            destination_type=EnumEventSinkType.MEMORY,
            destination_name="min-test",
            flush_interval_ms=100,
        )
        assert dest_min.flush_interval_ms == 100

        # Maximum valid value
        dest_max = ModelEventDestination(
            destination_type=EnumEventSinkType.MEMORY,
            destination_name="max-test",
            flush_interval_ms=60000,
        )
        assert dest_max.flush_interval_ms == 60000

    def test_enabled_can_be_set_to_false(self) -> None:
        """Test that enabled can be set to False."""
        dest = ModelEventDestination(
            destination_type=EnumEventSinkType.MEMORY,
            destination_name="disabled-test",
            enabled=False,
        )

        assert dest.enabled is False

    def test_file_path_with_spaces(self) -> None:
        """Test file_path can contain spaces."""
        dest = ModelEventDestination.create_file(
            name="spaces-test",
            file_path="/var/log/my events/validation.jsonl",
        )

        assert dest.file_path == "/var/log/my events/validation.jsonl"

    def test_destination_name_with_special_chars(self) -> None:
        """Test destination_name with allowed special characters."""
        dest = ModelEventDestination.create_memory(
            name="my-dest_123.test",
        )

        assert dest.destination_name == "my-dest_123.test"

    def test_multiple_kafka_servers(self) -> None:
        """Test Kafka with multiple bootstrap servers."""
        dest = ModelEventDestination.create_kafka(
            name="multi-server",
            topic="test.topic",
            bootstrap_servers="host1:9092,host2:9092,host3:9093",
        )

        assert "host1:9092" in dest.bootstrap_servers
        assert "host2:9092" in dest.bootstrap_servers
        assert "host3:9093" in dest.bootstrap_servers
