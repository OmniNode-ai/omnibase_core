"""
Node Configuration Summary TypedDict.

Type-safe dictionary for node configuration summary.
"""

from __future__ import annotations

from typing import TypedDict


class TypedDictNodeConfigurationSummary(TypedDict):
    """Type-safe dictionary for node configuration summary."""

    execution: object  # ONEX compliance: Use object instead of Any
    resources: object  # ONEX compliance: Use object instead of Any
    features: object  # ONEX compliance: Use object instead of Any
    connection: object  # ONEX compliance: Use object instead of Any
    is_production_ready: bool
    is_performance_optimized: bool
    has_custom_settings: bool


__all__ = ["TypedDictNodeConfigurationSummary"]
