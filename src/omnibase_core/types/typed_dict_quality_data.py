"""
TypedDict for quality data.

Strongly-typed representation for quality data updates.
Follows ONEX one-model-per-file and TypedDict naming conventions.
"""

from typing import TypedDict


class TypedDictQualityData(TypedDict, total=False):
    """Strongly-typed structure for quality data updates."""

    health_score: float
    success_rate: float
    documentation_coverage: float


__all__ = ["TypedDictQualityData"]
