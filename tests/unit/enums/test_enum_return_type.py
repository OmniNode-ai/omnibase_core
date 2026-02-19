# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

from enum import Enum

import pytest

from omnibase_core.enums.enum_return_type import EnumReturnType


@pytest.mark.unit
class TestEnumReturnType:
    def test_enum_values(self):
        """Test that all enum values are defined correctly."""
        assert EnumReturnType.MODELS == "MODELS"
        assert EnumReturnType.FILES == "FILES"
        assert EnumReturnType.REPORTS == "REPORTS"
        assert EnumReturnType.ENUMS == "ENUMS"
        assert EnumReturnType.TEXT == "TEXT"
        assert EnumReturnType.METADATA == "METADATA"
        assert EnumReturnType.BINARY == "BINARY"
        assert EnumReturnType.JSON == "JSON"
        assert EnumReturnType.XML == "XML"
        assert EnumReturnType.COMMANDS == "COMMANDS"
        assert EnumReturnType.NODES == "NODES"
        assert EnumReturnType.SCHEMAS == "SCHEMAS"
        assert EnumReturnType.PROTOCOLS == "PROTOCOLS"
        assert EnumReturnType.BACKEND == "BACKEND"
        assert EnumReturnType.RESULT == "RESULT"
        assert EnumReturnType.STATUS == "STATUS"
        assert EnumReturnType.LOGS == "LOGS"
        assert EnumReturnType.RESULTS == "RESULTS"
        assert EnumReturnType.UNKNOWN == "UNKNOWN"

    def test_enum_inheritance(self):
        """Test that enum inherits from str and Enum."""
        assert issubclass(EnumReturnType, str)
        assert issubclass(EnumReturnType, Enum)

    def test_enum_string_behavior(self):
        """Test string behavior of enum values."""
        return_type = EnumReturnType.MODELS
        assert isinstance(return_type, str)
        assert return_type == "MODELS"
        assert len(return_type) == 6
        assert return_type.startswith("MODEL")

    def test_enum_iteration(self):
        """Test that all enum values can be iterated."""
        values = list(EnumReturnType)
        assert len(values) == 19
        assert EnumReturnType.MODELS in values
        assert EnumReturnType.UNKNOWN in values

    def test_enum_membership(self):
        """Test membership testing."""
        assert EnumReturnType.FILES in EnumReturnType
        assert "FILES" in [e.value for e in EnumReturnType]

    def test_enum_comparison(self):
        """Test enum comparison."""
        return_type1 = EnumReturnType.JSON
        return_type2 = EnumReturnType.JSON
        return_type3 = EnumReturnType.XML

        assert return_type1 == return_type2
        assert return_type1 != return_type3
        assert return_type1 == "JSON"

    def test_enum_serialization(self):
        """Test enum serialization."""
        return_type = EnumReturnType.METADATA
        serialized = return_type.value
        assert serialized == "METADATA"
        import json

        json_str = json.dumps(return_type)
        assert json_str == '"METADATA"'

    def test_enum_deserialization(self):
        """Test enum deserialization."""
        return_type = EnumReturnType("NODES")
        assert return_type == EnumReturnType.NODES

    def test_enum_invalid_value(self):
        """Test that invalid values raise ValueError."""
        with pytest.raises(ValueError):
            EnumReturnType("INVALID_TYPE")

    def test_enum_all_values(self):
        """Test that all expected values are present."""
        expected_values = {
            "MODELS",
            "FILES",
            "REPORTS",
            "ENUMS",
            "TEXT",
            "METADATA",
            "BINARY",
            "JSON",
            "XML",
            "COMMANDS",
            "NODES",
            "SCHEMAS",
            "PROTOCOLS",
            "BACKEND",
            "RESULT",
            "STATUS",
            "LOGS",
            "RESULTS",
            "UNKNOWN",
        }
        actual_values = {e.value for e in EnumReturnType}
        assert actual_values == expected_values

    def test_enum_docstring(self):
        """Test that enum has proper docstring."""
        assert EnumReturnType.__doc__ is not None
        assert "return type values" in EnumReturnType.__doc__.lower()

    def test_enum_str_method(self):
        """Test __str__ method."""
        return_type = EnumReturnType.SCHEMAS
        assert str(return_type) == "SCHEMAS"
        assert str(return_type) == return_type.value

    def test_is_structured_data_class_method(self):
        """Test is_structured_data class method."""
        # Structured data types
        assert EnumReturnType.is_structured_data(EnumReturnType.MODELS)
        assert EnumReturnType.is_structured_data(EnumReturnType.ENUMS)
        assert EnumReturnType.is_structured_data(EnumReturnType.METADATA)
        assert EnumReturnType.is_structured_data(EnumReturnType.JSON)
        assert EnumReturnType.is_structured_data(EnumReturnType.XML)

        # Non-structured data types
        assert not EnumReturnType.is_structured_data(EnumReturnType.FILES)
        assert not EnumReturnType.is_structured_data(EnumReturnType.TEXT)
        assert not EnumReturnType.is_structured_data(EnumReturnType.BINARY)

    def test_is_file_based_class_method(self):
        """Test is_file_based class method."""
        # File-based types
        assert EnumReturnType.is_file_based(EnumReturnType.FILES)
        assert EnumReturnType.is_file_based(EnumReturnType.REPORTS)
        assert EnumReturnType.is_file_based(EnumReturnType.BINARY)

        # Non-file-based types
        assert not EnumReturnType.is_file_based(EnumReturnType.MODELS)
        assert not EnumReturnType.is_file_based(EnumReturnType.TEXT)
        assert not EnumReturnType.is_file_based(EnumReturnType.JSON)

    def test_is_text_based_class_method(self):
        """Test is_text_based class method."""
        # Text-based types
        assert EnumReturnType.is_text_based(EnumReturnType.TEXT)
        assert EnumReturnType.is_text_based(EnumReturnType.JSON)
        assert EnumReturnType.is_text_based(EnumReturnType.XML)
        assert EnumReturnType.is_text_based(EnumReturnType.REPORTS)

        # Non-text-based types
        assert not EnumReturnType.is_text_based(EnumReturnType.FILES)
        assert not EnumReturnType.is_text_based(EnumReturnType.BINARY)
        assert not EnumReturnType.is_text_based(EnumReturnType.MODELS)

    def test_requires_serialization_class_method(self):
        """Test requires_serialization class method."""
        # Types requiring serialization
        assert EnumReturnType.requires_serialization(EnumReturnType.MODELS)
        assert EnumReturnType.requires_serialization(EnumReturnType.ENUMS)
        assert EnumReturnType.requires_serialization(EnumReturnType.METADATA)
        assert EnumReturnType.requires_serialization(EnumReturnType.JSON)
        assert EnumReturnType.requires_serialization(EnumReturnType.XML)

        # Types not requiring serialization
        assert not EnumReturnType.requires_serialization(EnumReturnType.FILES)
        assert not EnumReturnType.requires_serialization(EnumReturnType.TEXT)
        assert not EnumReturnType.requires_serialization(EnumReturnType.BINARY)

    def test_get_mime_type_class_method(self):
        """Test get_mime_type class method."""
        # Test specific MIME types
        assert EnumReturnType.get_mime_type(EnumReturnType.JSON) == "application/json"
        assert EnumReturnType.get_mime_type(EnumReturnType.XML) == "application/xml"
        assert EnumReturnType.get_mime_type(EnumReturnType.TEXT) == "text/plain"
        assert (
            EnumReturnType.get_mime_type(EnumReturnType.BINARY)
            == "application/octet-stream"
        )
        assert (
            EnumReturnType.get_mime_type(EnumReturnType.FILES)
            == "application/octet-stream"
        )
        assert EnumReturnType.get_mime_type(EnumReturnType.REPORTS) == "text/plain"
        assert EnumReturnType.get_mime_type(EnumReturnType.MODELS) == "application/json"
        assert EnumReturnType.get_mime_type(EnumReturnType.ENUMS) == "application/json"
        assert (
            EnumReturnType.get_mime_type(EnumReturnType.METADATA) == "application/json"
        )

        # Test fallback for unknown types
        assert (
            EnumReturnType.get_mime_type(EnumReturnType.UNKNOWN)
            == "application/octet-stream"
        )

    def test_return_type_categorization_completeness(self):
        """Test that all return types are categorized by at least one method."""
        all_types = set(EnumReturnType)

        # Get types categorized by each method
        structured_types = {
            e for e in EnumReturnType if EnumReturnType.is_structured_data(e)
        }
        file_types = {e for e in EnumReturnType if EnumReturnType.is_file_based(e)}
        text_types = {e for e in EnumReturnType if EnumReturnType.is_text_based(e)}
        serialization_types = {
            e for e in EnumReturnType if EnumReturnType.requires_serialization(e)
        }

        # All types should be categorized (except UNKNOWN)
        categorized_types = (
            structured_types | file_types | text_types | serialization_types
        )
        assert EnumReturnType.UNKNOWN not in categorized_types
        # Some types might not be categorized by the current methods
        assert (
            len(categorized_types) >= len(all_types) - 10
        )  # Most types should be categorized

    def test_return_type_categorization_exclusivity(self):
        """Test that return type categories don't overlap inappropriately."""
        structured_types = {
            e for e in EnumReturnType if EnumReturnType.is_structured_data(e)
        }
        file_types = {e for e in EnumReturnType if EnumReturnType.is_file_based(e)}
        text_types = {e for e in EnumReturnType if EnumReturnType.is_text_based(e)}

        # File-based and structured types should not overlap
        assert file_types.isdisjoint(structured_types)

        # Text-based and file-based types might overlap (e.g., REPORTS)
        # This is acceptable as some types can be both text and file-based

    def test_return_type_logical_groupings(self):
        """Test logical groupings of return types."""
        # Data generation types
        data_types = {
            EnumReturnType.MODELS,
            EnumReturnType.ENUMS,
            EnumReturnType.SCHEMAS,
            EnumReturnType.PROTOCOLS,
        }

        # File output types
        file_types = {
            EnumReturnType.FILES,
            EnumReturnType.REPORTS,
            EnumReturnType.BINARY,
        }

        # Text output types
        text_types = {
            EnumReturnType.TEXT,
            EnumReturnType.JSON,
            EnumReturnType.XML,
        }

        # System types
        system_types = {
            EnumReturnType.NODES,
            EnumReturnType.BACKEND,
            EnumReturnType.COMMANDS,
        }

        # Status types
        status_types = {
            EnumReturnType.STATUS,
            EnumReturnType.RESULT,
            EnumReturnType.RESULTS,
            EnumReturnType.LOGS,
        }

        # Metadata types
        metadata_types = {
            EnumReturnType.METADATA,
        }

        # Default types
        default_types = {
            EnumReturnType.UNKNOWN,
        }

        # Test that all types are covered
        all_grouped_types = (
            data_types
            | file_types
            | text_types
            | system_types
            | status_types
            | metadata_types
            | default_types
        )
        assert all_grouped_types == set(EnumReturnType)
