"""
Cell Type Enum.

Strongly typed enumeration for notebook cell types.
Replaces Literal["code", "markdown"] patterns.
"""

from __future__ import annotations

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumCellType(StrValueHelper, str, Enum):
    """
    Strongly typed cell type discriminators.

    Used for Jupyter notebook cells and similar document structures
    where different cell types have different behaviors. Inherits from str
    for JSON serialization compatibility while providing type safety
    and IDE support.
    """

    CODE = "code"
    MARKDOWN = "markdown"

    @classmethod
    def is_executable(cls, cell_type: EnumCellType) -> bool:
        """Check if the cell type can be executed."""
        return cell_type == cls.CODE

    @classmethod
    def is_documentation(cls, cell_type: EnumCellType) -> bool:
        """Check if the cell type is for documentation."""
        return cell_type == cls.MARKDOWN

    @classmethod
    def supports_syntax_highlighting(cls, cell_type: EnumCellType) -> bool:
        """Check if the cell type supports syntax highlighting."""
        # Both code and markdown support syntax highlighting
        return cell_type in {cls.CODE, cls.MARKDOWN}

    @classmethod
    def produces_output(cls, cell_type: EnumCellType) -> bool:
        """Check if the cell type can produce execution output."""
        return cell_type == cls.CODE

    @classmethod
    def supports_rich_text(cls, cell_type: EnumCellType) -> bool:
        """Check if the cell type supports rich text formatting."""
        return cell_type == cls.MARKDOWN

    @classmethod
    def get_cell_description(cls, cell_type: EnumCellType) -> str:
        """Get a human-readable description of the cell type."""
        descriptions = {
            cls.CODE: "Executable code cell with syntax highlighting",
            cls.MARKDOWN: "Rich text documentation cell with markdown support",
        }
        return descriptions.get(cell_type, "Unknown cell type")

    @classmethod
    def get_typical_content(cls, cell_type: EnumCellType) -> str:
        """Get description of typical content for each cell type."""
        content_types = {
            cls.CODE: "Python code, function definitions, data analysis",
            cls.MARKDOWN: "Documentation, explanations, formatted text, images",
        }
        return content_types.get(cell_type, "Unknown content type")

    @classmethod
    def get_editor_mode(cls, cell_type: EnumCellType) -> str:
        """Get the appropriate editor mode for the cell type."""
        editor_modes = {
            cls.CODE: "python",  # Or language-specific
            cls.MARKDOWN: "markdown",
        }
        return editor_modes.get(cell_type, "text")


# Export for use
__all__ = ["EnumCellType"]
