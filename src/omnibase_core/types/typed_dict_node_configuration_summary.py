"""
Node Configuration Summary TypedDict.

Type-safe dictionary for node configuration summary.
"""

from __future__ import annotations

from typing import Any, TypedDict


class TypedDictNodeConfigurationSummary(TypedDict):
    """Type-safe dictionary for node configuration summary."""

    execution: Any  # Don't import model types from types directory
    resources: Any
    features: Any
    connection: Any
    is_production_ready: bool
    is_performance_optimized: bool
    has_custom_settings: bool
