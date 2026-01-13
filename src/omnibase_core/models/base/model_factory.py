"""
Base Factory Model.

Abstract base class for typed factories following ONEX one-model-per-file architecture.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from pydantic import BaseModel, ConfigDict


class ModelBaseFactory[T](ABC, BaseModel):
    """Abstract base class for typed factories."""

    @abstractmethod
    def create(self, **kwargs: object) -> T:
        """Create an object of type T."""
        ...

    @abstractmethod
    def can_create(self, type_name: str) -> bool:
        """Check if the factory can create the given type."""
        ...

    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=False,
        validate_assignment=True,
    )


# Export the model
__all__ = ["ModelBaseFactory"]
