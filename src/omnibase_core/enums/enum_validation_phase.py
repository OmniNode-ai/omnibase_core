# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Validation phase enumeration for contract validation pipeline."""

from __future__ import annotations

from enum import Enum, unique

from omnibase_core.enums.enum_str_enum_base import UtilStrValueHelper


@unique
class EnumValidationPhase(UtilStrValueHelper, str, Enum):
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
