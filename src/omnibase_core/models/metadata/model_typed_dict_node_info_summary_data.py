from __future__ import annotations

from typing import Dict, TypedDict

"""
Typed structure for node info summary serialization.
"""


from typing import TypedDict

from omnibase_core.models.metadata.model_typed_dict_node_core import (
    ModelTypedDictNodeCore,
)


class TypedDictNodeInfoSummaryData(TypedDict):
    """Typed structure for node info summary serialization."""

    core: ModelTypedDictNodeCore
    timestamps: dict[str, Any]  # From component method call - returns lifecycle summary
    categorization: dict[
        str,
        Any,
    ]  # From component method call - returns categorization summary
    quality: dict[str, Any]  # From component method call - returns quality summary
    performance: dict[
        str,
        Any,
    ]  # From component method call - returns performance summary


__all__ = ["ModelTypedDictNodeInfoSummaryData"]
