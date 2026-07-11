# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
TypedDict for analytics summary data.

Strongly-typed representation for analytics summary serialization.
Follows ONEX one-model-per-file and TypedDict naming conventions.
"""

from typing import TypedDict

from omnibase_core.types.typed_dict_core_analytics import TypedDictCoreAnalytics
from omnibase_core.types.typed_dict_timestamp_data import TypedDictTimestampData


class TypedDictAnalyticsSummaryData(TypedDict):
    """Strongly-typed structure for analytics summary serialization."""

    core: TypedDictCoreAnalytics
    quality: list[str]  # From component method call - returns list[str]
    # OMN-14337: errors/performance carry the analytics error/performance
    # summary domain models at runtime; widened to object to sever
    # types->models (immovable domain models, no structured reads here).
    errors: object
    performance: object
    timestamps: TypedDictTimestampData


__all__ = ["TypedDictAnalyticsSummaryData"]
