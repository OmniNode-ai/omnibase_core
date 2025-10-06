from typing import Any

from pydantic import Field

"""
Algorithm Factor Configuration Model - ONEX Standards Compliant.

Configuration for individual algorithm factors defining weight,
calculation method, and parameters for each factor in a multi-factor algorithm.

ZERO TOLERANCE: No Any types allowed in implementation.
"""

from pydantic import BaseModel, Field


class ModelAlgorithmFactorConfig(BaseModel):
    """
    Configuration for individual algorithm factors.

    Defines weight, calculation method, and parameters for
    each factor in a multi-factor algorithm.
    """

    weight: float = Field(
        ...,
        description="Factor weight in algorithm (0.0-1.0)",
        ge=0.0,
        le=1.0,
    )

    calculation_method: str = Field(
        ...,
        description="Calculation method identifier",
        min_length=1,
    )

    parameters: dict[str, float] = Field(
        default_factory=dict,
        description="Method-specific parameters",
    )

    normalization_enabled: bool = Field(
        default=True,
        description="Enable factor normalization",
    )

    caching_enabled: bool = Field(
        default=True,
        description="Enable factor-level caching",
    )

    model_config = {
        "extra": "ignore",
        "use_enum_values": False,
        "validate_assignment": True,
    }
