"""
Deprecation Summary Type Definition.

Type-safe dictionary for deprecation summary information.
"""

from __future__ import annotations

from typing import TypedDict


class ModelDeprecationSummary(TypedDict):
    """Type-safe dictionary for deprecation summary."""

    is_deprecated: bool
    has_replacement: bool
    deprecated_since: str | None
    replacement: str | None
    status: str  # EnumDeprecationStatus.value


__all__ = ["ModelDeprecationSummary"]
