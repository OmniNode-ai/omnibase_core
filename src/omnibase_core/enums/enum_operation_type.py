"""
Operation Type Enum.

Strongly typed enumeration for file operation types.
Replaces Literal["create", "overwrite", "append"] patterns.
"""

from __future__ import annotations

from enum import Enum, unique


@unique
class EnumOperationType(str, Enum):
    """
    Strongly typed file operation type discriminators.

    Used for file write operations and similar scenarios where operation type
    needs to be specified. Inherits from str for JSON serialization
    compatibility while providing type safety and IDE support.
    """

    CREATE = "create"
    OVERWRITE = "overwrite"
    APPEND = "append"

    def __str__(self) -> str:
        """Return the string value for serialization."""
        return self.value

    @classmethod
    def is_destructive(cls, operation_type: "EnumOperationType") -> bool:
        """Check if the operation type is destructive to existing data."""
        return operation_type in {cls.OVERWRITE}

    @classmethod
    def is_safe(cls, operation_type: "EnumOperationType") -> bool:
        """Check if the operation type is safe (non-destructive)."""
        return operation_type in {cls.CREATE, cls.APPEND}

    @classmethod
    def requires_existing_file(cls, operation_type: "EnumOperationType") -> bool:
        """Check if the operation type requires an existing file."""
        return operation_type in {cls.OVERWRITE, cls.APPEND}

    @classmethod
    def creates_new_file(cls, operation_type: "EnumOperationType") -> bool:
        """Check if the operation type creates a new file."""
        return operation_type == cls.CREATE

    @classmethod
    def modifies_content(cls, operation_type: "EnumOperationType") -> bool:
        """Check if the operation type modifies existing content."""
        return operation_type in {cls.OVERWRITE, cls.APPEND}

    @classmethod
    def get_operation_description(cls, operation_type: "EnumOperationType") -> str:
        """Get a human-readable description of the operation."""
        descriptions = {
            cls.CREATE: "Create new file (fails if file exists)",
            cls.OVERWRITE: "Replace existing file content completely",
            cls.APPEND: "Add content to end of existing file",
        }
        return descriptions.get(operation_type, "Unknown operation")


# Export for use
__all__ = ["EnumOperationType"]
