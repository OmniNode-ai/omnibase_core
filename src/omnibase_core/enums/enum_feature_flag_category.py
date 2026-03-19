# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Feature flag category enumeration.

Provides constrained category vocabulary for contract-declared feature flags.
Categories group flags by functional domain for dashboard display and filtering.
"""

from __future__ import annotations

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumFeatureFlagCategory(StrValueHelper, str, Enum):
    """
    Category for contract-declared feature flags.

    Categories are constrained to a controlled set to ensure consistent
    grouping in the registry API and omnidash dashboard.
    """

    RUNTIME = "runtime"
    """Process lifecycle, scheduling, startup behavior."""

    INTELLIGENCE = "intelligence"
    """Pattern enforcement, context enrichment, inference."""

    OBSERVABILITY = "observability"
    """Tracing, metrics, logging, OTEL."""

    INFRASTRUCTURE = "infrastructure"
    """Kafka, database, memory subsystems."""

    DASHBOARD = "dashboard"
    """Omnidash UI behavior."""

    GENERAL = "general"
    """Uncategorized (default)."""
