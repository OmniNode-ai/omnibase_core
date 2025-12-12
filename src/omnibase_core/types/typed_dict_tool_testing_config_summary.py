"""
TypedDict for tool testing configuration summary.

Strongly-typed representation for tool testing configuration summary data.
Follows ONEX one-model-per-file and TypedDict naming conventions.
"""

from __future__ import annotations

from typing import TypedDict

from omnibase_core.types.typed_dict_tool_testing_summary import (
    TypedDictToolTestingSummary,
)


class TypedDictToolTestingConfigSummary(TypedDict):
    """
    Strongly-typed dictionary for tool testing configuration summary.

    Replaces dict[str, Any] return type from get_summary()
    with proper type structure.
    """

    required_ci_tiers: list[str]
    minimum_coverage_percentage: float
    canonical_test_case_ids: list[str]
    performance_test_required: bool
    security_test_required: bool
    test_requirements: TypedDictToolTestingSummary


__all__ = ["TypedDictToolTestingConfigSummary"]
