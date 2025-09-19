"""
Execution output format enumeration.

Provides strongly typed output formats for node execution results.
"""

from enum import Enum


class EnumExecutionOutputFormat(str, Enum):
    """Format of execution output."""

    DICT = "dict"
    JSON = "json"
    YAML = "yaml"
    TEXT = "text"
    XML = "xml"
    CSV = "csv"
    BINARY = "binary"
    STRUCTURED = "structured"
