"""
Log format enumeration.
"""

import enum


class EnumLogFormat(enum.StrEnum):
    """Log format enumeration."""

    JSON = "json"
    TEXT = "text"
    KEY_VALUE = "key-value"
    MARKDOWN = "markdown"
    YAML = "yaml"
    CSV = "csv"
