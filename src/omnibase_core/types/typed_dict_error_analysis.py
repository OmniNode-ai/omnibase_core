"""
TypedDict for error category analysis results.

Provides type-safe structure for error analysis from missing tool tracking.
"""

from typing import TypedDict


class TypedDictErrorAnalysis(TypedDict):
    """Type-safe structure for error category analysis results."""

    category: str
    is_recoverable: bool
    requires_code_change: bool
    requires_configuration: bool
    estimated_fix_time: str
    fix_complexity: str


__all__ = ["TypedDictErrorAnalysis"]
