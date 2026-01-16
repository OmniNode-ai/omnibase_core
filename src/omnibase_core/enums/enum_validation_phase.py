"""Validation phase enumeration for contract validation pipeline."""

from __future__ import annotations

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumValidationPhase(StrValueHelper, str, Enum):
    """Contract validation pipeline phases.

    Phases: PATCH (validate patches), MERGE (validate merge), EXPANDED (validate resolved contract).
    """

    PATCH = "patch"
    """Phase 1: Patch validation - validates individual patches before merging."""

    MERGE = "merge"
    """Phase 2: Merge validation - validates merge operations between contracts."""

    EXPANDED = "expanded"
    """Phase 3: Expanded contract validation - validates fully resolved contracts."""


__all__ = ["EnumValidationPhase"]
