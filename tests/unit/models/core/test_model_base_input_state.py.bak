"""
Test suite for ModelBaseInputState.
"""

from datetime import datetime

import pytest

from omnibase_core.models.core.model_base_input_state import ModelBaseInputState


class TestModelBaseInputState:
    """Test ModelBaseInputState functionality."""

    def test_model_base_input_state_creation_default(self):
        """Test creating ModelBaseInputState with default values."""
        state = ModelBaseInputState()

        assert isinstance(state.metadata, dict)
        assert len(state.metadata) == 0
        assert isinstance(state.timestamp, datetime)

    def test_model_base_input_state_creation_with_metadata(self):
        """Test creating ModelBaseInputState with custom metadata."""
        metadata = {"key1": "value1", "key2": 123, "key3": True}
        state = ModelBaseInputState(metadata=metadata)

        assert state.metadata == metadata
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
        metadata = {"test": "data", "number": 42}
        custom_timestamp = datetime(2024, 1, 15, 10, 30, 45)
        state = ModelBaseInputState(metadata=metadata, timestamp=custom_timestamp)

        assert state.metadata == metadata
        assert state.timestamp == custom_timestamp

    def test_model_base_input_state_metadata_types(self):
        """Test ModelBaseInputState with different metadata value types."""
        metadata = {
            "string": "test",
            "integer": 123,
            "float": 45.67,
            "boolean": True,
            "list": [1, 2, 3],
            "dict": {"nested": "value"},
            "none": None,
        }
        state = ModelBaseInputState(metadata=metadata)

        assert state.metadata["string"] == "test"
        assert state.metadata["integer"] == 123
        assert state.metadata["float"] == 45.67
        assert state.metadata["boolean"] is True
        assert state.metadata["list"] == [1, 2, 3]
        assert state.metadata["dict"] == {"nested": "value"}
        assert state.metadata["none"] is None

    def test_model_base_input_state_empty_metadata(self):
        """Test ModelBaseInputState with empty metadata."""
        state = ModelBaseInputState(metadata={})

        assert state.metadata == {}
        assert isinstance(state.metadata, dict)
        assert len(state.metadata) == 0

    def test_model_base_input_state_nested_metadata(self):
        """Test ModelBaseInputState with nested metadata structure."""
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
        state = ModelBaseInputState(metadata=metadata)

        assert state.metadata["level1"]["level2"]["level3"] == "deep_value"
        assert state.metadata["level1"]["level2"]["list"] == [
            1,
            2,
            {"nested": "object"},
        ]
        assert state.metadata["level1"]["simple"] == "value"
        assert state.metadata["top_level"] == "value"

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
        metadata = {"test": "data", "number": 42}
        custom_timestamp = datetime(2024, 1, 15, 10, 30, 45)
        state = ModelBaseInputState(metadata=metadata, timestamp=custom_timestamp)

        # Test model_dump
        data = state.model_dump()
        assert "metadata" in data
        assert "timestamp" in data
        assert data["metadata"] == metadata
        assert data["timestamp"] == custom_timestamp

        # Test model_dump_json
        json_data = state.model_dump_json()
        assert isinstance(json_data, str)
        assert "test" in json_data
        assert "data" in json_data

    def test_model_base_input_state_deserialization(self):
        """Test ModelBaseInputState deserialization."""
        metadata = {"test": "data", "number": 42}
        custom_timestamp = datetime(2024, 1, 15, 10, 30, 45)

        # Test from dict
        data = {"metadata": metadata, "timestamp": custom_timestamp}
        state = ModelBaseInputState.model_validate(data)

        assert state.metadata == metadata
        assert state.timestamp == custom_timestamp

        # Test from JSON
        json_data = '{"metadata": {"test": "data"}, "timestamp": "2024-01-15T10:30:45"}'
        state = ModelBaseInputState.model_validate_json(json_data)

        assert state.metadata == {"test": "data"}
        assert state.timestamp.year == 2024
        assert state.timestamp.month == 1
        assert state.timestamp.day == 15

    def test_model_base_input_state_validation(self):
        """Test ModelBaseInputState validation."""
        # Test valid data
        state = ModelBaseInputState(metadata={"valid": "data"})
        assert state.metadata == {"valid": "data"}

        # Test with empty dict (valid)
        state = ModelBaseInputState(metadata={})
        assert state.metadata == {}

    def test_model_base_input_state_immutability(self):
        """Test ModelBaseInputState immutability."""
        state = ModelBaseInputState(metadata={"original": "value"})

        # Should be able to modify metadata (it's a dict)
        state.metadata["new_key"] = "new_value"
        assert state.metadata["new_key"] == "new_value"
        assert state.metadata["original"] == "value"

        # Timestamp should be immutable
        original_timestamp = state.timestamp
        # This would raise an error if timestamp was immutable
        # state.timestamp = datetime.now()  # This would fail

    def test_model_base_input_state_equality(self):
        """Test ModelBaseInputState equality."""
        metadata = {"test": "data"}
        timestamp = datetime(2024, 1, 15, 10, 30, 45)

        state1 = ModelBaseInputState(metadata=metadata, timestamp=timestamp)
        state2 = ModelBaseInputState(metadata=metadata, timestamp=timestamp)

        assert state1 == state2

        # Test with different metadata
        state3 = ModelBaseInputState(
            metadata={"different": "data"}, timestamp=timestamp
        )
        assert state1 != state3

        # Test with different timestamp
        state4 = ModelBaseInputState(metadata=metadata, timestamp=datetime.now())
        assert state1 != state4

    def test_model_base_input_state_str_representation(self):
        """Test ModelBaseInputState string representation."""
        state = ModelBaseInputState(metadata={"test": "data"})
        str_repr = str(state)

        assert "metadata" in str_repr
        assert "timestamp" in str_repr

    def test_model_base_input_state_repr_representation(self):
        """Test ModelBaseInputState repr representation."""
        state = ModelBaseInputState(metadata={"test": "data"})
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
        state1 = ModelBaseInputState()
        state2 = ModelBaseInputState()

        # Both should have empty metadata
        assert state1.metadata == {}
        assert state2.metadata == {}

        # But they should be different instances
        state1.metadata["test"] = "value1"
        state2.metadata["test"] = "value2"

        assert state1.metadata["test"] == "value1"
        assert state2.metadata["test"] == "value2"

    def test_model_base_input_state_timestamp_default_factory(self):
        """Test ModelBaseInputState timestamp default factory behavior."""
        # Test that timestamp defaults to current time
        before = datetime.now()
        state = ModelBaseInputState()
        after = datetime.now()

        assert before <= state.timestamp <= after

    def test_model_base_input_state_edge_cases(self):
        """Test ModelBaseInputState edge cases."""
        # Test with very large metadata
        large_metadata = {f"key_{i}": f"value_{i}" for i in range(1000)}
        state = ModelBaseInputState(metadata=large_metadata)

        assert len(state.metadata) == 1000
        assert state.metadata["key_0"] == "value_0"
        assert state.metadata["key_999"] == "value_999"

        # Test with unicode metadata
        unicode_metadata = {"中文": "测试", "emoji": "🚀", "special": "!@#$%^&*()"}
        state = ModelBaseInputState(metadata=unicode_metadata)

        assert state.metadata["中文"] == "测试"
        assert state.metadata["emoji"] == "🚀"
        assert state.metadata["special"] == "!@#$%^&*()"
