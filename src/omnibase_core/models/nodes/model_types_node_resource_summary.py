from __future__ import annotations

from typing import Dict, TypedDict

"""
TypedDict for node resource limits summary.

Replaces dict[str, Any] return type with structured typing.
"""


from typing import TypedDict


class ModelNodeResourceSummaryType(TypedDict):
    """
    Typed dict[str, Any]ionary for node resource limits summary.

    Replaces dict[str, Any] return type from get_resource_summary()
    with proper type structure.
    """

    max_memory_mb: int
    max_cpu_percent: float
    has_memory_limit: bool
    has_cpu_limit: bool
    has_any_limits: bool


# Export for use
__all__ = ["ModelNodeResourceSummaryType"]
