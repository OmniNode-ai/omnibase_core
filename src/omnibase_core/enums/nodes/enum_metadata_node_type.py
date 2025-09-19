"""
Metadata node type enumeration.

Provides strongly typed types for metadata nodes in ONEX framework.
"""

from enum import Enum


class EnumMetadataNodeType(str, Enum):
    """Types of metadata nodes."""

    FUNCTION = "function"
    DOCUMENTATION = "documentation"
    TEMPLATE = "template"
    GENERATOR = "generator"
    ANALYZER = "analyzer"
    VALIDATOR = "validator"
    FORMATTER = "formatter"
