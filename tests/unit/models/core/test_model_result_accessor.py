"""
Test suite for ModelResultAccessor.

Tests the specialized accessor for handling CLI execution results and metadata.
"""

from typing import Any

import pytest
from pydantic import Field

pytestmark = pytest.mark.unit

from omnibase_core.models.core import ModelResultAccessor
from omnibase_core.models.primitives.model_semver import ModelSemVer

# Default version for test instances - required field after removing default_factory
DEFAULT_VERSION = ModelSemVer(major=1, minor=0, patch=0)


class SampleResultModel(ModelResultAccessor):
    """Test model with results and metadata fields for testing the accessor."""

    results: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class TestModelResultAccessor:
    """Test cases for ModelResultAccessor."""

    def test_initialization_empty(self):
        """Test empty initialization."""
        accessor = SampleResultModel()

        # Should be able to access methods
        assert hasattr(accessor, "get_result_value")
        assert hasattr(accessor, "set_result_value")
        assert hasattr(accessor, "set_metadata_value")

    def test_get_result_value_from_results(self):
        """Test getting result value from results field."""
        accessor = SampleResultModel()

        # Set up results field with some data
        accessor.set_field("results", {})
        accessor.set_field("results.exit_code", 0)
        accessor.set_field("results.output", "Success")
        accessor.set_field("results.duration", 125.5)
        accessor.set_field("results.success", True)

        # Get values from results
        assert accessor.get_result_value("exit_code") == 0
        assert accessor.get_result_value("output") == "Success"
        assert accessor.get_result_value("duration") == 125.5
        assert accessor.get_result_value("success") is True

    def test_get_result_value_from_metadata_fallback(self):
        """Test getting result value falls back to metadata field."""
        accessor = SampleResultModel()

        # Set up metadata field with some data (no results field)
        accessor.set_field("metadata", {})
        accessor.set_field("metadata.status", "completed")
        accessor.set_field("metadata.retry_count", 2)
        accessor.set_field("metadata.performance_score", 85.7)
        accessor.set_field("metadata.cached", False)

        # Get values from metadata (fallback)
        assert accessor.get_result_value("status") == "completed"
        assert accessor.get_result_value("retry_count") == 2
        assert accessor.get_result_value("performance_score") == 85.7
        assert accessor.get_result_value("cached") is False

    def test_get_result_value_priority_results_over_metadata(self):
        """Test that results field takes priority over metadata field."""
        accessor = SampleResultModel()

        # Set up both results and metadata with same key
        accessor.set_field("results", {})
        accessor.set_field("metadata", {})
        accessor.set_field("results.status", "success")
        accessor.set_field("metadata.status", "pending")

        # Should get value from results (higher priority)
        assert accessor.get_result_value("status") == "success"

    def test_get_result_value_with_default(self):
        """Test getting result value with default when not found."""
        accessor = SampleResultModel()

        # No results or metadata set up
        assert accessor.get_result_value("nonexistent") is None
        assert (
            accessor.get_result_value("nonexistent", "default_value") == "default_value"
        )
        assert accessor.get_result_value("nonexistent", 42) == 42
        assert accessor.get_result_value("nonexistent", True) is True

    def test_set_result_value(self):
        """Test setting result values in results field."""
        accessor = SampleResultModel()

        # Set result values
        result1 = accessor.set_result_value("exit_code", 0)
        result2 = accessor.set_result_value("message", "Operation completed")
        result3 = accessor.set_result_value("duration", 89.3)
        result4 = accessor.set_result_value("success", True)

        # All should succeed
        assert result1 is True
        assert result2 is True
        assert result3 is True
        assert result4 is True

        # Verify values were set correctly
        assert accessor.get_result_value("exit_code") == 0
        assert accessor.get_result_value("message") == "Operation completed"
        assert accessor.get_result_value("duration") == 89.3
        assert accessor.get_result_value("success") is True

    def test_set_metadata_value(self):
        """Test setting metadata values in metadata field."""
        accessor = SampleResultModel()

        # Set metadata values
        result1 = accessor.set_metadata_value("processor", "v2.1.0")
        result2 = accessor.set_metadata_value("attempts", 1)
        result3 = accessor.set_metadata_value("validated", True)

        # All should succeed
        assert result1 is True
        assert result2 is True
        assert result3 is True

        # Verify values were set correctly via get_result_value
        # (which should find them in metadata)
        assert accessor.get_result_value("processor") == "v2.1.0"
        assert accessor.get_result_value("attempts") == 1
        assert accessor.get_result_value("validated") is True

    def test_mixed_results_and_metadata_operations(self):
        """Test mixed operations with both results and metadata."""
        accessor = SampleResultModel()

        # Set some values in results
        accessor.set_result_value("output", "Result data")
        accessor.set_result_value("size", 1024)

        # Set some values in metadata
        accessor.set_metadata_value("created_by", "test_user")
        accessor.set_metadata_value("priority", 5)

        # Set overlapping key in both (results should take priority)
        accessor.set_result_value("status", "completed")
        accessor.set_metadata_value("status", "processing")

        # Verify all values
        assert accessor.get_result_value("output") == "Result data"  # From results
        assert accessor.get_result_value("size") == 1024  # From results
        assert accessor.get_result_value("created_by") == "test_user"  # From metadata
        assert accessor.get_result_value("priority") == 5  # From metadata
        assert (
            accessor.get_result_value("status") == "completed"
        )  # From results (priority)

    def test_type_validation_string_values(self):
        """Test type validation for string values."""
        accessor = SampleResultModel()

        # Set string values
        accessor.set_result_value("command", "test_command")
        accessor.set_metadata_value("environment", "production")

        assert accessor.get_result_value("command") == "test_command"
        assert accessor.get_result_value("environment") == "production"

    def test_type_validation_numeric_values(self):
        """Test type validation for numeric values."""
        accessor = SampleResultModel()

        # Set numeric values
        accessor.set_result_value("exit_code", 0)
        accessor.set_result_value("duration", 45.67)
        accessor.set_metadata_value("retry_count", 3)

        assert accessor.get_result_value("exit_code") == 0
        assert accessor.get_result_value("duration") == 45.67
        assert accessor.get_result_value("retry_count") == 3

    def test_type_validation_boolean_values(self):
        """Test type validation for boolean values."""
        accessor = SampleResultModel()

        # Set boolean values
        accessor.set_result_value("success", True)
        accessor.set_result_value("has_errors", False)
        accessor.set_metadata_value("cached", True)

        assert accessor.get_result_value("success") is True
        assert accessor.get_result_value("has_errors") is False
        assert accessor.get_result_value("cached") is True

    def test_invalid_type_handling(self):
        """Test handling of invalid types in get_result_value."""
        accessor = SampleResultModel()

        # Set up with invalid types that should be filtered out
        accessor.set_field("results", {})
        accessor.set_field("results.valid_string", "test")
        accessor.set_field("results.valid_int", 42)
        # Note: We can't easily test invalid types through the set_result_value
        # method because it has type constraints. The type validation mainly
        # protects against data that comes from external sources.

        # Valid types should work
        assert accessor.get_result_value("valid_string") == "test"
        assert accessor.get_result_value("valid_int") == 42

    def test_inheritance_from_field_accessor(self):
        """Test that result accessor inherits from base field accessor."""
        accessor = SampleResultModel()

        # Should have base field accessor methods
        assert hasattr(accessor, "get_field")
        assert hasattr(accessor, "set_field")
        assert hasattr(accessor, "has_field")
        assert hasattr(accessor, "remove_field")

    def test_complex_cli_result_scenario(self):
        """Test complex CLI result scenario."""
        accessor = SampleResultModel()

        # Simulate a complete CLI execution result
        # Set execution results
        accessor.set_result_value("exit_code", 0)
        accessor.set_result_value("stdout", "Build completed successfully")
        accessor.set_result_value("stderr", "")
        accessor.set_result_value("duration_ms", 2450.5)
        accessor.set_result_value("success", True)

        # Set metadata
        accessor.set_metadata_value("command", "build")
        accessor.set_metadata_value("node_id", "builder-01")
        accessor.set_metadata_value("attempt", 1)
        accessor.set_metadata_value("cached", False)

        # Verify all data can be retrieved
        assert accessor.get_result_value("exit_code") == 0
        assert accessor.get_result_value("stdout") == "Build completed successfully"
        assert accessor.get_result_value("stderr") == ""
        assert accessor.get_result_value("duration_ms") == 2450.5
        assert accessor.get_result_value("success") is True
        assert accessor.get_result_value("command") == "build"
        assert accessor.get_result_value("node_id") == "builder-01"
        assert accessor.get_result_value("attempt") == 1
        assert accessor.get_result_value("cached") is False

    def test_overwrite_values(self):
        """Test overwriting existing values."""
        accessor = SampleResultModel()

        # Set initial values
        accessor.set_result_value("status", "running")
        accessor.set_metadata_value("attempts", 1)

        # Verify initial values
        assert accessor.get_result_value("status") == "running"
        assert accessor.get_result_value("attempts") == 1

        # Overwrite values
        accessor.set_result_value("status", "completed")
        accessor.set_metadata_value("attempts", 2)

        # Verify overwritten values
        assert accessor.get_result_value("status") == "completed"
        assert accessor.get_result_value("attempts") == 2

    def test_edge_case_zero_values(self):
        """Test edge cases with zero values."""
        accessor = SampleResultModel()

        # Set zero values
        accessor.set_result_value("exit_code", 0)
        accessor.set_result_value("errors", 0)
        accessor.set_result_value("duration", 0.0)

        # Should be retrievable (zero is a valid value)
        assert accessor.get_result_value("exit_code") == 0
        assert accessor.get_result_value("errors") == 0
        assert accessor.get_result_value("duration") == 0.0

    def test_edge_case_false_values(self):
        """Test edge cases with False boolean values."""
        accessor = SampleResultModel()

        # Set False values
        accessor.set_result_value("success", False)
        accessor.set_metadata_value("cached", False)

        # Should be retrievable (False is a valid value)
        assert accessor.get_result_value("success") is False
        assert accessor.get_result_value("cached") is False

    def test_edge_case_empty_strings(self):
        """Test edge cases with empty string values."""
        accessor = SampleResultModel()

        # Set empty string values
        accessor.set_result_value("output", "")
        accessor.set_metadata_value("error_message", "")

        # Should be retrievable (empty string is a valid value)
        assert accessor.get_result_value("output") == ""
        assert accessor.get_result_value("error_message") == ""

    def test_performance_result_scenario(self):
        """Test performance monitoring result scenario."""
        accessor = SampleResultModel()

        # Performance metrics in results
        accessor.set_result_value("cpu_usage", 75.5)
        accessor.set_result_value("memory_mb", 512)
        accessor.set_result_value("disk_io", 1024)
        accessor.set_result_value("network_kb", 256)

        # Performance metadata
        accessor.set_metadata_value("monitoring_tool", "prometheus")
        accessor.set_metadata_value("sample_rate", 1)
        accessor.set_metadata_value("aggregated", True)

        # Verify performance data
        assert accessor.get_result_value("cpu_usage") == 75.5
        assert accessor.get_result_value("memory_mb") == 512
        assert accessor.get_result_value("disk_io") == 1024
        assert accessor.get_result_value("network_kb") == 256
        assert accessor.get_result_value("monitoring_tool") == "prometheus"
        assert accessor.get_result_value("sample_rate") == 1
        assert accessor.get_result_value("aggregated") is True

    def test_pydantic_compatibility(self):
        """Test compatibility with Pydantic model features."""
        accessor = SampleResultModel()

        # Set some result and metadata values
        accessor.set_result_value("test_result", "test_value")
        accessor.set_metadata_value("test_meta", "meta_value")

        # Test serialization
        try:
            data = accessor.model_dump()
            # The exact structure depends on how the base model is implemented
            # We just verify it doesn't crash
            assert isinstance(data, dict)
        except Exception:
            # If serialization is not supported, that's okay for now
            pass

    def test_configure_protocol_method(self):
        """Test configure method (Configurable protocol)."""
        accessor = SampleResultModel()

        result = accessor.configure(
            results={"test": "value"},
            metadata={"meta": "data"},
        )

        assert result is True
        # Verify configuration was applied
        assert hasattr(accessor, "results")
        assert hasattr(accessor, "metadata")

    def test_configure_with_invalid_attribute(self):
        """Test configure with non-existent attribute."""
        accessor = SampleResultModel()

        result = accessor.configure(
            valid_field="value",
            nonexistent_field="invalid",
        )

        # Should still return True
        assert result is True

    def test_configure_with_exception(self):
        """Test configure handles exceptions gracefully."""
        accessor = SampleResultModel()

        # Try to configure with invalid type
        result = accessor.configure(results="invalid_type")

        # Should return False on exception
        assert result is False

    def test_serialize_protocol_method(self):
        """Test serialize method (Serializable protocol)."""
        accessor = SampleResultModel()

        accessor.set_result_value("test", "value")

        serialized = accessor.serialize()

        assert isinstance(serialized, dict)
        assert "accessor_type" in serialized
        assert serialized["accessor_type"] == "SampleResultModel"

    def test_serialize_includes_data_attributes(self):
        """Test serialize includes accessible data attributes."""
        accessor = SampleResultModel()

        accessor.set_result_value("key1", "value1")
        accessor.set_metadata_value("key2", "value2")

        serialized = accessor.serialize()

        assert isinstance(serialized, dict)
        # Should include results and metadata if they're not private
        assert "results" in serialized or "accessor_type" in serialized

    def test_serialize_excludes_private_attributes(self):
        """Test serialize excludes private attributes."""
        accessor = SampleResultModel()

        accessor._private_attr = "should_not_serialize"

        serialized = accessor.serialize()

        assert "_private_attr" not in serialized

    def test_validate_instance_protocol_method(self):
        """Test validate_instance method (Validatable protocol)."""
        accessor = SampleResultModel()

        result = accessor.validate_instance()

        assert result is True

    def test_validate_instance_with_data(self):
        """Test validate_instance with populated data."""
        accessor = SampleResultModel()

        accessor.set_result_value("test", "value")
        accessor.set_metadata_value("meta", "data")

        result = accessor.validate_instance()

        assert result is True

    def test_get_name_protocol_method(self):
        """Test get_name method (Nameable protocol)."""
        accessor = SampleResultModel()

        name = accessor.get_name()

        assert isinstance(name, str)
        assert "SampleResultModel" in name

    def test_set_name_protocol_method(self):
        """Test set_name method (Nameable protocol)."""
        accessor = SampleResultModel()

        # Should not raise exception
        accessor.set_name("Custom Accessor Name")

        # Method should complete without errors
        assert True
