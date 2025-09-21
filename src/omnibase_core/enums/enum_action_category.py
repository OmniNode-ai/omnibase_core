"""
Action Category Enum

Categories for organizing different types of CLI actions.
"""

from __future__ import annotations

from enum import Enum


class EnumActionCategory(str, Enum):
    """
    Categories for organizing different types of CLI actions.

    Provides consistent categorization for action organization and filtering.
    """

    LIFECYCLE = "lifecycle"
    VALIDATION = "validation"
    INTROSPECTION = "introspection"
    CONFIGURATION = "configuration"
    EXECUTION = "execution"
    REGISTRY = "registry"
    WORKFLOW = "workflow"
    SYSTEM = "system"

    def __str__(self) -> str:
        """Return the string value of the category."""
        return self.value

    def is_management_category(self) -> bool:
        """Check if this category involves management operations."""
        return self in [self.LIFECYCLE, self.CONFIGURATION, self.REGISTRY]

    def is_execution_category(self) -> bool:
        """Check if this category involves execution operations."""
        return self in [self.EXECUTION, self.WORKFLOW, self.SYSTEM]

    def is_inspection_category(self) -> bool:
        """Check if this category involves inspection operations."""
        return self in [self.VALIDATION, self.INTROSPECTION]