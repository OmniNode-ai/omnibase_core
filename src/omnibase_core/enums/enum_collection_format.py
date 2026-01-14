"""
Collection format enumeration.

Defines format types for data collections and exports.
"""

from __future__ import annotations

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumCollectionFormat(StrValueHelper, str, Enum):
    """
    Enumeration of collection format types.

    Used for data serialization and export operations.
    """

    # Structured data formats
    JSON = "json"
    YAML = "yaml"
    XML = "xml"
    TOML = "toml"

    # Tabular formats
    CSV = "csv"
    TSV = "tsv"
    EXCEL = "excel"
    ODS = "ods"

    # Text formats
    TEXT = "text"
    PLAIN = "plain"
    MARKDOWN = "markdown"
    HTML = "html"

    # Binary formats
    BINARY = "binary"
    PICKLE = "pickle"
    PARQUET = "parquet"
    AVRO = "avro"

    # Database formats
    SQL = "sql"
    SQLITE = "sqlite"

    # Special formats
    CUSTOM = "custom"
    AUTO = "auto"
    DEFAULT = "default"

    @classmethod
    def is_structured_format(cls, format_type: EnumCollectionFormat) -> bool:
        """Check if format supports structured data."""
        return format_type in {
            cls.JSON,
            cls.YAML,
            cls.XML,
            cls.TOML,
        }

    @classmethod
    def is_tabular_format(cls, format_type: EnumCollectionFormat) -> bool:
        """Check if format is designed for tabular data."""
        return format_type in {
            cls.CSV,
            cls.TSV,
            cls.EXCEL,
            cls.ODS,
        }

    @classmethod
    def is_text_format(cls, format_type: EnumCollectionFormat) -> bool:
        """Check if format is human-readable text."""
        return format_type in {
            cls.TEXT,
            cls.PLAIN,
            cls.MARKDOWN,
            cls.HTML,
            cls.JSON,
            cls.YAML,
            cls.XML,
            cls.TOML,
            cls.CSV,
            cls.TSV,
            cls.SQL,
        }

    @classmethod
    def is_binary_format(cls, format_type: EnumCollectionFormat) -> bool:
        """Check if format is binary."""
        return format_type in {
            cls.BINARY,
            cls.PICKLE,
            cls.PARQUET,
            cls.AVRO,
            cls.SQLITE,
            cls.EXCEL,
            cls.ODS,
        }

    @classmethod
    def get_default_extension(cls, format_type: EnumCollectionFormat) -> str:
        """Get default file extension for format."""
        mapping = {
            cls.JSON: ".json",
            cls.YAML: ".yaml",
            cls.XML: ".xml",
            cls.TOML: ".toml",
            cls.CSV: ".csv",
            cls.TSV: ".tsv",
            cls.EXCEL: ".xlsx",
            cls.ODS: ".ods",
            cls.TEXT: ".txt",
            cls.PLAIN: ".txt",
            cls.MARKDOWN: ".md",
            cls.HTML: ".html",
            cls.BINARY: ".bin",
            cls.PICKLE: ".pkl",
            cls.PARQUET: ".parquet",
            cls.AVRO: ".avro",
            cls.SQL: ".sql",
            cls.SQLITE: ".db",
        }
        return mapping.get(format_type, ".txt")

    @classmethod
    def get_mime_type(cls, format_type: EnumCollectionFormat) -> str:
        """Get MIME type for format."""
        mapping = {
            cls.JSON: "application/json",
            cls.YAML: "application/x-yaml",
            cls.XML: "application/xml",
            cls.TOML: "application/toml",
            cls.CSV: "text/csv",
            cls.TSV: "text/tab-separated-values",
            # Excel MIME type
            cls.EXCEL: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            cls.TEXT: "text/plain",
            cls.PLAIN: "text/plain",
            cls.MARKDOWN: "text/markdown",
            cls.HTML: "text/html",
            cls.BINARY: "application/octet-stream",
            cls.SQL: "application/sql",
        }
        return mapping.get(format_type, "application/octet-stream")


# Export the enum
__all__ = ["EnumCollectionFormat"]
