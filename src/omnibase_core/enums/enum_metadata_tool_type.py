"""
Metadata tool type enumeration.

Defines types of metadata tools available in the ONEX ecosystem.
"""

from __future__ import annotations

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumMetadataToolType(StrValueHelper, str, Enum):
    """
    Types of metadata tools.

    Categorizes metadata tools by their primary function and purpose
    in the ONEX metadata management system.
    """

    FUNCTION = "function"  # General function-based tool
    DOCUMENTATION = "documentation"  # Documentation generation tool
    TEMPLATE = "template"  # Template processing tool
    GENERATOR = "generator"  # Code/content generation tool
    ANALYZER = "analyzer"  # Analysis and inspection tool
    VALIDATOR = "validator"  # Validation and verification tool
    FORMATTER = "formatter"  # Formatting and transformation tool

    @classmethod
    def is_generation_tool(cls, tool_type: EnumMetadataToolType) -> bool:
        """
        Check if tool type is for generation.

        Args:
            tool_type: The tool type to check

        Returns:
            True if tool type is GENERATOR, TEMPLATE, or DOCUMENTATION
        """
        return tool_type in {cls.GENERATOR, cls.TEMPLATE, cls.DOCUMENTATION}

    @classmethod
    def is_validation_tool(cls, tool_type: EnumMetadataToolType) -> bool:
        """
        Check if tool type is for validation.

        Args:
            tool_type: The tool type to check

        Returns:
            True if tool type is VALIDATOR or ANALYZER
        """
        return tool_type in {cls.VALIDATOR, cls.ANALYZER}

    @classmethod
    def requires_input(cls, tool_type: EnumMetadataToolType) -> bool:
        """
        Check if tool type typically requires input data.

        Args:
            tool_type: The tool type to check

        Returns:
            True if tool type typically processes input
        """
        return tool_type in {
            cls.ANALYZER,
            cls.VALIDATOR,
            cls.FORMATTER,
            cls.TEMPLATE,
        }

    @classmethod
    def produces_output(cls, tool_type: EnumMetadataToolType) -> bool:
        """
        Check if tool type produces output files/data.

        Args:
            tool_type: The tool type to check

        Returns:
            True if tool type generates output
        """
        return tool_type in {
            cls.GENERATOR,
            cls.TEMPLATE,
            cls.DOCUMENTATION,
            cls.FORMATTER,
        }

    @classmethod
    def get_description(cls, tool_type: EnumMetadataToolType) -> str:
        """
        Get human-readable description of tool type.

        Args:
            tool_type: The tool type to describe

        Returns:
            Description of the tool type
        """
        descriptions = {
            cls.FUNCTION: "General-purpose function tool",
            cls.DOCUMENTATION: "Generates or manages documentation",
            cls.TEMPLATE: "Processes templates and generates from templates",
            cls.GENERATOR: "Generates code, files, or content",
            cls.ANALYZER: "Analyzes code, metadata, or structures",
            cls.VALIDATOR: "Validates compliance, correctness, or standards",
            cls.FORMATTER: "Formats or transforms data and code",
        }
        return descriptions.get(tool_type, "Unknown tool type")

    @classmethod
    def get_default_type(cls) -> EnumMetadataToolType:
        """
        Get the default tool type.

        Returns:
            Default tool type (FUNCTION)
        """
        return cls.FUNCTION


# Export the enum
__all__ = ["EnumMetadataToolType"]
