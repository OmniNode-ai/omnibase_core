"""
Test suite for ModelRouteHop.
"""

from datetime import datetime
from uuid import uuid4

from omnibase_core.models.core.model_route_hop import ModelRouteHop
from omnibase_core.models.core.model_route_hop_metadata import ModelRouteHopMetadata
from omnibase_core.models.primitives.model_semver import ModelSemVer

# Default version for test instances - required field after removing default_factory
DEFAULT_VERSION = ModelSemVer(major=1, minor=0, patch=0)


class TestModelRouteHop:
    """Test ModelRouteHop functionality."""

    def test_model_route_hop_creation_minimal(self):
        """Test creating ModelRouteHop with minimal required fields."""
        hop_id = uuid4()
        node_id = uuid4()

        hop = ModelRouteHop(
            version=DEFAULT_VERSION,
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
        assert isinstance(hop.metadata, ModelRouteHopMetadata)
        assert hop.metadata.model_dump(exclude_defaults=True) == {}
        assert isinstance(hop.timestamp, datetime)

    def test_model_route_hop_creation_complete(self):
        """Test creating ModelRouteHop with all fields."""
        hop_id = uuid4()
        node_id = uuid4()
        timestamp = datetime(2024, 1, 15, 10, 30, 45)
        metadata = ModelRouteHopMetadata(
            route_version="1.0",
            routing_table_id="table-123",
            custom_fields={"key1": "value1"},
        )

        hop = ModelRouteHop(
            version=DEFAULT_VERSION,
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
        assert hop.metadata.route_version == "1.0"
        assert hop.metadata.custom_fields["key1"] == "value1"

    def test_model_route_hop_creation_with_error(self):
        """Test creating ModelRouteHop with error message."""
        hop_id = uuid4()
        node_id = uuid4()

        hop = ModelRouteHop(
            version=DEFAULT_VERSION,
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
                version=DEFAULT_VERSION,
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
                version=DEFAULT_VERSION,
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
                version=DEFAULT_VERSION,
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
                version=DEFAULT_VERSION,
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
                version=DEFAULT_VERSION,
                hop_id=hop_id,
                node_id=node_id,
                hop_type="destination",
                error_info=error_message,
            )
            assert hop.error_info == error_message

    def test_model_route_hop_metadata_types(self):
        """Test ModelRouteHop with different ModelRouteHopMetadata field types."""
        hop_id = uuid4()
        node_id = uuid4()

        metadata = ModelRouteHopMetadata(
            route_version="1.0.0",
            routing_table_id="table-abc",
            queue_wait_time_ms=100,
            serialization_time_ms=50,
            message_size_bytes=1024,
            compression_ratio=0.75,
            debug_trace="trace info",
            tags=["tag1", "tag2", "tag3"],
            custom_fields={"custom_key": "custom_value"},
        )

        hop = ModelRouteHop(
            version=DEFAULT_VERSION,
            hop_id=hop_id,
            node_id=node_id,
            hop_type="router",
            metadata=metadata,
        )

        assert hop.metadata.route_version == "1.0.0"
        assert hop.metadata.routing_table_id == "table-abc"
        assert hop.metadata.queue_wait_time_ms == 100
        assert hop.metadata.serialization_time_ms == 50
        assert hop.metadata.message_size_bytes == 1024
        assert hop.metadata.compression_ratio == 0.75
        assert hop.metadata.debug_trace == "trace info"
        assert hop.metadata.tags == ["tag1", "tag2", "tag3"]
        assert hop.metadata.custom_fields["custom_key"] == "custom_value"

    def test_model_route_hop_empty_metadata(self):
        """Test ModelRouteHop with default (empty) metadata."""
        hop_id = uuid4()
        node_id = uuid4()

        hop = ModelRouteHop(
            version=DEFAULT_VERSION,
            hop_id=hop_id,
            node_id=node_id,
            hop_type="source",
            metadata=ModelRouteHopMetadata(),
        )

        assert isinstance(hop.metadata, ModelRouteHopMetadata)
        # Check that metadata has no non-default values set
        assert hop.metadata.model_dump(exclude_defaults=True) == {}
        # Check that custom_fields dict is empty
        assert len(hop.metadata.custom_fields) == 0

    def test_model_route_hop_nested_metadata(self):
        """Test ModelRouteHop metadata with tags and custom_fields."""
        hop_id = uuid4()
        node_id = uuid4()

        # ModelRouteHopMetadata has structured fields, not arbitrary nesting
        # Use tags for list data and custom_fields for string key-value pairs
        custom_fields = {
            "deep_value": "found",
            "simple": "value",
            "top_level": "value",
        }

        metadata = ModelRouteHopMetadata(
            route_version="2.0.0",
            tags=["level1", "level2", "level3"],
            custom_fields=custom_fields,
        )

        hop = ModelRouteHop(
            version=DEFAULT_VERSION,
            hop_id=hop_id,
            node_id=node_id,
            hop_type="router",
            metadata=metadata,
        )

        assert hop.metadata.route_version == "2.0.0"
        assert hop.metadata.tags == ["level1", "level2", "level3"]
        assert hop.metadata.custom_fields["deep_value"] == "found"
        assert hop.metadata.custom_fields["simple"] == "value"
        assert hop.metadata.custom_fields["top_level"] == "value"

    def test_model_route_hop_timestamp_formats(self):
        """Test ModelRouteHop with different timestamp formats."""
        hop_id = uuid4()
        node_id = uuid4()

        # Test with specific datetime
        specific_time = datetime(2024, 12, 25, 15, 30, 45)
        hop = ModelRouteHop(
            version=DEFAULT_VERSION,
            hop_id=hop_id,
            node_id=node_id,
            hop_type="source",
            timestamp=specific_time,
        )
        assert hop.timestamp == specific_time

        # Test with current time (default)
        hop = ModelRouteHop(
            version=DEFAULT_VERSION,
            hop_id=hop_id,
            node_id=node_id,
            hop_type="source",
        )
        assert isinstance(hop.timestamp, datetime)

        # Test with minimum datetime
        min_time = datetime.min
        hop = ModelRouteHop(
            version=DEFAULT_VERSION,
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
        metadata = ModelRouteHopMetadata(
            route_version="1.0",
            custom_fields={"test": "data"},
        )

        hop = ModelRouteHop(
            version=DEFAULT_VERSION,
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
        # Metadata should serialize to a dict with ModelRouteHopMetadata fields
        assert isinstance(data["metadata"], dict)
        assert data["metadata"]["route_version"] == "1.0"
        assert data["metadata"]["custom_fields"]["test"] == "data"

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
        metadata_dict = {
            "route_version": "1.0",
            "custom_fields": {"test": "data"},
        }

        # Test from dict
        data = {
            "hop_id": hop_id,
            "node_id": node_id,
            "service_name": "test_service",
            "timestamp": timestamp,
            "processing_duration_ms": 150,
            "hop_type": "router",
            "routing_decision": "route_to_queue_a",
            "metadata": metadata_dict,
        }
        hop = ModelRouteHop.model_validate(data)

        assert hop.hop_id == hop_id
        assert hop.node_id == node_id
        assert hop.service_name == "test_service"
        assert hop.timestamp == timestamp
        assert hop.processing_duration_ms == 150
        assert hop.hop_type == "router"
        assert hop.routing_decision == "route_to_queue_a"
        # Metadata should be deserialized to ModelRouteHopMetadata
        assert isinstance(hop.metadata, ModelRouteHopMetadata)
        assert hop.metadata.route_version == "1.0"
        assert hop.metadata.custom_fields["test"] == "data"

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
            version=DEFAULT_VERSION,
            hop_id=hop_id,
            node_id=node_id,
            hop_type="source",
        )
        assert hop.hop_id == hop_id
        assert hop.node_id == node_id
        assert hop.hop_type == "source"

    def test_model_route_hop_immutability(self):
        """Test ModelRouteHop mutability behavior."""
        hop_id = uuid4()
        node_id = uuid4()

        hop = ModelRouteHop(
            version=DEFAULT_VERSION,
            hop_id=hop_id,
            node_id=node_id,
            hop_type="source",
        )

        # Should be able to modify metadata custom_fields (it's a dict inside the model)
        hop.metadata.custom_fields["new_key"] = "new_value"
        assert hop.metadata.custom_fields["new_key"] == "new_value"

        # Should be able to modify metadata attributes
        hop.metadata.route_version = "2.0.0"
        assert hop.metadata.route_version == "2.0.0"

        # Should be able to modify other fields
        hop.service_name = "updated_service"
        assert hop.service_name == "updated_service"

    def test_model_route_hop_equality(self):
        """Test ModelRouteHop equality."""
        hop_id = uuid4()
        node_id = uuid4()
        timestamp = datetime(2024, 1, 15, 10, 30, 45)

        hop1 = ModelRouteHop(
            version=DEFAULT_VERSION,
            hop_id=hop_id,
            node_id=node_id,
            hop_type="source",
            timestamp=timestamp,
        )
        hop2 = ModelRouteHop(
            version=DEFAULT_VERSION,
            hop_id=hop_id,
            node_id=node_id,
            hop_type="source",
            timestamp=timestamp,
        )

        assert hop1 == hop2

        # Test with different hop_id
        hop3 = ModelRouteHop(
            version=DEFAULT_VERSION,
            hop_id=uuid4(),
            node_id=node_id,
            hop_type="source",
            timestamp=timestamp,
        )
        assert hop1 != hop3

        # Test with different hop_type
        hop4 = ModelRouteHop(
            version=DEFAULT_VERSION,
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
            version=DEFAULT_VERSION,
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
            version=DEFAULT_VERSION,
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

        # Test that metadata defaults to empty ModelRouteHopMetadata
        hop1 = ModelRouteHop(
            version=DEFAULT_VERSION,
            hop_id=hop_id,
            node_id=node_id,
            hop_type="source",
        )
        hop2 = ModelRouteHop(
            version=DEFAULT_VERSION,
            hop_id=hop_id,
            node_id=node_id,
            hop_type="source",
        )

        # Both should have default metadata (ModelRouteHopMetadata with empty custom_fields)
        assert isinstance(hop1.metadata, ModelRouteHopMetadata)
        assert isinstance(hop2.metadata, ModelRouteHopMetadata)
        assert hop1.metadata.model_dump(exclude_defaults=True) == {}
        assert hop2.metadata.model_dump(exclude_defaults=True) == {}

        # But they should be different instances (modifying one doesn't affect the other)
        hop1.metadata.custom_fields["test"] = "value1"
        hop2.metadata.custom_fields["test"] = "value2"

        assert hop1.metadata.custom_fields["test"] == "value1"
        assert hop2.metadata.custom_fields["test"] == "value2"

    def test_model_route_hop_timestamp_default_factory(self):
        """Test ModelRouteHop timestamp default factory behavior."""
        hop_id = uuid4()
        node_id = uuid4()

        # Test that timestamp defaults to current time (using utcnow)
        hop = ModelRouteHop(
            version=DEFAULT_VERSION,
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

        # Test with large custom_fields in metadata
        large_custom_fields = {f"key_{i}": f"value_{i}" for i in range(1000)}
        metadata = ModelRouteHopMetadata(custom_fields=large_custom_fields)
        hop = ModelRouteHop(
            version=DEFAULT_VERSION,
            hop_id=hop_id,
            node_id=node_id,
            hop_type="router",
            metadata=metadata,
        )

        assert len(hop.metadata.custom_fields) == 1000
        assert hop.metadata.custom_fields["key_0"] == "value_0"
        assert hop.metadata.custom_fields["key_999"] == "value_999"

        # Test with unicode custom_fields
        unicode_custom_fields = {
            "chinese": "测试",
            "emoji": "rocket_symbol",
            "special": "exclamation_at_hash",
        }
        metadata = ModelRouteHopMetadata(custom_fields=unicode_custom_fields)
        hop = ModelRouteHop(
            version=DEFAULT_VERSION,
            hop_id=hop_id,
            node_id=node_id,
            hop_type="destination",
            metadata=metadata,
        )

        assert hop.metadata.custom_fields["chinese"] == "测试"
        assert hop.metadata.custom_fields["emoji"] == "rocket_symbol"
        assert hop.metadata.custom_fields["special"] == "exclamation_at_hash"

        # Test with very large processing duration
        hop = ModelRouteHop(
            version=DEFAULT_VERSION,
            hop_id=hop_id,
            node_id=node_id,
            hop_type="router",
            processing_duration_ms=999999999,
        )
        assert hop.processing_duration_ms == 999999999

        # Test with negative processing duration
        hop = ModelRouteHop(
            version=DEFAULT_VERSION,
            hop_id=hop_id,
            node_id=node_id,
            hop_type="router",
            processing_duration_ms=-100,
        )
        assert hop.processing_duration_ms == -100
