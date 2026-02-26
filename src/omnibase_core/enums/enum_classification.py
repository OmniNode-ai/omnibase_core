# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Data classification enum for policy bundle classification gates.

Defines sensitivity levels for data flowing through tiered resolution.
Classification gates use these levels to constrain which resolution
tiers are permitted for data at each sensitivity level.

.. versionadded:: 0.21.0
    Phase 4 of authenticated dependency resolution (OMN-2893).
"""

from __future__ import annotations

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper

__all__ = ["EnumClassification"]


@unique
class EnumClassification(StrValueHelper, str, Enum):
    """Data classification level for policy bundle gates.

    Ordered from least to most sensitive. Classification gates
    map each level to the set of resolution tiers where data
    at that level may be resolved.
    """

    PUBLIC = "public"
    """Data that can be freely shared across all trust boundaries."""

    INTERNAL = "internal"
    """Data restricted to organization-internal resolution tiers."""

    CONFIDENTIAL = "confidential"
    """Sensitive data requiring encryption and restricted tier access."""

    RESTRICTED = "restricted"
    """Highly sensitive data limited to local-only resolution tiers."""
