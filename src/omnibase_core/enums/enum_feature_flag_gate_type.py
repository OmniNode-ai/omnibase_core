# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Feature flag gate-type enumeration.

Classifies each flag as gating a rollout cut-over path versus a long-lived
runtime toggle. Surfaced through the registry API and the omnidash dashboard so
operators can see which flags are expected to retire after a cut-over.
"""

from __future__ import annotations

from enum import Enum, unique

from omnibase_core.enums.enum_str_enum_base import UtilStrValueHelper


@unique
class EnumFeatureFlagGateType(UtilStrValueHelper, str, Enum):
    """Gate type for a registered feature flag."""

    MIGRATION = "migration"
    """Flag gating a rollout cut-over path; expected to retire after cut-over."""

    PERMANENT = "permanent"
    """Long-lived runtime toggle with no scheduled retirement."""
