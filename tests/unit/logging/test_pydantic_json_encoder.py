"""
Comprehensive unit tests for logging/pydantic_json_encoder.py module.

Tests cover:
- Pydantic model serialization
- UUID serialization
- ProtocolLogContext serialization (to_dict method)
- Mock object serialization (deadlock prevention)
- Fallback to default encoder
- Edge cases (None, nested models, special types)
- JSON encoding round-trip
"""

import json
from unittest.mock import MagicMock, Mock
from uuid import UUID, uuid4

import pytest
from pydantic import BaseModel

from omnibase_core.logging.pydantic_json_encoder import PydanticJSONEncoder


class SampleModel(BaseModel):
    """Sample Pydantic model for testing."""

    name: str
    value: int
    uuid: UUID


class NestedModel(BaseModel):
    """Nested Pydantic model for testing."""

    sample: SampleModel
    description: str


class MockLogContext:
    """Mock object with to_dict method (simulates ProtocolLogContext)."""

    def __init__(self, data: dict):
        self.data = data

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return self.data


class TestPydanticModelSerialization:
    """Test Pydantic model serialization."""

    def test_serialize_simple_pydantic_model(self):
        """Test serialization of simple Pydantic model."""
        model = SampleModel(name="test", value=42, uuid=uuid4())

        result = json.dumps(model, cls=PydanticJSONEncoder)

        # Should be valid JSON
        parsed = json.loads(result)
        assert parsed["name"] == "test"
        assert parsed["value"] == 42
        assert "uuid" in parsed

    def test_serialize_nested_pydantic_model(self):
        """Test serialization of nested Pydantic models."""
        inner_model = SampleModel(name="inner", value=10, uuid=uuid4())
        outer_model = NestedModel(sample=inner_model, description="nested test")

        result = json.dumps(outer_model, cls=PydanticJSONEncoder)

        # Should serialize nested models
        parsed = json.loads(result)
        assert parsed["description"] == "nested test"
        assert parsed["sample"]["name"] == "inner"
        assert parsed["sample"]["value"] == 10

    def test_serialize_pydantic_model_with_optional_fields(self):
        """Test serialization of Pydantic model with optional fields."""

        class ModelWithOptional(BaseModel):
            required: str
            optional: str | None = None

        model = ModelWithOptional(required="test")

        result = json.dumps(model, cls=PydanticJSONEncoder)

        parsed = json.loads(result)
        assert parsed["required"] == "test"
        assert parsed["optional"] is None

    def test_serialize_pydantic_model_list(self):
        """Test serialization of list of Pydantic models."""
        models = [
            SampleModel(name=f"model_{i}", value=i, uuid=uuid4()) for i in range(3)
        ]

        result = json.dumps(models, cls=PydanticJSONEncoder)

        parsed = json.loads(result)
        assert len(parsed) == 3
        assert parsed[0]["name"] == "model_0"
        assert parsed[2]["value"] == 2


class TestUUIDSerialization:
    """Test UUID serialization."""

    def test_serialize_uuid(self):
        """Test serialization of UUID object."""
        test_uuid = uuid4()

        result = json.dumps(test_uuid, cls=PydanticJSONEncoder)

        # Should be string representation
        parsed = json.loads(result)
        assert parsed == str(test_uuid)

    def test_serialize_uuid_in_dict(self):
        """Test serialization of UUID within dictionary."""
        test_uuid = uuid4()
        data = {"id": test_uuid, "name": "test"}

        result = json.dumps(data, cls=PydanticJSONEncoder)

        parsed = json.loads(result)
        assert parsed["id"] == str(test_uuid)
        assert parsed["name"] == "test"

    def test_serialize_uuid_in_list(self):
        """Test serialization of UUIDs in list."""
        uuids = [uuid4() for _ in range(3)]

        result = json.dumps(uuids, cls=PydanticJSONEncoder)

        parsed = json.loads(result)
        assert len(parsed) == 3
        for i, uuid_str in enumerate(parsed):
            assert uuid_str == str(uuids[i])

    def test_serialize_mixed_uuid_types(self):
        """Test serialization of mixed UUID and string types."""
        test_uuid = uuid4()
        data = {"uuid_obj": test_uuid, "uuid_str": str(test_uuid), "name": "mixed"}

        result = json.dumps(data, cls=PydanticJSONEncoder)

        parsed = json.loads(result)
        # Both should be strings in JSON
        assert parsed["uuid_obj"] == str(test_uuid)
        assert parsed["uuid_str"] == str(test_uuid)


class TestLogContextSerialization:
    """Test ProtocolLogContext (to_dict method) serialization."""

    def test_serialize_object_with_to_dict_method(self):
        """Test serialization of object with to_dict method."""
        context_data = {"function": "test_func", "line": 42, "module": "test_module"}
        log_context = MockLogContext(context_data)

        result = json.dumps(log_context, cls=PydanticJSONEncoder)

        parsed = json.loads(result)
        assert parsed == context_data

    def test_serialize_log_context_in_dict(self):
        """Test serialization of log context within dictionary."""
        context_data = {"event": "test_event", "timestamp": "2024-01-01"}
        log_context = MockLogContext(context_data)
        data = {"context": log_context, "level": "INFO"}

        result = json.dumps(data, cls=PydanticJSONEncoder)

        parsed = json.loads(result)
        assert parsed["context"] == context_data
        assert parsed["level"] == "INFO"

    def test_serialize_log_context_with_nested_data(self):
        """Test serialization of log context with nested data."""
        context_data = {
            "outer": {"inner": {"value": 42}},
            "list": [1, 2, 3],
        }
        log_context = MockLogContext(context_data)

        result = json.dumps(log_context, cls=PydanticJSONEncoder)

        parsed = json.loads(result)
        assert parsed["outer"]["inner"]["value"] == 42
        assert parsed["list"] == [1, 2, 3]

    def test_serialize_multiple_log_contexts(self):
        """Test serialization of multiple log contexts."""
        contexts = [MockLogContext({"id": i, "name": f"context_{i}"}) for i in range(3)]

        result = json.dumps(contexts, cls=PydanticJSONEncoder)

        parsed = json.loads(result)
        assert len(parsed) == 3
        assert parsed[1]["name"] == "context_1"


class TestFallbackSerialization:
    """Test fallback to default encoder."""

    def test_serialize_standard_types(self):
        """Test serialization of standard JSON types."""
        data = {
            "string": "text",
            "int": 42,
            "float": 3.14,
            "bool": True,
            "none": None,
            "list": [1, 2, 3],
            "dict": {"nested": "value"},
        }

        result = json.dumps(data, cls=PydanticJSONEncoder)

        parsed = json.loads(result)
        assert parsed == data

    def test_serialize_empty_containers(self):
        """Test serialization of empty containers."""
        data = {"empty_list": [], "empty_dict": {}, "empty_string": ""}

        result = json.dumps(data, cls=PydanticJSONEncoder)

        parsed = json.loads(result)
        assert parsed["empty_list"] == []
        assert parsed["empty_dict"] == {}
        assert parsed["empty_string"] == ""

    def test_serialize_unsupported_type_raises_error(self):
        """Test that unsupported types raise TypeError."""

        class UnsupportedType:
            """Type with no serialization support."""

        obj = UnsupportedType()

        with pytest.raises(TypeError):
            json.dumps(obj, cls=PydanticJSONEncoder)

    def test_fallback_to_default_encoder(self):
        """Test fallback to default encoder for standard types."""
        # Standard types should use default encoder path
        data = {"number": 123, "text": "hello"}

        result = json.dumps(data, cls=PydanticJSONEncoder)

        parsed = json.loads(result)
        assert parsed["number"] == 123
        assert parsed["text"] == "hello"


class TestComplexSerializationScenarios:
    """Test complex serialization scenarios."""

    def test_serialize_mixed_types(self):
        """Test serialization of mixed types in one structure."""
        test_uuid = uuid4()
        model = SampleModel(name="test", value=42, uuid=test_uuid)
        log_context = MockLogContext({"event": "test"})

        data = {
            "model": model,
            "uuid": test_uuid,
            "context": log_context,
            "standard": {"value": 123},
        }

        result = json.dumps(data, cls=PydanticJSONEncoder)

        parsed = json.loads(result)
        assert parsed["model"]["name"] == "test"
        assert parsed["uuid"] == str(test_uuid)
        assert parsed["context"]["event"] == "test"
        assert parsed["standard"]["value"] == 123

    def test_serialize_nested_mixed_types(self):
        """Test serialization of deeply nested mixed types."""
        inner_uuid = uuid4()
        inner_model = SampleModel(name="inner", value=10, uuid=inner_uuid)

        data = {
            "level1": {
                "level2": {
                    "model": inner_model,
                    "uuid": inner_uuid,
                    "list": [1, 2, 3],
                }
            }
        }

        result = json.dumps(data, cls=PydanticJSONEncoder)

        parsed = json.loads(result)
        assert parsed["level1"]["level2"]["model"]["name"] == "inner"
        assert parsed["level1"]["level2"]["uuid"] == str(inner_uuid)

    def test_serialize_list_of_mixed_types(self):
        """Test serialization of list containing mixed types."""
        test_uuid = uuid4()
        model = SampleModel(name="test", value=42, uuid=test_uuid)
        log_context = MockLogContext({"event": "test"})

        data = [
            model,
            test_uuid,
            log_context,
            {"standard": "dict"},
            "string",
            123,
        ]

        result = json.dumps(data, cls=PydanticJSONEncoder)

        parsed = json.loads(result)
        assert len(parsed) == 6
        assert parsed[0]["name"] == "test"
        assert parsed[1] == str(test_uuid)
        assert parsed[2]["event"] == "test"


class TestEdgeCases:
    """Test edge cases and special scenarios."""

    def test_serialize_none_value(self):
        """Test serialization of None value."""
        result = json.dumps(None, cls=PydanticJSONEncoder)

        parsed = json.loads(result)
        assert parsed is None

    def test_serialize_empty_pydantic_model(self):
        """Test serialization of Pydantic model with no fields."""

        class EmptyModel(BaseModel):
            """Empty model for testing."""

        model = EmptyModel()

        result = json.dumps(model, cls=PydanticJSONEncoder)

        parsed = json.loads(result)
        assert parsed == {}

    def test_serialize_pydantic_model_with_special_characters(self):
        """Test serialization of Pydantic model with special characters."""

        class ModelWithSpecialChars(BaseModel):
            text: str

        model = ModelWithSpecialChars(text="Special: \n\t\r ñ é ü 中文 🚀")

        result = json.dumps(model, cls=PydanticJSONEncoder)

        parsed = json.loads(result)
        assert "Special" in parsed["text"]

    def test_serialize_uuid_with_special_format(self):
        """Test serialization of UUID with different formats."""
        # UUID should be serialized consistently regardless of format
        test_uuid = UUID("12345678-1234-5678-1234-567812345678")

        result = json.dumps(test_uuid, cls=PydanticJSONEncoder)

        parsed = json.loads(result)
        assert parsed == str(test_uuid)

    def test_serialize_log_context_with_none_values(self):
        """Test serialization of log context with None values."""
        context_data = {"value": None, "name": "test"}
        log_context = MockLogContext(context_data)

        result = json.dumps(log_context, cls=PydanticJSONEncoder)

        parsed = json.loads(result)
        assert parsed["value"] is None
        assert parsed["name"] == "test"

    def test_round_trip_serialization(self):
        """Test round-trip serialization and deserialization."""
        test_uuid = uuid4()
        model = SampleModel(name="test", value=42, uuid=test_uuid)

        # Serialize
        json_str = json.dumps(model, cls=PydanticJSONEncoder)

        # Deserialize back to dict
        parsed = json.loads(json_str)

        # Recreate model
        recreated = SampleModel(**parsed)

        assert recreated.name == model.name
        assert recreated.value == model.value
        assert recreated.uuid == model.uuid


class TestMockObjectSerialization:
    """Test unittest.mock.Mock and MagicMock serialization (deadlock prevention)."""

    def test_serialize_mock_object(self):
        """Test that Mock objects serialize without triggering call tracking."""
        mock_obj = Mock()

        # Should not deadlock or raise exception
        result = json.dumps({"test": mock_obj}, cls=PydanticJSONEncoder)

        parsed = json.loads(result)
        # Mock should be serialized as its repr string
        assert "<Mock" in parsed["test"]

    def test_serialize_named_mock(self):
        """Test that named Mock objects serialize with their name."""
        named_mock = Mock(name="test_mock")

        result = json.dumps({"test": named_mock}, cls=PydanticJSONEncoder)

        parsed = json.loads(result)
        assert "test_mock" in parsed["test"]

    def test_serialize_magic_mock(self):
        """Test that MagicMock objects serialize safely."""
        magic_mock = MagicMock()

        result = json.dumps({"test": magic_mock}, cls=PydanticJSONEncoder)

        parsed = json.loads(result)
        assert "<MagicMock" in parsed["test"]

    def test_serialize_nested_mock_in_dict(self):
        """Test that nested Mock objects in dictionaries serialize safely."""
        data = {"outer": {"inner": Mock(name="nested_mock")}}

        result = json.dumps(data, cls=PydanticJSONEncoder)

        parsed = json.loads(result)
        assert "nested_mock" in parsed["outer"]["inner"]

    def test_serialize_list_of_mocks(self):
        """Test that lists containing Mock objects serialize safely."""
        mock_list = [Mock(name=f"mock_{i}") for i in range(3)]

        result = json.dumps({"mocks": mock_list}, cls=PydanticJSONEncoder)

        parsed = json.loads(result)
        assert len(parsed["mocks"]) == 3
        # Each mock should be serialized as string
        for i, mock_str in enumerate(parsed["mocks"]):
            assert f"mock_{i}" in mock_str

    def test_serialize_mock_does_not_call_to_dict(self):
        """Test that serializing Mock does NOT call to_dict (prevents deadlock)."""
        mock_obj = Mock()

        # Add to_dict method to the mock
        mock_obj.to_dict = Mock(return_value={"should": "not be called"})

        # Serialize
        result = json.dumps({"test": mock_obj}, cls=PydanticJSONEncoder)

        # to_dict should NOT have been called
        mock_obj.to_dict.assert_not_called()

        # Should serialize as repr, not as the to_dict return value
        parsed = json.loads(result)
        assert "<Mock" in parsed["test"]
        assert "should" not in parsed["test"]


class TestEncoderExportAndUsage:
    """Test encoder export and usage patterns."""

    def test_encoder_is_exported(self):
        """Test that PydanticJSONEncoder is properly exported."""
        from omnibase_core.logging.pydantic_json_encoder import __all__

        assert "PydanticJSONEncoder" in __all__

    def test_encoder_can_be_used_with_json_dump(self):
        """Test encoder works with json.dump (file writing)."""
        import tempfile

        test_uuid = uuid4()
        data = {"uuid": test_uuid, "value": 42}

        with tempfile.NamedTemporaryFile(mode="w+", delete=False) as f:
            json.dump(data, f, cls=PydanticJSONEncoder)
            f.flush()

            # Read back
            f.seek(0)
            parsed = json.load(f)

        assert parsed["uuid"] == str(test_uuid)
        assert parsed["value"] == 42

    def test_encoder_can_be_reused(self):
        """Test that encoder instance can be reused."""
        encoder = PydanticJSONEncoder()

        test_uuid = uuid4()
        model = SampleModel(name="test", value=42, uuid=test_uuid)

        # Use encoder multiple times
        result1 = encoder.default(model)
        result2 = encoder.default(test_uuid)

        assert result1["name"] == "test"
        assert result2 == str(test_uuid)
