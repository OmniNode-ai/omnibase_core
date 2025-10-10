"""
TypedDict for node info summary data.

Strongly-typed representation for node info summary serialization.
Follows ONEX one-model-per-file and TypedDict naming conventions.
"""

from __future__ import annotations

from typing import Any, TypedDict

from omnibase_core.types.typed_dict_node_core import TypedDictNodeCore


class TypedDictNodeInfoSummaryData(TypedDict):
    """Strongly-typed structure for node info summary serialization."""

    core: TypedDictNodeCore
    timestamps: dict[str, Any]  # From component method call - returns lifecycle summary
    categorization: dict[
        str, Any
    ]  # From component method call - returns categorization summary
    quality: dict[str, Any]  # From component method call - returns quality summary
    performance: dict[
        str, Any
    ]  # From component method call - returns performance summary


__all__ = ["TypedDictNodeInfoSummaryData"]
