"""
TypedDict for tool resource requirements summary.

Strongly-typed representation for tool resource requirements summary data.
Follows ONEX one-model-per-file and TypedDict naming conventions.
"""

from __future__ import annotations

from typing import TypedDict


class TypedDictToolResourceSummary(TypedDict):
    """
    Strongly-typed dictionary for tool resource requirements summary.

    Replaces dict[str, Any] return type from get_resource_summary()
    with proper type structure.
    """

    max_memory_mb: int
    max_cpu_percent: int
    timeout_seconds: int
    execution_mode: str
    requires_network: bool
    requires_separate_port: bool


__all__ = ["TypedDictToolResourceSummary"]
