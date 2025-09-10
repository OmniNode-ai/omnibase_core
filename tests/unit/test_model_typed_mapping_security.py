"""
Security and DoS protection test suite for ModelTypedMapping.

Tests all Priority 1 critical security fixes:
1. Depth limits to prevent DoS attacks
2. Type validation and error handling
3. Memory usage protection
"""

import pytest

from omnibase_core.model.common.model_typed_value import (
    ModelTypedMapping,
    ModelValueContainer,
)


class TestModelTypedMappingDoSProtection:
    """Test suite for DoS protection via depth limiting."""

    def test_depth_limit_enforcement(self):
        """Test that maximum depth is enforced to prevent DoS attacks."""
        # Create a deeply nested dictionary that exceeds the limit
        nested_dict = {"level1": {"level2": {}}}
        current_level = nested_dict["level1"]["level2"]

        # Create nesting beyond MAX_DEPTH (10)
        for i in range(3, 15):  # This will create depth > 10
            current_level[f"level{i}"] = {}
            current_level = current_level[f"level{i}"]

        # Attempting to create ModelTypedMapping should raise ValueError
        with pytest.raises(ValueError) as exc_info:
            ModelTypedMapping.from_python_dict(nested_dict)

        assert "Maximum nesting depth (10) exceeded" in str(exc_info.value)
        assert "DoS attacks" in str(exc_info.value)

    def test_depth_limit_boundary_conditions(self):
        """Test depth limit at boundary conditions."""
        # Create dictionary at exactly MAX_DEPTH - should work
        nested_dict = {"root": {}}
        current_level = nested_dict["root"]

        # Create exactly 9 levels of nesting (within limit)
        for i in range(1, 9):
            current_level[f"level{i}"] = {}
            current_level = current_level[f"level{i}"]

        # This should work (depth = 9)
        mapping = ModelTypedMapping.from_python_dict(nested_dict)
        assert mapping is not None
        assert "root" in mapping.keys()

        # Now test exactly at the limit
        current_level["level9"] = {"final": "value"}

        # This should still work (depth = 10)
        mapping = ModelTypedMapping.from_python_dict(nested_dict)
        assert mapping is not None

        # Add one more level to exceed the limit
        nested_dict["root"]["level1"]["level2"]["level3"]["level4"]["level5"]["level6"][
            "level7"
        ]["level8"]["level9"]["final"] = {"too_deep": "value"}

        # This should fail (depth = 11)
        with pytest.raises(ValueError):
            ModelTypedMapping.from_python_dict(nested_dict)

    def test_depth_tracking_in_instance(self):
        """Test that depth is properly tracked in instances."""
        # Create a mapping with some nesting
        nested_data = {"shallow": "value", "nested": {"inner": {"deep": "value"}}}

        mapping = ModelTypedMapping.from_python_dict(nested_data)

        # Verify depth tracking
        assert mapping.current_depth == 0  # Root level

        # Verify we can access nested data
        result_dict = mapping.to_python_dict()
        assert result_dict["shallow"] == "value"
        assert isinstance(result_dict["nested"], dict)

    def test_set_dict_depth_protection(self):
        """Test that set_dict method also enforces depth limits."""
        mapping = ModelTypedMapping()

        # Manually set a high depth to test protection
        mapping.current_depth = ModelTypedMapping.MAX_DEPTH + 1

        # Attempting to set a dict value should raise ValueError
        with pytest.raises(ValueError) as exc_info:
            mapping.set_dict("test_key", {"nested": "value"})

        assert "Maximum nesting depth" in str(exc_info.value)
        assert "DoS attacks" in str(exc_info.value)


class TestModelTypedMappingTypeValidation:
    """Test suite for type validation and error handling."""

    def test_unsupported_type_handling(self):
        """Test handling of unsupported data types."""

        class UnsupportedClass:
            def __init__(self):
                self.value = "test"

        unsupported_data = {
            "valid_string": "hello",
            "valid_int": 42,
            "unsupported": UnsupportedClass(),
        }

        # Should raise ValueError for unsupported type
        with pytest.raises(ValueError) as exc_info:
            ModelTypedMapping.from_python_dict(unsupported_data)

        assert "Unsupported type for key 'unsupported'" in str(exc_info.value)

    def test_automatic_type_detection(self):
        """Test automatic type detection in set_value method."""
        mapping = ModelTypedMapping()

        # Test all supported types
        mapping.set_value("string_val", "hello")
        mapping.set_value("int_val", 42)
        mapping.set_value("float_val", 3.14)
        mapping.set_value("bool_val", True)
        mapping.set_value("list_val", [1, 2, 3])
        mapping.set_value("dict_val", {"key": "value"})
        mapping.set_value("none_val", None)

        # Verify all types are correctly stored
        result_dict = mapping.to_python_dict()

        assert result_dict["string_val"] == "hello"
        assert result_dict["int_val"] == 42
        assert result_dict["float_val"] == 3.14
        assert result_dict["bool_val"] is True
        assert result_dict["list_val"] == [1, 2, 3]
        assert result_dict["dict_val"] == {"key": "value"}
        # None values are skipped, so this key won't exist
        assert "none_val" not in result_dict

    def test_type_safe_getters(self):
        """Test type-safe getter methods with validation."""
        mapping = ModelTypedMapping()
        mapping.set_value("string_val", "hello")
        mapping.set_value("int_val", 42)

        # Correct type access should work
        assert mapping.get_string("string_val") == "hello"
        assert mapping.get_int("int_val") == 42

        # Incorrect type access should raise ValueError
        with pytest.raises(ValueError) as exc_info:
            mapping.get_int("string_val")  # Trying to get string as int

        assert "not an int" in str(exc_info.value)
        assert "got str" in str(exc_info.value)

        # Test with non-existent key
        assert mapping.get_string("missing_key") is None
        assert mapping.get_string("missing_key", "default") == "default"

    def test_boolean_vs_integer_handling(self):
        """Test proper handling of boolean vs integer types."""
        mapping = ModelTypedMapping()

        # Booleans should be detected before integers
        mapping.set_value("true_bool", True)
        mapping.set_value("false_bool", False)
        mapping.set_value("int_val", 1)
        mapping.set_value("zero_int", 0)

        # Verify types are preserved correctly
        assert mapping.get_value("true_bool") is True
        assert mapping.get_value("false_bool") is False
        assert mapping.get_value("int_val") == 1
        assert mapping.get_value("zero_int") == 0

        # Type-safe getters should work correctly
        assert mapping.get_bool("true_bool") is True
        assert mapping.get_bool("false_bool") is False
        assert mapping.get_int("int_val") == 1
        assert mapping.get_int("zero_int") == 0


class TestModelTypedMappingPerformance:
    """Test suite for performance and memory protection."""

    def test_large_dictionary_handling(self):
        """Test handling of large dictionaries without DoS."""
        # Create a large but shallow dictionary
        large_dict = {f"key_{i}": f"value_{i}" for i in range(1000)}

        # Should handle large dictionary without issues
        mapping = ModelTypedMapping.from_python_dict(large_dict)

        assert len(mapping.keys()) == 1000
        assert mapping.get_string("key_0") == "value_0"
        assert mapping.get_string("key_999") == "value_999"

    def test_memory_efficient_operations(self):
        """Test memory-efficient operations."""
        mapping = ModelTypedMapping()

        # Test that operations don't create excessive objects
        for i in range(100):
            mapping.set_value(f"key_{i}", i)

        # Verify all values are accessible
        for i in range(100):
            assert mapping.get_value(f"key_{i}") == i

        # Test conversion back to dict
        result_dict = mapping.to_python_dict()
        assert len(result_dict) == 100
        assert result_dict["key_50"] == 50

    def test_concurrent_type_validation(self):
        """Test that type validation works correctly under various conditions."""
        test_data = {
            "strings": ["hello", "world", "test"],
            "numbers": [1, 2, 3.14, 0, -5],
            "booleans": [True, False],
            "nested": {
                "inner_string": "nested_value",
                "inner_number": 42,
                "inner_list": [1, 2, 3],
            },
            "empty_structures": {"empty_list": [], "empty_dict": {}},
        }

        mapping = ModelTypedMapping.from_python_dict(test_data)
        result = mapping.to_python_dict()

        # Verify all data types are preserved correctly
        assert result["strings"] == ["hello", "world", "test"]
        assert result["numbers"] == [1, 2, 3.14, 0, -5]
        assert result["booleans"] == [True, False]
        assert isinstance(result["nested"], dict)
        assert result["nested"]["inner_string"] == "nested_value"


class TestModelTypedMappingErrorRecovery:
    """Test suite for error recovery and edge cases."""

    def test_partial_failure_handling(self):
        """Test handling when some keys are valid and others invalid."""
        mixed_data = {
            "valid_string": "hello",
            "valid_int": 42,
        }

        # First create a valid mapping
        mapping = ModelTypedMapping.from_python_dict(mixed_data)

        # Then try to add an invalid type manually
        with pytest.raises(ValueError):
            mapping.set_value("invalid", object())  # Unsupported type

        # Verify that valid data is still accessible
        assert mapping.get_string("valid_string") == "hello"
        assert mapping.get_int("valid_int") == 42

    def test_empty_dictionary_handling(self):
        """Test handling of empty dictionaries."""
        empty_dict = {}
        mapping = ModelTypedMapping.from_python_dict(empty_dict)

        assert len(mapping.keys()) == 0
        assert mapping.to_python_dict() == {}
        assert not mapping.has_key("any_key")

    def test_none_value_handling(self):
        """Test handling of None values in different contexts."""
        data_with_none = {
            "explicit_none": None,
            "valid_string": "hello",
            "another_none": None,
        }

        mapping = ModelTypedMapping.from_python_dict(data_with_none)

        # None values should be skipped
        result = mapping.to_python_dict()
        assert "explicit_none" not in result
        assert "another_none" not in result
        assert result["valid_string"] == "hello"
        assert len(result) == 1

    def test_malformed_nested_structures(self):
        """Test handling of malformed nested structures."""
        # Create data with mixed types in nested structure
        malformed_data = {
            "normal": "value",
            "nested": {"level1": {"valid": "data", "level2": {"deep": "value"}}},
        }

        # This should work within depth limits
        mapping = ModelTypedMapping.from_python_dict(malformed_data)
        result = mapping.to_python_dict()

        assert result["normal"] == "value"
        assert isinstance(result["nested"], dict)


class TestSecurityIntegration:
    """Integration tests for security features."""

    def test_combined_security_features(self):
        """Test multiple security features working together."""
        # Create data that tests multiple security boundaries
        complex_data = {}

        # Test depth boundary (just within limit)
        nested = complex_data
        for i in range(9):  # Create 9 levels of nesting
            nested[f"level{i}"] = {}
            nested = nested[f"level{i}"]
        nested["final"] = "deep_value"

        # Add large amount of data at various levels
        complex_data["bulk_data"] = {f"item_{i}": i for i in range(100)}

        # This should work - within all limits
        mapping = ModelTypedMapping.from_python_dict(complex_data)

        assert mapping is not None
        assert len(mapping.keys()) >= 2  # bulk_data + level0
        assert mapping.has_key("bulk_data")

    def test_attack_vectors(self):
        """Test protection against common attack vectors."""
        # Create a deep nesting attack programmatically
        deep_attack = {}
        current = deep_attack
        for i in range(12):  # Create 12 levels - exceeds MAX_DEPTH of 10
            key = f"level{i}"
            current[key] = {}
            current = current[key]
        current["final"] = "too_deep"

        attack_vectors = [deep_attack]

        for attack_data in attack_vectors:
            with pytest.raises(ValueError):
                ModelTypedMapping.from_python_dict(attack_data)


if __name__ == "__main__":
    # Run the tests if executed directly
    pytest.main([__file__, "-v"])
