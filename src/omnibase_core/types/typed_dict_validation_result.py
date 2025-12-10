from __future__ import annotations

from typing import TypedDict

"""
TypedDict for validation results.
"""


class TypedDictValidationResult(TypedDict):
    """TypedDict for validation results."""

    is_valid: bool
    error_count: int
    warning_count: int
    info_count: int
    validation_time_ms: int
    rules_checked: int


__all__ = ["TypedDictValidationResult"]
