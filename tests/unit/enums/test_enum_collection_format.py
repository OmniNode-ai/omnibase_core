"""
Unit tests for EnumCollectionFormat.

Tests all aspects of the collection format enum including:
- Enum value validation
- Helper methods and class methods
- String representation
- JSON serialization compatibility
- Pydantic integration
- Format classification logic
- File extension and MIME type mapping
"""

import json

import pytest
from pydantic import BaseModel, ValidationError

from omnibase_core.enums.enum_collection_format import EnumCollectionFormat


class TestEnumCollectionFormat:
    """Test cases for EnumCollectionFormat."""

    def test_enum_values(self):
        """Test that all expected enum values are present."""
        # Structured data formats
        assert EnumCollectionFormat.JSON.value == "json"
        assert EnumCollectionFormat.YAML.value == "yaml"
        assert EnumCollectionFormat.XML.value == "xml"
        assert EnumCollectionFormat.TOML.value == "toml"

        # Tabular formats
        assert EnumCollectionFormat.CSV.value == "csv"
        assert EnumCollectionFormat.TSV.value == "tsv"
        assert EnumCollectionFormat.EXCEL.value == "excel"
        assert EnumCollectionFormat.ODS.value == "ods"

        # Text formats
        assert EnumCollectionFormat.TEXT.value == "text"
        assert EnumCollectionFormat.PLAIN.value == "plain"
        assert EnumCollectionFormat.MARKDOWN.value == "markdown"
        assert EnumCollectionFormat.HTML.value == "html"

        # Binary formats
        assert EnumCollectionFormat.BINARY.value == "binary"
        assert EnumCollectionFormat.PICKLE.value == "pickle"
        assert EnumCollectionFormat.PARQUET.value == "parquet"
        assert EnumCollectionFormat.AVRO.value == "avro"

        # Database formats
        assert EnumCollectionFormat.SQL.value == "sql"
        assert EnumCollectionFormat.SQLITE.value == "sqlite"

        # Special formats
        assert EnumCollectionFormat.CUSTOM.value == "custom"
        assert EnumCollectionFormat.AUTO.value == "auto"
        assert EnumCollectionFormat.DEFAULT.value == "default"

    def test_string_representation(self):
        """Test string representation of enum values."""
        assert str(EnumCollectionFormat.JSON) == "json"
        assert str(EnumCollectionFormat.CSV) == "csv"
        assert str(EnumCollectionFormat.MARKDOWN) == "markdown"
        assert str(EnumCollectionFormat.BINARY) == "binary"

    def test_is_structured_format(self):
        """Test is_structured_format classification method."""
        # Should be structured formats
        assert (
            EnumCollectionFormat.is_structured_format(EnumCollectionFormat.JSON) is True
        )
        assert (
            EnumCollectionFormat.is_structured_format(EnumCollectionFormat.YAML) is True
        )
        assert (
            EnumCollectionFormat.is_structured_format(EnumCollectionFormat.XML) is True
        )
        assert (
            EnumCollectionFormat.is_structured_format(EnumCollectionFormat.TOML) is True
        )

        # Should not be structured formats
        assert (
            EnumCollectionFormat.is_structured_format(EnumCollectionFormat.CSV) is False
        )
        assert (
            EnumCollectionFormat.is_structured_format(EnumCollectionFormat.TEXT)
            is False
        )
        assert (
            EnumCollectionFormat.is_structured_format(EnumCollectionFormat.BINARY)
            is False
        )

    def test_is_tabular_format(self):
        """Test is_tabular_format classification method."""
        # Should be tabular formats
        assert EnumCollectionFormat.is_tabular_format(EnumCollectionFormat.CSV) is True
        assert EnumCollectionFormat.is_tabular_format(EnumCollectionFormat.TSV) is True
        assert (
            EnumCollectionFormat.is_tabular_format(EnumCollectionFormat.EXCEL) is True
        )
        assert EnumCollectionFormat.is_tabular_format(EnumCollectionFormat.ODS) is True

        # Should not be tabular formats
        assert (
            EnumCollectionFormat.is_tabular_format(EnumCollectionFormat.JSON) is False
        )
        assert (
            EnumCollectionFormat.is_tabular_format(EnumCollectionFormat.TEXT) is False
        )
        assert (
            EnumCollectionFormat.is_tabular_format(EnumCollectionFormat.BINARY) is False
        )

    def test_is_text_format(self):
        """Test is_text_format classification method."""
        # Should be text formats
        assert EnumCollectionFormat.is_text_format(EnumCollectionFormat.TEXT) is True
        assert EnumCollectionFormat.is_text_format(EnumCollectionFormat.PLAIN) is True
        assert (
            EnumCollectionFormat.is_text_format(EnumCollectionFormat.MARKDOWN) is True
        )
        assert EnumCollectionFormat.is_text_format(EnumCollectionFormat.HTML) is True
        assert EnumCollectionFormat.is_text_format(EnumCollectionFormat.JSON) is True
        assert EnumCollectionFormat.is_text_format(EnumCollectionFormat.YAML) is True
        assert EnumCollectionFormat.is_text_format(EnumCollectionFormat.CSV) is True
        assert EnumCollectionFormat.is_text_format(EnumCollectionFormat.SQL) is True

        # Should not be text formats
        assert EnumCollectionFormat.is_text_format(EnumCollectionFormat.BINARY) is False
        assert EnumCollectionFormat.is_text_format(EnumCollectionFormat.PICKLE) is False
        assert (
            EnumCollectionFormat.is_text_format(EnumCollectionFormat.PARQUET) is False
        )

    def test_is_binary_format(self):
        """Test is_binary_format classification method."""
        # Should be binary formats
        assert (
            EnumCollectionFormat.is_binary_format(EnumCollectionFormat.BINARY) is True
        )
        assert (
            EnumCollectionFormat.is_binary_format(EnumCollectionFormat.PICKLE) is True
        )
        assert (
            EnumCollectionFormat.is_binary_format(EnumCollectionFormat.PARQUET) is True
        )
        assert EnumCollectionFormat.is_binary_format(EnumCollectionFormat.AVRO) is True
        assert (
            EnumCollectionFormat.is_binary_format(EnumCollectionFormat.SQLITE) is True
        )
        assert EnumCollectionFormat.is_binary_format(EnumCollectionFormat.EXCEL) is True
        assert EnumCollectionFormat.is_binary_format(EnumCollectionFormat.ODS) is True

        # Should not be binary formats
        assert EnumCollectionFormat.is_binary_format(EnumCollectionFormat.JSON) is False
        assert EnumCollectionFormat.is_binary_format(EnumCollectionFormat.CSV) is False
        assert EnumCollectionFormat.is_binary_format(EnumCollectionFormat.TEXT) is False

    def test_get_default_extension(self):
        """Test get_default_extension method."""
        # Test common formats
        assert (
            EnumCollectionFormat.get_default_extension(EnumCollectionFormat.JSON)
            == ".json"
        )
        assert (
            EnumCollectionFormat.get_default_extension(EnumCollectionFormat.YAML)
            == ".yaml"
        )
        assert (
            EnumCollectionFormat.get_default_extension(EnumCollectionFormat.CSV)
            == ".csv"
        )
        assert (
            EnumCollectionFormat.get_default_extension(EnumCollectionFormat.MARKDOWN)
            == ".md"
        )
        assert (
            EnumCollectionFormat.get_default_extension(EnumCollectionFormat.EXCEL)
            == ".xlsx"
        )
        assert (
            EnumCollectionFormat.get_default_extension(EnumCollectionFormat.BINARY)
            == ".bin"
        )
        assert (
            EnumCollectionFormat.get_default_extension(EnumCollectionFormat.SQL)
            == ".sql"
        )

        # Test formats without explicit mapping return .txt
        assert (
            EnumCollectionFormat.get_default_extension(EnumCollectionFormat.CUSTOM)
            == ".txt"
        )
        assert (
            EnumCollectionFormat.get_default_extension(EnumCollectionFormat.DEFAULT)
            == ".txt"
        )

    def test_get_mime_type(self):
        """Test get_mime_type method."""
        # Test common formats
        assert (
            EnumCollectionFormat.get_mime_type(EnumCollectionFormat.JSON)
            == "application/json"
        )
        assert (
            EnumCollectionFormat.get_mime_type(EnumCollectionFormat.YAML)
            == "application/x-yaml"
        )
        assert (
            EnumCollectionFormat.get_mime_type(EnumCollectionFormat.CSV) == "text/csv"
        )
        assert (
            EnumCollectionFormat.get_mime_type(EnumCollectionFormat.HTML) == "text/html"
        )
        assert (
            EnumCollectionFormat.get_mime_type(EnumCollectionFormat.MARKDOWN)
            == "text/markdown"
        )
        assert (
            EnumCollectionFormat.get_mime_type(EnumCollectionFormat.EXCEL)
            == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        # Test formats without explicit mapping return application/octet-stream
        assert (
            EnumCollectionFormat.get_mime_type(EnumCollectionFormat.CUSTOM)
            == "application/octet-stream"
        )
        assert (
            EnumCollectionFormat.get_mime_type(EnumCollectionFormat.PARQUET)
            == "application/octet-stream"
        )

    def test_enum_comparison(self):
        """Test enum comparison operations."""
        assert EnumCollectionFormat.JSON == EnumCollectionFormat.JSON
        assert EnumCollectionFormat.JSON != EnumCollectionFormat.YAML
        assert EnumCollectionFormat.JSON == "json"
        assert EnumCollectionFormat.CSV != "json"

    def test_enum_membership(self):
        """Test enum membership checks."""
        assert EnumCollectionFormat.JSON in EnumCollectionFormat
        assert EnumCollectionFormat.CSV in EnumCollectionFormat
        assert EnumCollectionFormat.BINARY in EnumCollectionFormat

    def test_enum_iteration(self):
        """Test iteration over enum values."""
        formats = list(EnumCollectionFormat)
        assert len(formats) > 20  # Should have many format types
        assert EnumCollectionFormat.JSON in formats
        assert EnumCollectionFormat.CSV in formats
        assert EnumCollectionFormat.BINARY in formats

    def test_json_serialization(self):
        """Test JSON serialization of enum values."""
        assert json.dumps(EnumCollectionFormat.JSON) == '"json"'
        assert json.dumps(EnumCollectionFormat.CSV) == '"csv"'

    def test_pydantic_model_integration(self):
        """Test Pydantic model integration with enum."""

        class ExportConfig(BaseModel):
            format: EnumCollectionFormat

        # Test valid enum value
        config = ExportConfig(format=EnumCollectionFormat.JSON)
        assert config.format == EnumCollectionFormat.JSON

        # Test valid string value
        config = ExportConfig(format="csv")
        assert config.format == EnumCollectionFormat.CSV

        # Test invalid value
        with pytest.raises(ValidationError):
            ExportConfig(format="invalid_format")

    def test_enum_uniqueness(self):
        """Test that all enum values are unique."""
        values = [fmt.value for fmt in EnumCollectionFormat]
        assert len(values) == len(set(values))


class TestEnumCollectionFormatOverlaps:
    """Test format classification overlaps."""

    def test_text_and_binary_overlap(self):
        """Test that some formats can be both text and binary (like Excel)."""
        # Excel and ODS are in tabular, binary, but not text
        assert (
            EnumCollectionFormat.is_tabular_format(EnumCollectionFormat.EXCEL) is True
        )
        assert EnumCollectionFormat.is_binary_format(EnumCollectionFormat.EXCEL) is True
        assert EnumCollectionFormat.is_text_format(EnumCollectionFormat.EXCEL) is False

    def test_structured_formats_are_text(self):
        """Test that structured formats are also text formats."""
        assert (
            EnumCollectionFormat.is_structured_format(EnumCollectionFormat.JSON) is True
        )
        assert EnumCollectionFormat.is_text_format(EnumCollectionFormat.JSON) is True

        assert (
            EnumCollectionFormat.is_structured_format(EnumCollectionFormat.YAML) is True
        )
        assert EnumCollectionFormat.is_text_format(EnumCollectionFormat.YAML) is True

    def test_tabular_csv_tsv_are_text(self):
        """Test that CSV and TSV are both tabular and text."""
        assert EnumCollectionFormat.is_tabular_format(EnumCollectionFormat.CSV) is True
        assert EnumCollectionFormat.is_text_format(EnumCollectionFormat.CSV) is True

        assert EnumCollectionFormat.is_tabular_format(EnumCollectionFormat.TSV) is True
        assert EnumCollectionFormat.is_text_format(EnumCollectionFormat.TSV) is True


class TestEnumCollectionFormatEdgeCases:
    """Test edge cases for EnumCollectionFormat."""

    def test_case_sensitivity(self):
        """Test that enum values are case-sensitive."""

        class ExportConfig(BaseModel):
            format: EnumCollectionFormat

        # Lowercase should work
        config = ExportConfig(format="json")
        assert config.format == EnumCollectionFormat.JSON

        # Uppercase should fail
        with pytest.raises(ValidationError):
            ExportConfig(format="JSON")

    def test_whitespace_handling(self):
        """Test that whitespace in values is rejected."""

        class ExportConfig(BaseModel):
            format: EnumCollectionFormat

        with pytest.raises(ValidationError):
            ExportConfig(format=" json")

        with pytest.raises(ValidationError):
            ExportConfig(format="json ")

    def test_all_formats_have_extensions(self):
        """Test that all formats can return an extension."""
        for fmt in EnumCollectionFormat:
            extension = EnumCollectionFormat.get_default_extension(fmt)
            assert isinstance(extension, str)
            assert extension.startswith(".")
            assert len(extension) > 1

    def test_all_formats_have_mime_types(self):
        """Test that all formats can return a MIME type."""
        for fmt in EnumCollectionFormat:
            mime_type = EnumCollectionFormat.get_mime_type(fmt)
            assert isinstance(mime_type, str)
            assert "/" in mime_type
