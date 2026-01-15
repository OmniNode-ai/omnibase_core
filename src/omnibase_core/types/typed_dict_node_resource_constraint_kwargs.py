"""
Node Resource Constraint TypedDict.

TypedDict for create_constrained method kwargs.
"""

from __future__ import annotations

from typing import TypedDict


class TypedDictNodeResourceConstraintKwargs(TypedDict, total=False):
    """TypedDict for create_constrained method kwargs."""

    max_memory_mb: int
    max_cpu_percent: float


__all__ = ["TypedDictNodeResourceConstraintKwargs"]
