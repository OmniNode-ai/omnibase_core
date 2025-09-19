"""
Output format enumeration for CLI operations.

Migrated from archived with enhanced utility methods.
Follows ONEX one-enum-per-file naming conventions.
"""

from enum import Enum


class EnumOutputFormat(str, Enum):
    """
    Strongly typed output format for CLI operations.

    Inherits from str for JSON serialization compatibility while providing
    type safety and IDE support.
    """

    TEXT = "text"  # Human-readable text format
    JSON = "json"  # JSON format for machine consumption
    YAML = "yaml"  # YAML format for machine consumption
    XML = "xml"  # XML format for structured data
    MARKDOWN = "markdown"  # Markdown format for documentation
    TABLE = "table"  # Tabular format for terminal display
    CSV = "csv"  # CSV format for tabular data
    DETAILED = "detailed"  # Detailed format for comprehensive output
    COMPACT = "compact"  # Compact format for minimal output
    RAW = "raw"  # Raw format for unprocessed output
    BINARY = "binary"  # Binary format for non-text data

    def __str__(self) -> str:
        """Return the string value for serialization."""
        return self.value

    @classmethod
    def is_structured(cls, format_type: "EnumOutputFormat") -> bool:
        """Check if the format is structured data."""
        return format_type in {cls.JSON, cls.YAML, cls.XML, cls.CSV}

    @classmethod
    def is_human_readable(cls, format_type: "EnumOutputFormat") -> bool:
        """Check if the format is human-readable."""
        return format_type in {
            cls.TEXT,
            cls.JSON,
            cls.YAML,
            cls.XML,
            cls.MARKDOWN,
            cls.TABLE,
            cls.CSV,
            cls.DETAILED,
            cls.COMPACT,
        }

    @classmethod
    def is_machine_readable(cls, format_type: "EnumOutputFormat") -> bool:
        """Check if the format is optimized for machine consumption."""
        return format_type in {
            cls.JSON,
            cls.YAML,
            cls.XML,
            cls.CSV,
            cls.RAW,
            cls.BINARY,
        }


# Export for use
__all__ = ["EnumOutputFormat"]
