#!/usr/bin/env python3
"""
Algorithm Configuration Model - ONEX Standards Compliant.

Algorithm configuration and parameters defining the computational algorithm
with factors, weights, and execution parameters for contract-driven behavior.

ZERO TOLERANCE: No Any types allowed in implementation.
"""

from pydantic import BaseModel, Field, field_validator

from .model_algorithm_factor_config import ModelAlgorithmFactorConfig


class ModelAlgorithmConfig(BaseModel):
    """
    Algorithm configuration and parameters.

    Defines the computational algorithm with factors, weights,
    and execution parameters for contract-driven behavior.
    """

    algorithm_type: str = Field(
        ...,
        description="Algorithm type identifier",
        min_length=1,
    )

    factors: dict[str, ModelAlgorithmFactorConfig] = Field(
        ...,
        description="Algorithm factors with configuration",
    )

    normalization_method: str = Field(
        default="min_max",
        description="Global normalization method",
    )

    precision_digits: int = Field(
        default=6,
        description="Precision for floating point calculations",
        ge=1,
        le=15,
    )

    @field_validator("factors")
    @classmethod
    def validate_factor_weights_sum(
        cls,
        v: dict[str, ModelAlgorithmFactorConfig],
    ) -> dict[str, ModelAlgorithmFactorConfig]:
        """Validate that factor weights sum to approximately 1.0."""
        total_weight = sum(factor.weight for factor in v.values())
        if not (0.99 <= total_weight <= 1.01):
            msg = f"Factor weights must sum to 1.0, got {total_weight}"
            raise ValueError(msg)
        return v
