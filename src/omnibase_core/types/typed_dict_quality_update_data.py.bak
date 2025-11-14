from __future__ import annotations

from typing import TypedDict

"""
Typed structure for quality data updates.
"""

from omnibase_core.enums.enum_documentation_quality import EnumDocumentationQuality


class TypedDictQualityUpdateData(TypedDict, total=False):
    """Typed structure for quality data updates."""

    quality_score: float
    documentation_quality: EnumDocumentationQuality
    test_coverage: float
    maintainability_index: float


__all__ = ["TypedDictQualityUpdateData"]
