"""
Algorithm Factor Configuration Model.

Configuration for individual algorithm factors defining weight,
calculation method, and parameters for each factor in a multi-factor algorithm.

Strict typing is enforced: No Any types allowed in implementation.
"""

from pydantic import BaseModel, ConfigDict, Field


class ModelAlgorithmFactorConfig(BaseModel):
    """
    Configuration for individual algorithm factors.

    Defines weight, calculation method, and parameters for
    each factor in a multi-factor algorithm.
    """

    weight: float = Field(
        default=...,
        description="Factor weight in algorithm (0.0-1.0)",
        ge=0.0,
        le=1.0,
    )

    calculation_method: str = Field(
        default=...,
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

    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=False,
        validate_assignment=True,
    )
