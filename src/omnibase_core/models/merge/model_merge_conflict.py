"""
Merge Conflict Model for Contract Merging.

This module defines ModelMergeConflict, which represents a conflict
detected during contract merge operations. Conflicts occur when a
contract patch cannot be cleanly merged with a base profile.

This is a pure data model with no side effects.

See Also:
    - OMN-1127: Typed Contract Merge Engine
    - EnumMergeConflictType: Categorizes the conflict types
    - ModelContractPatch: The patch that may cause conflicts

.. versionadded:: 0.4.1
    Added as part of Typed Contract Merge Engine (OMN-1127)
"""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_merge_conflict_type import EnumMergeConflictType


class ModelMergeConflict(BaseModel):
    """
    Represents a conflict detected during contract merge.

    When merging a contract patch with a base profile, conflicts may arise.
    This model captures all relevant information about such conflicts,
    enabling precise error reporting and potential resolution strategies.

    The model is immutable (frozen) to ensure thread safety and prevent
    modification after detection.

    Attributes:
        field: The field path where the conflict occurred (dot-notation).
        base_value: The value from the base profile.
        patch_value: The value from the patch attempting to override.
        conflict_type: Category of the conflict.
        message: Human-readable explanation of the conflict.
        suggested_resolution: Optional suggestion for resolving the conflict.

    Example:
        >>> # Type mismatch conflict
        >>> conflict = ModelMergeConflict(
        ...     field="descriptor.timeout_ms",
        ...     base_value=5000,
        ...     patch_value="invalid",
        ...     conflict_type=EnumMergeConflictType.TYPE_MISMATCH,
        ...     message="Expected int, got str",
        ... )
        >>> conflict.is_type_error()
        True

        >>> # List conflict
        >>> list_conflict = ModelMergeConflict(
        ...     field="handlers",
        ...     base_value=["handler_a"],
        ...     patch_value={"add": ["handler_a"], "remove": ["handler_a"]},
        ...     conflict_type=EnumMergeConflictType.LIST_CONFLICT,
        ...     message="Cannot add and remove 'handler_a' simultaneously",
        ...     suggested_resolution="Remove 'handler_a' from either add or remove list",
        ... )
        >>> list_conflict.is_list_conflict()
        True

    Thread Safety:
        This model is immutable (frozen=True) and safe for concurrent access.

    .. versionadded:: 0.4.1
        Added as part of Typed Contract Merge Engine (OMN-1127)
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        from_attributes=True,
        validate_assignment=True,
    )

    field: str = Field(
        ...,
        min_length=1,
        description="The field path where conflict occurred (dot-notation for nested)",
    )

    base_value: Any = Field(
        ...,
        description="Value from the base profile",
    )

    patch_value: Any = Field(
        ...,
        description="Value from the patch attempting to override",
    )

    conflict_type: EnumMergeConflictType = Field(
        ...,
        description="Type of conflict detected",
    )

    message: str | None = Field(
        default=None,
        description="Human-readable explanation of the conflict",
    )

    suggested_resolution: str | None = Field(
        default=None,
        description="Optional suggestion for resolving the conflict",
    )

    def is_type_error(self) -> bool:
        """
        Check if this is a type mismatch conflict.

        Returns:
            True if conflict_type is TYPE_MISMATCH.
        """
        return self.conflict_type == EnumMergeConflictType.TYPE_MISMATCH

    def is_list_conflict(self) -> bool:
        """
        Check if this is a list add/remove conflict.

        Returns:
            True if conflict_type is LIST_CONFLICT.
        """
        return self.conflict_type == EnumMergeConflictType.LIST_CONFLICT

    def is_schema_violation(self) -> bool:
        """
        Check if this is a schema violation conflict.

        Returns:
            True if conflict_type is SCHEMA_VIOLATION.
        """
        return self.conflict_type == EnumMergeConflictType.SCHEMA_VIOLATION

    def is_required_missing(self) -> bool:
        """
        Check if this is a required field missing conflict.

        Returns:
            True if conflict_type is REQUIRED_MISSING.
        """
        return self.conflict_type == EnumMergeConflictType.REQUIRED_MISSING

    def is_constraint_conflict(self) -> bool:
        """
        Check if this is a constraint conflict.

        Returns:
            True if conflict_type is CONSTRAINT_CONFLICT or INCOMPATIBLE.
        """
        return self.conflict_type in (
            EnumMergeConflictType.CONSTRAINT_CONFLICT,
            EnumMergeConflictType.INCOMPATIBLE,
        )

    def get_field_path_parts(self) -> list[str]:
        """
        Get the field path as a list of parts.

        Returns:
            List of field path segments.

        Example:
            >>> conflict = ModelMergeConflict(
            ...     field="descriptor.timeout_ms",
            ...     base_value=5000,
            ...     patch_value="invalid",
            ...     conflict_type=EnumMergeConflictType.TYPE_MISMATCH,
            ... )
            >>> conflict.get_field_path_parts()
            ['descriptor', 'timeout_ms']
        """
        return self.field.split(".")

    def get_parent_field(self) -> str | None:
        """
        Get the parent field path, if any.

        Returns:
            Parent field path or None if field is top-level.

        Example:
            >>> conflict = ModelMergeConflict(
            ...     field="descriptor.timeout_ms",
            ...     base_value=5000,
            ...     patch_value="invalid",
            ...     conflict_type=EnumMergeConflictType.TYPE_MISMATCH,
            ... )
            >>> conflict.get_parent_field()
            'descriptor'
        """
        parts = self.get_field_path_parts()
        if len(parts) <= 1:
            return None
        return ".".join(parts[:-1])

    def __str__(self) -> str:
        """Return a human-readable string representation."""
        msg = self.message or f"{self.conflict_type.value} at '{self.field}'"
        return f"MergeConflict({self.field}): {msg}"

    def __repr__(self) -> str:
        """Return a detailed string representation for debugging."""
        return (
            f"ModelMergeConflict(field={self.field!r}, "
            f"conflict_type={self.conflict_type.name}, "
            f"base_value={self.base_value!r}, "
            f"patch_value={self.patch_value!r})"
        )


__all__ = [
    "ModelMergeConflict",
]
