"""
TypedDict for node feature flags summary.

Replaces dict[str, str] return type with structured typing.
"""

from __future__ import annotations

from typing import TypedDict


class NodeFeatureSummaryType(TypedDict):
    """
    Typed dictionary for node feature flags summary.

    Replaces dict[str, str] return type from get_feature_summary()
    with proper type structure.
    """

    enable_caching: str
    enable_monitoring: str
    enable_tracing: str
    enabled_features: str
    enabled_count: str
    is_monitoring_enabled: str
    is_debug_mode: str


# Export for use
__all__ = ["NodeFeatureSummaryType"]
