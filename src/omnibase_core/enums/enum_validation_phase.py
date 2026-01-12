# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""Validation phase enumeration for contract validation pipeline."""

from __future__ import annotations

from enum import Enum, unique


@unique
class EnumValidationPhase(str, Enum):
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
