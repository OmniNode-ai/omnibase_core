"""
Collection item protocol for generic collections.

This module defines the protocol for items that can be stored in
ModelGenericCollection instances, providing type safety and constraints.
"""

from typing import Protocol, runtime_checkable

from ..models.core.model_item_summary import ModelItemSummary


@runtime_checkable
class CollectionItem(Protocol):
    """Protocol for items that can be stored in collections."""

    def model_dump(self) -> ModelItemSummary:
        """
        Return a strongly-typed summary representation of the model.

        Returns:
            ModelItemSummary with typed fields instead of generic dict
        """
        ...
