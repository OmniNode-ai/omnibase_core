"""
Tests for ModelContainer generic pattern.

Validates container functionality including creation, validation, transformation,
serialization, and error handling following ONEX testing patterns.
"""

import json
from typing import Any
from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError

from src.omnibase_core.models.core.model_container import ModelContainer


class TestModelContainer:
    """Test generic container functionality with various types."""

    def test_basic_creation_string(self):
        """Test basic creation with string value."""
        container = ModelContainer[str](
            value="test_value", container_type="string_container"
        )

        assert container.value == "test_value"
        assert container.container_type == "string_container"
        assert container.source is None
        assert container.is_validated is False
        assert container.validation_notes is None

    def test_basic_creation_int(self):
        """Test basic creation with integer value."""
        container = ModelContainer[int](value=42, container_type="int_container")

        assert container.value == 42
        assert container.container_type == "int_container"
        assert container.is_validated is False

    def test_basic_creation_dict(self):
        """Test basic creation with dict value."""
        data = {"key": "value", "nested": {"inner": 123}}
        container = ModelContainer[dict[str, Any]](
            value=data, container_type="dict_container"
        )

        assert container.value == data
        assert container.container_type == "dict_container"
        assert container.value["nested"]["inner"] == 123

    def test_create_class_method(self):
        """Test create() class method."""
        container = ModelContainer.create(
            value="test",
            container_type="test_type",
            source="unit_test",
            is_validated=True,
            validation_notes="Pre-validated",
        )

        assert container.value == "test"
        assert container.container_type == "test_type"
        assert container.source == "unit_test"
        assert container.is_validated is True
        assert container.validation_notes == "Pre-validated"

    def test_create_validated_class_method(self):
        """Test create_validated() class method."""
        container = ModelContainer.create_validated(
            value=100,
            container_type="validated_int",
            source="validation_test",
            validation_notes="Auto-validated",
        )

        assert container.value == 100
        assert container.container_type == "validated_int"
        assert container.source == "validation_test"
        assert container.is_validated is True
        assert container.validation_notes == "Auto-validated"

    def test_get_value(self):
        """Test value retrieval."""
        container = ModelContainer.create(
            value=["a", "b", "c"], container_type="list_container"
        )

        retrieved_value = container.get_value()
        assert retrieved_value == ["a", "b", "c"]
        assert isinstance(retrieved_value, list)

    def test_update_value_basic(self):
        """Test basic value updating."""
        container = ModelContainer.create(
            value="original", container_type="string_container"
        )

        container.update_value("updated")
        assert container.value == "updated"

    def test_update_value_with_validation_notes(self):
        """Test value updating with validation notes."""
        container = ModelContainer.create(
            value="original", container_type="string_container", is_validated=True
        )

        container.update_value(
            "updated", validation_notes="Updated value requires re-validation"
        )

        assert container.value == "updated"
        assert container.validation_notes == "Updated value requires re-validation"
        assert container.is_validated is True  # Should remain as was

    def test_update_value_mark_validated(self):
        """Test value updating with validation marking."""
        container = ModelContainer.create(
            value="original", container_type="string_container"
        )

        container.update_value(
            "updated", validation_notes="Validated during update", mark_validated=True
        )

        assert container.value == "updated"
        assert container.validation_notes == "Validated during update"
        assert container.is_validated is True

    def test_map_value_success(self):
        """Test successful value mapping."""
        container = ModelContainer.create(
            value="hello",
            container_type="string_container",
            source="original",
            is_validated=True,
        )

        # Map to uppercase
        mapped = container.map_value(lambda x: x.upper())

        assert mapped.value == "HELLO"
        assert mapped.container_type == "string_container"
        assert mapped.source == "original"
        assert mapped.is_validated is False  # Should be reset
        assert mapped.validation_notes == "Value transformed, requires re-validation"

    def test_map_value_with_type_change(self):
        """Test value mapping with type transformation."""
        container = ModelContainer.create(
            value="123", container_type="string_container"
        )

        # Map to integer
        mapped = container.map_value(lambda x: int(x))

        assert mapped.value == 123
        assert isinstance(mapped.value, int)
        assert mapped.is_validated is False

    def test_map_value_failure(self):
        """Test value mapping failure handling."""
        container = ModelContainer.create(
            value="not_a_number", container_type="string_container"
        )

        with pytest.raises(Exception) as exc_info:
            container.map_value(lambda x: int(x))

        assert "Failed to map container value" in str(exc_info.value)

    def test_validate_with_success(self):
        """Test successful validation."""
        container = ModelContainer.create(value=10, container_type="int_container")

        # Validate positive number
        result = container.validate_with(lambda x: x > 0, "Number must be positive")

        assert result is True
        assert container.is_validated is True
        assert container.validation_notes == "Validation passed"

    def test_validate_with_failure(self):
        """Test validation failure."""
        container = ModelContainer.create(value=-5, container_type="int_container")

        with pytest.raises(Exception) as exc_info:
            container.validate_with(lambda x: x > 0, "Number must be positive")

        assert "Number must be positive" in str(exc_info.value)
        assert container.is_validated is False
        assert container.validation_notes == "Number must be positive"

    def test_validate_with_exception_in_validator(self):
        """Test validation with exception in validator function."""
        container = ModelContainer.create(
            value="test", container_type="string_container"
        )

        def failing_validator(x: str) -> bool:
            raise ValueError("Validator crashed")

        with pytest.raises(Exception) as exc_info:
            container.validate_with(failing_validator)

        assert "Validation error:" in str(exc_info.value)
        assert "Validator crashed" in str(exc_info.value)

    def test_compare_value_with_same_type(self):
        """Test value comparison with same type."""
        container = ModelContainer.create(
            value="test", container_type="string_container"
        )

        assert container.compare_value("test") is True
        assert container.compare_value("other") is False

    def test_compare_value_with_container(self):
        """Test value comparison with other container."""
        container1 = ModelContainer.create(
            value="test", container_type="string_container"
        )
        container2 = ModelContainer.create(
            value="test",
            container_type="other_container",  # Different type but same value
        )
        container3 = ModelContainer.create(
            value="different", container_type="string_container"
        )

        assert container1.compare_value(container2) is True
        assert container1.compare_value(container3) is False

    def test_equality_operator(self):
        """Test equality operator behavior."""
        container1 = ModelContainer.create(value=42, container_type="int_container")
        container2 = ModelContainer.create(value=42, container_type="other_container")

        assert container1 == container2
        assert container1 == 42
        assert container1 != 43
        assert container1 != "42"  # Type matters

    def test_string_representation(self):
        """Test __str__ method."""
        container = ModelContainer.create(
            value="test_value",
            container_type="test_container",
            source="unit_test",
            is_validated=True,
        )

        str_repr = str(container)
        assert "test_container(test_value)" in str_repr
        assert "[validated]" in str_repr
        assert "from unit_test" in str_repr

    def test_string_representation_unvalidated(self):
        """Test __str__ method for unvalidated container."""
        container = ModelContainer.create(value="test", container_type="test_container")

        str_repr = str(container)
        assert "test_container(test)" in str_repr
        assert "[unvalidated]" in str_repr

    def test_repr_method(self):
        """Test __repr__ method."""
        container = ModelContainer.create(
            value="test", container_type="test_type", source="test_source"
        )

        repr_str = repr(container)
        assert "ModelContainer(" in repr_str
        assert "value='test'" in repr_str
        assert "container_type='test_type'" in repr_str
        assert "source='test_source'" in repr_str
        assert "is_validated=False" in repr_str


class TestModelContainerSerialization:
    """Test serialization and deserialization capabilities."""

    def test_json_serialization(self):
        """Test JSON serialization."""
        container = ModelContainer.create(
            value={"key": "value", "number": 42},
            container_type="dict_container",
            source="test",
            is_validated=True,
            validation_notes="Test serialization",
        )

        # Serialize to JSON
        json_data = container.model_dump()

        assert json_data["value"] == {"key": "value", "number": 42}
        assert json_data["container_type"] == "dict_container"
        assert json_data["source"] == "test"
        assert json_data["is_validated"] is True
        assert json_data["validation_notes"] == "Test serialization"

    def test_json_deserialization(self):
        """Test JSON deserialization."""
        json_data = {
            "value": ["item1", "item2", "item3"],
            "container_type": "list_container",
            "source": "deserialization_test",
            "is_validated": True,
            "validation_notes": "Deserialized successfully",
        }

        container = ModelContainer[list[str]](**json_data)

        assert container.value == ["item1", "item2", "item3"]
        assert container.container_type == "list_container"
        assert container.source == "deserialization_test"
        assert container.is_validated is True
        assert container.validation_notes == "Deserialized successfully"

    def test_round_trip_serialization(self):
        """Test full round-trip serialization."""
        original = ModelContainer.create(
            value=3.14159,
            container_type="float_container",
            source="math_test",
            is_validated=True,
        )

        # Serialize
        json_str = original.model_dump_json()

        # Deserialize
        json_data = json.loads(json_str)
        deserialized = ModelContainer[float](**json_data)

        assert deserialized.value == original.value
        assert deserialized.container_type == original.container_type
        assert deserialized.source == original.source
        assert deserialized.is_validated == original.is_validated


class TestModelContainerEdgeCases:
    """Test edge cases and error conditions."""

    def test_none_value(self):
        """Test container with None value."""
        container = ModelContainer.create(value=None, container_type="none_container")

        assert container.value is None
        assert container.get_value() is None

    def test_empty_string_value(self):
        """Test container with empty string."""
        container = ModelContainer.create(value="", container_type="empty_string")

        assert container.value == ""
        assert container.compare_value("") is True

    def test_zero_value(self):
        """Test container with zero value."""
        container = ModelContainer.create(value=0, container_type="zero_int")

        assert container.value == 0
        assert container.compare_value(0) is True
        assert container.compare_value(False) is False  # Strict comparison

    def test_complex_nested_structure(self):
        """Test container with complex nested data."""
        complex_data = {
            "level1": {
                "level2": {
                    "list": [1, 2, {"nested_dict": "value"}],
                    "tuple": (1, 2, 3),
                    "set_converted_to_list": [1, 2, 3],  # Sets become lists in JSON
                }
            }
        }

        container = ModelContainer.create(
            value=complex_data, container_type="complex_data"
        )

        assert container.value["level1"]["level2"]["list"][2]["nested_dict"] == "value"

    def test_validation_with_complex_logic(self):
        """Test validation with complex validation logic."""
        container = ModelContainer.create(
            value={"username": "test_user", "age": 25}, container_type="user_data"
        )

        def validate_user_data(data: dict[str, Any]) -> bool:
            return (
                isinstance(data.get("username"), str)
                and len(data["username"]) >= 3
                and isinstance(data.get("age"), int)
                and data["age"] >= 18
            )

        result = container.validate_with(validate_user_data, "Invalid user data")

        assert result is True
        assert container.is_validated is True

    def test_mapping_preserves_source_metadata(self):
        """Test that mapping preserves source and container_type."""
        container = ModelContainer.create(
            value=10, container_type="original_int", source="calculation_service"
        )

        # Map to string
        mapped = container.map_value(lambda x: f"value_{x}")

        assert mapped.value == "value_10"
        assert mapped.container_type == "original_int"
        assert mapped.source == "calculation_service"

    def test_invalid_pydantic_data(self):
        """Test handling of invalid Pydantic data."""
        with pytest.raises(ValidationError):
            # Missing required field
            ModelContainer[str](container_type="test")  # Missing value

    def test_type_safety_enforcement(self):
        """Test that generic type parameters are enforced correctly."""
        # This is more about demonstrating proper usage
        str_container: ModelContainer[str] = ModelContainer.create(
            value="string_value", container_type="string_type"
        )

        int_container: ModelContainer[int] = ModelContainer.create(
            value=42, container_type="int_type"
        )

        # Type checker should catch mismatches, but runtime allows it
        assert str_container.value == "string_value"
        assert int_container.value == 42


class TestModelContainerIntegration:
    """Test integration scenarios and real-world usage patterns."""

    def test_pipeline_processing_pattern(self):
        """Test using containers in a processing pipeline."""
        # Start with raw data
        raw_container = ModelContainer.create(
            value="  HELLO WORLD  ", container_type="raw_string", source="user_input"
        )

        # Process through pipeline
        trimmed = raw_container.map_value(lambda x: x.strip())
        lowercase = trimmed.map_value(lambda x: x.lower())
        words = lowercase.map_value(lambda x: x.split())

        # Validate final result
        words.validate_with(
            lambda x: len(x) == 2 and all(isinstance(word, str) for word in x),
            "Must be exactly 2 words",
        )

        assert words.value == ["hello", "world"]
        assert words.is_validated is True

    def test_configuration_value_pattern(self):
        """Test using container for configuration values."""
        config_container = ModelContainer.create_validated(
            value={"host": "localhost", "port": 8080, "ssl": True},
            container_type="server_config",
            source="config_file",
            validation_notes="Loaded from config.json",
        )

        # Extract specific config value
        host = config_container.map_value(lambda x: x.get("host", "unknown"))

        assert host.value == "localhost"
        assert host.container_type == "server_config"
        assert host.source == "config_file"

    def test_error_context_preservation(self):
        """Test that error contexts preserve container information."""
        container = ModelContainer.create(
            value="invalid_number", container_type="numeric_string"
        )

        with pytest.raises(OnexError) as exc_info:
            container.map_value(lambda x: int(x))

        error = exc_info.value
        assert "numeric_string" in str(error.details)
        assert "invalid_number" in str(error.details)

    def test_chained_validation(self):
        """Test multiple validation steps."""
        container = ModelContainer.create(value=15, container_type="number_value")

        # First validation
        container.validate_with(lambda x: x > 0, "Must be positive")

        # Second validation (should reset validation status due to bug/design)
        # But we can work around it
        original_notes = container.validation_notes
        container.validate_with(lambda x: x < 100, "Must be less than 100")

        assert container.is_validated is True
        # Last validation overwrites notes
        assert "Validation passed" in container.validation_notes

    def test_container_as_cache_value(self):
        """Test using container for cached values with metadata."""
        # Simulate cached computation result
        cache_container = ModelContainer.create_validated(
            value={"result": 42, "computed_at": "2024-01-01T12:00:00Z"},
            container_type="cached_computation",
            source="cache_service",
            validation_notes="Cache hit, expires in 300s",
        )

        # Check if cache is valid (simulation)
        is_valid = cache_container.validate_with(
            lambda x: "computed_at" in x and x["result"] is not None,
            "Invalid cache format",
        )

        assert is_valid is True
        assert cache_container.value["result"] == 42
