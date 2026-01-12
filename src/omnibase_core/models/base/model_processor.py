"""
Base Processor Model.

Abstract base class for typed processors following ONEX one-model-per-file architecture.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from pydantic import BaseModel, ConfigDict


class ModelServiceBaseProcessor(ABC, BaseModel):
    """Abstract base class for typed processors."""

    @abstractmethod
    def process(self, input_data: object) -> object:
        """Process input data."""
        ...

    @abstractmethod
    def can_process(self, input_data: object) -> bool:
        """Check if the processor can handle the input data."""
        ...

    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=False,
        validate_assignment=True,
    )


# Export the model
__all__ = ["ModelServiceBaseProcessor"]
