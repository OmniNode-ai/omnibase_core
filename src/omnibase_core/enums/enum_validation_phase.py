# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""Validation phase enumeration for contract validation pipeline.

This enum identifies which phase of the contract validation pipeline
is being executed. The pipeline processes contracts through three
sequential phases, each performing different types of validation.

Validation Pipeline Flow:
    PATCH -> MERGE -> EXPANDED

Phase Descriptions:
    - PATCH: Validates individual contract patches before merging
    - MERGE: Validates the merge operation between base and patch contracts
    - EXPANDED: Validates the fully expanded/resolved contract

Related:
    - OMN-1128: Contract Validation Pipeline
    - EnumPatchValidationErrorCode: Error codes used in PATCH phase
    - EnumMergeConflictType: Conflict types detected in MERGE phase

.. versionadded:: 0.4.0
"""

from __future__ import annotations

from enum import Enum, unique


@unique
class EnumValidationPhase(str, Enum):
    """Contract validation pipeline phases.

    This enum represents the three sequential phases of contract validation.
    Each phase performs distinct validation logic and may produce different
    types of errors or warnings.

    Attributes:
        PATCH: Phase 1 - Patch validation. Validates individual contract
            patches for structural correctness, duplicate entries, and
            semantic consistency before they are merged with base contracts.
        MERGE: Phase 2 - Merge validation. Validates the merge operation
            between base contracts and patches, detecting conflicts and
            ensuring merge semantics are correctly applied.
        EXPANDED: Phase 3 - Expanded contract validation. Validates the
            fully resolved contract after all patches are applied and
            all references are expanded.

    Example:
        >>> from omnibase_core.enums import EnumValidationPhase
        >>> phase = EnumValidationPhase.PATCH
        >>> print(f"Currently in {phase.value} validation phase")
        Currently in patch validation phase
    """

    PATCH = "patch"
    """Phase 1: Patch validation - validates individual patches before merging."""

    MERGE = "merge"
    """Phase 2: Merge validation - validates merge operations between contracts."""

    EXPANDED = "expanded"
    """Phase 3: Expanded contract validation - validates fully resolved contracts."""


__all__ = ["EnumValidationPhase"]
