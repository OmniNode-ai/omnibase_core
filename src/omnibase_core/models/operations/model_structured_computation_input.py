"""
Strongly-typed structured computation input model.

Represents structured data inputs for computation operations.
Follows ONEX strong typing principles and one-model-per-file architecture.
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from omnibase_core.enums.enum_computation_type import EnumComputationType
from omnibase_core.models.operations.model_computation_input_base import (
    ModelComputationInputBase,
)


class ModelStructuredComputationInput(ModelComputationInputBase):
    """
    Strongly-typed structured computation input for computation operations.

    Represents structured data inputs with schema and validation specifications.
    """

    computation_type: Literal[EnumComputationType.STRUCTURED] = Field(
        default=EnumComputationType.STRUCTURED,
        description="Structured computation type discriminator",
    )
    schema_definition: str = Field(
        default=...,
        description="Schema definition for structured data",
    )
    validation_level: str = Field(default="strict", description="Data validation level")
    transformation_rules: dict[str, str] = Field(
        default_factory=dict,
        description="Data transformation rules",
    )
    nested_processing: bool = Field(
        default=True,
        description="Whether to process nested structures",
    )


# Export for use
__all__ = ["ModelStructuredComputationInput"]
