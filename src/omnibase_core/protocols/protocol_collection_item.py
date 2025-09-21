"""
Collection item protocol for generic collections.

This module defines the protocol for items that can be stored in
ModelGenericCollection instances, providing type safety and constraints.
"""

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class CollectionItem(Protocol):
    """Protocol for items that can be stored in collections."""

    def model_dump(self) -> dict[str, Any]:
        """
        Return a dictionary representation of the model.

        Returns:
            Dictionary with string keys and serializable values
        """
        ...
