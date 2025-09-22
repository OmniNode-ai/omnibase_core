"""
Base Processor Model.

Abstract base class for typed processors following ONEX one-model-per-file architecture.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel


class BaseProcessor(ABC, BaseModel):
    """Abstract base class for typed processors."""

    @abstractmethod
    def process(self, input_data: Any) -> object:
        """Process input data."""
        ...

    @abstractmethod
    def can_process(self, input_data: Any) -> bool:
        """Check if the processor can handle the input data."""
        ...


# Export the model
__all__ = ["BaseProcessor"]
