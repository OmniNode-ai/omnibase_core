from pydantic import Field, field_validator

from omnibase_core.errors.error_codes import ModelOnexError

"""
Algorithm Configuration Model - ONEX Standards Compliant.

Algorithm configuration and parameters defining the computational algorithm
with factors, weights, and execution parameters for contract-driven behavior.

ZERO TOLERANCE: No Any types allowed in implementation.
"""

from typing import Any

from pydantic import BaseModel, Field, field_validator

from omnibase_core.errors.error_codes import ModelCoreErrorCode, ModelOnexError
from omnibase_core.models.common.model_error_context import ModelErrorContext
from omnibase_core.models.common.model_schema_value import ModelSchemaValue

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
            raise ModelOnexError(
                message=msg,
                error_code=ModelCoreErrorCode.VALIDATION_ERROR,
                details=ModelErrorContext.with_context(
                    {
                        "error_type": ModelSchemaValue.from_value("valueerror"),
                        "validation_context": ModelSchemaValue.from_value(
                            "model_validation",
                        ),
                    },
                ),
            )
        return v

    model_config = {
        "extra": "ignore",
        "use_enum_values": False,
        "validate_assignment": True,
    }
