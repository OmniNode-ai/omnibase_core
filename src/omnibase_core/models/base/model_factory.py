from __future__ import annotations

from typing import TypeVar

"""
Base Factory Model.

Abstract base class for typed factories following ONEX one-model-per-file architecture.
"""


from abc import ABC, abstractmethod
from typing import Generic

from pydantic import BaseModel

# Generic type variable for the type this factory creates
T = TypeVar("T")


class ModelBaseFactory(ABC, BaseModel, Generic[T]):
    """Abstract base class for typed factories."""

    @abstractmethod
    def create(self, **kwargs: object) -> T:
        """Create an object of type T."""
        ...

    @abstractmethod
    def can_create(self, type_name: str) -> bool:
        """Check if the factory can create the given type."""
        ...

    model_config = {
        "extra": "ignore",
        "use_enum_values": False,
        "validate_assignment": True,
    }


# Export the model
__all__ = ["ModelBaseFactory"]
