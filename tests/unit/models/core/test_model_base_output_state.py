"""
Test suite for ModelBaseOutputState.
"""

from datetime import datetime

import pytest

from omnibase_core.models.common.model_schema_value import ModelSchemaValue
from omnibase_core.models.core.model_base_output_state import ModelBaseOutputState
from omnibase_core.models.primitives.model_semver import ModelSemVer

# Default version for test instances - required field after removing default_factory
DEFAULT_VERSION = ModelSemVer(major=1, minor=0, patch=0)


def _make_metadata(data: dict) -> dict[str, ModelSchemaValue]:
    """Convert a plain dict to dict[str, ModelSchemaValue]."""
    return {k: ModelSchemaValue.from_value(v) for k, v in data.items()}


@pytest.mark.unit
class TestModelBaseOutputState:
    """Test ModelBaseOutputState functionality."""

    def test_model_base_output_state_creation_default(self):
        """Test creating ModelBaseOutputState with default values."""
        state = ModelBaseOutputState(version=DEFAULT_VERSION)

        assert isinstance(state.metadata, dict)
        assert len(state.metadata) == 0
        assert isinstance(state.timestamp, datetime)
        assert state.processing_time_ms is None

    def test_model_base_output_state_creation_with_metadata(self):
        """Test creating ModelBaseOutputState with custom metadata."""
        metadata = _make_metadata({"key1": "value1", "key2": 123, "key3": True})
        state = ModelBaseOutputState(metadata=metadata)

        assert state.metadata["key1"].get_string() == "value1"
        assert state.metadata["key2"].get_number() == 123
        assert state.metadata["key3"].get_boolean() is True
        assert isinstance(state.timestamp, datetime)
        assert state.processing_time_ms is None

    def test_model_base_output_state_creation_with_timestamp(self):
        """Test creating ModelBaseOutputState with custom timestamp."""
        custom_timestamp = datetime(2024, 1, 15, 10, 30, 45)
        state = ModelBaseOutputState(timestamp=custom_timestamp)

        assert state.timestamp == custom_timestamp
        assert isinstance(state.metadata, dict)
        assert len(state.metadata) == 0
        assert state.processing_time_ms is None

    def test_model_base_output_state_creation_with_processing_time(self):
        """Test creating ModelBaseOutputState with processing time."""
        processing_time = 150.5
        state = ModelBaseOutputState(processing_time_ms=processing_time)

        assert state.processing_time_ms == processing_time
        assert isinstance(state.metadata, dict)
        assert isinstance(state.timestamp, datetime)

    def test_model_base_output_state_creation_with_all_fields(self):
        """Test creating ModelBaseOutputState with all fields."""
        metadata = _make_metadata({"test": "data", "number": 42})
        custom_timestamp = datetime(2024, 1, 15, 10, 30, 45)
        processing_time = 250.75

        state = ModelBaseOutputState(
            version=DEFAULT_VERSION,
            metadata=metadata,
            timestamp=custom_timestamp,
            processing_time_ms=processing_time,
        )

        assert state.metadata["test"].get_string() == "data"
        assert state.metadata["number"].get_number() == 42
        assert state.timestamp == custom_timestamp
        assert state.processing_time_ms == processing_time

    def test_model_base_output_state_processing_time_types(self):
        """Test ModelBaseOutputState with different processing time types."""
        # Test with integer (should be converted to float)
        state = ModelBaseOutputState(processing_time_ms=100)
        assert state.processing_time_ms == 100.0
        assert isinstance(state.processing_time_ms, float)

        # Test with float
        state = ModelBaseOutputState(processing_time_ms=150.5)
        assert state.processing_time_ms == 150.5
        assert isinstance(state.processing_time_ms, float)

        # Test with zero
        state = ModelBaseOutputState(processing_time_ms=0.0)
        assert state.processing_time_ms == 0.0

        # Test with negative value
        state = ModelBaseOutputState(processing_time_ms=-10.5)
        assert state.processing_time_ms == -10.5

    def test_model_base_output_state_processing_time_edge_cases(self):
        """Test ModelBaseOutputState with processing time edge cases."""
        # Test with very small value
        state = ModelBaseOutputState(processing_time_ms=0.001)
        assert state.processing_time_ms == 0.001

        # Test with very large value
        state = ModelBaseOutputState(processing_time_ms=999999.99)
        assert state.processing_time_ms == 999999.99

        # Test with None (default)
        state = ModelBaseOutputState(version=DEFAULT_VERSION)
        assert state.processing_time_ms is None

    def test_model_base_output_state_metadata_types(self):
        """Test ModelBaseOutputState with different metadata value types."""
        metadata = _make_metadata(
            {
                "string": "test",
                "integer": 123,
                "float": 45.67,
                "boolean": True,
                "list": [1, 2, 3],
                "dict": {"nested": "value"},
                "none": None,
            }
        )
        state = ModelBaseOutputState(metadata=metadata)

        assert state.metadata["string"].get_string() == "test"
        assert state.metadata["integer"].get_number() == 123
        assert state.metadata["float"].get_number() == 45.67
        assert state.metadata["boolean"].get_boolean() is True
        assert state.metadata["list"].is_array()
        assert state.metadata["dict"].is_object()
        assert state.metadata["none"].is_null()

    def test_model_base_output_state_empty_metadata(self):
        """Test ModelBaseOutputState with empty metadata."""
        state = ModelBaseOutputState(metadata={})

        assert state.metadata == {}
        assert isinstance(state.metadata, dict)
        assert len(state.metadata) == 0

    def test_model_base_output_state_nested_metadata(self):
        """Test ModelBaseOutputState with nested metadata structure."""
        metadata = _make_metadata(
            {
                "level1": {
                    "level2": {
                        "level3": "deep_value",
                        "list": [1, 2, {"nested": "object"}],
                    },
                    "simple": "value",
                },
                "top_level": "value",
            }
        )
        state = ModelBaseOutputState(metadata=metadata)

        level1 = state.metadata["level1"].get_object()
        level2 = level1["level2"].get_object()
        assert level2["level3"].get_string() == "deep_value"
        assert level1["simple"].get_string() == "value"
        assert state.metadata["top_level"].get_string() == "value"

    def test_model_base_output_state_timestamp_formats(self):
        """Test ModelBaseOutputState with different timestamp formats."""
        # Test with specific datetime
        specific_time = datetime(2024, 12, 25, 15, 30, 45)
        state = ModelBaseOutputState(timestamp=specific_time)
        assert state.timestamp == specific_time

        # Test with current time
        now = datetime.now()
        state = ModelBaseOutputState(timestamp=now)
        assert state.timestamp == now

        # Test with minimum datetime
        min_time = datetime.min
        state = ModelBaseOutputState(timestamp=min_time)
        assert state.timestamp == min_time

    def test_model_base_output_state_serialization(self):
        """Test ModelBaseOutputState serialization."""
        metadata = _make_metadata({"test": "data", "number": 42})
        custom_timestamp = datetime(2024, 1, 15, 10, 30, 45)
        processing_time = 150.5

        state = ModelBaseOutputState(
            version=DEFAULT_VERSION,
            metadata=metadata,
            timestamp=custom_timestamp,
            processing_time_ms=processing_time,
        )

        # Test model_dump
        data = state.model_dump()
        assert "metadata" in data
        assert "timestamp" in data
        assert "processing_time_ms" in data
        assert data["timestamp"] == custom_timestamp
        assert data["processing_time_ms"] == processing_time

        # Test model_dump_json
        json_data = state.model_dump_json()
        assert isinstance(json_data, str)
        assert "test" in json_data
        assert "data" in json_data

    def test_model_base_output_state_deserialization(self):
        """Test ModelBaseOutputState deserialization."""
        metadata = _make_metadata({"test": "data", "number": 42})
        custom_timestamp = datetime(2024, 1, 15, 10, 30, 45)
        processing_time = 150.5

        # Test from dict
        data = {
            "metadata": metadata,
            "timestamp": custom_timestamp,
            "processing_time_ms": processing_time,
        }
        state = ModelBaseOutputState.model_validate(data)

        assert state.metadata["test"].get_string() == "data"
        assert state.timestamp == custom_timestamp
        assert state.processing_time_ms == processing_time

    def test_model_base_output_state_validation(self):
        """Test ModelBaseOutputState validation."""
        # Test valid data
        metadata = _make_metadata({"valid": "data"})
        state = ModelBaseOutputState(metadata=metadata)
        assert state.metadata["valid"].get_string() == "data"

        # Test with empty dict (valid)
        state = ModelBaseOutputState(metadata={})
        assert state.metadata == {}

        # Test with None processing time
        state = ModelBaseOutputState(processing_time_ms=None)
        assert state.processing_time_ms is None

    def test_model_base_output_state_immutability(self):
        """Test ModelBaseOutputState immutability."""
        metadata = _make_metadata({"original": "value"})
        state = ModelBaseOutputState(metadata=metadata)

        # Should be able to modify metadata (it's a dict)
        state.metadata["new_key"] = ModelSchemaValue.create_string("new_value")
        assert state.metadata["new_key"].get_string() == "new_value"
        assert state.metadata["original"].get_string() == "value"

        # Should be able to modify processing time
        state.processing_time_ms = 200.0
        assert state.processing_time_ms == 200.0

    def test_model_base_output_state_equality(self):
        """Test ModelBaseOutputState equality."""
        metadata = _make_metadata({"test": "data"})
        timestamp = datetime(2024, 1, 15, 10, 30, 45)
        processing_time = 150.5

        state1 = ModelBaseOutputState(
            version=DEFAULT_VERSION,
            metadata=metadata,
            timestamp=timestamp,
            processing_time_ms=processing_time,
        )
        state2 = ModelBaseOutputState(
            version=DEFAULT_VERSION,
            metadata=metadata,
            timestamp=timestamp,
            processing_time_ms=processing_time,
        )

        assert state1 == state2

        # Test with different metadata
        state3 = ModelBaseOutputState(
            version=DEFAULT_VERSION,
            metadata=_make_metadata({"different": "data"}),
            timestamp=timestamp,
            processing_time_ms=processing_time,
        )
        assert state1 != state3

        # Test with different timestamp
        state4 = ModelBaseOutputState(
            version=DEFAULT_VERSION,
            metadata=metadata,
            timestamp=datetime.now(),
            processing_time_ms=processing_time,
        )
        assert state1 != state4

        # Test with different processing time
        state5 = ModelBaseOutputState(
            version=DEFAULT_VERSION,
            metadata=metadata,
            timestamp=timestamp,
            processing_time_ms=200.0,
        )
        assert state1 != state5

    def test_model_base_output_state_str_representation(self):
        """Test ModelBaseOutputState string representation."""
        metadata = _make_metadata({"test": "data"})
        state = ModelBaseOutputState(metadata=metadata)
        str_repr = str(state)

        assert "metadata" in str_repr
        assert "timestamp" in str_repr
        assert "processing_time_ms" in str_repr

    def test_model_base_output_state_repr_representation(self):
        """Test ModelBaseOutputState repr representation."""
        metadata = _make_metadata({"test": "data"})
        state = ModelBaseOutputState(metadata=metadata)
        repr_str = repr(state)

        assert "ModelBaseOutputState" in repr_str
        assert "metadata" in repr_str
        assert "timestamp" in repr_str
        assert "processing_time_ms" in repr_str

    def test_model_base_output_state_field_descriptions(self):
        """Test ModelBaseOutputState field descriptions."""
        # Check that fields have proper descriptions
        fields = ModelBaseOutputState.model_fields

        assert "metadata" in fields
        assert "timestamp" in fields
        assert "processing_time_ms" in fields

        # Check field descriptions
        assert "Metadata for the output state" in fields["metadata"].description
        assert (
            "Timestamp when the output was created" in fields["timestamp"].description
        )
        assert (
            "Time taken to process in milliseconds"
            in fields["processing_time_ms"].description
        )

    def test_model_base_output_state_default_factory(self):
        """Test ModelBaseOutputState default factory behavior."""
        # Test that metadata defaults to empty dict
        state1 = ModelBaseOutputState(version=DEFAULT_VERSION)
        state2 = ModelBaseOutputState(version=DEFAULT_VERSION)

        # Both should have empty metadata
        assert state1.metadata == {}
        assert state2.metadata == {}

        # But they should be different instances
        state1.metadata["test"] = ModelSchemaValue.create_string("value1")
        state2.metadata["test"] = ModelSchemaValue.create_string("value2")

        assert state1.metadata["test"].get_string() == "value1"
        assert state2.metadata["test"].get_string() == "value2"

    def test_model_base_output_state_timestamp_default_factory(self):
        """Test ModelBaseOutputState timestamp default factory behavior."""
        # Test that timestamp defaults to current time
        before = datetime.now()
        state = ModelBaseOutputState(version=DEFAULT_VERSION)
        after = datetime.now()

        assert before <= state.timestamp <= after

    def test_model_base_output_state_processing_time_validation(self):
        """Test ModelBaseOutputState processing time validation."""
        # Test with valid processing times
        valid_times = [0.0, 0.001, 100.0, 999999.99, -10.5]

        for time_val in valid_times:
            state = ModelBaseOutputState(processing_time_ms=time_val)
            assert state.processing_time_ms == time_val

    def test_model_base_output_state_edge_cases(self):
        """Test ModelBaseOutputState edge cases."""
        # Test with very large metadata
        large_metadata = _make_metadata({f"key_{i}": f"value_{i}" for i in range(1000)})
        state = ModelBaseOutputState(metadata=large_metadata)

        assert len(state.metadata) == 1000
        assert state.metadata["key_0"].get_string() == "value_0"
        assert state.metadata["key_999"].get_string() == "value_999"

        # Test with unicode metadata
        unicode_metadata = _make_metadata(
            {"chinese": "test_value", "emoji": "rocket", "special": "!@#$%^&*()"}
        )
        state = ModelBaseOutputState(metadata=unicode_metadata)

        assert state.metadata["chinese"].get_string() == "test_value"
        assert state.metadata["emoji"].get_string() == "rocket"
        assert state.metadata["special"].get_string() == "!@#$%^&*()"

        # Test with very small processing time
        state = ModelBaseOutputState(processing_time_ms=0.000001)
        assert state.processing_time_ms == 0.000001

        # Test with very large processing time
        state = ModelBaseOutputState(processing_time_ms=999999999.999)
        assert state.processing_time_ms == 999999999.999
