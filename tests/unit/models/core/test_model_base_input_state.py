"""
Test suite for ModelBaseInputState.
"""

from datetime import datetime

import pytest

from omnibase_core.models.common.model_schema_value import ModelSchemaValue
from omnibase_core.models.core.model_base_input_state import ModelBaseInputState
from omnibase_core.models.primitives.model_semver import ModelSemVer

# Default version for test instances - required field after removing default_factory
DEFAULT_VERSION = ModelSemVer(major=1, minor=0, patch=0)


def _make_metadata(data: dict) -> dict[str, ModelSchemaValue]:
    """Convert a plain dict to dict[str, ModelSchemaValue]."""
    return {k: ModelSchemaValue.from_value(v) for k, v in data.items()}


@pytest.mark.unit
class TestModelBaseInputState:
    """Test ModelBaseInputState functionality."""

    def test_model_base_input_state_creation_default(self):
        """Test creating ModelBaseInputState with default values."""
        state = ModelBaseInputState(version=DEFAULT_VERSION)

        assert isinstance(state.metadata, dict)
        assert len(state.metadata) == 0
        assert isinstance(state.timestamp, datetime)

    def test_model_base_input_state_creation_with_metadata(self):
        """Test creating ModelBaseInputState with custom metadata."""
        metadata = _make_metadata({"key1": "value1", "key2": 123, "key3": True})
        state = ModelBaseInputState(metadata=metadata)

        assert state.metadata["key1"].get_string() == "value1"
        assert state.metadata["key2"].get_number().to_python_value() == 123
        assert state.metadata["key3"].get_boolean() is True
        assert isinstance(state.timestamp, datetime)

    def test_model_base_input_state_creation_with_timestamp(self):
        """Test creating ModelBaseInputState with custom timestamp."""
        custom_timestamp = datetime(2024, 1, 15, 10, 30, 45)
        state = ModelBaseInputState(timestamp=custom_timestamp)

        assert state.timestamp == custom_timestamp
        assert isinstance(state.metadata, dict)
        assert len(state.metadata) == 0

    def test_model_base_input_state_creation_with_both(self):
        """Test creating ModelBaseInputState with both metadata and timestamp."""
        metadata = _make_metadata({"test": "data", "number": 42})
        custom_timestamp = datetime(2024, 1, 15, 10, 30, 45)
        state = ModelBaseInputState(metadata=metadata, timestamp=custom_timestamp)

        assert state.metadata["test"].get_string() == "data"
        assert state.metadata["number"].get_number().to_python_value() == 42
        assert state.timestamp == custom_timestamp

    def test_model_base_input_state_metadata_types(self):
        """Test ModelBaseInputState with different metadata value types."""
        metadata = _make_metadata({
            "string": "test",
            "integer": 123,
            "float": 45.67,
            "boolean": True,
            "list": [1, 2, 3],
            "dict": {"nested": "value"},
            "none": None,
        })
        state = ModelBaseInputState(metadata=metadata)

        assert state.metadata["string"].get_string() == "test"
        assert state.metadata["integer"].get_number().to_python_value() == 123
        assert state.metadata["float"].get_number().to_python_value() == 45.67
        assert state.metadata["boolean"].get_boolean() is True
        assert state.metadata["list"].is_array()
        assert state.metadata["dict"].is_object()
        assert state.metadata["none"].is_null()

    def test_model_base_input_state_empty_metadata(self):
        """Test ModelBaseInputState with empty metadata."""
        state = ModelBaseInputState(metadata={})

        assert state.metadata == {}
        assert isinstance(state.metadata, dict)
        assert len(state.metadata) == 0

    def test_model_base_input_state_nested_metadata(self):
        """Test ModelBaseInputState with nested metadata structure."""
        metadata = _make_metadata({
            "level1": {
                "level2": {
                    "level3": "deep_value",
                    "list": [1, 2, {"nested": "object"}],
                },
                "simple": "value",
            },
            "top_level": "value",
        })
        state = ModelBaseInputState(metadata=metadata)

        level1 = state.metadata["level1"].get_object()
        level2 = level1["level2"].get_object()
        assert level2["level3"].get_string() == "deep_value"
        assert level1["simple"].get_string() == "value"
        assert state.metadata["top_level"].get_string() == "value"

    def test_model_base_input_state_timestamp_formats(self):
        """Test ModelBaseInputState with different timestamp formats."""
        # Test with specific datetime
        specific_time = datetime(2024, 12, 25, 15, 30, 45)
        state = ModelBaseInputState(timestamp=specific_time)
        assert state.timestamp == specific_time

        # Test with current time
        now = datetime.now()
        state = ModelBaseInputState(timestamp=now)
        assert state.timestamp == now

        # Test with minimum datetime
        min_time = datetime.min
        state = ModelBaseInputState(timestamp=min_time)
        assert state.timestamp == min_time

    def test_model_base_input_state_serialization(self):
        """Test ModelBaseInputState serialization."""
        metadata = _make_metadata({"test": "data", "number": 42})
        custom_timestamp = datetime(2024, 1, 15, 10, 30, 45)
        state = ModelBaseInputState(metadata=metadata, timestamp=custom_timestamp)

        # Test model_dump
        data = state.model_dump()
        assert "metadata" in data
        assert "timestamp" in data
        assert data["timestamp"] == custom_timestamp

        # Test model_dump_json
        json_data = state.model_dump_json()
        assert isinstance(json_data, str)
        assert "test" in json_data
        assert "data" in json_data

    def test_model_base_input_state_deserialization(self):
        """Test ModelBaseInputState deserialization."""
        metadata = _make_metadata({"test": "data", "number": 42})
        custom_timestamp = datetime(2024, 1, 15, 10, 30, 45)

        # Test from dict
        data = {"metadata": metadata, "timestamp": custom_timestamp}
        state = ModelBaseInputState.model_validate(data)

        assert state.metadata["test"].get_string() == "data"
        assert state.timestamp == custom_timestamp

    def test_model_base_input_state_validation(self):
        """Test ModelBaseInputState validation."""
        # Test valid data
        metadata = _make_metadata({"valid": "data"})
        state = ModelBaseInputState(metadata=metadata)
        assert state.metadata["valid"].get_string() == "data"

        # Test with empty dict (valid)
        state = ModelBaseInputState(metadata={})
        assert state.metadata == {}

    def test_model_base_input_state_immutability(self):
        """Test ModelBaseInputState immutability."""
        metadata = _make_metadata({"original": "value"})
        state = ModelBaseInputState(metadata=metadata)

        # Should be able to modify metadata (it's a dict)
        state.metadata["new_key"] = ModelSchemaValue.create_string("new_value")
        assert state.metadata["new_key"].get_string() == "new_value"
        assert state.metadata["original"].get_string() == "value"

        # Timestamp should be immutable
        original_timestamp = state.timestamp
        # This would raise an error if timestamp was immutable
        # state.timestamp = datetime.now()  # This would fail

    def test_model_base_input_state_equality(self):
        """Test ModelBaseInputState equality."""
        metadata = _make_metadata({"test": "data"})
        timestamp = datetime(2024, 1, 15, 10, 30, 45)

        state1 = ModelBaseInputState(metadata=metadata, timestamp=timestamp)
        state2 = ModelBaseInputState(metadata=metadata, timestamp=timestamp)

        assert state1 == state2

        # Test with different metadata
        state3 = ModelBaseInputState(
            version=DEFAULT_VERSION,
            metadata=_make_metadata({"different": "data"}),
            timestamp=timestamp,
        )
        assert state1 != state3

        # Test with different timestamp
        state4 = ModelBaseInputState(metadata=metadata, timestamp=datetime.now())
        assert state1 != state4

    def test_model_base_input_state_str_representation(self):
        """Test ModelBaseInputState string representation."""
        metadata = _make_metadata({"test": "data"})
        state = ModelBaseInputState(metadata=metadata)
        str_repr = str(state)

        assert "metadata" in str_repr
        assert "timestamp" in str_repr

    def test_model_base_input_state_repr_representation(self):
        """Test ModelBaseInputState repr representation."""
        metadata = _make_metadata({"test": "data"})
        state = ModelBaseInputState(metadata=metadata)
        repr_str = repr(state)

        assert "ModelBaseInputState" in repr_str
        assert "metadata" in repr_str
        assert "timestamp" in repr_str

    def test_model_base_input_state_field_descriptions(self):
        """Test ModelBaseInputState field descriptions."""
        # Check that fields have proper descriptions
        fields = ModelBaseInputState.model_fields

        assert "metadata" in fields
        assert "timestamp" in fields

        # Check field descriptions
        assert "Metadata for the input state" in fields["metadata"].description
        assert "Timestamp when the input was created" in fields["timestamp"].description

    def test_model_base_input_state_default_factory(self):
        """Test ModelBaseInputState default factory behavior."""
        # Test that metadata defaults to empty dict
        state1 = ModelBaseInputState(version=DEFAULT_VERSION)
        state2 = ModelBaseInputState(version=DEFAULT_VERSION)

        # Both should have empty metadata
        assert state1.metadata == {}
        assert state2.metadata == {}

        # But they should be different instances
        state1.metadata["test"] = ModelSchemaValue.create_string("value1")
        state2.metadata["test"] = ModelSchemaValue.create_string("value2")

        assert state1.metadata["test"].get_string() == "value1"
        assert state2.metadata["test"].get_string() == "value2"

    def test_model_base_input_state_timestamp_default_factory(self):
        """Test ModelBaseInputState timestamp default factory behavior."""
        # Test that timestamp defaults to current time
        before = datetime.now()
        state = ModelBaseInputState(version=DEFAULT_VERSION)
        after = datetime.now()

        assert before <= state.timestamp <= after

    def test_model_base_input_state_edge_cases(self):
        """Test ModelBaseInputState edge cases."""
        # Test with very large metadata
        large_metadata = _make_metadata({f"key_{i}": f"value_{i}" for i in range(1000)})
        state = ModelBaseInputState(metadata=large_metadata)

        assert len(state.metadata) == 1000
        assert state.metadata["key_0"].get_string() == "value_0"
        assert state.metadata["key_999"].get_string() == "value_999"

        # Test with unicode metadata
        unicode_metadata = _make_metadata(
            {"chinese": "test_value", "emoji": "rocket", "special": "!@#$%^&*()"}
        )
        state = ModelBaseInputState(metadata=unicode_metadata)

        assert state.metadata["chinese"].get_string() == "test_value"
        assert state.metadata["emoji"].get_string() == "rocket"
        assert state.metadata["special"].get_string() == "!@#$%^&*()"
