"""
Test suite for ProtocolValidatable implementation in value containers.

Tests protocol compliance across all 8 container types and validation scenarios.
"""

import math
from typing import runtime_checkable

import pytest

from omnibase_core.models.common.model_typed_value import (
    BoolContainer,
    DictContainer,
    FloatContainer,
    IntContainer,
    ListContainer,
    ModelTypedMapping,
    ModelValueContainer,
    ProtocolValidatable,
    StringContainer,
)


class TestProtocolValidatableCompliance:
    """Test that all container types implement ProtocolValidatable correctly."""

    def test_modelvaluecontainer_implements_protocol(self):
        """Test that ModelValueContainer implements ProtocolValidatable."""
        # ONEX-compliant pattern: Direct __init__ calls instead of factory methods
        container = ModelValueContainer(value="test")

        # Runtime protocol check
        assert isinstance(container, ProtocolValidatable)

        # Method existence
        assert hasattr(container, "is_valid")
        assert hasattr(container, "get_errors")
        assert callable(container.is_valid)
        assert callable(container.get_errors)

    def test_all_container_aliases_implement_protocol(self):
        """Test that all container type aliases implement ProtocolValidatable."""
        containers = [
            StringContainer(value="test"),
            IntContainer(value=42),
            FloatContainer(value=3.14),
            BoolContainer(value=True),
            ListContainer(value=[1, 2, 3]),
            DictContainer(value={"key": "value"}),
        ]

        for container in containers:
            assert isinstance(container, ProtocolValidatable)
            assert hasattr(container, "is_valid")
            assert hasattr(container, "get_errors")

    def test_modeltypedmapping_implements_protocol(self):
        """Test that ModelTypedMapping implements ProtocolValidatable."""
        mapping = ModelTypedMapping()

        assert isinstance(mapping, ProtocolValidatable)
        assert hasattr(mapping, "is_valid")
        assert hasattr(mapping, "get_errors")


class TestModelValueContainerValidation:
    """Test validation logic for ModelValueContainer."""

    def test_valid_string_container(self):
        """Test validation of valid string containers."""
        container = StringContainer(value="valid string")

        assert container.is_valid()
        assert container.get_errors() == []

    def test_empty_string_validation(self):
        """Test validation of empty strings."""
        # Default: empty strings not allowed
        container = StringContainer(value="")
        assert not container.is_valid()
        errors = container.get_errors()
        assert any("Empty strings not allowed" in error for error in errors)

        # With allow_empty metadata
        container_allowed = StringContainer(value="", metadata={"allow_empty": "true"})
        assert container_allowed.is_valid()
        assert container_allowed.get_errors() == []

    def test_numeric_validation(self):
        """Test validation of numeric containers."""
        # Valid numbers
        int_container = IntContainer(value=42)
        float_container = FloatContainer(value=3.14)

        assert int_container.is_valid()
        assert float_container.is_valid()
        assert int_container.get_errors() == []
        assert float_container.get_errors() == []

        # Invalid floats
        nan_container = FloatContainer(value=float("nan"))
        inf_container = FloatContainer(value=float("inf"))

        assert not nan_container.is_valid()
        assert not inf_container.is_valid()

        nan_errors = nan_container.get_errors()
        inf_errors = inf_container.get_errors()

        assert any("NaN" in error for error in nan_errors)
        assert any("infinite" in error for error in inf_errors)

    def test_list_validation(self):
        """Test validation of list containers."""
        # Valid list
        valid_list = ListContainer(value=[1, "two", 3.0, True])
        assert valid_list.is_valid()
        assert valid_list.get_errors() == []

        # Large list (DoS prevention)
        large_list = ListContainer(value=list(range(15000)))
        assert not large_list.is_valid()
        errors = large_list.get_errors()
        assert any("exceeds maximum length" in error for error in errors)

        # Non-serializable list (test by bypassing field validation)
        # Since Pydantic prevents non-serializable objects at creation,
        # we test the validation logic by creating a valid container and then
        # modifying it to contain non-serializable data
        bad_list = ListContainer(value=[1, 2, 3])
        # Create a mock object that's not JSON serializable
        import json

        original_dumps = json.dumps

        def failing_dumps(obj, *args, **kwargs):
            if obj == [1, 2, 3]:
                raise TypeError("Mock non-serializable list")
            return original_dumps(obj, *args, **kwargs)

        json.dumps = failing_dumps
        try:
            assert not bad_list.is_json_serializable()
            assert not bad_list.is_valid()
            errors = bad_list.get_errors()
            assert any("not JSON serializable" in error for error in errors)
        finally:
            json.dumps = original_dumps

    def test_dict_validation(self):
        """Test validation of dict containers."""
        # Valid dict
        valid_dict = DictContainer(value={"key1": "value1", "key2": 42})
        assert valid_dict.is_valid()
        assert valid_dict.get_errors() == []

        # Large dict (DoS prevention)
        large_dict = DictContainer(value={f"key_{i}": i for i in range(1500)})
        assert not large_dict.is_valid()
        errors = large_dict.get_errors()
        assert any("exceeds maximum size" in error for error in errors)

        # Non-string keys - this now fails at Pydantic validation time (fail-fast!)
        with pytest.raises(Exception):  # Pydantic validation error
            bad_dict = DictContainer(value={42: "numeric_key", "string_key": "value"})

    def test_metadata_validation(self):
        """Test validation of container metadata."""
        # Valid metadata
        container = StringContainer(
            value="test", metadata={"type": "test", "source": "unit_test"}
        )
        assert container.is_valid()
        assert container.get_errors() == []

        # Invalid metadata types (should not happen due to field validation, but test edge case)
        container = StringContainer(value="test")
        # Manually set invalid metadata to test validation logic
        container.metadata = {"valid_key": "valid_value"}
        assert container.is_valid()

        # Large metadata (DoS prevention)
        large_metadata = {f"key_{i}": f"value_{i}" for i in range(150)}
        container = StringContainer(value="test", metadata=large_metadata)
        assert not container.is_valid()
        errors = container.get_errors()
        assert any("exceeds maximum size" in error for error in errors)

        # Long keys/values
        long_key = "x" * 150
        long_value = "y" * 1500

        long_key_container = StringContainer(value="test", metadata={long_key: "value"})
        long_value_container = StringContainer(
            value="test", metadata={"key": long_value}
        )

        assert not long_key_container.is_valid()
        assert not long_value_container.is_valid()


class TestModelTypedMappingValidation:
    """Test validation logic for ModelTypedMapping."""

    def test_valid_mapping(self):
        """Test validation of valid mappings."""
        mapping = ModelTypedMapping()
        mapping.set_string("name", "test")
        mapping.set_int("age", 25)
        mapping.set_bool("active", True)

        assert mapping.is_valid()
        assert mapping.get_errors() == []

    def test_mapping_with_invalid_containers(self):
        """Test mapping validation when containers are invalid."""
        mapping = ModelTypedMapping()
        mapping.set_string("empty", "")  # Invalid empty string
        mapping.set_float("nan_value", float("nan"))  # Invalid NaN

        assert not mapping.is_valid()
        errors = mapping.get_errors()

        # Should contain errors for both invalid containers
        assert len(errors) >= 2
        assert any("empty" in error and "Empty strings" in error for error in errors)
        assert any("nan_value" in error and "NaN" in error for error in errors)

    def test_mapping_constraint_validation(self):
        """Test mapping-level constraint validation."""
        mapping = ModelTypedMapping()

        # Test key constraints
        mapping.data[""] = StringContainer(value="empty_key")  # Empty key
        mapping.data["valid_key"] = StringContainer(value="value")
        mapping.data["key_with_\x00_null"] = StringContainer(
            value="null_byte"
        )  # Control character

        assert not mapping.is_valid()
        errors = mapping.get_errors()

        assert any("Empty key not allowed" in error for error in errors)
        assert any("null byte" in error for error in errors)

    def test_aggregate_validation_methods(self):
        """Test aggregate validation helper methods."""
        mapping = ModelTypedMapping()
        mapping.set_string("valid", "value")
        mapping.set_string("invalid", "")  # Invalid empty string
        mapping.set_int("number", 42)

        # Test validate_all_containers
        all_results = mapping.validate_all_containers()
        assert "valid" in all_results
        assert "invalid" in all_results
        assert "number" in all_results

        assert all_results["valid"] == []  # No errors
        assert len(all_results["invalid"]) > 0  # Has errors
        assert all_results["number"] == []  # No errors

        # Test get_invalid_containers
        invalid_only = mapping.get_invalid_containers()
        assert "invalid" in invalid_only
        assert "valid" not in invalid_only
        assert "number" not in invalid_only

        # Test is_container_valid
        assert mapping.is_container_valid("valid")
        assert not mapping.is_container_valid("invalid")
        assert mapping.is_container_valid("number")

        # Test KeyError for non-existent key
        with pytest.raises(KeyError):
            mapping.is_container_valid("nonexistent")

    def test_depth_limit_validation(self):
        """Test depth limit constraint validation."""
        mapping = ModelTypedMapping()
        # Manually set depth beyond limit for testing
        mapping.current_depth = mapping.MAX_DEPTH + 1

        assert not mapping.is_valid()
        errors = mapping.get_errors()
        assert any("exceeds maximum depth" in error for error in errors)

    def test_large_mapping_validation(self):
        """Test large mapping size constraint."""
        mapping = ModelTypedMapping()

        # This would normally be prevented by from_python_dict, but test validation
        # Add many entries to test size limit
        for i in range(15000):
            mapping.data[f"key_{i}"] = StringContainer(value=f"value_{i}")

        assert not mapping.is_valid()
        errors = mapping.get_errors()
        assert any("exceeds maximum size" in error for error in errors)


class TestProtocolValidatableEdgeCases:
    """Test edge cases and error conditions."""

    def test_validation_exception_handling(self):
        """Test that validation methods handle exceptions gracefully."""
        container = StringContainer(value="test")

        # Mock JSON dumps to raise an exception during validation
        import json

        original_dumps = json.dumps

        def failing_dumps(obj, *args, **kwargs):
            if obj == "test":
                raise TypeError("Simulated JSON error")
            return original_dumps(obj, *args, **kwargs)

        json.dumps = failing_dumps
        try:
            # Should return False on exception, not raise
            assert not container.is_valid()

            # get_errors should capture the exception
            errors = container.get_errors()
            assert len(errors) > 0
            assert any("not JSON serializable" in error for error in errors)
        finally:
            json.dumps = original_dumps

    def test_protocol_runtime_checking(self):
        """Test runtime protocol checking works correctly."""
        containers = [
            StringContainer(value="test"),
            IntContainer(value=42),
            FloatContainer(value=3.14),
            BoolContainer(value=True),
            ListContainer(value=[1, 2, 3]),
            DictContainer(value={"key": "value"}),
            ModelTypedMapping(),
        ]

        for container in containers:
            # Runtime protocol check should work
            assert isinstance(container, ProtocolValidatable)

            # Methods should be callable
            result = container.is_valid()
            assert isinstance(result, bool)

            errors = container.get_errors()
            assert isinstance(errors, list)
            assert all(isinstance(error, str) for error in errors)


if __name__ == "__main__":
    # Run tests if script is executed directly
    pytest.main([__file__, "-v"])
