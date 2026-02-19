# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Merge Conflict Type Enumeration for Contract Merging.

This module defines EnumMergeConflictType, which categorizes the types of
conflicts that can occur during contract merge operations. Used by the
Typed Contract Merge Engine to report precise conflict information.

Includes geometric conflict types from the Neumann pattern for classifying
parallel agent output relationships. These enable coarse classification of
agent outputs for intelligent routing to resolution strategies.

See Also:
    - OMN-1127: Typed Contract Merge Engine
    - OMN-1852: Geometric conflict types (Neumann pattern)
    - ModelMergeConflict: Uses this enum to classify conflicts
    - ModelContractPatch: The patch model that may cause conflicts

.. versionadded:: 0.4.1
    Added as part of Typed Contract Merge Engine (OMN-1127)

.. versionadded:: 0.16.1
    Added geometric conflict types (OMN-1852)
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

    Traditional conflict types classify merge-level data incompatibilities.
    Geometric conflict types (from the Neumann pattern) classify the spatial
    relationship between parallel agent outputs for intelligent routing to
    resolution strategies.

    Geometric Type Resolution Policy (GI-3):
        - IDENTICAL, ORTHOGONAL, LOW_CONFLICT: auto-resolvable
        - CONFLICTING: partially auto-resolvable
        - OPPOSITE, AMBIGUOUS: MUST require human approval

    Attributes:
        TYPE_MISMATCH: Field types don't match between base and patch.
        INCOMPATIBLE: Values are semantically incompatible.
        REQUIRED_MISSING: A required field is missing in the patch.
        SCHEMA_VIOLATION: Value violates schema constraints.
        LIST_CONFLICT: Add/remove operations conflict on the same item.
        NULLABLE_VIOLATION: Non-nullable field assigned null value.
        CONSTRAINT_CONFLICT: Constraints from base and patch are contradictory.
        ORTHOGONAL: Agents modified different aspects; can auto-merge.
        LOW_CONFLICT: Minor differences between agents; pick best.
        IDENTICAL: Agents produced same result; deduplicate.
        OPPOSITE: Contradictory conclusions; REQUIRES human approval.
        CONFLICTING: Partial overlap between agent outputs; needs resolution.
        AMBIGUOUS: Cannot determine relationship; REQUIRES human approval.

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

    .. versionadded:: 0.16.1
        Added geometric conflict types (OMN-1852)
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

    # Geometric conflict types (Neumann pattern) - classify parallel agent outputs
    # See OMN-1852 for semantics and GI-3 for approval policy.

    ORTHOGONAL = "orthogonal"
    """Agents modified different aspects; safe to auto-merge."""

    LOW_CONFLICT = "low_conflict"
    """Minor differences between agent outputs; pick best result."""

    IDENTICAL = "identical"
    """Agents produced the same result; deduplicate."""

    OPPOSITE = "opposite"
    """Contradictory agent conclusions; REQUIRES human approval (GI-3)."""

    CONFLICTING = "conflicting"
    """Partial overlap between agent outputs; needs resolution strategy."""

    AMBIGUOUS = "ambiguous"
    """Cannot determine agent output relationship; REQUIRES human approval (GI-3)."""

    def __repr__(self) -> str:
        """Return a detailed representation for debugging."""
        return f"EnumMergeConflictType.{self.name}"


__all__ = [
    "EnumMergeConflictType",
]
