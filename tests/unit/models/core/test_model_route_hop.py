"""
Test suite for ModelRouteHop.
"""

from datetime import datetime
from uuid import UUID, uuid4

import pytest

from omnibase_core.models.core.model_route_hop import ModelRouteHop


class TestModelRouteHop:
    """Test ModelRouteHop functionality."""

    def test_model_route_hop_creation_minimal(self):
        """Test creating ModelRouteHop with minimal required fields."""
        hop_id = uuid4()
        node_id = uuid4()

        hop = ModelRouteHop(
            hop_id=hop_id,
            node_id=node_id,
            hop_type="source",
        )

        assert hop.hop_id == hop_id
        assert hop.node_id == node_id
        assert hop.hop_type == "source"
        assert hop.service_name is None
        assert hop.processing_duration_ms is None
        assert hop.routing_decision is None
        assert hop.error_info is None
        assert hop.metadata == {}
        assert isinstance(hop.timestamp, datetime)

    def test_model_route_hop_creation_complete(self):
        """Test creating ModelRouteHop with all fields."""
        hop_id = uuid4()
        node_id = uuid4()
        timestamp = datetime(2024, 1, 15, 10, 30, 45)
        metadata = {"key1": "value1", "key2": 123}

        hop = ModelRouteHop(
            hop_id=hop_id,
            node_id=node_id,
            service_name="test_service",
            timestamp=timestamp,
            processing_duration_ms=150,
            hop_type="router",
            routing_decision="route_to_queue_a",
            error_info=None,
            metadata=metadata,
        )

        assert hop.hop_id == hop_id
        assert hop.node_id == node_id
        assert hop.service_name == "test_service"
        assert hop.timestamp == timestamp
        assert hop.processing_duration_ms == 150
        assert hop.hop_type == "router"
        assert hop.routing_decision == "route_to_queue_a"
        assert hop.error_info is None
        assert hop.metadata == metadata

    def test_model_route_hop_creation_with_error(self):
        """Test creating ModelRouteHop with error message."""
        hop_id = uuid4()
        node_id = uuid4()

        hop = ModelRouteHop(
            hop_id=hop_id,
            node_id=node_id,
            hop_type="destination",
            error_info="Connection timeout",
        )

        assert hop.hop_id == hop_id
        assert hop.node_id == node_id
        assert hop.hop_type == "destination"
        assert hop.error_info == "Connection timeout"

    def test_model_route_hop_hop_types(self):
        """Test ModelRouteHop with different hop types."""
        hop_id = uuid4()
        node_id = uuid4()

        hop_types = ["source", "router", "destination"]

        for hop_type in hop_types:
            hop = ModelRouteHop(
                hop_id=hop_id,
                node_id=node_id,
                hop_type=hop_type,
            )
            assert hop.hop_type == hop_type

    def test_model_route_hop_service_names(self):
        """Test ModelRouteHop with different service names."""
        hop_id = uuid4()
        node_id = uuid4()

        service_names = [
            "auth_service",
            "payment_service",
            "notification_service",
            None,
        ]

        for service_name in service_names:
            hop = ModelRouteHop(
                hop_id=hop_id,
                node_id=node_id,
                hop_type="router",
                service_name=service_name,
            )
            assert hop.service_name == service_name

    def test_model_route_hop_processing_duration(self):
        """Test ModelRouteHop with different processing durations."""
        hop_id = uuid4()
        node_id = uuid4()

        durations = [0, 1, 100, 1000, 9999, None]

        for duration in durations:
            hop = ModelRouteHop(
                hop_id=hop_id,
                node_id=node_id,
                hop_type="router",
                processing_duration_ms=duration,
            )
            assert hop.processing_duration_ms == duration

    def test_model_route_hop_routing_decisions(self):
        """Test ModelRouteHop with different routing decisions."""
        hop_id = uuid4()
        node_id = uuid4()

        decisions = [
            "route_to_queue_a",
            "route_to_queue_b",
            "route_to_dead_letter",
            "retry_after_delay",
            None,
        ]

        for decision in decisions:
            hop = ModelRouteHop(
                hop_id=hop_id,
                node_id=node_id,
                hop_type="router",
                routing_decision=decision,
            )
            assert hop.routing_decision == decision

    def test_model_route_hop_error_messages(self):
        """Test ModelRouteHop with different error messages."""
        hop_id = uuid4()
        node_id = uuid4()

        error_messages = [
            "Connection timeout",
            "Authentication failed",
            "Rate limit exceeded",
            "Service unavailable",
            None,
        ]

        for error_message in error_messages:
            hop = ModelRouteHop(
                hop_id=hop_id,
                node_id=node_id,
                hop_type="destination",
                error_info=error_message,
            )
            assert hop.error_info == error_message

    def test_model_route_hop_metadata_types(self):
        """Test ModelRouteHop with different metadata value types."""
        hop_id = uuid4()
        node_id = uuid4()

        metadata = {
            "string": "test",
            "integer": 123,
            "float": 45.67,
            "boolean": True,
            "list": [1, 2, 3],
            "dict": {"nested": "value"},
            "none": None,
        }

        hop = ModelRouteHop(
            hop_id=hop_id,
            node_id=node_id,
            hop_type="router",
            metadata=metadata,
        )

        assert hop.metadata["string"] == "test"
        assert hop.metadata["integer"] == 123
        assert hop.metadata["float"] == 45.67
        assert hop.metadata["boolean"] is True
        assert hop.metadata["list"] == [1, 2, 3]
        assert hop.metadata["dict"] == {"nested": "value"}
        assert hop.metadata["none"] is None

    def test_model_route_hop_empty_metadata(self):
        """Test ModelRouteHop with empty metadata."""
        hop_id = uuid4()
        node_id = uuid4()

        hop = ModelRouteHop(
            hop_id=hop_id,
            node_id=node_id,
            hop_type="source",
            metadata={},
        )

        assert hop.metadata == {}
        assert isinstance(hop.metadata, dict)
        assert len(hop.metadata) == 0

    def test_model_route_hop_nested_metadata(self):
        """Test ModelRouteHop with nested metadata structure."""
        hop_id = uuid4()
        node_id = uuid4()

        metadata = {
            "level1": {
                "level2": {
                    "level3": "deep_value",
                    "list": [1, 2, {"nested": "object"}],
                },
                "simple": "value",
            },
            "top_level": "value",
        }

        hop = ModelRouteHop(
            hop_id=hop_id,
            node_id=node_id,
            hop_type="router",
            metadata=metadata,
        )

        assert hop.metadata["level1"]["level2"]["level3"] == "deep_value"
        assert hop.metadata["level1"]["level2"]["list"] == [1, 2, {"nested": "object"}]
        assert hop.metadata["level1"]["simple"] == "value"
        assert hop.metadata["top_level"] == "value"

    def test_model_route_hop_timestamp_formats(self):
        """Test ModelRouteHop with different timestamp formats."""
        hop_id = uuid4()
        node_id = uuid4()

        # Test with specific datetime
        specific_time = datetime(2024, 12, 25, 15, 30, 45)
        hop = ModelRouteHop(
            hop_id=hop_id,
            node_id=node_id,
            hop_type="source",
            timestamp=specific_time,
        )
        assert hop.timestamp == specific_time

        # Test with current time (default)
        hop = ModelRouteHop(
            hop_id=hop_id,
            node_id=node_id,
            hop_type="source",
        )
        assert isinstance(hop.timestamp, datetime)

        # Test with minimum datetime
        min_time = datetime.min
        hop = ModelRouteHop(
            hop_id=hop_id,
            node_id=node_id,
            hop_type="source",
            timestamp=min_time,
        )
        assert hop.timestamp == min_time

    def test_model_route_hop_serialization(self):
        """Test ModelRouteHop serialization."""
        hop_id = uuid4()
        node_id = uuid4()
        timestamp = datetime(2024, 1, 15, 10, 30, 45)
        metadata = {"test": "data", "number": 42}

        hop = ModelRouteHop(
            hop_id=hop_id,
            node_id=node_id,
            service_name="test_service",
            timestamp=timestamp,
            processing_duration_ms=150,
            hop_type="router",
            routing_decision="route_to_queue_a",
            metadata=metadata,
        )

        # Test model_dump
        data = hop.model_dump()
        assert "hop_id" in data
        assert "node_id" in data
        assert "service_name" in data
        assert "timestamp" in data
        assert "processing_duration_ms" in data
        assert "hop_type" in data
        assert "routing_decision" in data
        assert "metadata" in data
        assert data["hop_id"] == hop_id
        assert data["node_id"] == node_id
        assert data["service_name"] == "test_service"
        assert data["timestamp"] == timestamp.isoformat()
        assert data["processing_duration_ms"] == 150
        assert data["hop_type"] == "router"
        assert data["routing_decision"] == "route_to_queue_a"
        assert data["metadata"] == metadata

        # Test model_dump_json
        json_data = hop.model_dump_json()
        assert isinstance(json_data, str)
        assert "test_service" in json_data
        assert "router" in json_data

    def test_model_route_hop_deserialization(self):
        """Test ModelRouteHop deserialization."""
        hop_id = uuid4()
        node_id = uuid4()
        timestamp = datetime(2024, 1, 15, 10, 30, 45)
        metadata = {"test": "data", "number": 42}

        # Test from dict
        data = {
            "hop_id": hop_id,
            "node_id": node_id,
            "service_name": "test_service",
            "timestamp": timestamp,
            "processing_duration_ms": 150,
            "hop_type": "router",
            "routing_decision": "route_to_queue_a",
            "metadata": metadata,
        }
        hop = ModelRouteHop.model_validate(data)

        assert hop.hop_id == hop_id
        assert hop.node_id == node_id
        assert hop.service_name == "test_service"
        assert hop.timestamp == timestamp
        assert hop.processing_duration_ms == 150
        assert hop.hop_type == "router"
        assert hop.routing_decision == "route_to_queue_a"
        assert hop.metadata == metadata

        # Test from JSON
        json_data = (
            '{"hop_id": "'
            + str(hop_id)
            + '", "node_id": "'
            + str(node_id)
            + '", "hop_type": "source", "timestamp": "2024-01-15T10:30:45"}'
        )
        hop = ModelRouteHop.model_validate_json(json_data)

        assert hop.hop_id == hop_id
        assert hop.node_id == node_id
        assert hop.hop_type == "source"
        assert hop.timestamp.year == 2024
        assert hop.timestamp.month == 1
        assert hop.timestamp.day == 15

    def test_model_route_hop_validation(self):
        """Test ModelRouteHop validation."""
        hop_id = uuid4()
        node_id = uuid4()

        # Test valid data
        hop = ModelRouteHop(
            hop_id=hop_id,
            node_id=node_id,
            hop_type="source",
        )
        assert hop.hop_id == hop_id
        assert hop.node_id == node_id
        assert hop.hop_type == "source"

    def test_model_route_hop_immutability(self):
        """Test ModelRouteHop immutability."""
        hop_id = uuid4()
        node_id = uuid4()

        hop = ModelRouteHop(
            hop_id=hop_id,
            node_id=node_id,
            hop_type="source",
        )

        # Should be able to modify metadata (it's a dict)
        hop.metadata["new_key"] = "new_value"
        assert hop.metadata["new_key"] == "new_value"

        # Should be able to modify other fields
        hop.service_name = "updated_service"
        assert hop.service_name == "updated_service"

    def test_model_route_hop_equality(self):
        """Test ModelRouteHop equality."""
        hop_id = uuid4()
        node_id = uuid4()
        timestamp = datetime(2024, 1, 15, 10, 30, 45)

        hop1 = ModelRouteHop(
            hop_id=hop_id,
            node_id=node_id,
            hop_type="source",
            timestamp=timestamp,
        )
        hop2 = ModelRouteHop(
            hop_id=hop_id,
            node_id=node_id,
            hop_type="source",
            timestamp=timestamp,
        )

        assert hop1 == hop2

        # Test with different hop_id
        hop3 = ModelRouteHop(
            hop_id=uuid4(),
            node_id=node_id,
            hop_type="source",
            timestamp=timestamp,
        )
        assert hop1 != hop3

        # Test with different hop_type
        hop4 = ModelRouteHop(
            hop_id=hop_id,
            node_id=node_id,
            hop_type="router",
            timestamp=timestamp,
        )
        assert hop1 != hop4

    def test_model_route_hop_str_representation(self):
        """Test ModelRouteHop string representation."""
        hop_id = uuid4()
        node_id = uuid4()

        hop = ModelRouteHop(
            hop_id=hop_id,
            node_id=node_id,
            hop_type="source",
        )
        str_repr = str(hop)

        assert "source" in str_repr

    def test_model_route_hop_repr_representation(self):
        """Test ModelRouteHop repr representation."""
        hop_id = uuid4()
        node_id = uuid4()

        hop = ModelRouteHop(
            hop_id=hop_id,
            node_id=node_id,
            hop_type="source",
        )
        repr_str = repr(hop)

        assert "ModelRouteHop" in repr_str
        assert "hop_id" in repr_str
        assert "node_id" in repr_str
        assert "hop_type" in repr_str

    def test_model_route_hop_field_descriptions(self):
        """Test ModelRouteHop field descriptions."""
        # Check that fields have proper descriptions
        fields = ModelRouteHop.model_fields

        assert "hop_id" in fields
        assert "node_id" in fields
        assert "service_name" in fields
        assert "timestamp" in fields
        assert "processing_duration_ms" in fields
        assert "hop_type" in fields
        assert "routing_decision" in fields
        assert "error_info" in fields
        assert "metadata" in fields

        # Check field descriptions
        assert "Unique identifier for this hop" in fields["hop_id"].description
        assert "ID of the node that processed this hop" in fields["node_id"].description
        assert "Service name if applicable" in fields["service_name"].description
        assert "When this hop was processed" in fields["timestamp"].description
        assert (
            "Time spent processing at this hop in milliseconds"
            in fields["processing_duration_ms"].description
        )
        assert "Type of hop" in fields["hop_type"].description
        assert (
            "Routing decision made at this hop"
            in fields["routing_decision"].description
        )
        assert "Error information if hop failed" in fields["error_info"].description
        assert "Additional hop-specific metadata" in fields["metadata"].description

    def test_model_route_hop_default_factory(self):
        """Test ModelRouteHop default factory behavior."""
        hop_id = uuid4()
        node_id = uuid4()

        # Test that metadata defaults to empty dict
        hop1 = ModelRouteHop(
            hop_id=hop_id,
            node_id=node_id,
            hop_type="source",
        )
        hop2 = ModelRouteHop(
            hop_id=hop_id,
            node_id=node_id,
            hop_type="source",
        )

        # Both should have empty metadata
        assert hop1.metadata == {}
        assert hop2.metadata == {}

        # But they should be different instances
        hop1.metadata["test"] = "value1"
        hop2.metadata["test"] = "value2"

        assert hop1.metadata["test"] == "value1"
        assert hop2.metadata["test"] == "value2"

    def test_model_route_hop_timestamp_default_factory(self):
        """Test ModelRouteHop timestamp default factory behavior."""
        hop_id = uuid4()
        node_id = uuid4()

        # Test that timestamp defaults to current time (using utcnow)
        hop = ModelRouteHop(
            hop_id=hop_id,
            node_id=node_id,
            hop_type="source",
        )

        # The timestamp should be a datetime object
        assert isinstance(hop.timestamp, datetime)

    def test_model_route_hop_edge_cases(self):
        """Test ModelRouteHop edge cases."""
        hop_id = uuid4()
        node_id = uuid4()

        # Test with very large metadata
        large_metadata = {f"key_{i}": f"value_{i}" for i in range(1000)}
        hop = ModelRouteHop(
            hop_id=hop_id,
            node_id=node_id,
            hop_type="router",
            metadata=large_metadata,
        )

        assert len(hop.metadata) == 1000
        assert hop.metadata["key_0"] == "value_0"
        assert hop.metadata["key_999"] == "value_999"

        # Test with unicode metadata
        unicode_metadata = {"中文": "测试", "emoji": "🚀", "special": "!@#$%^&*()"}
        hop = ModelRouteHop(
            hop_id=hop_id,
            node_id=node_id,
            hop_type="destination",
            metadata=unicode_metadata,
        )

        assert hop.metadata["中文"] == "测试"
        assert hop.metadata["emoji"] == "🚀"
        assert hop.metadata["special"] == "!@#$%^&*()"

        # Test with very large processing duration
        hop = ModelRouteHop(
            hop_id=hop_id,
            node_id=node_id,
            hop_type="router",
            processing_duration_ms=999999999,
        )
        assert hop.processing_duration_ms == 999999999

        # Test with negative processing duration
        hop = ModelRouteHop(
            hop_id=hop_id,
            node_id=node_id,
            hop_type="router",
            processing_duration_ms=-100,
        )
        assert hop.processing_duration_ms == -100
