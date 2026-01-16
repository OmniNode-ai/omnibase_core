"""
ONEX Contract Merge Models Module.

This module provides the data models for the Typed Contract Merge Engine,
including merge conflicts and merge result representations.

Models included:
    Core Models (OMN-1127):
        - ModelMergeConflict: Represents a conflict detected during merge

Example:
    >>> from omnibase_core.models.merge import ModelMergeConflict
    >>> from omnibase_core.enums import EnumMergeConflictType
    >>>
    >>> conflict = ModelMergeConflict(
    ...     field="descriptor.timeout_ms",
    ...     base_value=5000,
    ...     patch_value="invalid",
    ...     conflict_type=EnumMergeConflictType.TYPE_MISMATCH,
    ...     message="Expected int, got str",
    ... )

.. versionadded:: 0.4.1
    Added as part of Typed Contract Merge Engine (OMN-1127)
"""

from omnibase_core.models.merge.model_merge_conflict import ModelMergeConflict

__all__ = [
    "ModelMergeConflict",
]
