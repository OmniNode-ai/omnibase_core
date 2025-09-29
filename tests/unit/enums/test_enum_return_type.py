"""
Unit tests for EnumReturnType.

Test coverage for return type enumeration and helper methods.
"""

import pytest

from omnibase_core.enums import EnumReturnType


class TestEnumReturnType:
    """Test cases for EnumReturnType."""

    def test_enum_values(self):
        """Test core enum values are present."""
        expected_core_values = {
            "MODELS",
            "FILES",
            "REPORTS",
            "ENUMS",
            "TEXT",
            "METADATA",
            "BINARY",
            "JSON",
            "XML",
        }
        actual_values = {return_type.value for return_type in EnumReturnType}
        # Test that all expected core values are present
        assert expected_core_values.issubset(actual_values)

    def test_string_inheritance(self):
        """Test that enum inherits from str."""
        assert isinstance(EnumReturnType.JSON, str)
        assert EnumReturnType.JSON == "JSON"

    def test_is_structured_data(self):
        """Test structured data classification."""
        structured_types = {
            EnumReturnType.MODELS,
            EnumReturnType.ENUMS,
            EnumReturnType.METADATA,
            EnumReturnType.JSON,
            EnumReturnType.XML,
        }

        for return_type in EnumReturnType:
            expected = return_type in structured_types
            actual = EnumReturnType.is_structured_data(return_type)
            assert (
                actual == expected
            ), f"{return_type} structured data classification failed"

    def test_is_file_based(self):
        """Test file-based classification."""
        file_based_types = {
            EnumReturnType.FILES,
            EnumReturnType.REPORTS,
            EnumReturnType.BINARY,
        }

        for return_type in EnumReturnType:
            expected = return_type in file_based_types
            actual = EnumReturnType.is_file_based(return_type)
            assert actual == expected, f"{return_type} file-based classification failed"

    def test_is_text_based(self):
        """Test text-based classification."""
        text_based_types = {
            EnumReturnType.TEXT,
            EnumReturnType.JSON,
            EnumReturnType.XML,
            EnumReturnType.REPORTS,
        }

        for return_type in EnumReturnType:
            expected = return_type in text_based_types
            actual = EnumReturnType.is_text_based(return_type)
            assert actual == expected, f"{return_type} text-based classification failed"

    def test_requires_serialization(self):
        """Test serialization requirement classification."""
        serialization_types = {
            EnumReturnType.MODELS,
            EnumReturnType.ENUMS,
            EnumReturnType.METADATA,
            EnumReturnType.JSON,
            EnumReturnType.XML,
        }

        for return_type in EnumReturnType:
            expected = return_type in serialization_types
            actual = EnumReturnType.requires_serialization(return_type)
            assert actual == expected, f"{return_type} serialization requirement failed"

    def test_get_mime_type(self):
        """Test MIME type mapping."""
        mime_type_map = {
            EnumReturnType.JSON: "application/json",
            EnumReturnType.XML: "application/xml",
            EnumReturnType.TEXT: "text/plain",
            EnumReturnType.BINARY: "application/octet-stream",
            EnumReturnType.FILES: "application/octet-stream",
            EnumReturnType.REPORTS: "text/plain",
            EnumReturnType.MODELS: "application/json",
            EnumReturnType.ENUMS: "application/json",
            EnumReturnType.METADATA: "application/json",
        }

        for return_type, expected_mime in mime_type_map.items():
            actual_mime = EnumReturnType.get_mime_type(return_type)
            assert (
                actual_mime == expected_mime
            ), f"{return_type} MIME type mapping failed"

    def test_str_representation(self):
        """Test string representation."""
        for return_type in EnumReturnType:
            assert str(return_type) == return_type.value
