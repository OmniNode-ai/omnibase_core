"""
TypedDict for node resource limits summary.

Strongly-typed representation for node resource limits summary data.
Follows ONEX one-model-per-file and TypedDict naming conventions.
"""

from __future__ import annotations

from typing import TypedDict


class TypedDictNodeResourceSummaryType(TypedDict):
    """
    Strongly-typed dictionary for node resource limits summary.

    Replaces dict[str, Any] return type from get_resource_summary()
    with proper type structure.
    """

    max_memory_mb: int
    max_cpu_percent: float
    has_memory_limit: bool
    has_cpu_limit: bool
    has_any_limits: bool


__all__ = ["TypedDictNodeResourceSummaryType"]
