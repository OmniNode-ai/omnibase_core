from enum import Enum

import pytest

from omnibase_core.enums.enum_file_type import EnumFileType


class TestEnumFileType:
    def test_enum_values(self):
        """Test that all enum values are defined correctly."""
        assert EnumFileType.PYTHON == "python"
        assert EnumFileType.YAML == "yaml"
        assert EnumFileType.MARKDOWN == "markdown"
        assert EnumFileType.JSON == "json"
        assert EnumFileType.IGNORE == "ignore"
        assert EnumFileType.UNKNOWN == "unknown"

    def test_enum_inheritance(self):
        """Test that enum inherits from str and Enum."""
        assert issubclass(EnumFileType, str)
        assert issubclass(EnumFileType, Enum)

    def test_enum_string_behavior(self):
        """Test string behavior of enum values."""
        file_type = EnumFileType.PYTHON
        assert isinstance(file_type, str)
        assert file_type == "python"
        assert len(file_type) == 6
        assert file_type.startswith("pyth")

    def test_enum_iteration(self):
        """Test that all enum values can be iterated."""
        values = list(EnumFileType)
        assert len(values) == 6
        assert EnumFileType.PYTHON in values
        assert EnumFileType.UNKNOWN in values

    def test_enum_membership(self):
        """Test membership testing."""
        assert EnumFileType.YAML in EnumFileType
        assert "yaml" in [e.value for e in EnumFileType]

    def test_enum_comparison(self):
        """Test enum comparison."""
        file_type1 = EnumFileType.JSON
        file_type2 = EnumFileType.JSON
        file_type3 = EnumFileType.YAML

        assert file_type1 == file_type2
        assert file_type1 != file_type3
        assert file_type1 == "json"

    def test_enum_serialization(self):
        """Test enum serialization."""
        file_type = EnumFileType.MARKDOWN
        serialized = file_type.value
        assert serialized == "markdown"
        import json

        json_str = json.dumps(file_type)
        assert json_str == '"markdown"'

    def test_enum_deserialization(self):
        """Test enum deserialization."""
        file_type = EnumFileType("python")
        assert file_type == EnumFileType.PYTHON

    def test_enum_invalid_value(self):
        """Test that invalid values raise ValueError."""
        with pytest.raises(ValueError):
            EnumFileType("invalid_type")

    def test_enum_all_values(self):
        """Test that all expected values are present."""
        expected_values = {"python", "yaml", "markdown", "json", "ignore", "unknown"}
        actual_values = {e.value for e in EnumFileType}
        assert actual_values == expected_values

    def test_enum_str_method(self):
        """Test __str__ method."""
        file_type = EnumFileType.YAML
        assert str(file_type) == "yaml"
        assert str(file_type) == file_type.value

    def test_enum_file_categories(self):
        """Test logical grouping of file types."""
        # Code files
        code_files = {EnumFileType.PYTHON}

        # Configuration files
        config_files = {EnumFileType.YAML, EnumFileType.JSON}

        # Documentation files
        doc_files = {EnumFileType.MARKDOWN}

        # System files
        system_files = {EnumFileType.IGNORE}

        # Unknown files
        unknown_files = {EnumFileType.UNKNOWN}

        # Test that all types are covered
        all_categories = (
            code_files | config_files | doc_files | system_files | unknown_files
        )
        assert all_categories == set(EnumFileType)

    def test_enum_common_extensions(self):
        """Test that enum values correspond to common file extensions."""
        extension_mapping = {
            EnumFileType.PYTHON: [".py", ".pyi"],
            EnumFileType.YAML: [".yaml", ".yml"],
            EnumFileType.MARKDOWN: [".md", ".markdown"],
            EnumFileType.JSON: [".json"],
            EnumFileType.IGNORE: [".gitignore", ".ignore"],
        }

        # Test that we can map extensions to file types
        for file_type, extensions in extension_mapping.items():
            # Check that the file type value matches one of the extension types
            extension_types = [ext.lstrip(".") for ext in extensions]
            # For python, check if it matches 'py' or 'python'
            if file_type == EnumFileType.PYTHON:
                assert (
                    file_type.value == "python"
                )  # The enum value is "python", not "py"
            else:
                assert file_type.value in extension_types

    def test_enum_workflow_usage(self):
        """Test typical workflow usage patterns."""
        # Common development workflow file types
        dev_files = {EnumFileType.PYTHON, EnumFileType.YAML, EnumFileType.MARKDOWN}

        # Configuration workflow file types
        config_files = {EnumFileType.YAML, EnumFileType.JSON}

        # Documentation workflow file types
        doc_files = {EnumFileType.MARKDOWN}

        # All should be valid enum values
        for file_type in dev_files | config_files | doc_files:
            assert file_type in EnumFileType
