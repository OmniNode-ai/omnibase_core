"""
Action Category Enum

Categories for organizing different types of actions across tools.
"""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumActionCategory(StrValueHelper, str, Enum):
    """
    Categories for organizing different types of actions across tools.

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

    def is_management_category(self) -> bool:
        """
        Check if this category involves management operations.

        Returns:
            True if management category, False otherwise
        """
        return self in {
            self.LIFECYCLE,
            self.CONFIGURATION,
            self.REGISTRY,
        }

    def is_execution_category(self) -> bool:
        """
        Check if this category involves execution operations.

        Returns:
            True if execution category, False otherwise
        """
        return self in {
            self.EXECUTION,
            self.WORKFLOW,
            self.SYSTEM,
        }

    def is_inspection_category(self) -> bool:
        """
        Check if this category involves inspection operations.

        Returns:
            True if inspection category, False otherwise
        """
        return self in {
            self.VALIDATION,
            self.INTROSPECTION,
        }
