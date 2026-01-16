"""
Merge Conflict Type Enumeration for Contract Merging.

This module defines EnumMergeConflictType, which categorizes the types of
conflicts that can occur during contract merge operations. Used by the
Typed Contract Merge Engine to report precise conflict information.

See Also:
    - OMN-1127: Typed Contract Merge Engine
    - ModelMergeConflict: Uses this enum to classify conflicts
    - ModelContractPatch: The patch model that may cause conflicts

.. versionadded:: 0.4.1
    Added as part of Typed Contract Merge Engine (OMN-1127)
"""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumMergeConflictType(StrValueHelper, str, Enum):
    """
    Types of conflicts that can occur during contract merge.

    When merging a contract patch with a base profile, various conflicts
    can arise. This enum categorizes these conflicts to enable precise
    error reporting and conflict resolution strategies.

    Attributes:
        TYPE_MISMATCH: Field types don't match between base and patch.
            Example: Base has string, patch provides int.
        INCOMPATIBLE: Values are semantically incompatible.
            Example: Conflicting timeout values or constraint violations.
        REQUIRED_MISSING: A required field is missing in the patch.
            Example: Patch omits a mandatory field required by the profile.
        SCHEMA_VIOLATION: Value violates schema constraints.
            Example: String value exceeds max_length, int out of range.
        LIST_CONFLICT: Add/remove operations conflict on the same item.
            Example: handlers__add and handlers__remove both reference same handler.
        NULLABLE_VIOLATION: Non-nullable field assigned null value.
            Example: Patch sets None for a required non-nullable field.
        CONSTRAINT_CONFLICT: Constraints from base and patch are contradictory.
            Example: Base requires timeout > 1000, patch requires timeout < 500.

    Example:
        >>> from omnibase_core.enums import EnumMergeConflictType
        >>>
        >>> conflict_type = EnumMergeConflictType.TYPE_MISMATCH
        >>> assert conflict_type.value == "type_mismatch"
        >>> assert str(conflict_type) == "type_mismatch"
        >>> assert repr(conflict_type) == "EnumMergeConflictType.TYPE_MISMATCH"

    Note:
        This enum is used by ModelMergeConflict to classify merge conflicts.
        See omnibase_core.models.merge.ModelMergeConflict for usage examples.

    .. versionadded:: 0.4.1
        Added as part of Typed Contract Merge Engine (OMN-1127)
    """

    TYPE_MISMATCH = "type_mismatch"
    """Types don't match between base and patch (e.g., string vs int)."""

    INCOMPATIBLE = "incompatible"
    """Values are semantically incompatible (e.g., conflicting constraints)."""

    REQUIRED_MISSING = "required_missing"
    """Required field missing in patch when profile mandates it."""

    SCHEMA_VIOLATION = "schema_violation"
    """Value violates schema constraints (e.g., min/max, pattern)."""

    LIST_CONFLICT = "list_conflict"
    """Add/remove conflict on same item in a list field."""

    NULLABLE_VIOLATION = "nullable_violation"
    """Non-nullable field assigned null value."""

    CONSTRAINT_CONFLICT = "constraint_conflict"
    """Constraints from base and patch are contradictory."""

    def __repr__(self) -> str:
        """Return a detailed representation for debugging."""
        return f"EnumMergeConflictType.{self.name}"


__all__ = [
    "EnumMergeConflictType",
]
