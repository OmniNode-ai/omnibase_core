"""
Base Factory Model.

Abstract base class for typed factories following ONEX one-model-per-file architecture.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel


class BaseFactory(ABC, BaseModel):
    """Abstract base class for typed factories."""

    @abstractmethod
    def create(self, **kwargs: Any) -> object:
        """Create an object."""
        ...

    @abstractmethod
    def can_create(self, type_name: str) -> bool:
        """Check if the factory can create the given type."""
        ...


# Export the model
__all__ = ["BaseFactory"]