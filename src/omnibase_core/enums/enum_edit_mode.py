"""
Edit Mode Enum.

Strongly typed enumeration for edit operation modes.
Replaces Literal["replace", "insert", "delete"] patterns.
"""

from __future__ import annotations

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumEditMode(StrValueHelper, str, Enum):
    """
    Strongly typed edit mode discriminators.

    Used for notebook cell operations and other edit scenarios where
    the type of edit operation needs to be specified. Inherits from str
    for JSON serialization compatibility while providing type safety
    and IDE support.
    """

    REPLACE = "replace"
    INSERT = "insert"
    DELETE = "delete"

    @classmethod
    def is_destructive(cls, edit_mode: EnumEditMode) -> bool:
        """Check if the edit mode is destructive to existing content."""
        return edit_mode in {cls.REPLACE, cls.DELETE}

    @classmethod
    def is_additive(cls, edit_mode: EnumEditMode) -> bool:
        """Check if the edit mode adds new content."""
        return edit_mode == cls.INSERT

    @classmethod
    def requires_content(cls, edit_mode: EnumEditMode) -> bool:
        """Check if the edit mode requires content to be provided."""
        return edit_mode in {cls.REPLACE, cls.INSERT}

    @classmethod
    def requires_target(cls, edit_mode: EnumEditMode) -> bool:
        """Check if the edit mode requires a target to operate on."""
        return edit_mode in {cls.REPLACE, cls.DELETE}

    @classmethod
    def changes_structure(cls, edit_mode: EnumEditMode) -> bool:
        """Check if the edit mode changes document structure."""
        return edit_mode in {cls.INSERT, cls.DELETE}

    @classmethod
    def get_operation_description(cls, edit_mode: EnumEditMode) -> str:
        """Get a human-readable description of the edit operation."""
        descriptions = {
            cls.REPLACE: "Replace existing content with new content",
            cls.INSERT: "Insert new content at specified position",
            cls.DELETE: "Remove existing content",
        }
        return descriptions.get(edit_mode, "Unknown edit operation")

    @classmethod
    def get_required_parameters(cls, edit_mode: EnumEditMode) -> list[str]:
        """Get list[Any]of required parameters for each edit mode."""
        requirements = {
            cls.REPLACE: ["target_identifier", "new_content"],
            cls.INSERT: ["position_identifier", "new_content"],
            cls.DELETE: ["target_identifier"],
        }
        return requirements.get(edit_mode, [])


# Export for use
__all__ = ["EnumEditMode"]
