"""
Strongly-typed numeric computation input model.

Represents numeric data inputs for computation operations.
Follows ONEX strong typing principles and one-model-per-file architecture.
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from omnibase_core.enums.enum_computation_type import EnumComputationType
from omnibase_core.models.operations.model_computation_input_base import (
    ModelComputationInputBase,
)


class ModelNumericComputationInput(ModelComputationInputBase):
    """
    Strongly-typed numeric computation input for computation operations.

    Represents numeric data inputs with precision and calculation specifications.
    """

    computation_type: Literal[EnumComputationType.NUMERIC] = Field(
        default=EnumComputationType.NUMERIC,
        description="Numeric computation type discriminator",
    )
    numeric_parameters: dict[str, float] = Field(
        default_factory=dict,
        description="Numeric parameters for calculations",
    )
    precision_requirements: int = Field(
        default=2,
        description="Required decimal precision",
    )
    calculation_mode: str = Field(
        default="standard",
        description="Calculation mode or algorithm",
    )
    rounding_strategy: str = Field(
        default="round_half_up",
        description="Numeric rounding strategy",
    )


# Export for use
__all__ = ["ModelNumericComputationInput"]
