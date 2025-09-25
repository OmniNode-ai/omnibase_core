"""
Result Factory TypedDict for Model Creation.

Specialized TypedDict for result-type models with success/error patterns.
"""

from __future__ import annotations

from typing import Any, TypedDict


class TypedDictResultFactoryKwargs(TypedDict, total=False):
    """Typed dictionary for result factory parameters."""

    success: bool
    exit_code: int
    error_message: str
    data: Any  # Don't import models from types - use Any for generic data
    output_text: str
    warnings: list[str]
