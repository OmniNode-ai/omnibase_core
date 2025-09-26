"""
Base Factory Model.

Abstract base class for typed factories following ONEX one-model-per-file architecture.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from pydantic import BaseModel

# Generic type variable for the type this factory creates
T = TypeVar("T")


class BaseFactory(ABC, BaseModel, Generic[T]):
    """Abstract base class for typed factories."""

    @abstractmethod
    def create(self, **kwargs: object) -> T:
        """Create an object of type T."""
        ...

    @abstractmethod
    def can_create(self, type_name: str) -> bool:
        """Check if the factory can create the given type."""
        ...


# Export the model
__all__ = ["BaseFactory"]
