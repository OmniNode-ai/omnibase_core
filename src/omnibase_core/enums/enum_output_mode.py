"""
Output Mode Enum.

Strongly typed enumeration for output mode types.
Replaces Literal["content", "files_with_matches", "count"] patterns.
"""

from __future__ import annotations

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumOutputMode(StrValueHelper, str, Enum):
    """
    Strongly typed output mode discriminators.

    Used for search and grep operations where the format of output
    needs to be specified. Inherits from str for JSON serialization
    compatibility while providing type safety and IDE support.
    """

    CONTENT = "content"
    FILES_WITH_MATCHES = "files_with_matches"
    COUNT = "count"

    @classmethod
    def returns_full_content(cls, output_mode: EnumOutputMode) -> bool:
        """Check if the output mode returns full content."""
        return output_mode == cls.CONTENT

    @classmethod
    def returns_file_paths(cls, output_mode: EnumOutputMode) -> bool:
        """Check if the output mode returns file paths."""
        return output_mode == cls.FILES_WITH_MATCHES

    @classmethod
    def returns_statistics(cls, output_mode: EnumOutputMode) -> bool:
        """Check if the output mode returns statistical information."""
        return output_mode == cls.COUNT

    @classmethod
    def is_minimal_output(cls, output_mode: EnumOutputMode) -> bool:
        """Check if the output mode provides minimal information."""
        return output_mode in {cls.FILES_WITH_MATCHES, cls.COUNT}

    @classmethod
    def is_verbose_output(cls, output_mode: EnumOutputMode) -> bool:
        """Check if the output mode provides detailed information."""
        return output_mode == cls.CONTENT

    @classmethod
    def get_output_description(cls, output_mode: EnumOutputMode) -> str:
        """Get a human-readable description of the output mode."""
        descriptions = {
            cls.CONTENT: "Return matching lines with full content",
            cls.FILES_WITH_MATCHES: "Return only file paths that contain matches",
            cls.COUNT: "Return count of matches per file",
        }
        return descriptions.get(output_mode, "Unknown output mode")

    @classmethod
    def get_typical_use_case(cls, output_mode: EnumOutputMode) -> str:
        """Get typical use case for each output mode."""
        use_cases = {
            cls.CONTENT: "Viewing actual matching content for analysis",
            cls.FILES_WITH_MATCHES: "Finding which files contain patterns",
            cls.COUNT: "Getting statistics about match frequency",
        }
        return use_cases.get(output_mode, "Unknown use case")

    @classmethod
    def supports_context_lines(cls, output_mode: EnumOutputMode) -> bool:
        """Check if the output mode supports context lines."""
        return output_mode == cls.CONTENT


# Export for use
__all__ = ["EnumOutputMode"]
