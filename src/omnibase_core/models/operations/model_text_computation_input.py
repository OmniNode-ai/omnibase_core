"""
Strongly-typed text computation input model.

Represents text data inputs for computation operations.
Follows ONEX strong typing principles and one-model-per-file architecture.
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from omnibase_core.enums.enum_computation_type import EnumComputationType
from omnibase_core.models.operations.model_computation_input_base import (
    ModelComputationInputBase,
)


class ModelTextComputationInput(ModelComputationInputBase):
    """
    Strongly-typed text computation input for computation operations.

    Represents text data inputs with encoding and locale specifications.
    """

    computation_type: Literal[EnumComputationType.TEXT] = Field(
        default=EnumComputationType.TEXT,
        description="Text computation type discriminator",
    )
    text_parameters: dict[str, str] = Field(
        default_factory=dict,
        description="Text-specific parameters",
    )
    encoding: str = Field(default="utf-8", description="Text encoding")
    language_locale: str = Field(
        default="en-US",
        description="Language and locale for text processing",
    )
    case_sensitivity: bool = Field(
        default=True,
        description="Whether text processing is case sensitive",
    )


# Export for use
__all__ = ["ModelTextComputationInput"]
