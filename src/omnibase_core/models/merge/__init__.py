# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
ONEX Contract Merge Models Module.

This module provides the data models for the Typed Contract Merge Engine,
including merge conflicts, geometric conflict analysis, resolution tracking,
and overlay stacking.

Models included:
    Core Models (OMN-1127):
        - ModelMergeConflict: Represents a conflict detected during merge

    Geometric Conflict Models (OMN-1853):
        - ModelGeometricConflictDetails: Rich conflict analysis with similarity metrics
        - ModelConflictResolutionResult: Resolution tracking with GI-3 enforcement

    Overlay Stacking Models (OMN-2757):
        - ModelOverlayRef: Immutable record of an overlay applied during merge
        - ModelOverlayStackEntry: Ordered overlay entry in multi-patch pipeline

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

.. versionadded:: 0.16.1
    Added geometric conflict models (OMN-1853)

.. versionadded:: 0.18.0
    Added overlay stacking models (OMN-2757)
"""

from omnibase_core.models.merge.model_conflict_resolution_result import (
    ModelConflictResolutionResult,
)
from omnibase_core.models.merge.model_geometric_conflict_details import (
    ModelGeometricConflictDetails,
)
from omnibase_core.models.merge.model_merge_conflict import ModelMergeConflict
from omnibase_core.models.merge.model_overlay_ref import ModelOverlayRef
from omnibase_core.models.merge.model_overlay_stack_entry import ModelOverlayStackEntry

__all__ = [
    "ModelConflictResolutionResult",
    "ModelGeometricConflictDetails",
    "ModelMergeConflict",
    "ModelOverlayRef",
    "ModelOverlayStackEntry",
]
