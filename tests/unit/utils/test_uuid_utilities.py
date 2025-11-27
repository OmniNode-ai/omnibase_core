"""Tests for UUID utilities."""

from uuid import UUID

from omnibase_core.utils.util_uuid_utilities import uuid_from_string


class TestUuidUtilities:
    """Test UUID utility functions."""

    def test_uuid_from_string_basic(self):
        """Test basic UUID generation from string."""
        input_string = "test_string"
        result = uuid_from_string(input_string)

        assert isinstance(result, UUID)
        assert str(result) != input_string  # Should be a UUID, not the original string

    def test_uuid_from_string_deterministic(self):
        """Test that same input produces same UUID."""
        input_string = "deterministic_test"
        result1 = uuid_from_string(input_string)
        result2 = uuid_from_string(input_string)

        assert result1 == result2

    def test_uuid_from_string_different_inputs(self):
        """Test that different inputs produce different UUIDs."""
        result1 = uuid_from_string("input1")
        result2 = uuid_from_string("input2")

        assert result1 != result2

    def test_uuid_from_string_with_namespace(self):
        """Test UUID generation with custom namespace."""
        input_string = "test"
        namespace = "custom_namespace"
        result = uuid_from_string(input_string, namespace)

        assert isinstance(result, UUID)

        # Different namespace should produce different UUID
        result_default = uuid_from_string(input_string)
        assert result != result_default

    def test_uuid_from_string_namespace_consistency(self):
        """Test that same namespace produces consistent results."""
        input_string = "test"
        namespace = "consistent_namespace"

        result1 = uuid_from_string(input_string, namespace)
        result2 = uuid_from_string(input_string, namespace)

        assert result1 == result2

    def test_uuid_from_string_unicode(self):
        """Test UUID generation with Unicode characters."""
        input_string = "测试字符串"
        result = uuid_from_string(input_string)

        assert isinstance(result, UUID)

    def test_uuid_from_string_special_characters(self):
        """Test UUID generation with special characters."""
        input_string = "test@#$%^&*()_+-=[]{}|;':\",./<>?"
        result = uuid_from_string(input_string)

        assert isinstance(result, UUID)

    def test_uuid_from_string_empty_string(self):
        """Test UUID generation with empty string."""
        result = uuid_from_string("")

        assert isinstance(result, UUID)

    def test_uuid_from_string_long_string(self):
        """Test UUID generation with long string."""
        long_string = "a" * 1000
        result = uuid_from_string(long_string)

        assert isinstance(result, UUID)

    def test_uuid_from_string_none_input(self):
        """Test UUID generation with None input."""
        result = uuid_from_string(None)
        assert isinstance(result, UUID)

    def test_uuid_from_string_format(self):
        """Test that generated UUID follows proper format."""
        result = uuid_from_string("format_test")
        uuid_str = str(result)

        # UUID should be in format: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
        parts = uuid_str.split("-")
        assert len(parts) == 5
        assert len(parts[0]) == 8
        assert len(parts[1]) == 4
        assert len(parts[2]) == 4
        assert len(parts[3]) == 4
        assert len(parts[4]) == 12

    def test_uuid_from_string_hex_characters(self):
        """Test that UUID contains only valid hex characters."""
        result = uuid_from_string("hex_test")
        uuid_str = str(result).replace("-", "")

        # Should only contain hex characters
        for char in uuid_str:
            assert char in "0123456789abcdef"

    def test_uuid_from_string_case_sensitivity(self):
        """Test that UUID generation is case sensitive."""
        result_lower = uuid_from_string("test")
        result_upper = uuid_from_string("TEST")

        assert result_lower != result_upper

    def test_uuid_from_string_whitespace(self):
        """Test UUID generation with whitespace."""
        result_spaces = uuid_from_string("  test  ")
        result_no_spaces = uuid_from_string("test")

        # Should be different due to whitespace
        assert result_spaces != result_no_spaces

    def test_uuid_from_string_multiple_calls(self):
        """Test multiple calls with same parameters."""
        input_string = "multiple_calls"
        namespace = "test_namespace"

        results = [uuid_from_string(input_string, namespace) for _ in range(10)]

        # All results should be identical
        for result in results[1:]:
            assert result == results[0]

    def test_uuid_from_string_different_namespaces(self):
        """Test that different namespaces produce different UUIDs."""
        input_string = "same_input"
        result1 = uuid_from_string(input_string, "namespace1")
        result2 = uuid_from_string(input_string, "namespace2")

        assert result1 != result2

    def test_uuid_from_string_namespace_with_special_chars(self):
        """Test UUID generation with namespace containing special characters."""
        input_string = "test"
        namespace = "namespace@#$%"
        result = uuid_from_string(input_string, namespace)

        assert isinstance(result, UUID)

    def test_uuid_from_string_very_long_namespace(self):
        """Test UUID generation with very long namespace."""
        input_string = "test"
        namespace = "a" * 1000
        result = uuid_from_string(input_string, namespace)

        assert isinstance(result, UUID)
