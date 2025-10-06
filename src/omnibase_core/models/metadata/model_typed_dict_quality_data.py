from __future__ import annotations

from typing import Dict, TypedDict

"""
Typed structure for quality data updates.
"""


from typing import TypedDict


class TypedDictQualityData(TypedDict, total=False):
    """Typed structure for quality data updates."""

    health_score: float
    success_rate: float
    documentation_coverage: float


__all__ = ["ModelTypedDictQualityData"]
