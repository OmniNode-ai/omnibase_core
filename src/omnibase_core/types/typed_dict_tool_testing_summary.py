"""
TypedDict for tool testing requirements summary.

Strongly-typed representation for tool testing requirements summary data.
Follows ONEX one-model-per-file and TypedDict naming conventions.
"""

from __future__ import annotations

from typing import TypedDict


class TypedDictToolTestingSummary(TypedDict):
    """
    Strongly-typed dictionary for tool testing requirements summary.

    Replaces dict[str, Any] return type from get_test_requirement_summary()
    with proper type structure.
    """

    requires_unit: bool
    requires_integration: bool
    requires_e2e: bool
    requires_performance: bool
    requires_security: bool
    ci_tier_count: int
    has_canonical_tests: bool
    canonical_test_count: int
    minimum_coverage: float


__all__ = ["TypedDictToolTestingSummary"]
