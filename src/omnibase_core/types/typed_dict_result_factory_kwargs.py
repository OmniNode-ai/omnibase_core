"""
Result Factory TypedDict for Model Creation.

Specialized TypedDict for result-type models with success/error patterns.
"""

from __future__ import annotations

from typing import TypedDict


class TypedDictResultFactoryKwargs(TypedDict, total=False):
    """Typed dictionary for result factory parameters."""

    success: bool
    exit_code: int
    error_message: str
    data: object  # ONEX compliance: Use object instead of Any for generic data
    output_text: str
    warnings: list[str]


__all__ = ["TypedDictResultFactoryKwargs"]
