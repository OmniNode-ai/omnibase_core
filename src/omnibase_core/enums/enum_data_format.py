"""
Data format enumeration for specifying data format types.

Provides strongly typed data format specifications for examples,
configurations, and data processing across the ONEX architecture.
"""

from __future__ import annotations

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumDataFormat(StrValueHelper, str, Enum):
    """
    Strongly typed data formats.

    Inherits from str for JSON serialization compatibility while providing
    type safety and IDE support for data format specification.
    """

    # Common data formats
    JSON = "json"
    YAML = "yaml"
    XML = "xml"
    TEXT = "text"
    CSV = "csv"
    TSV = "tsv"

    # Binary formats
    BINARY = "binary"
    BYTES = "bytes"

    # Structured formats
    AVRO = "avro"
    PARQUET = "parquet"
    PROTOBUF = "protobuf"

    # Configuration formats
    TOML = "toml"
    INI = "ini"
    PROPERTIES = "properties"

    # Markup formats
    HTML = "html"
    MARKDOWN = "markdown"
    RST = "rst"

    # Archive formats
    ZIP = "zip"
    TAR = "tar"
    GZIP = "gzip"

    @classmethod
    def get_text_formats(cls) -> list[EnumDataFormat]:
        """Get text-based data formats."""
        return [
            cls.JSON,
            cls.YAML,
            cls.XML,
            cls.TEXT,
            cls.CSV,
            cls.TSV,
            cls.TOML,
            cls.INI,
            cls.PROPERTIES,
            cls.HTML,
            cls.MARKDOWN,
            cls.RST,
        ]

    @classmethod
    def get_binary_formats(cls) -> list[EnumDataFormat]:
        """Get binary data formats."""
        return [
            cls.BINARY,
            cls.BYTES,
            cls.AVRO,
            cls.PARQUET,
            cls.PROTOBUF,
            cls.ZIP,
            cls.TAR,
            cls.GZIP,
        ]

    @classmethod
    def get_structured_formats(cls) -> list[EnumDataFormat]:
        """Get structured data formats."""
        return [
            cls.JSON,
            cls.YAML,
            cls.XML,
            cls.AVRO,
            cls.PARQUET,
            cls.PROTOBUF,
        ]

    @classmethod
    def get_config_formats(cls) -> list[EnumDataFormat]:
        """Get configuration file formats."""
        return [
            cls.JSON,
            cls.YAML,
            cls.TOML,
            cls.INI,
            cls.PROPERTIES,
        ]

    @classmethod
    def is_text_format(cls, format_type: EnumDataFormat) -> bool:
        """Check if format is text-based."""
        return format_type in cls.get_text_formats()

    @classmethod
    def is_binary_format(cls, format_type: EnumDataFormat) -> bool:
        """Check if format is binary."""
        return format_type in cls.get_binary_formats()

    @classmethod
    def is_structured_format(cls, format_type: EnumDataFormat) -> bool:
        """Check if format is structured data."""
        return format_type in cls.get_structured_formats()

    @classmethod
    def supports_schema_validation(cls, format_type: EnumDataFormat) -> bool:
        """Check if format supports schema validation."""
        return format_type in {cls.JSON, cls.YAML, cls.XML, cls.AVRO, cls.PROTOBUF}

    def get_file_extension(self) -> str:
        """Get typical file extension for this format."""
        extension_map = {
            self.JSON: ".json",
            self.YAML: ".yaml",
            self.XML: ".xml",
            self.TEXT: ".txt",
            self.CSV: ".csv",
            self.TSV: ".tsv",
            self.BINARY: ".bin",
            self.BYTES: ".bin",
            self.AVRO: ".avro",
            self.PARQUET: ".parquet",
            self.PROTOBUF: ".proto",
            self.TOML: ".toml",
            self.INI: ".ini",
            self.PROPERTIES: ".properties",
            self.HTML: ".html",
            self.MARKDOWN: ".md",
            self.RST: ".rst",
            self.ZIP: ".zip",
            self.TAR: ".tar",
            self.GZIP: ".gz",
        }
        return extension_map.get(self, "")


# Export for use
__all__ = ["EnumDataFormat"]
