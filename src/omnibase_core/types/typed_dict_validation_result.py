"""
TypedDict for validation results.
"""

from __future__ import annotations

from typing import TypedDict


class TypedDictValidationResult(TypedDict):
    is_valid: bool
    error_level_count: int
    warning_count: int
    info_count: int
    validation_time_ms: int
    rules_checked: int


__all__ = ["TypedDictValidationResult"]
